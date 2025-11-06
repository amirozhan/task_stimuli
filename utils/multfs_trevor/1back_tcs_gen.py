# oneback_sessions_generator.py
from typing import List, Optional, Tuple, Dict
from collections import Counter
import random
import pandas as pd

# ---------------- de Bruijn utilities ----------------

def _debruijn_indices(k: int, n: int) -> List[int]:
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
    return [f"{loc}{obj}" for loc in (0, 1) for obj in (0, 1, 2, 3)]

def _symbol_to_loc_obj(sym: str) -> Tuple[int, int]:
    return int(sym[0]), int(sym[1])

def _ctg_from_obj(obj: int) -> int:
    return 0 if obj <= 1 else 1

# ---------------- core segmentation (handles any ntcs 5..64) ----------------

def _build_segments_for_ntcs(
    ntcs: int,
    seq_len: int = 6,
    seed: Optional[int] = None,
) -> List[List[str]]:
    """
    Return a list of trials as node-chains (each is a list of symbols like '00','13',...).
    Trials are contiguous slices of a de Bruijn cycle so that their consecutive pairs
    cover exactly `ntcs` unique ordered pairs with no repeats.

    If ntcs % (seq_len-1) != 0, the final trial will be shorter (rem+1 nodes).
    """
    assert 5 <= ntcs <= 64, "ntcs must be in [5, 64]"
    assert seq_len >= 2, "seq_len must be >= 2"
    pairs_per_full_trial = seq_len - 1

    symbols = _symbols8()
    cyc_idx = _debruijn_indices(k=len(symbols), n=2)  # covers all 64 ordered pairs once
    # rotate for reproducibility/variety
    if seed is not None:
        r = seed % len(cyc_idx)
        cyc_idx = cyc_idx[r:] + cyc_idx[:r]

    cycle_nodes = [symbols[i] for i in cyc_idx] + [symbols[cyc_idx[0]]]  # close cycle

    trials: List[List[str]] = []
    edge_pos = 0
    pairs_remaining = ntcs

    while pairs_remaining > 0:
        take_pairs = min(pairs_per_full_trial, pairs_remaining)
        # take_pairs edges -> take_pairs+1 nodes
        start = edge_pos
        end = edge_pos + take_pairs
        trials.append(cycle_nodes[start:end + 1])
        edge_pos += take_pairs
        pairs_remaining -= take_pairs

    return trials  # last trial may be shorter when ntcs not multiple of (seq_len-1)

# ---------------- instantiation ----------------

def _instantiate_trials(
    nodes_list: List[List[str]],
    seed: Optional[int],
    include_chain_col: bool = True,
) -> pd.DataFrame:
    """
    Build a DataFrame from node chains.
    Columns per position X: locX, refX, objX, ctgX, angX.
    Also includes `tc_nodes` and `tc_pairs` if include_chain_col=True.
    Handles mixed trial lengths (last trial may be shorter).
    """
    rng = random.Random(seed)
    max_len = max(len(nodes) for nodes in nodes_list)

    rows = []
    for nodes in nodes_list:
        row: Dict[str, Optional[int]] = {}
        # fill available positions
        for i, sym in enumerate(nodes, start=1):
            loc, obj = _symbol_to_loc_obj(sym)
            ang = rng.randint(0, 1)
            ref = obj * 2 + ang  # your rule
            row[f"loc{i}"] = loc
            row[f"ref{i}"] = ref
            row[f"obj{i}"] = obj
            row[f"ctg{i}"] = _ctg_from_obj(obj)
            row[f"ang{i}"] = ang
        # pad unused positions to keep rectangular DF
        for i in range(len(nodes) + 1, max_len + 1):
            row[f"loc{i}"] = None
            row[f"ref{i}"] = None
            row[f"obj{i}"] = None
            row[f"ctg{i}"] = None
            row[f"ang{i}"] = None

        if include_chain_col:
            row["tc_nodes"] = "_".join(nodes)
            row["tc_pairs"] = ",".join(f"{nodes[j]}_{nodes[j+1]}" for j in range(len(nodes)-1))

        rows.append(row)

    # column order
    cols = []
    for i in range(1, max_len + 1):
        cols += [f"loc{i}", f"ref{i}", f"obj{i}", f"ctg{i}", f"ang{i}"]
    if include_chain_col:
        cols += ["tc_nodes", "tc_pairs"]

    df = pd.DataFrame(rows)[cols]
    # Use pandas' nullable ints so None is allowed for padded cells
    for i in range(1, max_len + 1):
        for col in (f"loc{i}", f"ref{i}", f"obj{i}", f"ctg{i}", f"ang{i}"):
            if col in df.columns:
                df[col] = df[col].astype("Int64")
    return df

# ---------------- public APIs ----------------

def generate_oneback_block(
    ntcs: int,
    seq_len: int = 6,
    seed: Optional[int] = None,
    include_chain_col: bool = True,
) -> pd.DataFrame:
    """
    Single-session block covering exactly `ntcs` unique ordered pairs with minimal trials.
    If `ntcs` is not a multiple of (seq_len-1), the last trial is shorter.
    """
    trials_nodes = _build_segments_for_ntcs(ntcs=ntcs, seq_len=seq_len, seed=seed)
    return _instantiate_trials(trials_nodes, seed=seed, include_chain_col=include_chain_col)

def generate_oneback_sessions(
    ntcs: int,
    sessions: int = 4,
    seq_len: int = 6,
    seed: Optional[int] = None,
    include_chain_col: bool = True,
) -> List[pd.DataFrame]:
    """
    Multi-session version: returns a list of DataFrames (one per session).
    Every session uses the EXACT SAME set of `ntcs` ordered pairs (no repeats within a session).
    Trials are the same contiguous segments across sessions but are **shuffled** per session.
    `ang` is re-sampled per session; `ref = obj*2 + ang`.
    """
    assert sessions >= 1
    base_nodes = _build_segments_for_ntcs(ntcs=ntcs, seq_len=seq_len, seed=seed)

    rng = random.Random(seed)
    dfs: List[pd.DataFrame] = []
    for s in range(sessions):
        segs = list(base_nodes)
        if s > 0:
            rng.shuffle(segs)  # reorder trials for variety
        df = _instantiate_trials(segs, seed=None if seed is None else seed + 1000 + s,
                                 include_chain_col=include_chain_col)
        dfs.append(df)
    return dfs

# ---------------- optional sanity checks ----------------

def sanity_check_oneback_trials(df: pd.DataFrame) -> Dict[str, object]:
    """
    Ensures:
      - no pair repeats within the session
      - adjacency holds within each trial (WX_YZ, YZ_AB, ...)
    """
    # infer max possible positions
    max_pos = max(int(c[3:]) for c in df.columns if c.startswith("loc"))
    # extract nodes per row, tolerating shorter final trials
    trials = []
    for _, row in df.iterrows():
        if "tc_nodes" in df.columns:
            nodes = str(row["tc_nodes"]).split("_")
        else:
            nodes = []
            for i in range(1, max_pos + 1):
                loc = row.get(f"loc{i}")
                obj = row.get(f"obj{i}")
                if pd.isna(loc) or pd.isna(obj):
                    break
                nodes.append(f"{int(loc)}{int(obj)}")
        trials.append(nodes)

    # build pairs
    all_pairs = []
    repeats = Counter()
    adjacency_ok = True
    for t in trials:
        pairs = [f"{t[i]}_{t[i+1]}" for i in range(len(t)-1)]
        all_pairs.extend(pairs)
        # adjacency
        for i in range(len(pairs)-1):
            if pairs[i].split("_")[1] != pairs[i+1].split("_")[0]:
                adjacency_ok = False
        # count within this trial for local repeats (optional)
        local_counts = Counter(pairs)
        for p, c in local_counts.items():
            if c > 1:
                repeats[p] += c

    global_counts = Counter(all_pairs)
    global_repeats = {p:c for p,c in global_counts.items() if c > 1}

    return {
        "ok_no_repeats": len(global_repeats) == 0,
        "ok_adjacency": adjacency_ok,
        "n_unique_pairs": len(global_counts),
        "global_repeats": global_repeats,
        "local_repeats": dict(repeats),
    }

def sanity_check_across_sessions(dfs: List[pd.DataFrame]) -> dict:
    """
    Ensures that all sessions:
      - Contain the exact same set of unique TC pairs
      - Have no repeats within themselves
      - Maintain adjacency constraints in every trial
    Returns a dictionary summary.
    """
    session_reports = []
    session_pairsets = []
    all_ok_within = True
    adjacency_ok = True

    for i, df in enumerate(dfs, start=1):
        rep = sanity_check_oneback_trials(df)
        session_reports.append(rep)
        session_pairsets.append(set(",".join(df["tc_pairs"].dropna()).split(",")))

        if not rep["ok_no_repeats"]:
            all_ok_within = False
        if not rep["ok_adjacency"]:
            adjacency_ok = False

    # Check identical pair sets across sessions
    first_pairs = session_pairsets[0]
    all_same = all(pairs == first_pairs for pairs in session_pairsets[1:])

    return {
        "n_sessions": len(dfs),
        "all_same_pairs": all_same,
        "ok_no_repeats_within": all_ok_within,
        "ok_adjacency_within": adjacency_ok,
        "n_unique_pairs": len(first_pairs),
        "pairset_example": list(first_pairs)[:10],  # preview some pairs
    }

def save_block_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)

# ---------------- example usage ----------------
# if __name__ == "__main__":
#     # Single session like before (e.g., 60 TCs -> 12 trials)
#     df1 = generate_oneback_block(ntcs=60, seq_len=6, seed=123, include_chain_col=True)
#     print("Single session shape:", df1.shape)
#     print(sanity_check_oneback_trials(df1))

#     # Four sessions sharing the exact same TCs
#     dfs = generate_oneback_sessions(ntcs=60, sessions=4, seq_len=6, seed=123, include_chain_col=True)
#     print("Sessions:", [d.shape for d in dfs])
#     print("All sessions have same pairs:",
#           len({frozenset(sum([d.tc_pairs.str.split(",").sum() for d in dfs], []))}) == 1)


if __name__ == "__main__":
    import os
    from pathlib import Path

    # Output dir
    tcs_dir = Path("/Users/lucasgomez/Desktop/Neuro/Bashivan/MGH_NACC+MULTFS/MULTFS/task_stimuli/data/multfs/trevor/tcs")
    os.makedirs(tcs_dir, exist_ok=True)

    def run_and_save(task_name, seed):
        print(f"\n----- Generating 1back block for {task_name} -----")
        dfs = generate_oneback_sessions(ntcs=50, sessions=2, seq_len=6, seed=seed, include_chain_col=True)

        # Per-session checks
        for i, df in enumerate(dfs, start=1):
            rep = sanity_check_oneback_trials(df)
            print(f"Session {i}: repeats={rep['ok_no_repeats']}, adjacency={rep['ok_adjacency']}, "
                  f"unique_pairs={rep['n_unique_pairs']}")
            save_block_csv(df, tcs_dir / f"{task_name}_session0{i}.csv")

        # Cross-session consistency check
        multi_rep = sanity_check_across_sessions(dfs)
        print(f"\nCross-session sanity for {task_name}:")
        print(f"  Same TC pairs across sessions: {multi_rep['all_same_pairs']}")
        print(f"  All sessions individually clean: {multi_rep['ok_no_repeats_within'] and multi_rep['ok_adjacency_within']}")
        print(f"  Total unique pairs: {multi_rep['n_unique_pairs']}")

    # Run all 3 tasks
    run_and_save("1back_loc", seed=0)
    run_and_save("1back_ctg", seed=1)
    run_and_save("1back_obj", seed=2)