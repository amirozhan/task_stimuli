from __future__ import annotations

from pathlib import Path
import time, random, json, csv, hashlib
import pandas as pd
from typing import Optional, Dict, Any, List

# ---------- CONFIG ----------
AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
CSV_COLS = [
    "subject","episode_id","episode_date","mode",
    "block_id","block_order",
    "song_id","song_dir","song_file","song_relpath",
    "segment_start","segment_len","segment_relpath",
    "is_new","first_seen_episode_id","first_seen_date","first_seen_block_id","first_seen_block_order",
    "played","rating_value","confirmation",
]

# ---------- UTIL ----------
def _ensure(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _hash_seed(*parts) -> int:
    h = hashlib.sha256("||".join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16)

def _abs_path(root: Path, rel_or_abs: str) -> str:
    p = Path(rel_or_abs)
    return str(p if p.is_absolute() else (root / p).resolve())

# ---------- CATALOG (NO SUFFIXES) ----------
def _scan_catalog(root_dir: Path) -> pd.DataFrame:
    """
    Expect root_dir to contain:
      - shared/    (same content for all subjects)
      - favorite/  (subject-specific favorites; must contain >= 20)
    Returns bare-stem song_id (no bucket suffix), bucket, and paths.
    If the same stem exists in both buckets, they will share the same song_id.
    """
    rows = []
    for bucket in ("shared", "favorite"):
        folder = root_dir / bucket
        if not folder.exists():
            continue
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix.lower() in AUDIO_EXT:
                rel = p.relative_to(root_dir)
                rows.append({
                    "song_id": rel.stem,   # always bare stem
                    "path": str(rel),
                    "bucket": bucket,
                })
    if not rows:
        raise ValueError(f"No audio found under {root_dir}/shared or {root_dir}/favorite")

    df = pd.DataFrame(rows)

    # Enrich paths
    pseries = df["path"].apply(Path)
    df["song_dir"]     = pseries.apply(lambda x: str(x.parent))
    df["song_file"]    = pseries.apply(lambda x: x.name)
    df["song_relpath"] = df["path"]
    return df.reset_index(drop=True)

def _select_80_20(catalog: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pick exactly 80 shared + 20 favorite (stable by sorted bare stem)."""
    shared_all   = catalog[catalog.bucket=="shared"].sort_values("song_id").reset_index(drop=True)
    favorite_all = catalog[catalog.bucket=="favorite"].sort_values("song_id").reset_index(drop=True)

    if len(shared_all) < 80:
        raise ValueError(f"Need >=80 shared songs, found {len(shared_all)}")
    if len(favorite_all) < 20:
        raise ValueError(f"Need >=20 favorite songs, found {len(favorite_all)}")

    shared80   = shared_all.iloc[:80].copy()
    favorite20 = favorite_all.iloc[:20].copy()
    return shared80, favorite20

# ---------- SEGMENTS (CONFIG-ONLY) ----------
def _normalize_song_keys(song_id: str) -> list[str]:
    """No suffixes used anywhere; just the bare stem."""
    return [song_id]

def _load_segments_file(path_str: str) -> Dict[str, Dict[str, float]]:
    """Load JSON or CSV into { song_key: {'start': float, 'len': float} }."""
    p = Path(path_str)
    if not p.exists():
        raise FileNotFoundError(f"segments file not found: {path_str}")
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON segments must be an object of {song_key: {start,len}}")
        out = {}
        for k, v in data.items():
            if not isinstance(v, dict) or "len" not in v:
                raise ValueError(f"Bad JSON entry for {k}: needs {{'start': float, 'len': float}}")
            out[k] = {"start": float(v.get("start", 0.0)), "len": float(v["len"])}
        return out
    elif p.suffix.lower() == ".csv":
        out: Dict[str, Dict[str, float]] = {}
        with p.open("r", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            if not {"song_id","start","len"}.issubset({c.strip() for c in rdr.fieldnames or []}):
                raise ValueError("CSV must have headers: song_id,start,len")
            for row in rdr:
                k = row["song_id"].strip()
                out[k] = {"start": float(row["start"]), "len": float(row["len"])}
        return out
    else:
        raise ValueError("segments file must be .json or .csv")

def _segment_lookup_configs_only(
    row: pd.Series,
    *,
    dict_cfg: Optional[Dict[str, Dict[str, float]]],
    shared_cfg: Optional[Dict[str, Dict[str, float]]],
    favorite_cfg: Optional[Dict[str, Dict[str, float]]],
    generic_cfg: Optional[Dict[str, Dict[str, float]]],
) -> tuple[float, float]:
    """
    Strict config-only resolution.
    Precedence:
      1) dict_cfg (in-code)
      2) bucket-specific cfg (shared/favorite)
      3) generic cfg (single file for both)
    If no hit, raise.
    """
    def _try(cfg: Optional[Dict[str, Dict[str, float]]]) -> Optional[tuple[float,float]]:
        if not cfg:
            return None
        for k in _normalize_song_keys(row["song_id"]):
            if k in cfg:
                info = cfg[k]
                return round(float(info.get("start", 0.0)), 3), float(info["len"])
        return None

    hit = _try(dict_cfg)
    if hit is not None:
        return hit

    hit = _try(shared_cfg if row["bucket"] == "shared" else favorite_cfg)
    if hit is not None:
        return hit

    hit = _try(generic_cfg)
    if hit is not None:
        return hit

    raise ValueError(
        f"No segment config for song_id='{row['song_id']}' (bucket={row['bucket']}). "
        f"Tried keys: {_normalize_song_keys(row['song_id'])}"
    )

# ---------- EPISODE TEMPLATE ----------
def _episode_template(n_blocks: int,
                      episode_index: int,
                      n_shared_slots: int = 80,
                      n_favorite_slots: int = 20) -> pd.DataFrame:
    """Global 100-slot template (80 shared / 20 favorite), identical order across subjects per episode."""
    assert n_shared_slots + n_favorite_slots == 100
    base = ["shared"] * n_shared_slots + ["favorite"] * n_favorite_slots

    rng = random.Random(_hash_seed("EPISODE", episode_index))
    idxs = list(range(100))
    rng.shuffle(idxs)
    perm_types = [base[i] for i in idxs]

    rows = []
    block_orders = {b: 0 for b in range(1, n_blocks+1)}
    for pos, slot_type in enumerate(perm_types, start=1):
        b = ((pos - 1) % n_blocks) + 1
        block_orders[b] += 1
        rows.append({
            "slot_idx": pos,
            "slot_type": slot_type,
            "block_id": b,
            "block_order": block_orders[b],
        })
    return pd.DataFrame(rows)

# ---------- MATERIALIZE ----------
def _materialize_episode_for_subject(
    root: Path,
    subject: str,
    episode_id: str,
    episode_date: str,
    mode: str,
    template: pd.DataFrame,
    shared80: pd.DataFrame,
    favorite20: pd.DataFrame,
    dict_cfg: Optional[Dict[str,Any]],
    shared_cfg: Optional[Dict[str,Any]],
    favorite_cfg: Optional[Dict[str,Any]],
    generic_cfg: Optional[Dict[str,Any]],
) -> list[dict]:
    """Fill template with concrete songs; segments come ONLY from configs."""
    rows: List[dict] = []

    ep_seed = _hash_seed("EPORDER", episode_id)
    rng_shared   = random.Random(ep_seed + 101)
    rng_favorite = random.Random(ep_seed + 202)

    shared_idxs   = list(range(len(shared80)));   rng_shared.shuffle(shared_idxs)
    favorite_idxs = list(range(len(favorite20))); rng_favorite.shuffle(favorite_idxs)

    shared_in_ep   = shared80.iloc[shared_idxs].reset_index(drop=True)
    favorite_in_ep = favorite20.iloc[favorite_idxs].reset_index(drop=True)

    sh_ptr, fv_ptr = 0, 0
    first_seen: Dict[str, Dict[str, Any]] = {}

    for _, slot in template.sort_values("slot_idx").iterrows():
        if slot["slot_type"] == "shared":
            r = shared_in_ep.iloc[sh_ptr]; sh_ptr += 1
        else:
            r = favorite_in_ep.iloc[fv_ptr]; fv_ptr += 1

        seg_start, seg_len = _segment_lookup_configs_only(
            r,
            dict_cfg=dict_cfg,
            shared_cfg=shared_cfg,
            favorite_cfg=favorite_cfg,
            generic_cfg=generic_cfg,
        )

        key = r["song_id"]  # bare stem; note: same stem across buckets shares first_seen
        if key not in first_seen:
            first_seen[key] = {
                "first_seen_episode_id": episode_id,
                "first_seen_date": episode_date,
                "first_seen_block_id": int(slot["block_id"]),
                "first_seen_block_order": int(slot["block_order"]),
            }
            is_new = 1
        else:
            is_new = 0
        meta = first_seen[key]

        rows.append({
            "subject": subject,
            "episode_id": episode_id,
            "episode_date": episode_date,
            "mode": mode,
            "block_id": int(slot["block_id"]),
            "block_order": int(slot["block_order"]),
            "song_id": r["song_id"],
            "song_dir": r["song_dir"],
            "song_file": r["song_file"],
            "song_relpath": r["song_relpath"],
            "segment_start": seg_start,
            "segment_len": seg_len,
            "segment_relpath": r["song_relpath"],
            "is_new": int(is_new),
            "first_seen_episode_id": meta["first_seen_episode_id"],
            "first_seen_date": meta["first_seen_date"],
            "first_seen_block_id": int(meta["first_seen_block_id"]),
            "first_seen_block_order": int(meta["first_seen_block_order"]),
            "played": 0,
            "rating_value": "",
            "confirmation": "",
        })
    return rows

# ---------- PUBLIC: PLAN ALL EPISODES (CONFIGS ONLY) ----------
def plan_all_episodes(
    root_dir: str,
    subject: str,
    *,
    n_episodes: int = 5,
    n_blocks: int = 4,
    # ONLY configs; at least one of these must be provided
    segments_dict: Optional[Dict[str, Any]] = None,       # in-code dict
    segments_path: Optional[str] = None,                  # single file for both buckets
    segments_path_shared: Optional[str] = None,           # shared-only file
    segments_path_favorite: Optional[str] = None,         # favorite-only file
    mode: str = "fixed-segments"
) -> list[Path]:
    """
    Creates: root_dir/episodes/EppXX/Bk{1..n_blocks}/{plan.csv, playlist.tsv}
    Uses ONLY configs (no defaults). Precedence:
      segments_dict > (shared|favorite file) > generic file.
    Raises if any of the 80+20 tracks lack a config entry (by bare stem).
    """
    if not (segments_dict or segments_path or segments_path_shared or segments_path_favorite):
        raise ValueError("Config-only mode: provide segments_dict and/or segments_path and/or segments_path_shared/segments_path_favorite.")

    root = Path(root_dir)
    _ensure(root / "episodes")

    catalog = _scan_catalog(root)
    shared80, favorite20 = _select_80_20(catalog)

    dict_cfg = segments_dict if segments_dict else None
    shared_cfg = _load_segments_file(segments_path_shared) if segments_path_shared else None
    favorite_cfg = _load_segments_file(segments_path_favorite) if segments_path_favorite else None
    generic_cfg = _load_segments_file(segments_path) if segments_path else None

    # Fast coverage check so failures are explicit
    def _has_entry(row: pd.Series) -> bool:
        try:
            _segment_lookup_configs_only(
                row,
                dict_cfg=dict_cfg,
                shared_cfg=shared_cfg,
                favorite_cfg=favorite_cfg,
                generic_cfg=generic_cfg,
            )
            return True
        except ValueError:
            return False

    missing = []
    for df in (shared80, favorite20):
        for _, r in df.iterrows():
            if not _has_entry(r):
                missing.append((r["song_id"], r["bucket"], _normalize_song_keys(r["song_id"])))
    if missing:
        lines = "\n".join(f"  - {sid} (bucket={b}) keys tried: {keys}" for sid, b, keys in missing)
        raise ValueError(
            "Config-only mode: some songs have no segment entry.\n"
            f"Add them to the appropriate config(s):\n{lines}"
        )

    episode_date = time.strftime("%Y-%m-%d")
    out_dirs: list[Path] = []

    for e in range(1, n_episodes + 1):
        episode_id = f"E{e:02d}"
        ep_dir = root / "episodes" / episode_id
        _ensure(ep_dir)

        template = _episode_template(n_blocks=n_blocks, episode_index=e)

        rows = _materialize_episode_for_subject(
            root=root,
            subject=subject,
            episode_id=episode_id,
            episode_date=episode_date,
            mode=mode,
            template=template,
            shared80=shared80,
            favorite20=favorite20,
            dict_cfg=dict_cfg,
            shared_cfg=shared_cfg,
            favorite_cfg=favorite_cfg,
            generic_cfg=generic_cfg,
        )

        df = pd.DataFrame(rows, columns=CSV_COLS)
        for b in sorted(df["block_id"].unique()):
            block_dir = ep_dir / f"B{b}"
            _ensure(block_dir)
            block_df = df[df.block_id == b].sort_values("block_order").reset_index(drop=True)
            block_df.to_csv(block_dir / "plan.csv", index=False)

            # Runner playlist
            tsv = block_df[["song_relpath", "segment_start", "segment_len"]].copy()
            tsv.rename(columns={"song_relpath": "path", "segment_start": "start", "segment_len": "dur"}, inplace=True)
            tsv["path"] = tsv["path"].apply(lambda p: _abs_path(root, p))
            tsv[["path", "start", "dur"]].to_csv(block_dir / "playlist.tsv", sep="\t", index=False)

            out_dirs.append(block_dir)

    return out_dirs