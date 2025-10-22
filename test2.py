import os
os.environ['PSYCHOPY_AUDIO_LIBRARY'] = 'sounddevice'  # belt & suspenders

import sounddevice as sd
OUTPUT_IDX = 1            # <-- your chosen output index
sd.default.device = (None, OUTPUT_IDX)
sd.default.samplerate = 48000

# Use the sounddevice backend class directly:
from psychopy.sound.backend_sounddevice import SoundDeviceSound as Sound

# test
snd = Sound('A', secs=0.5, volume=1.0)
snd.play()
sd.wait()

# sanity: confirm which class you’re using
print("Sound class:", Sound)
