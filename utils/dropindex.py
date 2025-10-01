import pandas as pd
import os

path_to_dir = r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\multfs\updated_cond_file\blockfiles"

for fp in os.listdir(path_to_dir):
    df = pd.read_csv(os.path.join(path_to_dir, fp))
    for col in list(df.columns):
        if 'Unnamed' in col:
            df = df.drop(columns=[col])

    df.to_csv(os.path.join(path_to_dir, fp), index=False)