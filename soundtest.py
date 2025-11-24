import os, time, pandas



# import sounddevice as sd
# sd.default.device = (None, 1)

from psychopy import prefs
prefs.hardware['audioLib'] =['ptb']

from psychopy import core
from psychopy import sound as pysound
track_path = r'C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic\Sub-00\music\shared\track1.mp3'
snd = pysound.Sound(track_path,volume=5)
print("Duration:", getattr(snd, "duration", None))  # should be > 0
snd.play()
core.wait(120)