from session_planner import plan_all_episodes
from pathlib import Path

if __name__ == "__main__":
    from pathlib import Path
    # roots
    # main_path = r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic"
    # sub = "05"

    # subject_dir = Path(main_path) / f"Sub-{sub}" / "music"
    # subject_dir.mkdir(parents=True, exist_ok=True)

    # # config files (written earlier by your generator)
    # segments_shared   = subject_dir / "segments_shared.json"
    # segments_favorite = subject_dir / "segments_favorite.json"

    # # run planner
    # out_dirs = plan_all_episodes(
    #     root_dir=str(subject_dir),
    #     subject=sub,
    #     n_episodes=12,
    #     n_blocks=20,
    #     segments_path_shared=str(segments_shared),
    #     segments_path_favorite=str(segments_favorite),
    # )

    sub = "05"

    # Where the audio + JSON configs live on THIS machine (and where the
    # episode/block folders will be written). On Linux, point this at your
    # local checkout. On the task computer, point this at the Windows path.
    local_main_path = Path(__file__).resolve().parents[2] / "data" / "mutemusic"
    # local_main_path = Path(r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic")

    # What absolute path prefix to embed inside playlist.tsv. Set this to the
    # path the runner (task computer) will see at runtime. Set to None to use
    # the local absolute path instead.
    emit_main_path = r"C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\data\mutemusic"

    subject_dir = local_main_path / f"Sub-{sub}" / "music"
    subject_dir.mkdir(parents=True, exist_ok=True)
    emit_root = (
        rf"{emit_main_path}\Sub-{sub}\music" if emit_main_path else None
    )

    # config files (written earlier by your generator)
    segments_shared   = subject_dir / "segments_shared_new.json"
    segments_favorite = subject_dir / "segments_favorite_new.json"
    segments_control  = subject_dir / "segments_control_lastfm.json"

    # Folder-name suffixes (must match what generate_config.py used).
    # E.g. shared folder is "shared_30_new", control folder is "control_lastfm".
    shared_suffix   = "_30_new"
    favorite_suffix = "_10_new"
    control_suffix  = "_lastfm"

    # control bucket is optional: only enable if the file exists
    has_control = segments_control.exists()
    control_kwargs = {}
    if has_control:
        control_kwargs = {
            "segments_path_control": str(segments_control),
            "n_shared": 30,    # adjust to match your subset_shared
            "n_favorite": 10,  # adjust to match your subset_favorite
            "n_control": 10,   # adjust to match your subset_control
        }

    # additional 5 episodes (E06..E10) with 10 blocks each
    out_dirs = plan_all_episodes(
        root_dir=str(subject_dir),
        subject=sub,
        n_episodes=5,
        n_blocks=10,
        start_episode=6,
        emit_root=emit_root,
        shared_suffix=shared_suffix,
        favorite_suffix=favorite_suffix,
        control_suffix=control_suffix,
        segments_path_shared=str(segments_shared),
        segments_path_favorite=str(segments_favorite),
        **control_kwargs,
    )
    print("Generated:", out_dirs)