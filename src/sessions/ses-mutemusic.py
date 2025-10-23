import os
import pandas
from ..tasks.mutemusic import Playlist
from pathlib import Path

STIMULI_PATH  = 'data/mutemusic'

def get_tasks(parsed):
    sub = f'Sub-{parsed.subject}'
    subj_dir = Path(STIMULI_PATH) / sub
    sessions_root = subj_dir / "episodes"
    session_num = 'E01'
    #import pdb;pdb.set_trace()
    session_dir = sessions_root / session_num

       
    for block_dir in sorted(session_dir.glob("B*")):
        #import pdb;pdb.set_trace()
        plan = block_dir / "plan.csv"
        playlist = block_dir / "playlist.tsv"
    
        
        # Ensure we read start/dur from playlist
        # (Playlist itself will read the TSV; we just hand the path)
        
        task = Playlist(
            tsv_path=str(playlist),
            block_dir=str(block_dir),
            use_eyetracking=True,
            et_calibrate=True,  # or only for the first block if you prefer
            name=f"task-mutemusic_{session_dir.name}_{block_dir.name}"
        )
        yield task
        # return  # one block per run


"""
def get_tasks(parsed):

    sub = f'Sub-{parsed.subject}'
    playlists_order_path = os.path.join(STIMULI_PATH, sub, f'{sub}_Playlist_order.tsv')
    playlist_order = pandas.read_csv(playlists_order_path, sep=' ')

    current_playlist = len(playlist_order)f
    for i, row in playlist_order.iterrows():
        if not row['done']:
            current_playlist = i
            break

    playlist_sequence = playlist_order[current_playlist:]
    for i, row in playlist_sequence.iterrows():
        pli = row['playlist']
        playlist_file = f'{sub}_Playlist_{pli}.tsv'
        playlist_path = os.path.abspath(os.path.join(STIMULI_PATH, sub, playlist_file))
        #playlist_path = os.path.join(STIMULI_PATH, sub, playlist_file)
        print(playlist_path)
        playlist = Playlist(
            tsv_path=playlist_path,
            use_eyetracking=True,
            et_calibrate=i==current_playlist,
            name=f"task-mutemusic_run-{i}")
        yield playlist

        if playlist._task_completed:
            playlist_order['done'].iloc[i] = 1
            playlist_order.to_csv(playlists_order_path, sep=' ', index=False)
"""