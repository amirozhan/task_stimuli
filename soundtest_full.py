import os, time, pandas

import json

# import sounddevice as sd
# sd.default.device = (None, 1)

from psychopy import prefs
prefs.hardware['audioLib'] =['ptb']

from psychopy import core
from psychopy import sound

## FULL
path_to_shared = r'C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic\Sub-02\music\shared'
shared_json_path = r'C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic\Sub-02\music\segments_shared.json'

# Load shared_json
shared_dict = json.load(open(shared_json_path, 'r'))

for track, snl in shared_dict.items():
    # cont = ''
    # while cont != 'x':
    #     print('Press X to continue')
    #     cont = input()

    start = float(snl['start'])
    dur = float(snl['len'])

    track_path = os.path.join(path_to_shared, track + '.mp3')
    
    stop  = start + dur
    
    print('Now playing: ', track)
    snd = sound.Sound(track_path,startTime=start,stopTime=stop,volume=5)

    snd.play()
    core.wait(dur + 5)