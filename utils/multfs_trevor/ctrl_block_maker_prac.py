import pandas as pd
import numpy as np
import os
import random

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------
OUTLIER_CSV_PATH = '/mnt/store1/lucas/checkpoints/fixed/tf_medium_full_3000eps_ubt_semifixed/results/ctrl_pred_betas/LH_RH/nps5to50/MASTER_selected_conditions.csv'
OUTPUT_DIR = '/home/lucas/projects/task_stimuli/data/multfs/trevor/blockfiles/session06'

# GLOBAL SEED FOR REPRODUCIBILITY
SEED = 5112000

# Apply seeds immediately
random.seed(SEED)
np.random.seed(SEED)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Study Design
STUDY_DESIGN = {
    "DMSA_CL":             {"rnd": 3},
    "DMSO_LC":             {"rnd": 3},
    "OnebackA_LO":         {"rnd": 3},
    "OnebackO_LO":         {"rnd": 3},
    "Twoback_LOC":         {"rnd": 3},
    "Twoback_CTG":         {"rnd": 3},
    "InterDMS_LOC_ABCABC": {"rnd": 3},
    "InterDMS_LOC_ABBCCA": {"rnd": 3},
    "InterDMS_CTG_ABBCCA": {"rnd": 3},
    "ctxDM_OLC":           {"rnd": 3},
    "ctxDM_LOL":           {"rnd": 3}
}

# Task Stimuli Counts
TASK_PARAMS = {
    "DMSA":     2,
    "DMSO":     2,
    "Oneback":  5,
    "Twoback":  5,
    "InterDMS": 6, 
    "ctxDM":    3,
}

# Task name remapper
task_name_map ={
    'DMSA_CL': 'dms_a_cl',
    'DMSO_LC': 'dms_o_lc',
    'OnebackA_LO': '1back_a_lo',
    'OnebackO_LO': '1back_o_lo',
    'Twoback_LOC': '2back_loc',
    'Twoback_CTG': '2back_ctg',
    'InterDMS_LOC_ABCABC': 'interdms2_loc_ABCABC',
    'InterDMS_LOC_ABBCCA': 'interdms2_loc_ABBCCA',
    'InterDMS_CTG_ABBCCA': 'interdms2_ctg_ABBCCA',
    'ctxDM_OLC': 'ctxdm_olc',
    'ctxDM_LOL': 'ctxdm_lol'
}

# ---------------------------------------------------------
# 2. PARSING LOGIC
# ---------------------------------------------------------

def get_n_stimuli(task_name):
    """
    Finds the stimulus count for a task block. 
    Matches against TASK_PARAMS keys (e.g. 'ctxDM' inside 'ctxDM_OLC').
    """
    keys = sorted(TASK_PARAMS.keys(), key=len, reverse=True)
    for key in keys:
        if key in task_name:
            return TASK_PARAMS[key]
    
    print(f"  [WARN] Could not match '{task_name}' to any TASK_PARAM. Defaulting to 6.")
    return 6

def generate_random_trial(task_name, n_stimuli):
    row = {}
    tc_list = []
    
    for i in range(1, n_stimuli + 1):
        # Using numpy random which was seeded globally
        r_loc = np.random.choice([0, 1])
        r_obj = np.random.choice([0, 1, 2, 3])
        r_ctg = r_obj // 2
        
        # Determine Angle/Ref using global random state
        r_ang = random.randint(0, 1)
        r_ref = r_obj * 2 + r_ang 
        
        row[f'loc{i}'] = r_loc
        row[f'ref{i}'] = r_ref 
        row[f'obj{i}'] = r_obj
        row[f'ctg{i}'] = r_ctg
        row[f'ang{i}'] = r_ang
        
        tc_list.append(f"{r_loc}{r_obj}")

    row['tc'] = '_'.join(tc_list)
    row['task_name'] = task_name
    row['trial_type'] = 'random'
    
    return row

# ---------------------------------------------------------
# 3. MAIN LOOP
# ---------------------------------------------------------
def main():
    print(f"Loading outliers from {OUTLIER_CSV_PATH}...")
    if not os.path.exists(OUTLIER_CSV_PATH):
        print(f"Error: {OUTLIER_CSV_PATH} not found.")
        return

    # Load master list
    outliers_df = pd.read_csv(OUTLIER_CSV_PATH, dtype={'condition': str})

    for block_name, recipe in STUDY_DESIGN.items():
        print(f"--- Generating block: {block_name} ---")
        
        expected_n_stim = get_n_stimuli(block_name)
        print(f"  > Detected Limit: {expected_n_stim} stimuli")
        
        block_rows = []

        # 3. GENERATE RANDOM
        rnd_count = recipe.get('rnd', 0)
        
        if rnd_count > 0:
            existing_tcs = set(row['tc'] for row in block_rows)
            
            for _ in range(rnd_count):
                while True:
                    rnd_row = generate_random_trial(block_name, n_stimuli=expected_n_stim)
                    
                    if rnd_row['tc'] not in existing_tcs:
                        block_rows.append(rnd_row)
                        existing_tcs.add(rnd_row['tc'])
                        break
            
        final_df = pd.DataFrame(block_rows)
        final_df = final_df.fillna(0)
        
        feature_cols = []
        prefixes = ['loc', 'ref', 'obj', 'ctg', 'ang']
        for i in range(1, expected_n_stim + 1):
            for p in prefixes:
                feature_cols.append(f"{p}{i}")
                    
        cols_to_save = feature_cols + ['tc']
        cols_to_save = [c for c in cols_to_save if c in final_df.columns]
        
        # Shuffle with random_state
        final_df = final_df.sample(frac=1, random_state=SEED).reset_index(drop=True)
        output_df = final_df[cols_to_save]

        # Final sanity check
        if output_df['tc'].duplicated().any():
            dup_tcs = output_df[output_df['tc'].duplicated()]['tc'].unique()
            raise ValueError(f"  [ERROR] Duplicate TCs found in block '{block_name}': {dup_tcs}")

        save_path = os.path.join(OUTPUT_DIR, f"{task_name_map[block_name]}_block_0.csv")
        output_df.to_csv(save_path, index=False)
        print(f"  Saved {save_path} ({len(output_df)} trials)")

if __name__ == "__main__":
    main()