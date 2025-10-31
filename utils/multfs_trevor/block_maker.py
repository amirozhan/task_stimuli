# block_maker.py
"""
block_maker.py
---------------
Randomly selects N rows from an input CSV (task block design file)
and saves a new CSV with identical columns.
"""

import pandas as pd
from pathlib import Path
from typing import Optional


def make_block(df: pd.DataFrame, out_path: Path, n_rows: int, seed: Optional[int] = None) -> pd.DataFrame:
    """
    Randomly select n_rows from a given CSV and save to out_path.
    Preserves all columns and their order.
    """
 
    # if requested more rows than available, save the whole dataframe
    if n_rows > len(df):
        df.to_csv(out_path, index=False)
        print(f"[WARN] Requested {n_rows} rows but input has only {len(df)} rows. Saved full file.")
        return df
        

    sampled = df.sample(n=n_rows, replace=False, random_state=seed)
    sampled.to_csv(out_path, index=False)
    print(f"[OK] Selected {n_rows} rows and saved to → '{out_path.name}'")
    return sampled


# ---------------- MAIN ----------------
if __name__ == "__main__":
    # --- CONFIG ---
    # Input task design file
    tcs_dir = Path("/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/ozhan_branch/task_stimuli/data/multfs/updated_cond_file/trevor/tcs")

    # Output file
    blocks_dir = Path("/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/ozhan_branch/task_stimuli/data/multfs/updated_cond_file/trevor/blockfiles")

    session = 1

    # # Number of rows (trials) to sample
    # N = 14

    # # Random seed (for reproducibility)
    # SEED = 42

    #     # --- RUN ---
    # make_block(in_csv, out_csv, N, seed=SEED)

    # Task block map
    block_map = {
        'ctxdm_col': 2, # blocks per session
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
    """
    ----- Make ctxdm col and lco blocks -----
    """
    taskname = "ctxdm"
    variants = ["col", "lco"]

    for variant in variants:
        n_blocks = block_map[f"{taskname}_{variant}"]
        in_csv = tcs_dir / f"{taskname}_{variant}_session0{session}.csv"
        df = pd.read_csv(in_csv)

        n_trials_per_block = len(df) // n_blocks

        for b in range(1, n_blocks + 1):
            out_csv = blocks_dir / f"{taskname}_{variant}_block{b:02d}_block_{b-1}.csv"
            make_block(df, out_csv, n_rows=n_trials_per_block, seed=0 + b)

    # """
    # ----- Make interdms blocks (loc, ctg, obj; ABAB and ABBA) -----
    # """
    # taskname = "interdms"
    # variants = ["loc_ABAB", "loc_ABBA", "ctg_ABAB", "ctg_ABBA", "obj_ABAB", "obj_ABBA"]

    # for variant in variants:
    #     n_blocks = block_map[f"{taskname}_{variant}"]
    #     in_csv = tcs_dir / f"{taskname}_{variant}_session0{session}.csv"
    #     df = pd.read_csv(in_csv)

    #     n_trials_per_block = len(df) // n_blocks

    #     for b in range(1, n_blocks + 1):
    #         out_csv = blocks_dir / f"{taskname}_{variant}_block{b:02d}_session0{session}.csv"
    #         make_block(in_csv, out_csv, n_rows=n_trials_per_block, seed=100 + b)    


