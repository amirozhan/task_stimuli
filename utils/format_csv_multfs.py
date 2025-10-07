import os
import pandas as pd

files_dir = '/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/ozhan_branch/task_stimuli/data/multfs/updated_cond_file/blockfiles'

for file in os.listdir(files_dir):
    if file.endswith('.csv'):
        df = pd.read_csv(os.path.join(files_dir, file))
        
        for col in df.columns:
            if 'Unnamed' in col:
                df = df.drop(columns=[col])
        df.to_csv(os.path.join(files_dir, file), index=False)
