import os
import glob
import librosa  # For audio analysis
import numpy as np
from pydub import AudioSegment
# from pydub.effects import low_shelf_filter

# --- Helper Functions ---

# --- START: Manual Definition for low_shelf_filter (Version 2) ---
# We are adding this function manually to fix the ImportError
# This version removes the 'get_extra_args' dependency
def low_shelf_filter(seg, cutoff, gain, order=5):
    # This import is still needed, but it's inside the main script
    # from pydub.audio_segment import AudioSegment 

    # We removed get_extra_args() and just create the list directly
    args = [
        "-af",
        "lowshelf=f={cutoff}:g={gain}:o={order}".format(
            cutoff=cutoff,
            gain=gain,
            order=order,
        )
    ]
    
    return seg._spawn(seg.raw_data, overrides={"extra_args": args})
# --- END: Manual Definition ---


def match_target_amplitude(sound, target_dbfs):
    """Normalizes the audio to a target average loudness (dBFS)."""
    change_in_dbfs = target_dbfs - sound.dBFS
    return sound.apply_gain(change_in_dbfs)

def get_bass_to_mid_ratio(file_path, bass_range, mid_range):
    """
    Analyzes the file and returns the ratio of 
    average bass power to average mid-range power.
    """
    try:
        # 1. Load file with librosa
        #    sr=None preserves the original sample rate
        y, sr = librosa.load(file_path, sr=None)
        
        # 2. Get a spectrogram (power for each frequency over time)
        #    np.abs() gets the magnitude
        S = np.abs(librosa.stft(y))
        
        # 3. Get the list of frequencies for each row in the spectrogram
        freqs = librosa.fft_frequencies(sr=sr)
        
        # 4. Find the array indices (rows) that correspond to our frequency ranges
        bass_indices = np.where((freqs >= bass_range[0]) & (freqs <= bass_range[1]))
        mid_indices = np.where((freqs >= mid_range[0]) & (freqs <= mid_range[1]))
        
        # 5. Calculate the average power in those bands
        #    np.mean(S[indices]) averages all power values in all timeframes
        avg_bass_power = np.mean(S[bass_indices])
        avg_mid_power = np.mean(S[mid_indices])
        
        # Avoid division by zero if a file is silent
        if avg_mid_power == 0:
            return 0
            
        return avg_bass_power / avg_mid_power
        
    except Exception as e:
        print(f"  Could not analyze {file_path}. Error: {e}")
        return 0

# --- Configuration ---

# 1. Input/Output Folders
INPUT_FOLDER = "/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/Songs/base_equalized" 
OUTPUT_FOLDER = "/Users/lucasgomez/Desktop/Neuro/Bashivan/Music2Brain/Songs/base_equalized_bassreduc"

# 2. Loudness Normalization
TARGET_DBFS = -20.0

# 3. Bass Filter Settings (only applied if song is "too bassy")
BASS_REDUCTION_DB = -6.0  # How much to cut the bass
BASS_CUTOFF_HZ = 250      # Apply the cut below this frequency

# 4. --- KEY: Analysis & Threshold Settings ---
BASS_FREQ_RANGE = (60, 250)   # "Bass" is 60 Hz to 250 Hz
MID_FREQ_RANGE = (300, 2000)  # "Mids" are 300 Hz to 2000 Hz

# This is the "magic number" you will need to tune.
# A ratio of 2.0 means the bass is, on average, 2x louder than the mids.
# Start here, and adjust based on the console output.
BASS_TO_MID_RATIO_THRESHOLD = 2.0  

# -----------------------------------------------

# Create the output folder if it doesn't exist
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

print("Starting batch processing...")
print(f"Loudness Target: {TARGET_DBFS} dBFS")
print(f"Bass Ratio Threshold: {BASS_TO_MID_RATIO_THRESHOLD}")
print("-" * 30)

# Find all .mp3 files in the input folder
for mp3_file_path in glob.glob(os.path.join(INPUT_FOLDER, "*.mp3")):
    
    file_name = os.path.basename(mp3_file_path)
    output_file_path = os.path.join(OUTPUT_FOLDER, file_name)
    
    print(f"Processing: {file_name}")

    try:
        # 1. ANALYZE the song to get its bass ratio
        ratio = get_bass_to_mid_ratio(mp3_file_path, BASS_FREQ_RANGE, MID_FREQ_RANGE)
        
        # 2. LOAD the song for processing with pydub
        song = AudioSegment.from_mp3(mp3_file_path)
        
        # 3. DECIDE: Apply filter or not?
        if ratio > BASS_TO_MID_RATIO_THRESHOLD:
            print(f"  ...Bassy! (Ratio: {ratio:.2f}). Applying filter.")
            # NEW CODE:
            processed_song = low_shelf_filter(
                song, 
                cutoff=BASS_CUTOFF_HZ, 
                gain=BASS_REDUCTION_DB, 
                order=5
            )
        else:
            print(f"  ...OK. (Ratio: {ratio:.2f}). Skipping filter.")
            processed_song = song # Just pass the original song along
        
        # 4. NORMALIZE the result (either filtered or original)
        normalized_song = match_target_amplitude(processed_song, TARGET_DBFS)
        
        # 5. EXPORT
        normalized_song.export(output_file_path, format="mp3", bitrate="192k")
        
    except Exception as e:
        print(f"  !!! FAILED to process {file_name}. Error: {e}")

print(f"\nDone! Processed files are in '{OUTPUT_FOLDER}'.")