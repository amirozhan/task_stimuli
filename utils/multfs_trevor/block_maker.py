# block_maker.py
"""
block_maker.py
---------------
Randomly partitions a task CSV into N disjoint blocks (no overlap) and
saves each block as a new CSV with identical columns.
"""

import pandas as pd
from pathlib import Path
import os
from typing import Optional, List


def partition_df_into_blocks(df: pd.DataFrame, n_blocks: int, seed: Optional[int] = None) -> List[pd.DataFrame]:
    """
    Randomly shuffle the dataframe once (reproducibly with `seed`) and split into
    `n_blocks` disjoint chunks whose sizes differ by at most 1.
    Returns a list of DataFrames (one per block), preserving column order.
    """
    if n_blocks <= 0:
        raise ValueError("n_blocks must be >= 1")
    if n_blocks > len(df):
        # Each block gets at most 1 row; some blocks will be empty
        print(f"[WARN] n_blocks ({n_blocks}) > number of rows ({len(df)}). Some blocks will be empty.")

    shuffled = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    n = len(shuffled)
    base = n // n_blocks
    rem = n % n_blocks  # first `rem` blocks get one extra row

    blocks = []
    start = 0
    for b in range(n_blocks):
        size = base + (1 if b < rem else 0)
        end = start + size
        blocks.append(shuffled.iloc[start:end].copy())
        start = end
    return blocks

# ---------------- MAIN ----------------
if __name__ == "__main__":
    # --- CONFIG ---
    tcs_dir = Path("/Users/lucasgomez/Desktop/Neuro/Bashivan/MGH_NACC+MULTFS/MULTFS/task_stimuli/data/multfs/trevor/tcs")
    blocks_dir = Path("/Users/lucasgomez/Desktop/Neuro/Bashivan/MGH_NACC+MULTFS/MULTFS/task_stimuli/data/multfs/trevor/blockfiles")
    blocks_dir.mkdir(parents=True, exist_ok=True)

    session = 2
    seed = 1  # used to shuffle/partition per task

    # How many blocks per session per task
    block_map = {
        'ctxdm_col': 2,  # blocks per session
        'ctxdm_lco': 2,
        'interdms_loc_ABAB': 1,
        'interdms_loc_ABBA': 1,
        'interdms_ctg_ABAB': 1,
        'interdms_ctg_ABBA': 1,
        'interdms_obj_ABAB': 1,
        'interdms_obj_ABBA': 1,
        '1back_loc': 1,
        '1back_ctg': 1,
        '1back_obj': 1,
    }

    # ----- Make blocks for all tasks in block_map -----
    for task, n_blocks in block_map.items():
        if '1back' in task:
            in_csv = tcs_dir / f"{task}_session0{session}.csv"
        else:
            in_csv = tcs_dir / f"{task}.csv"
        if not in_csv.exists():
            print(f"[SKIP] Missing input: {in_csv}")
            continue

        df = pd.read_csv(in_csv)
        blocks = partition_df_into_blocks(df, n_blocks=n_blocks, seed=seed)

        # Save each block; no overlap between them
        for idx, df_block in enumerate(blocks):
            os.makedirs(blocks_dir / f"session0{session}", exist_ok=True)
            out_csv = blocks_dir / f"session0{session}" / f"{task}_block_{idx}.csv"   # e.g., ctxdm_col_block0.csv, ctxdm_col_block1.csv
            df_block.to_csv(out_csv, index=False)
            print(f"[OK] {task}: wrote block {idx} with {len(df_block)} rows → {out_csv.name}")