import os
import pandas
from ..tasks.mutemusic import Playlist
from pathlib import Path
from natsort import natsorted
import shutil
import re

STIMULI_PATH  = 'data/mutemusic'

def episode_from_session(session_val: str) -> str:
    """
    Normalize --session into an episode code like 'E01'.
    Accepts '01', 1, or 'E01'.
    """
    s = str(session_val).strip()
    if not s:
        raise ValueError("--session is required (e.g., 01)")

    if s.upper().startswith("E"):
        # Already like 'E01' or 'e1'
        ep = s.upper()
        # Optional sanity: pad if needed (E1 -> E01)
        try:
            n = int(ep[1:])
            return f"E{n:02d}"
        except Exception:
            return ep
    else:
        # '01' or '1' -> 'E01'
        try:
            n = int(s)
            return f"E{n:02d}"
        except Exception:
            # Last resort: treat whatever was passed as suffix
            return f"E{s}"
        
def _parse_blocks_arg(blocks_arg, all_block_ids):
    if not blocks_arg:
        return set(all_block_ids)
    blocks_arg = blocks_arg.strip()
    if "-" in blocks_arg and "," not in blocks_arg:
        a, b = blocks_arg.split("-", 1)
        return set(range(int(a), int(b) + 1))
    if "," in blocks_arg:
        return {int(tok.strip()) for tok in blocks_arg.split(",")}
    return {int(blocks_arg)}

def _block_num_from_dirname(block_dir: Path) -> int:
    # Match pattern like 'B1', 'B1_repeat', 'B1_repeat_1'
    match = re.match(r'^B(\d+)', block_dir.name)
    if match:
        return int(match.group(1))
    raise ValueError(f"Invalid block directory name: {block_dir.name}")


def _results_exist(block_dir: Path) -> bool:
    return any(block_dir.glob("results_*.csv"))

def _prepare_repeat_dir(block_dir: Path) -> Path:

    base_name = block_dir.name
    parent = block_dir.parent

    repeat_name = f"{base_name}_repeat"
    repeat_dir = parent / repeat_name

    #repeat_dir = block_dir.parent / f"{block_dir.name}_repeat"
    #repeat_dir.mkdir(exist_ok=True)

    # If that already exists, increment suffixes: B01_repeat_2, B01_repeat_3, ...
    counter = 2
    while repeat_dir.exists():
        repeat_name = f"{base_name}_repeat_{counter}"
        repeat_dir = parent / repeat_name
        counter += 1

    # Now create the chosen repeat dir
    repeat_dir.mkdir(exist_ok=True)

    for fname in ("plan.csv", "playlist.tsv"):
        src = block_dir / fname
        dst = repeat_dir / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
    return repeat_dir



def get_tasks(parsed):
    sub = f"Sub-{parsed.subject}"
    subj_dir = Path(STIMULI_PATH) / sub
    session_num = episode_from_session(parsed.session)
    session_dir = subj_dir / "episodes" / session_num

    blocks_all = natsorted(session_dir.glob("B*"))
    ids_all = [_block_num_from_dirname(b) for b in blocks_all]
    keep_ids = _parse_blocks_arg(getattr(parsed, "blocks", None), ids_all)
    blocks = [b for b in blocks_all if _block_num_from_dirname(b) in keep_ids]

    if not blocks:
        raise RuntimeError(f"No blocks selected. Available: {ids_all}; requested: {getattr(parsed,'blocks',None)}")

    for block_dir in blocks:
        playlist = block_dir / "playlist.tsv"
        save_dir = _prepare_repeat_dir(block_dir) if _results_exist(block_dir) else block_dir

        yield Playlist(
            tsv_path=str(playlist),
            block_dir=str(save_dir),
            use_eyetracking=True,
            et_calibrate=True,
            name=f"task-mutemusic_{session_num}_{block_dir.name}"
            
        )

"""
def get_tasks(parsed):
    sub = f'Sub-{parsed.subject}'
    subj_dir = Path(STIMULI_PATH) / sub
    sessions_root = subj_dir / "episodes"
    #session_num = 'E01'
    session_num = episode_from_session(parsed.session) 
    #import pdb;pdb.set_trace()
    session_dir = sessions_root / session_num
    if not session_dir.exists():
        raise FileNotFoundError(f"Episode folder not found: {session_dir}")

       
    for block_dir in natsorted(session_dir.glob("B*")):
        # import pdb;pdb.set_trace()
        plan = block_dir / "plan.csv"
        playlist = block_dir / "playlist.tsv"
    
        
        # Ensure we read start/dur from playlist
        # (Playlist itself will read the TSV; we just hand the path)
        
        task = Playlist(
            tsv_path=str(playlist),
            block_dir=str(block_dir),
            use_eyetracking=True,
            et_calibrate=True,  # or only for the first block if you prefer
            name=f"task-mutemusic_{session_dir.name}_{block_dir.name}"
        )
        yield task
        # return  # one block per run
"""