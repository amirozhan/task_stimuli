import pandas as pd

filep = r'C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic\Sub-01\Sub-01_Playlist_1.tsv'

df =  pd.read_table(filep, sep='\t')

print(df.columns)