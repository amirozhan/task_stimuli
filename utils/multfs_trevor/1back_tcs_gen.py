# oneback_block_generator_ref_from_obj_ang.py
# Generate minimal 1-back trials (length 6) covering a requested number of unique ordered pairs.
# Columns per position X=1..seq_len: locX, refX, objX, ctgX, angX
# angX is random; obj/loc from the node chain; refX = objX*2 + angX

from typing import List, Optional
from math import ceil
import random
import pandas as pd

# -------------------- core combinatorics --------------------

def _debruijn_indices(k: int, n: int) -> List[int]:
    """de Bruijn sequence indices for alphabet size k and subsequences of length n."""
    a = [0] * (k * n)
    seq = []
    def db(t, p):
        if t > n:
            if n % p == 0:
                seq.extend(a[1:p+1])
        else:
            a[t] = a[t - p]
            db(t + 1, p)
            for j in range(a[t - p] + 1, k):
                a[t] = j
                db(t + 1, t)
    db(1, 1)
    return seq  # length k**n

def _symbols8() -> List[str]:
    # 8 symbols = two-digit strings "lo": "00","01","02","03","10","11","12","13"
    return [f"{loc}{obj}" for loc in (0, 1) for obj in (0, 1, 2, 3)]

def _build_trials_min_for_pairs(ntcs: int, seq_len: int = 6, seed: Optional[int] = None) -> List[List[str]]:
    """
    Build the minimal number of trials (each with seq_len nodes) whose consecutive pairs
    cover at least ntcs unique ordered pairs (no pair repeats across all trials).
    """
    assert 5 <= ntcs <= 64, "ntcs must be in [5, 64]"
    assert seq_len >= 2, "seq_len must be >= 2"
    pairs_per_trial = seq_len - 1
    n_trials = ceil(ntcs / pairs_per_trial)

    symbols = _symbols8()                         # 8 symbols
    cyc_idx = _debruijn_indices(k=len(symbols), n=2)  # 64 indices (pairs cover all 8x8 once)
    # Rotate by seed for variety
    if seed is not None:
        r = seed % len(cyc_idx)
        cyc_idx = cyc_idx[r:] + cyc_idx[:r]

    # Turn into cyclic node list (close the cycle)
    cycle_nodes = [symbols[i] for i in cyc_idx] + [symbols[cyc_idx[0]]]

    # Non-overlapping chunks of 5 edges => 6 nodes per trial
    trials: List[List[str]] = []
    edge_pos = 0
    for _ in range(n_trials):
        start = edge_pos
        end = edge_pos + (seq_len - 1)  # inclusive node index
        trials.append(cycle_nodes[start:end + 1])
        edge_pos += (seq_len - 1)

    return trials

# -------------------- task design helpers --------------------

def _ctg_from_obj(obj: int) -> int:
    # obj 0-1 -> ctg 0; obj 2-3 -> ctg 1
    return 0 if obj <= 1 else 1

def _symbol_to_loc_obj(sym: str):
    # "01" -> (0,1)
    if len(sym) != 2 or not sym.isdigit():
        raise ValueError(f"Bad symbol '{sym}' (expected two digits 'lo')")
    loc = int(sym[0]); obj = int(sym[1])
    if loc not in (0, 1) or obj not in (0, 1, 2, 3):
        raise ValueError(f"Out-of-range symbol '{sym}'")
    return loc, obj

# -------------------- public API --------------------

def generate_oneback_block(
    ntcs: int,
    seq_len: int = 6,
    seed: Optional[int] = None,
    include_chain_col: bool = True,
) -> pd.DataFrame:
    """
    Generate a 1-back block with the minimal number of trials (rows) to cover at least `ntcs` unique ordered pairs.
    Each trial has `seq_len` nodes (default 6 -> 5 pairs per trial).

    Columns per position X=1..seq_len:
        locX, refX, objX, ctgX, angX
    Plus optional:
        tc_nodes: '00_13_11_00_01_10'
        tc_pairs: '00_13,13_11,11_00,00_01,01_10'

    Rules:
        - locX,objX from the node chain
        - ctgX from objX (0-1 -> 0; 2-3 -> 1)
        - angX is random in {0,1}
        - refX = objX * 2 + angX   (your updated rule)
    """
    rng = random.Random(seed)
    trials = _build_trials_min_for_pairs(ntcs=ntcs, seq_len=seq_len, seed=seed)

    rows = []
    for nodes in trials:
        row = {}
        for i, sym in enumerate(nodes, start=1):
            loc, obj = _symbol_to_loc_obj(sym)
            ang = rng.randint(0, 1)              # random angle
            ref = obj * 2 + ang                  # derived from (obj, ang)
            row[f"loc{i}"] = loc
            row[f"obj{i}"] = obj
            row[f"ctg{i}"] = _ctg_from_obj(obj)
            row[f"ang{i}"] = ang
            row[f"ref{i}"] = ref

        if include_chain_col:
            pairs = [f"{nodes[j]}_{nodes[j+1]}" for j in range(len(nodes)-1)]
            row["tc"] = ",".join(pairs)

        rows.append(row)

    # Column order: group by position
    base_cols = []
    for i in range(1, seq_len + 1):
        base_cols += [f"loc{i}", f"ref{i}", f"obj{i}", f"ctg{i}", f"ang{i}"]
    if include_chain_col:
        base_cols += ["tc"]

    df = pd.DataFrame(rows)[base_cols]
    return df

# --- Sanity utilities ---

from typing import List, Tuple, Dict, Any
from collections import Counter

def _pairs_from_nodes(nodes: List[str]) -> List[str]:
    """['00','13','11'] -> ['00_13','13_11']"""
    return [f"{nodes[i]}_{nodes[i+1]}" for i in range(len(nodes)-1)]

def _nodes_from_df_row(row, seq_len: int) -> List[str]:
    """
    Rebuild the node chain for one trial (row) as two-digit strings 'lo'.
    Uses 'tc_nodes' when present; otherwise reconstructs from locX/objX.
    """
    if "tc_nodes" in row and isinstance(row["tc_nodes"], str) and row["tc_nodes"]:
        return row["tc_nodes"].split("_")

    nodes = []
    for i in range(1, seq_len + 1):
        loc = int(row[f"loc{i}"])
        obj = int(row[f"obj{i}"])
        nodes.append(f"{loc}{obj}")
    return nodes

def _extract_trials_from_df(df) -> List[List[str]]:
    """
    Returns a list of trials, where each trial is a list of node strings (e.g. ['00','13','11','00','01','10']).
    Infers seq_len from the DataFrame.
    """
    # infer seq_len by counting how many loc* columns
    seq_len = max(
        int(col[3:])  # from 'locX'
        for col in df.columns
        if col.startswith("loc")
    )
    trials = []
    for _, row in df.iterrows():
        trials.append(_nodes_from_df_row(row, seq_len))
    return trials

def sanity_check_oneback_trials(df) -> Dict[str, Any]:
    """
    Checks two properties:
      1) No tc (ordered pair) repeats anywhere (within/across trials).
      2) Within each trial, consecutive pairs share the touching stimulus (WX_YZ, YZ_AB, ...).

    Returns a report dict. Raises no exceptions—so you can print/report gracefully.
    """
    trials = _extract_trials_from_df(df)

    # 1) No repeats across all trials
    all_pairs = []
    per_trial_pairs = []
    for t in trials:
        pairs = _pairs_from_nodes(t)
        per_trial_pairs.append(pairs)
        all_pairs.extend(pairs)

    pair_counts = Counter(all_pairs)
    repeated_pairs = {p: c for p, c in pair_counts.items() if c > 1}

    # 2) Adjacency within each trial
    adjacency_violations: List[Tuple[int, int, str, str]] = []  # (trial_idx, j, p_j, p_j+1)
    for ti, pairs in enumerate(per_trial_pairs):
        for j in range(len(pairs) - 1):
            left = pairs[j].split("_")
            right = pairs[j + 1].split("_")
            if left[1] != right[0]:
                adjacency_violations.append((ti, j, pairs[j], pairs[j + 1]))

    ok_no_repeats = len(repeated_pairs) == 0
    ok_adjacency = len(adjacency_violations) == 0

    return {
        "ok": ok_no_repeats and ok_adjacency,
        "ok_no_repeats": ok_no_repeats,
        "ok_adjacency": ok_adjacency,
        "repeated_pairs": repeated_pairs,           # dict like {'00_13': 2, ...}
        "adjacency_violations": adjacency_violations,  # list of (trial_idx, pos, pair_j, pair_j+1)
        "n_trials": len(trials),
        "n_unique_pairs": len(pair_counts),
    }

def save_block_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)

if __name__ == "__main__":
    # Output dir
    tcs_dir = "/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/ozhan_branch/task_stimuli/data/multfs/updated_cond_file/trevor/tcs"

    """
    ----- Generate 1back block with 60 unique pairs for 1back-loc -----
    """
    df_1back_loc = generate_oneback_block(ntcs=60, seq_len=6, seed=0, include_chain_col=True)

    # Run sanity checks
    report_1back_loc = sanity_check_oneback_trials(df_1back_loc)
    print("Sanity OK for 1back_loc:", report_1back_loc["ok"])
    print("Unique pairs covered for 1back_loc:", report_1back_loc["n_unique_pairs"])
    
    # Save to CSV
    save_block_csv(df_1back_loc, tcs_dir + "/1back_loc_all_trials.csv")

    """
    ----- Generate 1back block with 30 unique pairs for 1back-ctg -----
    """
    df_1back_ctg = generate_oneback_block(ntcs=60, seq_len=6, seed=1, include_chain_col=True)

    # Run sanity checks
    report_1back_ctg = sanity_check_oneback_trials(df_1back_ctg)
    print("Sanity OK for 1back_ctg:", report_1back_ctg["ok"])
    print("Unique pairs covered for 1back_ctg:", report_1back_ctg["n_unique_pairs"])    

    # Save to CSV
    save_block_csv(df_1back_ctg, tcs_dir + "/1back_ctg_all_trials.csv")    

    """
    ----- Generate 1back block with 15 unique pairs for 1back-obj -----
    """
    df_1back_obj = generate_oneback_block(ntcs=60, seq_len=6, seed=2, include_chain_col=True)

    # Run sanity checks
    report_1back_obj = sanity_check_oneback_trials(df_1back_obj)
    print("Sanity OK for 1back_obj:", report_1back_obj["ok"])
    print("Unique pairs covered for 1back_obj:", report_1back_obj["n_unique_pairs"])    

    # Save to CSV
    save_block_csv(df_1back_obj, tcs_dir + "/1back_obj_all_trials.csv")