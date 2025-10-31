import os, time, pandas


# import sounddevice as sd
# sd.default.device = (None, 1)

from psychopy import prefs
prefs.hardware['audioLib'] =['ptb']

from psychopy import core
from psychopy import sound as pysound

from psychopy import sound
import soundfile as sf
import numpy as np
from scipy.signal import resample

import sounddevice as sd
import soundfile as sf
import numpy as np

def play_segment_with_speed(path, seg_start=10, seg_dur=30, speed=1.5):
    # load audio
    data, sr = sf.read(path)
    
    # slice the segment
    start_idx = int(seg_start * sr)
    stop_idx  = int((seg_start + seg_dur) * sr)
    seg = data[start_idx:stop_idx]
    
    # resample to change playback speed
    new_len = int(len(seg) / speed)
    if seg.ndim == 1:
        seg_resampled = np.interp(
            np.linspace(0, len(seg), new_len),
            np.arange(len(seg)),
            seg
        )
    else:  # stereo
        seg_resampled = np.vstack([
            np.interp(np.linspace(0, len(seg), new_len),
                      np.arange(len(seg)), seg[:, ch])
            for ch in range(seg.shape[1])
        ]).T
    
    # play
    print(f"▶ Playing {path} [{seg_start:.1f}-{seg_start+seg_dur:.1f}s] speed={speed}x")
    sd.play(seg_resampled, sr)
    sd.wait()



tracks_dir = r'C:\Users\Lucas\Desktop\NACC\task_stimuli\data\mutemusic\Sub-00\music\shared'
seg_json = r'C:\Users\Lucas\Desktop\NACC\task_stimuli\data\mutemusic\Sub-00\music\segments_shared.json'

# load segments info
import json
with open(seg_json, 'r') as f:
    segments_info = json.load(f)

for track, seg_info in segments_info.items():
    track_path = os.path.join(tracks_dir, track + '.mp3')
    print("Loading track:", track_path)
    seg_start = float(seg_info.get('start', 10))
    seg_dur   = float(seg_info.get('dur', 30))
    seg_stop  = seg_start + seg_dur
    track_name = os.path.split(track_path)[1]

    play_segment_with_speed(track_path, seg_start=seg_start, seg_dur=seg_dur, speed=3)
    # snd = sound.Sound(track_path,startTime=seg_start,stopTime=seg_stop,volume=5)
