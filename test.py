import os, time, pandas

from psychopy import prefs

prefs.hardware['audioLib'] =['ptb']

from psychopy import visual, event, core, logging
from psychopy import sound as pysound
track_path = r'C:\Users\Bashivan Lab\Desktop\music\blues.00000.wav'
snd = pysound.Sound(track_path,volume=1)
print("Duration:", getattr(snd, "duration", None))  # should be > 0
snd.play()
core.wait(2)