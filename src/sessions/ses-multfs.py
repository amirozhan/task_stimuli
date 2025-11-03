import os
from ..tasks import multfs
from ..tasks.task_base import Pause
import pandas as pd
import re

data_path = "./data/multfs/trevor"

def extract_task_name(block_file_name):
    s = block_file_name

    match = re.match(r"^(.*?)_block_\d+$", s)
    if match:
        task_name = match.group(1)
        print(task_name)  # → interdms_loc_ABAB
    else:
        task_name = s  # fallback if pattern not found
    return task_name

def get_tasks(parsed):

    study_design = pd.read_csv(
        os.path.join(data_path, 'study_designs', f"sub-{int(parsed.subject):02d}_design.tsv"),
        delimiter='\t')

    session = int(parsed.session)

    session_runs = study_design[study_design.session.eq(session)]

    print("*"*100)
    print("Today we will run the tasks in the following order")
    print('- func_task-dms')
    for ri, runs in session_runs.iterrows():
        print(f"- func_task-{runs.block_file_name.split('_')[0]}")

    yield multfs.multfs_dms(
        os.path.join(data_path, "blockfiles/dms_loc.csv"), 
        "dms_loc",
        n_trials = 4,
        name = f"task-dmsloc",
        feature='loc',
        use_eyetracking=True,
        et_calibrate=True, # first task
    )

    yield Pause(
            text="Please wait while we setup the scanner for the next block...",
            wait_key='8',
    )

    tasks_idxs = {
        'interdms': 0,
        'ctxdm': 0,
        '1back': 0
    }

    for ri, (_, runs) in enumerate(session_runs.iterrows()):

        kwargs = {
            'use_eyetracking':True,
            'et_calibrate': ri == 2
            }
        
        # Take a break halfway through
        if ri== len(session_runs)//2 and ri != 0:
            yield Pause(
                text="You can take a short break.\n\n Let us know when you are ready to continue!",
                wait_key='8',
            )

        kwargs = {
            'use_eyetracking':True,
            'et_calibrate': ri == 2
            }

        block_file_name = runs.block_file_name
        feat = block_file_name.split('_')[1] # TODO get consistent filenaming!
        block_file_path = os.path.join(data_path, f"blockfiles/session{session:02d}", block_file_name + '.csv') 
        n_trials = len(pd.read_csv(block_file_path))

        if 'interdms' in block_file_name:
            tasks_idxs['interdms'] += 1
            order = block_file_name.split('_')[2]
            kls = multfs.multfs_interdms_ABAB if order == 'ABAB' else multfs.multfs_interdms_ABBA
            yield kls(
                block_file_path,
                extract_task_name(block_file_name),
                n_trials,
                name = f"task-{block_file_name}",
                feature = feat,
                **kwargs
            )
        elif 'ctxdm' in block_file_name:
            tasks_idxs['ctxdm'] += 1
            yield multfs.multfs_CTXDM(
                block_file_path,
                extract_task_name(block_file_name),
                n_trials,
                name = f"task-{block_file_name}",
                feature=feat,
                **kwargs
            )
        elif '1back' in block_file_name:
            tasks_idxs['1back'] += 1
            yield multfs.multfs_1back(
                block_file_path,
                extract_task_name(block_file_name),
                n_trials,
                name = f"task-{block_file_name}",
                feature=feat,
                **kwargs
            )

        yield Pause(
                text="Please wait while we setup the scanner for the next block...",
                wait_key='8',
        )
