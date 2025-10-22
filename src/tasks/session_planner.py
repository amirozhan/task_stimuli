from __future__ import annotations

from pathlib import Path
import time, random, hashlib, json
import pandas as pd
from typing import Optional, Dict, Any

# ---------- CONFIG ----------
AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
CSV_COLS = [
    "subject","session_id","session_date","mode",
    "block_id","block_order",
    "song_id","song_dir","song_file","song_relpath",
    "segment_start","segment_len","segment_relpath",
    "is_new","first_seen_session_id","first_seen_date","first_seen_block_id","first_seen_block_order",
    "played","rating_value","confirmation",
]

def _ensure(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _hash_seed(*parts) -> int:
    h = hashlib.sha256("||".join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16)

def _scan_catalog(root_dir: Path) -> pd.DataFrame:
    """
    Build a simple catalog from root_dir with subfolders 'shared' and 'favorite'.
    Columns: song_id, path (relative), bucket ('shared'|'favorite'), song_dir, song_file, song_relpath
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
                    "song_id": rel.stem,  # filename without extension
                    "path": str(rel),
                    "bucket": bucket,
                })
    if not rows:
        raise ValueError(f"No audio found under {root_dir}/shared or {root_dir}/favorite")

    df = pd.DataFrame(rows)

    # Deduplicate stems: if same stem in both buckets, tag with bucket suffix.
    dup = df.duplicated("song_id", keep=False)
    if dup.any():
        df.loc[dup, "song_id"] = df.loc[dup].apply(
            lambda r: f"{r['song_id']}__{r['bucket']}", axis=1
        )

    # Enrich paths
    pseries = df["path"].apply(Path)
    df["song_dir"]     = pseries.apply(lambda x: str(x.parent))
    df["song_file"]    = pseries.apply(lambda x: x.name)
    df["song_relpath"] = df["path"]

    return df.reset_index(drop=True)

def _distribute_blocks(catalog: pd.DataFrame, n_blocks: int) -> pd.DataFrame:
    """
    Round-robin assignment into n_blocks (stable across runs).
    Returns rows: song_id, block_id, base_order
    """
    rows = []
    ordered = pd.concat(
        [catalog[catalog["bucket"] == "shared"],
         catalog[catalog["bucket"] == "favorite"]],
        ignore_index=True
    )
    for i, (_, r) in enumerate(ordered.iterrows(), start=0):
        b = (i % n_blocks) + 1
        rows.append({"song_id": r["song_id"], "block_id": b, "base_order": i})
    return pd.DataFrame(rows)

def _session_shuffle(block_df: pd.DataFrame, session_seed: int) -> pd.DataFrame:
    """
    Deterministically shuffle order within each block using session_seed.
    """
    rng = random.Random(session_seed)
    out = []
    for b in sorted(block_df["block_id"].unique()):
        chunk = block_df[block_df.block_id == b].copy()
        idxs = list(chunk.index)
        rng.shuffle(idxs)
        chunk = chunk.loc[idxs].reset_index(drop=True)
        chunk["session_order"] = range(1, len(chunk) + 1)
        out.append(chunk)
    return pd.concat(out, ignore_index=True)

def _abs_path(root: Path, rel_or_abs: str) -> str:
    p = Path(rel_or_abs)
    return str(p if p.is_absolute() else (root / p).resolve())

def _load_segments_json(root_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Try to load root_dir/segments.json with structure:
    {
      "song_id": {"start": float, "len": float}, ...
    }
    song_id must match the catalog song_id (after any bucket tagging).
    """
    path = root_dir / "segments.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print("[plan] segments.json ignored: root is not an object")
            return None
        return data
    except Exception as e:
        print(f"[plan] segments.json ignored (load error): {e}")
        return None

def _rows_for_block(
    songs: pd.DataFrame,
    cat: pd.DataFrame,
    *,
    subject: str,
    session_id: str,
    session_date: str,
    mode: str,
    shared_segment_start: float,
    shared_segment_len: float,
    favorite_segment_len: float,
    first_seen: Dict[str, Dict[str, Any]],
    block_id: int,
    song_segments: Optional[Dict[str, Any]] = None
) -> list[dict]:
    rows = []
    for order, (_, s) in enumerate(songs.iterrows(), start=1):
        r = cat[cat.song_id == s.song_id].iloc[0]
        key = r["song_id"]

        # Determine segment policy
        if r["bucket"] == "shared":
            if song_segments and key in song_segments and isinstance(song_segments[key], dict):
                seg_info = song_segments[key]
                # Fallback to globals if missing keys
                seg_start = float(seg_info.get("start", shared_segment_start))
                seg_len   = float(seg_info.get("len",   shared_segment_len))
            else:
                seg_start = float(shared_segment_start)
                seg_len   = float(shared_segment_len)
        else:
            seg_start = 0.0
            seg_len   = float(favorite_segment_len)

        # First-seen bookkeeping
        if key not in first_seen:
            first_seen[key] = {
                "first_seen_session_id": session_id,
                "first_seen_date": session_date,
                "first_seen_block_id": block_id,
                "first_seen_block_order": order,
            }
            is_new = 1
        else:
            is_new = 0
        meta = first_seen[key]

        rows.append({
            "subject": subject,
            "session_id": session_id,
            "session_date": session_date,
            "mode": mode,
            "block_id": int(block_id),
            "block_order": int(order),
            "song_id": r["song_id"],
            "song_dir": r["song_dir"],
            "song_file": r["song_file"],
            "song_relpath": r["song_relpath"],
            "segment_start": round(seg_start, 3),
            "segment_len": seg_len,
            "segment_relpath": r["song_relpath"],
            "is_new": int(is_new),
            "first_seen_session_id": meta["first_seen_session_id"],
            "first_seen_date": meta["first_seen_date"],
            "first_seen_block_id": int(meta["first_seen_block_id"]),
            "first_seen_block_order": int(meta["first_seen_block_order"]),
            "played": 0,
            "rating_value": "",
            "confirmation": "",
        })
    return rows

def plan_all_sessions(
    root_dir: str,
    subject: str,
    *,
    n_sessions: int = 10,
    n_blocks: int = 4,
    shared_segment_start: float = 30.0,
    shared_segment_len: float = 10.0,
    segment_len: float = 10.0,         # for favorite/
    mode: str = "fixed-segments"       # label only; runner ignores this
) -> list[Path]:
    """
    Layout:
      root_dir/
        shared/     <-- fixed or per-song (via segments.json) segments
        favorite/   <-- plays from t=0 for a fixed duration

    Creates:
      root_dir/sessions/Sxx/Bk/{plan.csv, playlist.tsv}
    """
    root = Path(root_dir)
    _ensure(root / "sessions")

    catalog = _scan_catalog(root)
    block_map = _distribute_blocks(catalog, n_blocks=n_blocks)

    # Optional per-song overrides
    song_segments = _load_segments_json(root)
    if song_segments:
        print(f"[plan] Using segments.json overrides for {len(song_segments)} song(s) in 'shared/' (where keys match song_id).")

    session_date = time.strftime("%Y-%m-%d")
    first_seen: Dict[str, Dict[str, Any]] = {}

    out_dirs: list[Path] = []
    for s in range(1, n_sessions + 1):
        session_id = f"S{s:02d}"
        sess_dir = root / "sessions" / session_id
        _ensure(sess_dir)

        # Deterministic shuffle within blocks per session
        sess_seed = _hash_seed(subject, session_id, "order")
        shuffled = _session_shuffle(block_map, sess_seed)

        for b in sorted(shuffled["block_id"].unique()):
            this_block = shuffled[shuffled.block_id == b].copy()
            songs = this_block.merge(catalog, on="song_id", how="left")

            rows = _rows_for_block(
                songs[["song_id"]],
                catalog,
                subject=subject,
                session_id=session_id,
                session_date=session_date,
                mode=mode,
                shared_segment_start=shared_segment_start,
                shared_segment_len=shared_segment_len,
                favorite_segment_len=segment_len,
                first_seen=first_seen,
                block_id=b,
                song_segments=song_segments,
            )

            block_dir = sess_dir / f"B{b}"
            _ensure(block_dir)

            plan_df = pd.DataFrame(rows, columns=CSV_COLS)
            plan_df.to_csv(block_dir / "plan.csv", index=False)

            # Runner playlist: absolute path + start/dur
            tsv = plan_df[["song_relpath", "segment_start", "segment_len"]].copy()
            tsv.rename(columns={"song_relpath": "path", "segment_start": "start", "segment_len": "dur"}, inplace=True)
            tsv["path"] = tsv["path"].apply(lambda p: _abs_path(root, p))
            tsv[["path", "start", "dur"]].to_csv(block_dir / "playlist.tsv", sep="\t", index=False)

            out_dirs.append(block_dir)

    return out_dirs
