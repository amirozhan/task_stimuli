# session_planner.py
from pathlib import Path
import time, random
import pandas as pd

CSV_COLS = [
    "subject","session_id","session_date","mode",
    "block_id","block_order",
    "song_id","song_dir","song_file","song_relpath",
    "segment_start","segment_len","segment_relpath",
    "is_new","first_seen_session_id","first_seen_date","first_seen_block_id","first_seen_block_order",
    "played","rating_value","confirmation",
]

def _ensure(p: Path): p.mkdir(parents=True, exist_ok=True)

def load_catalog(subject_dir: Path) -> pd.DataFrame:
    """catalog.tsv columns: song_id, path, duration_sec"""
    df = pd.read_csv(subject_dir / "catalog.tsv", sep="\t")
    need = {"song_id","path","duration_sec"}
    if not need.issubset(df.columns):
        raise ValueError(f"catalog.tsv must have columns {need}")
    p = df["path"].apply(Path)
    df["song_dir"]   = p.apply(lambda x: str(x.parent))
    df["song_file"]  = p.apply(lambda x: x.name)
    df["song_relpath"] = p.apply(lambda x: str(x))
    return df

def build_blocks(catalog: pd.DataFrame, n_blocks=4, seed=0) -> pd.DataFrame:
    """Greedy duration balancing -> multiple songs per block."""
    df = catalog.sample(frac=1, random_state=seed).reset_index(drop=True)
    totals = [0.0]*n_blocks
    bins = [[] for _ in range(n_blocks)]
    for _, r in df.iterrows():
        k = min(range(n_blocks), key=lambda i: totals[i])
        bins[k].append(r)
        totals[k] += float(r["duration_sec"] or 0.0)
    rows = []
    for b, chunk in enumerate(bins, start=1):
        for order, r in enumerate(chunk, start=1):
            rows.append({"song_id": r["song_id"], "block_id": b, "block_order": order})
    return pd.DataFrame(rows)

def _pick_start(duration, seg_len, used, rng: random.Random):
    if duration <= seg_len:
        return 0.0
    for _ in range(200):
        s = rng.uniform(0.0, max(0.0, duration - seg_len))
        # avoid overlapping earlier segments for this song
        if all(not (s < u+seg_len and u < s+seg_len) for u in used):
            return s
    # fallback if we fail to find a gap
    return 0.0

def _first_seen_index(subject_dir: Path) -> pd.DataFrame:
    """Scan previous results.csv files to map (song_id, start, len) -> first seen metadata."""
    rows = []
    sess_root = subject_dir / "sessions"
    if not sess_root.exists():
        return pd.DataFrame(columns=["song_id","segment_start","segment_len",
                                     "first_seen_session_id","first_seen_date",
                                     "first_seen_block_id","first_seen_block_order"])
    for sdir in sess_root.iterdir():
        if not sdir.is_dir(): continue
        sid = sdir.name
        for bdir in sdir.iterdir():
            if not bdir.is_dir(): continue
            f = bdir / "results.csv"
            if not f.exists(): continue
            df = pd.read_csv(f)
            for _, r in df.iterrows():
                rows.append({
                    "song_id": r.get("song_id"),
                    "segment_start": float(r.get("segment_start", 0.0)),
                    "segment_len": float(r.get("segment_len", 0.0)),
                    "first_seen_session_id": r.get("first_seen_session_id", sid),
                    "first_seen_date": r.get("first_seen_date", r.get("session_date","")),
                    "first_seen_block_id": int(r.get("first_seen_block_id", r.get("block_id", 0))),
                    "first_seen_block_order": int(r.get("first_seen_block_order", r.get("block_order", 0))),
                })
    if not rows:
        return pd.DataFrame(columns=["song_id","segment_start","segment_len",
                                     "first_seen_session_id","first_seen_date",
                                     "first_seen_block_id","first_seen_block_order"])
    idx = (pd.DataFrame(rows)
             .sort_values(["first_seen_date","first_seen_session_id"])
             .drop_duplicates(["song_id","segment_start","segment_len"], keep="first"))
    return idx

def plan_session(subject_dir: str, subject: str, session_id: str,
                 mode: str = "new", segment_len: float = 10.0,
                 n_blocks: int = 4, seed: int | None = None,
                 blocks_per_session: int | None = None):
    """
    Creates per-session/per-block:
      sessions/<session_id>/B<k>/plan.csv
      sessions/<session_id>/B<k>/playlist.tsv   (columns: path, start, dur)
    Returns: list of block directories (Path objects).
    """
    subject_dir = Path(subject_dir)
    _ensure(subject_dir / "sessions" / session_id)

    catalog = load_catalog(subject_dir)
    blocks = build_blocks(catalog, n_blocks=n_blocks, seed=0)  # stable split per subject

    # choose which blocks to run this session
    all_block_ids = sorted(blocks["block_id"].unique())
    if blocks_per_session:
        rng_sel = random.Random((seed or 0) + 1337)
        rng_sel.shuffle(all_block_ids)
        block_ids = all_block_ids[:blocks_per_session]
    else:
        block_ids = all_block_ids

    session_date = time.strftime("%Y-%m-%d")
    rng = random.Random(seed if seed is not None else (hash((subject, session_id)) & 0xffffffff))
    first_idx = _first_seen_index(subject_dir)

    out_dirs = []

    for b_id in block_ids:
        songs = blocks[blocks.block_id == b_id].merge(catalog, on="song_id", how="left").copy()
        rows = []
        for order, (_, row) in enumerate(songs.iterrows(), start=1):
            duration_sec = float(row.duration_sec or 0.0)

            if mode == "repeat":
                prevs = first_idx[first_idx.song_id.eq(row.song_id)]
                if len(prevs):
                    pr = prevs.iloc[0]  # reuse an already-seen segment for this song
                    start = float(pr["segment_start"])
                    is_new = 0
                    first_meta = pr
                else:
                    start = _pick_start(duration_sec, segment_len, [], rng)
                    is_new = 1
                    first_meta = {
                        "first_seen_session_id": session_id,
                        "first_seen_date": session_date,
                        "first_seen_block_id": b_id,
                        "first_seen_block_order": order
                    }
            else:
                past = []
                if not first_idx.empty:
                    past = first_idx[first_idx.song_id.eq(row.song_id)]["segment_start"].astype(float).tolist()
                start = _pick_start(duration_sec, segment_len, past, rng)
                is_new = 1
                first_meta = {
                    "first_seen_session_id": session_id,
                    "first_seen_date": session_date,
                    "first_seen_block_id": b_id,
                    "first_seen_block_order": order
                }

            # No pre-slicing. We keep original song path and planned snippet times.
            # For traceability we copy song_relpath into segment_relpath.
            rows.append({
                "subject": subject,
                "session_id": session_id,
                "session_date": session_date,
                "mode": mode,
                "block_id": int(b_id),
                "block_order": int(order),
                "song_id": row["song_id"],
                "song_dir": row["song_dir"],
                "song_file": row["song_file"],
                "song_relpath": row["song_relpath"],
                "segment_start": round(float(start), 3),
                "segment_len": float(segment_len),
                "segment_relpath": row["song_relpath"],
                "is_new": int(is_new),
                "first_seen_session_id": first_meta["first_seen_session_id"],
                "first_seen_date": first_meta["first_seen_date"],
                "first_seen_block_id": int(first_meta["first_seen_block_id"]),
                "first_seen_block_order": int(first_meta["first_seen_block_order"]),
                "played": 0,
                "rating_value": "",
                "confirmation": "",
            })

        block_dir = subject_dir / "sessions" / session_id / f"B{b_id}"
        _ensure(block_dir)
        plan_df = pd.DataFrame(rows, columns=CSV_COLS)
        plan_df.to_csv(block_dir / "plan.csv", index=False)

        # Build playlist.tsv for the runner: path, start, dur (dur = segment_len)
        def _abs_path(rel_or_abs: str) -> str:
            p = Path(rel_or_abs)
            return str(p if p.is_absolute() else (subject_dir / p))

        tsv = plan_df[["song_relpath","segment_start","segment_len"]].copy()
        tsv.rename(columns={"song_relpath":"path","segment_start":"start","segment_len":"dur"}, inplace=True)
        tsv["path"] = tsv["path"].apply(_abs_path)
        tsv[["path","start","dur"]].to_csv(block_dir / "playlist.tsv", sep="\t", index=False)

        out_dirs.append(block_dir)

    return out_dirs
