# balanced_tc_block_generator.py
import random
from collections import Counter
from typing import List, Optional, Tuple
import pandas as pd

# ---------- Balanced TC generation ----------

def _balanced_obj_pool(total_slots: int, rng: random.Random) -> List[int]:
    """
    Build a multiset of object labels 0..3 whose counts differ by at most 1.
    """
    base = total_slots // 4
    rem = total_slots % 4
    counts = [base] * 4
    for k in rng.sample([0, 1, 2, 3], rem):
        counts[k] += 1
    pool = [k for k in range(4) for _ in range(counts[k])]
    rng.shuffle(pool)
    return pool

def generate_balanced_unique_tcs(ntcs: int, nobjs: int, seed: Optional[int] = None) -> List[str]:
    """
    Generate `ntcs` UNIQUE task conditions (TCs) with `nobjs` objects each,
    such that the overall counts of obj 0/1/2/3 across ALL TCs are balanced
    (each differs by at most 1).

    TC format: 'l0o0_l1o1_...' e.g. '00_11_01' for nobjs=3.
    """
    if ntcs <= 0 or nobjs <= 0:
        raise ValueError("ntcs and nobjs must be positive.")
    rng = random.Random(seed)

    total_slots = ntcs * nobjs
    obj_pool = _balanced_obj_pool(total_slots, rng)

    tcs: List[str] = []
    used = set()
    idx = 0

    for _ in range(ntcs):
        # take next `nobjs` objs and shuffle their order within the TC
        row_objs = obj_pool[idx:idx + nobjs]
        idx += nobjs
        rng.shuffle(row_objs)

        attempts = 0
        while True:
            locs = [rng.randint(0, 1) for _ in range(nobjs)]
            tc = "_".join(f"{locs[i]}{row_objs[i]}" for i in range(nobjs))
            if tc not in used:
                used.add(tc)
                tcs.append(tc)
                break

            # If collision: nudge (flip a random loc; if still collision, rotate objs)
            attempts += 1
            if attempts > 20:
                j = rng.randrange(nobjs)
                locs[j] ^= 1
                tc = "_".join(f"{locs[i]}{row_objs[i]}" for i in range(nobjs))
                if tc not in used:
                    used.add(tc)
                    tcs.append(tc)
                    break
                row_objs = row_objs[1:] + row_objs[:1]  # rotate and retry
                attempts = 0

    return tcs

# ---------- Trial instantiation ----------

def _parse_tc(tc: str) -> Tuple[List[int], List[int]]:
    tokens = tc.split("_")
    locs, objs = [], []
    for tok in tokens:
        if len(tok) != 2 or not tok.isdigit():
            raise ValueError(f"Bad token '{tok}' in tc '{tc}'")
        loc = int(tok[0]); obj = int(tok[1])
        if loc not in (0,1) or obj not in (0,1,2,3):
            raise ValueError(f"Out-of-range in token '{tok}'")
        locs.append(loc); objs.append(obj)
    return locs, objs

def _ctg_from_obj(obj: int) -> int:
    return 0 if obj <= 1 else 1

def build_block_from_tcs(
    tcs: List[str],
    seed: Optional[int] = None,
    include_tc: bool = True,
    put_tc_last: bool = True,
) -> pd.DataFrame:
    """
    Instantiate each single-TC into a trial row with columns:
      locX, refX, objX, ctgX, angX  (X = 1..nobjs)
    Plus optional 'tc' column.
    Uses rule: refX = objX * 2 + angX ; angX is random.
    """
    if not tcs:
        raise ValueError("Empty tcs list.")
    rng = random.Random(seed)

    # infer number of objects from first tc and validate
    first_locs, first_objs = _parse_tc(tcs[0])
    nobjs = len(first_locs)

    rows = []
    for tc in tcs:
        locs, objs = _parse_tc(tc)
        if len(locs) != nobjs:
            raise ValueError(f"Inconsistent nobjs for tc '{tc}'")
        row = {}
        for i in range(nobjs):
            x = i + 1
            ang = rng.randint(0, 1)
            ref = objs[i] * 2 + ang
            row[f"loc{x}"] = locs[i]
            row[f"obj{x}"] = objs[i]
            row[f"ctg{x}"] = _ctg_from_obj(objs[i])
            row[f"ang{x}"] = ang
            row[f"ref{x}"] = ref
        if include_tc:
            row["tc"] = tc
        rows.append(row)

    # column order
    base = []
    for x in range(1, nobjs + 1):
        base += [f"loc{x}", f"ref{x}", f"obj{x}", f"ctg{x}", f"ang{x}"]
    if include_tc:
        cols = base + (["tc"] if put_tc_last else [])
        if not put_tc_last:
            cols = ["tc"] + base
    else:
        cols = base

    return pd.DataFrame(rows)[cols]

def save_block_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)

# ---------- Quick sanity helpers ----------

def summarize_obj_balance(tcs: List[str]) -> Counter:
    objs = [int(tok[1]) for tc in tcs for tok in tc.split("_")]
    return Counter(objs)

def check_unique_tcs(tcs: List[str]) -> bool:
    return len(tcs) == len(set(tcs))


if __name__ == "__main__":
    # Output dir
    tcs_dir = "/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/ozhan_branch/task_stimuli/data/multfs/trevor/tcs"

    # ntcs variant mapping
    ntcs_variants = {
        "col": 30,
        "lco": 30,
        "loc_ABAB": 7,
        "loc_ABBA": 7,
        "ctg_ABAB": 7,
        "ctg_ABBA": 7,
        "obj_ABAB": 7,
        "obj_ABBA": 7,
    }

    """
    ----- Generate ctxdm col and lco tcs -----
    """
    taskname = "ctxdm"
    variants = ["col", "lco"]

    for variant in variants:
        ntcs = ntcs_variants[variant]
        # Generate balanced unique TCs
        tcs = generate_balanced_unique_tcs(ntcs=ntcs, nobjs=3, seed=0)
        print(f"Generated {len(tcs)} unique TCs for {taskname}-{variant}")
        print("Obj counts:", summarize_obj_balance(tcs))  # should differ by at most 1

        # Instantiate trials
        df = build_block_from_tcs(tcs, seed=0, include_tc=True, put_tc_last=True)
        print(df.head())

        # Save to CSV
        save_block_csv(df, tcs_dir + f"/{taskname}_{variant}_session01.csv")

    """----- Generate interdms tcs (loc, ctg, obj; ABAB and ABBA) -----
    """
    taskname = "interdms"
    variants = ["loc_ABAB", "loc_ABBA", "ctg_ABAB", "ctg_ABBA", "obj_ABAB", "obj_ABBA"]

    for variant in variants:
        ntcs = ntcs_variants[variant]
        # Generate balanced unique TCs
        tcs = generate_balanced_unique_tcs(ntcs=ntcs, nobjs=4, seed=0)
        print(f"Generated {len(tcs)} unique TCs for {taskname}-{variant}")
        print("Obj counts:", summarize_obj_balance(tcs))  # should differ by at most 1

        # Instantiate trials
        df = build_block_from_tcs(tcs, seed=0, include_tc=True, put_tc_last=True)
        print(df.head())

        # Save to CSV
        save_block_csv(df, tcs_dir + f"/{taskname}_{variant}_session01.csv")   
