import os
import random
import pandas as pd

# ---------------- MAIN ----------------
if __name__ == "__main__":
    sub = '01'
    session = 1
    seed = 0  # used to shuffle/partition per task

    block_dir = f"/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/ozhan_branch/task_stimuli/data/multfs/trevor/blockfiles/session0{session}"
    studyds_dir = "/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/ozhan_branch/task_stimuli/data/multfs/trevor/study_designs"

    # get block file names with .csv stripped
    block_file_names = [f[:-4] for f in os.listdir(block_dir) if f.endswith('.csv')]

    # randomly shuffle block file names with seed
    random.seed(seed)
    random.shuffle(block_file_names)

    # mapping function: ctxdm -> A, interdms -> B, 1back -> C
    def scan_type_from_name(name: str) -> str:
        task_root = name.split('_', 1)[0]  # 'ctxdm', 'interdms', '1back', etc.
        return {'ctxdm': 'A', 'interdms': 'B', '1back': 'C'}.get(task_root, 'UNKNOWN')

    # create a dataframe with columns ['session', 'block_file_name', 'scan_type']
    session_runs = pd.DataFrame({
        'session': [session] * len(block_file_names),
        'block_file_name': block_file_names,
    })
    session_runs['scan_type'] = session_runs['block_file_name'].apply(scan_type_from_name)

    # save to tsv
    out_tsv = os.path.join(studyds_dir, f"sub-{sub}_design.tsv")
    session_runs.to_csv(out_tsv, sep='\t', index=False)
    print(f"Wrote study design to {out_tsv}")

