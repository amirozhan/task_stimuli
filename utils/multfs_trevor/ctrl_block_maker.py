import pandas as pd
import numpy as np
import os

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------
OUTLIER_CSV_PATH = '/mnt/store1/lucas/checkpoints/fixed/tf_medium_full_3000eps_ubt_semifixed/results/ctrl_pred_betas/LH_RH/nps5to50/MASTER_selected_conditions.csv'
OUTPUT_DIR = '/home/lucas/projects/task_stimuli/data/multfs/trevor/blockfiles/session05'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Study Design
# Updated Study Design
STUDY_DESIGN = {
    "DMSA_CL":             {"8BL": 10, "rnd": 1},
    "DMSO_LC":             {"10v": 10, "rnd": 1},
    "OnebackA_LO":         {"46": 3, "8BL": 2, "9-46d": 2, "p9-46v": 2, "rnd": 1},
    "OnebackO_LO":         {"46": 3, "8C": 2, "9-46d": 2, "p9-46v": 2, "rnd": 1},
    "Twoback_LOC":         {"10v": 2, "8BL": 1, "8C": 2, "9-46d": 2, "p9-46v": 2, "rnd": 1},
    "Twoback_CTG":         {"10v": 2, "8BL": 1, "8C": 2, "9-46d": 2, "p9-46v": 2, "rnd": 1},
    "InterDMS_LOC_ABCABC": {"46": 3, "8C": 2, "p9-46v": 1, "rnd": 1},
    "InterDMS_LOC_ABBCCA": {"46": 3, "8C": 2, "9-46d": 1, "rnd": 1},
    "InterDMS_CTG_ABBCCA": {"8BL": 1, "9-46d": 3, "p9-46v": 2, "rnd": 1},
    "ctxDM_OLC":           {"10v": 3, "8BL": 3, "9-46d": 1, "p9-46v": 1, "rnd": 1},
    "ctxDM_LOL":           {"10v": 3, "8BL": 3, "8C": 2, "rnd": 1}
}

# Task Stimuli Counts (CRITICAL: These define the columns generated)
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
    # Sort keys by length descending (e.g. check 'InterDMS' before 'DMS')
    keys = sorted(TASK_PARAMS.keys(), key=len, reverse=True)
    for key in keys:
        if key in task_name:
            return TASK_PARAMS[key]
    
    # Debugging print if we hit default
    print(f"  [WARN] Could not match '{task_name}' to any TASK_PARAM. Defaulting to 6.")
    return 6

def expand_condition_to_row(condition_str, task_name, n_stim_limit, trial_type='outlier'):
    """
    Parses a condition string (e.g. '101112').
    CRITICAL: Only parses up to 'n_stim_limit' pairs, ignoring any extra characters.
    """
    # if 'ctx' in task_name:
    #     import pdb; pdb.set_trace()
    s = str(condition_str).strip()
    
    
    row = {}
    tc_list = []

    for i in range(n_stim_limit):
        # Extract chunk (Loc, Obj)
        chunk = s[i*2 : i*2+2]
        

        loc_val = int(chunk[0])
        obj_val = int(chunk[1])

            
        idx = i + 1 
        
        row[f'loc{idx}'] = loc_val
        row[f'ref{idx}'] = 0
        row[f'obj{idx}'] = obj_val
        row[f'ctg{idx}'] = obj_val // 2
        row[f'ang{idx}'] = 0
        
        tc_list.append(f"{loc_val}{obj_val}")

    # Metadata
    row['tc'] = '_'.join(tc_list)

    row['task_name'] = task_name
    row['trial_type'] = trial_type
    
    return row

def generate_random_trial(task_name, n_stimuli):
    row = {}
    tc_list = []
    
    for i in range(1, n_stimuli + 1):
        r_loc = np.random.choice([0, 1])
        r_obj = np.random.choice([0, 1, 2, 3])
        r_ctg = r_obj // 2
        
        row[f'loc{i}'] = r_loc
        row[f'ref{i}'] = 0
        row[f'obj{i}'] = r_obj
        row[f'ctg{i}'] = r_ctg
        row[f'ang{i}'] = 0
        
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
        
        # 1. DETERMINE EXPECTED STIMULI (Enforce this limit)
        expected_n_stim = get_n_stimuli(block_name)
        print(f"  > Detected Limit: {expected_n_stim} stimuli")
        
        block_rows = []
        
        # 2. PROCESS OUTLIERS
        for source, count in recipe.items():
            if source == 'rnd': continue
            
            # Filter
            candidates = outliers_df[
                (outliers_df['Task'] == f"task-{block_name}") & 
                (outliers_df['ROI'] == source)
            ]
            
            if len(candidates) == 0:
                raise ValueError(f"No candidates found for block '{block_name}' and source '{source}'. Check your CSV and STUDY_DESIGN.")

            # Sample
            if len(candidates) < count:
                print(f"  [WARN] {source}: Requested {count}, found {len(candidates)}. Resampling.")
                selected = candidates.sample(n=count, replace=True)
            else:
                selected = candidates.sample(n=count, replace=False)
            
            # EXPAND ROWS
            for _, row_series in selected.iterrows():
                cond_str = row_series['condition']
                # Pass strict limit to parsing function
                parsed_row = expand_condition_to_row(
                    cond_str, 
                    block_name, 
                    n_stim_limit=expected_n_stim, # <--- Fix applied here
                    trial_type=f'outlier_{source}'
                )
                block_rows.append(parsed_row)

        # 3. GENERATE RANDOM
        rnd_count = recipe.get('rnd', 0)
        
        if rnd_count > 0:
            # Create a set of TCs currently in the block to avoid duplicates
            existing_tcs = set(row['tc'] for row in block_rows)
            
            for _ in range(rnd_count):
                while True:
                    # Generate Candidate
                    rnd_row = generate_random_trial(block_name, n_stimuli=expected_n_stim)
                    
                    # Check if Candidate already exists in this block
                    if rnd_row['tc'] not in existing_tcs:
                        # Found unique! Add it.
                        block_rows.append(rnd_row)
                        existing_tcs.add(rnd_row['tc']) # Add to set so we don't pick it again
                        break
                    # If duplicate, loop repeats immediately
            
        final_df = pd.DataFrame(block_rows)
        final_df = final_df.fillna(0)
        
        # Select exact feature columns based on Expected N
        feature_cols = []
        prefixes = ['loc', 'ref', 'obj', 'ctg', 'ang']
        for i in range(1, expected_n_stim + 1):
            for p in prefixes:
                feature_cols.append(f"{p}{i}")
                    
        # Add metadata cols
        cols_to_save = feature_cols + ['tc']
        
        # Safety check: ensure columns exist (random gen might have made them, outliers might have failed)
        cols_to_save = [c for c in cols_to_save if c in final_df.columns]
        
        # Shuffle
        final_df = final_df.sample(frac=1).reset_index(drop=True)
        output_df = final_df[cols_to_save]

        # Final sanity check: Ensure no duplicate TCs within this block
        if output_df['tc'].duplicated().any():
            dup_tcs = output_df[output_df['tc'].duplicated()]['tc'].unique()
            raise ValueError(f"  [ERROR] Duplicate TCs found in block '{block_name}': {dup_tcs}")

        save_path = os.path.join(OUTPUT_DIR, f"{task_name_map[block_name]}_block_0.csv")
        output_df.to_csv(save_path, index=False)
        print(f"  Saved {save_path} ({len(output_df)} trials)")

if __name__ == "__main__":
    main()