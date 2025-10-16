from session_planner import plan_session
from pathlib import Path

subject = "00"
subject_dir = Path("data/mutemusic") / f"Sub-{subject}"

plan_session(
    subject_dir=str(subject_dir),
    subject=subject,
    session_id="2025-10-16",
    mode="new",
    segment_len=10.0,
    n_blocks=4,
    seed=42
)