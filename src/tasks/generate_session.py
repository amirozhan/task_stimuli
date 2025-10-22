from session_planner import plan_all_sessions
from pathlib import Path

subject = "00"
subject_dir = Path("data/mutemusic") / f"Sub-{subject}"

out_dirs = plan_all_sessions(
    root_dir=r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic\Sub-00\music",
    subject=subject,
    n_sessions=10,            # how many sessions to generate
    n_blocks=4,              # how many blocks per session
    shared_segment_start=30, # fallback start if not in JSON
    shared_segment_len=10,   # fallback length if not in JSON
    segment_len=10           # used for favorite/
)

print("Generated:", out_dirs)