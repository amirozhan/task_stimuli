#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, random
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}

# ---------------- utils ----------------
def _hash_seed(*parts) -> int:
    h = hashlib.sha256("||".join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16)

def _per_song_rng(global_seed: int, song_key: str) -> random.Random:
    return random.Random(_hash_seed(global_seed, song_key))

def _scan_catalog(root_dir: Path) -> list[dict]:
    """
    Return rows: {stem, path, bucket}. We DO NOT add any suffixes.
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
                    "stem": rel.stem,     # bare stem
                    "path": str(rel),
                    "bucket": bucket,
                })
    if not rows:
        raise ValueError(f"No audio found under {root_dir}/shared or {root_dir}/favorite")
    return rows

def _maybe_probe_duration_seconds(abs_path: Path) -> Optional[float]:
    """Try pydub -> soundfile -> librosa; return None if not available."""
    try:
        from pydub.utils import mediainfo
        info = mediainfo(str(abs_path))
        if info and "duration" in info:
            return float(info["duration"])
    except Exception:
        pass
    try:
        import soundfile as sf
        with sf.SoundFile(str(abs_path)) as f:
            return float(len(f) / f.samplerate)
    except Exception:
        pass
    try:
        import librosa
        return float(librosa.get_duration(path=str(abs_path)))
    except Exception:
        pass
    return None

# ---------------- core ----------------
def _build_segments_for_bucket(
    items: list[dict],
    root: Path,
    *,
    seed: int,
    seg_len: float,
    max_start: float,
    randomize: bool,
    clamp_to_duration: bool,
    use_bare_stem_keys: bool,
) -> Dict[str, Dict[str, float]]:
    cfg: Dict[str, Dict[str, float]] = {}
    for r in items:
        key_for_config = r["stem"] if use_bare_stem_keys else f"{r['stem']}__{r['bucket']}"
        abs_path = (root / r["path"]).resolve()

        if randomize:
            rng = _per_song_rng(seed, key_for_config)  # seed by the key we write
            start = rng.uniform(10.0, max(10.0, float(max_start)))
        else:
            start = 10.0

        length = float(seg_len)

        if clamp_to_duration:
            dur = _maybe_probe_duration_seconds(abs_path)
            if dur is not None:
                if length > dur:
                    length = max(10.0, dur)
                    start = 10.0
                else:
                    latest_start = max(10.0, dur - length)
                    if start > latest_start:
                        start = latest_start

        cfg[key_for_config] = {"start": round(float(start), 3), "len": length}
    return cfg

def generate_segments_json_split(
    root_dir: str,
    out_shared_json: str,
    out_favorite_json: str,
    *,
    seed: int = 1234,
    shared_len: float = 10.0,
    favorite_len: float = 10.0,
    shared_max_start: float = 60.0,
    favorite_max_start: float = 5.0,
    randomize_shared: bool = True,
    randomize_favorite: bool = True,
    clamp_to_duration: bool = True,
    subset_shared: Optional[int] = None,
    subset_favorite: Optional[int] = None,
    use_bare_stem_keys: bool = True,   # <-- NEW default: no suffixes
) -> Tuple[Path, Path]:
    """
    Writes two JSON files (shared & favorite) whose keys are the bare stems by default.
    """
    root = Path(root_dir).resolve()
    items = _scan_catalog(root)

    shared_items = [r for r in items if r["bucket"] == "shared"]
    favorite_items = [r for r in items if r["bucket"] == "favorite"]

    shared_items.sort(key=lambda r: r["stem"])
    favorite_items.sort(key=lambda r: r["stem"])

    if subset_shared is not None:
        if len(shared_items) < subset_shared:
            raise ValueError(f"shared has {len(shared_items)} < requested subset {subset_shared}")
        shared_items = shared_items[:subset_shared]

    if subset_favorite is not None:
        if len(favorite_items) < subset_favorite:
            raise ValueError(f"favorite has {len(favorite_items)} < requested subset {subset_favorite}")
        favorite_items = favorite_items[:subset_favorite]

    shared_cfg = _build_segments_for_bucket(
        shared_items, root,
        seed=seed, seg_len=shared_len, max_start=shared_max_start,
        randomize=randomize_shared, clamp_to_duration=clamp_to_duration,
        use_bare_stem_keys=use_bare_stem_keys,
    )
    favorite_cfg = _build_segments_for_bucket(
        favorite_items, root,
        seed=seed, seg_len=favorite_len, max_start=favorite_max_start,
        randomize=randomize_favorite, clamp_to_duration=clamp_to_duration,
        use_bare_stem_keys=use_bare_stem_keys,
    )

    out_shared = Path(out_shared_json); out_shared.parent.mkdir(parents=True, exist_ok=True)
    out_favorite = Path(out_favorite_json); out_favorite.parent.mkdir(parents=True, exist_ok=True)

    out_shared.write_text(json.dumps(shared_cfg, indent=2, ensure_ascii=False))
    out_favorite.write_text(json.dumps(favorite_cfg, indent=2, ensure_ascii=False))

    print(f"[ok] wrote {len(shared_cfg)} shared entries → {out_shared}")
    print(f"[ok] wrote {len(favorite_cfg)} favorite entries → {out_favorite}")
    return out_shared, out_favorite

main_path = r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic"
sub = "01"

subject_dir = Path(main_path) / f"Sub-{sub}" / "music"
#subject_dir.mkdir(parents=True, exist_ok=True)  # just in case

out_shared   = subject_dir / "segments_shared.json"
out_favorite = subject_dir / "segments_favorite.json"

generate_segments_json_split(
    root_dir=str(subject_dir.resolve()),
    out_shared_json=str(out_shared.resolve()),
    out_favorite_json=str(out_favorite.resolve()),
    seed=42,
    shared_len=30.0,
    favorite_len=30.0,
    shared_max_start=60,
    favorite_max_start=120,
    randomize_shared=True,
    randomize_favorite=True,
    clamp_to_duration=True,
    subset_shared=80,
    subset_favorite=20,
)
print("Wrote:", out_shared, "and", out_favorite)