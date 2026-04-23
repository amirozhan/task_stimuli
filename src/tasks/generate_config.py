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

def _scan_catalog(root_dir: Path, shared_suffix: str, favorite_suffix: str, control_suffix: str) -> list[dict[str, Any]]:
    """
    Return rows: {stem, path, bucket}. We DO NOT add any suffixes.
    """
    rows = []
    for bucket in (f"shared{shared_suffix}",f"favorite{favorite_suffix}",f"control{control_suffix}"):
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
    safety_margin: float = 1.0,
) -> Dict[str, Dict[str, float]]:
    cfg: Dict[str, Dict[str, float]] = {}
    for r in items:
        key_for_config = r["stem"] if use_bare_stem_keys else f"{r['stem']}__{r['bucket']}"
        abs_path = (root / r["path"]).resolve()

        length = float(seg_len)

        # Always probe duration so we can guarantee start+length+margin <= dur
        dur = _maybe_probe_duration_seconds(abs_path) if clamp_to_duration else None
        if clamp_to_duration and dur is None:
            raise RuntimeError(
                f"Could not probe duration for {abs_path}. Install pydub, soundfile, or librosa."
            )

        if clamp_to_duration:
            usable = dur - safety_margin
            if length > usable:
                length = max(1.0, usable)
                latest_start = 0.0
            else:
                latest_start = max(0.0, usable - length)
            min_start = min(10.0, latest_start)
        else:
            latest_start = float(max_start)
            min_start = 10.0

        if randomize:
            rng = _per_song_rng(seed, key_for_config)
            hi = min(float(max_start), latest_start) if clamp_to_duration else float(max_start)
            hi = max(min_start, hi)
            start = rng.uniform(min_start, hi)
        else:
            start = min_start

        # Final hard clamp (defensive)
        if clamp_to_duration:
            start = min(start, latest_start)

        cfg[key_for_config] = {"start": round(float(start), 3), "len": round(float(length), 3)}
    return cfg

def generate_segments_json_split(
    root_dir: str,
    out_shared_json: str,
    out_favorite_json: str,
    out_control_json: Optional[str],
    *,
    seed: int = 1234,
    shared_len: float = 10.0,
    favorite_len: float = 10.0,
    control_len: Optional[float] = 10.0,
    shared_max_start: float = 60.0,
    favorite_max_start: float = 5.0,
    control_max_start: Optional[float] = 60.0,
    randomize_shared: bool = True,
    randomize_favorite: bool = True,
    randomize_control: Optional[bool] = True,
    clamp_to_duration: bool = True,
    subset_shared: Optional[int] = None,
    subset_favorite: Optional[int] = None,
    subset_control: Optional[int] = None,
    shared_stem_suffix: str = "",
    favorite_stem_suffix: str = "",
    control_stem_suffix: str = "",
    use_bare_stem_keys: bool = True, 
) -> Tuple[Path, Path]:
    """
    Writes two JSON files (shared & favorite) whose keys are the bare stems by default.
    """
    root = Path(root_dir).resolve()
    items = _scan_catalog(root, shared_stem_suffix, favorite_stem_suffix, control_stem_suffix)

    shared_items = [r for r in items if r["bucket"] == f"shared{shared_stem_suffix}"]
    favorite_items = [r for r in items if r["bucket"] == f"favorite{favorite_stem_suffix}"]
    control_items = [r for r in items if r["bucket"] == f"control{control_stem_suffix}"]

    shared_items.sort(key=lambda r: r["stem"])
    favorite_items.sort(key=lambda r: r["stem"])
    control_items.sort(key=lambda r: r["stem"])

    if subset_shared is not None:
        if len(shared_items) < subset_shared:
            raise ValueError(f"shared has {len(shared_items)} < requested subset {subset_shared}")
        shared_items = shared_items[:subset_shared]

    if subset_favorite is not None:
        if len(favorite_items) < subset_favorite:
            raise ValueError(f"favorite has {len(favorite_items)} < requested subset {subset_favorite}")
        favorite_items = favorite_items[:subset_favorite]

    if subset_control is not None:
        if len(control_items) < subset_control:
            raise ValueError(f"control has {len(control_items)} < requested subset {subset_control}")
        control_items = control_items[:subset_control]

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

    if out_control_json is not None:
        control_cfg = _build_segments_for_bucket(
            control_items, root,
            seed=seed, seg_len=control_len, max_start=control_max_start,
            randomize=randomize_control, clamp_to_duration=clamp_to_duration,
            use_bare_stem_keys=use_bare_stem_keys,
        )

        out_control = Path(out_control_json); out_control.parent.mkdir(parents=True, exist_ok=True)
        out_control.write_text(json.dumps(control_cfg, indent=2, ensure_ascii=False))
        print(f"[ok] wrote {len(control_cfg)} control entries → {out_control}")

    return out_shared, out_favorite, out_control if out_control_json is not None else None

# main_path = r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic"
# sub = "05"

# subject_dir = Path(main_path) / f"Sub-{sub}" / "music"
# #subject_dir.mkdir(parents=True, exist_ok=True)  # just in case

# out_shared   = subject_dir / "segments_shared.json"
# out_favorite = subject_dir / "segments_favorite.json"

# generate_segments_json_split(
#     root_dir=str(subject_dir.resolve()),
#     out_shared_json=str(out_shared.resolve()),
#     out_favorite_json=str(out_favorite.resolve()),
#     seed=42,
#     shared_len=30.0,
#     favorite_len=30.0,
#     shared_max_start=60,
#     favorite_max_start=120,
#     randomize_shared=True,
#     randomize_favorite=True,
#     clamp_to_duration=True,
#     subset_shared=80,
#     subset_favorite=20,
# )

# main_path = r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic"
main_path = r"C:\\Users\\Lucas\\Desktop\\NACC\\task_stimuli\\data\\mutemusic"
sub = "03"

subject_dir = Path(main_path) / f"Sub-{sub}" / "music"
#subject_dir.mkdir(parents=True, exist_ok=True)  # just in case

out_shared   = subject_dir / "segments_shared_new.json"
out_favorite = subject_dir / "segments_favorite_new.json"
out_control  = subject_dir / "segments_control_lastfm.json"


generate_segments_json_split(
    root_dir=str(subject_dir.resolve()),
    out_shared_json=str(out_shared.resolve()),
    out_control_json=str(out_control.resolve()),
    out_favorite_json=str(out_favorite.resolve()),
    seed=42,
    shared_len=30.0,
    control_len=30.0,
    favorite_len=30.0,
    shared_max_start=90,
    control_max_start=120,
    favorite_max_start=120,
    randomize_shared=True,
    randomize_control=True,
    randomize_favorite=True,
    clamp_to_duration=True,
    subset_shared=30,
    subset_control=10,
    subset_favorite=10,
    shared_stem_suffix="_30_new",
    control_stem_suffix="_lastfm",
    favorite_stem_suffix="_10_new",
)
print("Wrote:", out_shared, "and", out_favorite)