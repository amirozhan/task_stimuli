from session_planner import plan_all_episodes
from pathlib import Path

if __name__ == "__main__":
    from pathlib import Path
    # roots
    main_path = r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic"
    sub = "00"

    subject_dir = Path(main_path) / f"Sub-{sub}" / "music"
    subject_dir.mkdir(parents=True, exist_ok=True)

    # config files (written earlier by your generator)
    segments_shared   = subject_dir / "segments_shared.json"
    segments_favorite = subject_dir / "segments_favorite.json"

    # run planner
    out_dirs = plan_all_episodes(
        root_dir=str(subject_dir),
        subject=sub,
        n_episodes=12,
        n_blocks=20,
        segments_path_shared=str(segments_shared),
        segments_path_favorite=str(segments_favorite),
    )
    print("Generated:", out_dirs)