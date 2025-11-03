import os, sys, time, random
import warnings
import pandas as pd

# Suppress pandas SettingWithCopy and Future warnings (used inside psychopy.data)
warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import psychopy
from psychopy import visual, core, data, logging, event
from psychopy.hardware import keyboard
from psychopy.constants import (NOT_STARTED, STARTED, PLAYING, PAUSED, STOPPED, FINISHED, PRESSED, RELEASED, FOREVER)
from .task_base import Task
from .task_base import Fixation
from psychopy import logging
logging.console.setLevel(logging.ERROR)

from ..shared import config, utils

INITIAL_WAIT = 3
FINAL_WAIT = 10

TR = 1.49
STIMULI_DURATION = TR
LONG_ISI_BASE = 2 * TR + 0.5
SHORT_ISI_BASE = 1 * TR + 0.25
ITI = 1.25
IMAGES_FOLDER = "data/multfs/MULTIF_4_stim"

MULTFS_YES_KEY = "2"
MULTFS_NO_KEY = "3"
CONTINUE_KEY = "4"

INSTRUCTION_DURATION = 120

# TODO: modify to MRI screen size
screensize = config.EXP_WINDOW["size"]
# print("screensize:", screensize)
triplet_id_to_pos = [(-.5, 0), (.5, 0), ]

# STIMULI_SIZE = (screensize[0], screensize[1]/2)
STIMULI_SIZE = (1.3,.9)
print("stimuli size:", STIMULI_SIZE)

class multfs_base(Task):

    def __init__(self, block_path, task_name, *args, **kwargs):
        super().__init__(**kwargs)
        print(f"[multfs] loading conditions from: {block_path}")
        self.block_path = block_path
        self.task_name = task_name
        self.item_list = data.importConditions(block_path)
        self.temp_dict = {}
        self.instruction = instructions_converter(self.task_name) + "\n" + INSTRUCTIONS_DONE + "\n" + \
            """The beginning of a trial is indicated with a fixation cross at the center of the screen.\n
            The presence of a red dot during an object screen indicates that an answer response is not required yet.\n
            When ready press 3.
            """
        self.abbrev_instruction = abbrev_instructions_converter(self.task_name)
        # print("abbrev instruction:", self.abbrev_instructionobal start time )
        self.start_time = "DNS" # to tag output files
        self.globalClock = core.Clock() # to track the time since experiment start
        self.routineTimer = core.Clock() # to track time remaining of each (possibly non-slip) routine
        self.frameTolerance = 0.001 # how close to onset before 'same' frame
        self.storage_dict = {}

        self._trial_sampling_method = "sequential"

    def _setup(self, exp_win):
        self.fixation = visual.TextStim(exp_win, text="+", alignText="center", color="white")
        self.empty_text = visual.TextStim(exp_win, text="", alignText = "center", color = "white", height = 0.1)
        self.no_response_marker = visual.Circle(exp_win, 20, units='pix', fillColor=(255,0,0), colorSpace='rgb255')
        
        total_duration = (
            INITIAL_WAIT +
            self.n_trials * ( self.seq_len * STIMULI_DURATION + sum(self.trial_isis) ) +
            (self.n_trials - 1) * ITI +
            FINAL_WAIT
            )
        print(f"TOTAL DURATION: {total_duration}")

        super()._setup(exp_win)

    def _instructions(self, exp_win, ctl_win):
        yield True
        screen_text_bold = visual.TextStim(
            win=exp_win,
            name='introtext',
            text=self.abbrev_instruction,
            font='Arial',
            pos=(0, 0.5), height=0.1, ori=0,
            color="white", colorSpace='rgb', opacity=1,
            languageStyle='LTR',
            wrapWidth=config.WRAP_WIDTH,
            flipHoriz=config.MIRROR_X,
        )
        screen_text = visual.TextStim(
            win = exp_win,
            name = 'introtext',
            text=self.instruction,
            font = 'Arial',
            pos = (0,0), height = 0.05, ori = 0,
            color="white", colorSpace = 'rgb', opacity = 1,
            languageStyle = 'LTR',
            wrapWidth=config.WRAP_WIDTH,
            flipHoriz=config.MIRROR_X,
        )

        # -- prepare to start Routine "Intro" --
        for _frame in range(int(np.floor(config.FRAME_RATE * INSTRUCTION_DURATION))):
            screen_text_bold.draw(exp_win)
            screen_text.draw(exp_win)
            if ctl_win:
                screen_text_bold.draw(ctl_win)
                screen_text.draw(ctl_win)

            keys = psychopy.event.getKeys(keyList=['space', CONTINUE_KEY])
            if keys:
                break
            yield False
        # print("end of the instruction time:", resp_time)

    def _block_intro(self, exp_win, ctl_win, onset, n_trials = 4):
        screen_text_bold = visual.TextStim(
            win=exp_win,
            name='introtext_bold',
            text=self.abbrev_instruction,
            font='Arial',
            pos=(0, 0.2), height=0.1, ori=0,
            color="white", colorSpace='rgb', opacity=1,
            languageStyle='LTR',
            wrapWidth=config.WRAP_WIDTH,
            flipHoriz=config.MIRROR_X,
        )
        screen_text = visual.TextStim(
            win=exp_win,
            name='blockintrotext',
            text= 'New Block! \n\nEach block contains %d trials, each starts with fixation. \n\nWait to continue!' % n_trials, # todo: modify the key instructions
            font='Open Sans',
            pos=(0, 0), height=0.05, ori=0,
            color="white", colorSpace='rgb', opacity=1,
            languageStyle='LTR',
            wrapWidth=config.WRAP_WIDTH,
            flipHoriz=config.MIRROR_X,
        )

        # -- prepare to start Routine "Intro" --
        print("start of the block instruction:", self.globalClock.getTime())
        screen_text_bold.draw(exp_win)
        screen_text.draw(exp_win)
        if ctl_win:
            screen_text_bold.draw(ctl_win)
            screen_text.draw(ctl_win)
        utils.wait_until(self.task_timer, onset - 1./config.FRAME_RATE)
        yield True
        utils.wait_until(
            self.task_timer,
            onset + config.INSTRUCTION_DURATION - 10./config.FRAME_RATE
        )
        yield True
        psychopy.event.getKeys() # flush keys ?
        print("end of the block instruction:", self.globalClock.getTime())

    def _block_end(self, exp_win, ctl_win, onset):
        screen_text = visual.TextStim(
            win=exp_win,
            name='blockendtext',
            text= 'End of the block! \n\nWait to start next block', # todo: modify the key instructions
            font='Open Sans',
            pos=(0, 0), height=0.05, ori=0,
            color="white", colorSpace='rgb', opacity=1,
            languageStyle='LTR',
            wrapWidth=config.WRAP_WIDTH,
            flipHoriz=config.MIRROR_X,
        )
        utils.wait_until(self.task_timer, onset - 1./config.FRAME_RATE)
        # -- prepare to start Routine "Intro" --
        screen_text.draw(exp_win)
        if ctl_win:
            screen_text.draw(ctl_win)
        yield True
        utils.wait_until(
            self.task_timer,
            onset + config.INSTRUCTION_DURATION - 10./config.FRAME_RATE
        )
        yield True

    def _generate_unique_filename(self, suffix, time, ext="tsv"):
        fname = os.path.join(
            self.output_path, f"{self.output_fname_base}_{self.name}_{suffix}_{time}.{ext}"
        )
        fi = 1
        while os.path.exists(fname):
            fname = os.path.join(
                self.output_path,
                f"{self.output_fname_base}_{self.name}_{suffix}-{fi:03d}_{time}.{ext}",
            )
            fi += 1
        return fname

    def _save(self):
        if hasattr(self, 'trials'):
            self.trials.saveAsWideText(self._generate_unique_filename("events", self.start_time, "tsv"))
        return None

    def _run(self, exp_win, ctl_win):
        self.start_time = time.strftime("%H%M%S") # update to tag output files
        print("START TIME:", self.start_time)
        self.fixation.draw()
        yield True

        self.trials = data.TrialHandler(self.item_list, 1, method=self._trial_sampling_method)
        n_trials = len(self.trials.trialList)
        
        exp_win.logOnFlip(
            level=logging.EXP, msg=f"memory: {self.name} starting"
        )

        img = visual.ImageStim(exp_win, size=STIMULI_SIZE, units="norm", flipHoriz=config.MIRROR_X)
    
        final_wait_txt = visual.TextStim(
            exp_win,
            text="Waiting for scanner to finish capturing...",
            alignText="center",
            color="white",
            wrapWidth=config.WRAP_WIDTH,
            flipHoriz=config.MIRROR_X,
        )

        onset = INITIAL_WAIT

        trial_idx = 0
        for trial in self.trials:
            exp_win.logOnFlip(level=logging.EXP, msg=f"{self.name}_{self.feature}: trial {trial_idx}")


            for n_stim in range(self.seq_len):
                onset = (
                    INITIAL_WAIT + # wait before the first trial
                    (trial_idx) * ( self.seq_len * STIMULI_DURATION + sum(self.trial_isis) + ITI) + # previous trials buffer
                    n_stim*STIMULI_DURATION + sum(self.trial_isis[:n_stim]) # within-trial stimuli and ISIs buffer
                    )

                img.image = IMAGES_FOLDER + "/" + str(trial["ref%s" % str(n_stim+1)]) + "/image.png"
                img.pos = triplet_id_to_pos[trial[f"loc{n_stim+1}"]]
                img.draw()

                # flush response keys before the stimuli onset
                multfs_answer_keys = psychopy.event.getKeys([MULTFS_YES_KEY, MULTFS_NO_KEY, 'space'])
                # log responses leaking from the previous trial, in case we want to exclude corrupted trial
                self.trials.addData("late_responses_%d" % n_stim, multfs_answer_keys)

                if n_stim in self.no_response_frames:
                    self.no_response_marker.draw(exp_win)

                utils.wait_until(self.task_timer, onset - 1/config.FRAME_RATE)
                yield True
                self.trials.addData(
                    "stimulus_%d_onset" % n_stim,
                    self._exp_win_last_flip_time - self._exp_win_first_flip_time)
                utils.wait_until(
                    self.task_timer,
                    onset + STIMULI_DURATION - 1/config.FRAME_RATE,
                    keyboard_accuracy=.0001)
                yield True
                self.trials.addData(
                    "stimulus_%d_offset" % n_stim,
                    self._exp_win_last_flip_time - self._exp_win_first_flip_time)
                # wait until almost the end of the ISI to collect responses.
                utils.wait_until(
                    self.task_timer,
                    onset + STIMULI_DURATION + self.trial_isis[n_stim] - 10./config.FRAME_RATE,
                    keyboard_accuracy=.0001)

                multfs_answer_keys = psychopy.event.getKeys(
                    [MULTFS_YES_KEY, MULTFS_NO_KEY, 'space'], timeStamped=self.task_timer
                )

                if n_stim not in self.no_response_frames:
                    if len(multfs_answer_keys):
                        self.trials.addData("response_%d" % n_stim, multfs_answer_keys[-1][0])
                        self.trials.addData("response_%d_time" % n_stim, multfs_answer_keys[-1][1])
                        self.trials.addData("all_responses_%d" % n_stim, multfs_answer_keys)                

            self.fixation.draw()
            yield True
            if trial_idx < n_trials-1:
                utils.wait_until(self.task_timer, onset + STIMULI_DURATION + self.trial_isis[-1] + ITI - 9./config.FRAME_RATE)
            else:
                utils.wait_until(self.task_timer, onset + STIMULI_DURATION + self.trial_isis[-1] - 9./config.FRAME_RATE)
            yield True

            if trial_idx >= n_trials:
                self.trials.addData("trial_end", self.task_timer.getTime())
                break

            trial_idx += 1

        baseline_offset = onset + STIMULI_DURATION + self.trial_isis[-1] + FINAL_WAIT
        # Draw final wait text
        final_wait_txt.draw()
        yield True
        utils.wait_until(
            self.task_timer,
            baseline_offset - 1./config.FRAME_RATE)
        yield True
        print("END TIME:", self.start_time)


class multfs_dms(multfs_base):

    def __init__(self, block_path, task_name, n_trials, feature = "loc", session = None, **kwargs):
        super().__init__(block_path, task_name, **kwargs)

        self.feature = feature
        self.session = session # todo: add progress bar

        self.seq_len = 2
        self.no_response_frames = [0]
        self.trial_isis = [SHORT_ISI_BASE, LONG_ISI_BASE]
        self.n_trials = n_trials

class multfs_1back(multfs_base):

    def __init__(self, block_path, task_name, n_trials, feature = "loc", seq_len=6, session = None, **kwargs):
        super().__init__(block_path, task_name, **kwargs)
        self.seq_len = seq_len
        self.feature = feature
        self.session = session # todo: add progress bar
        self.no_response_frames = [0]
        self.trial_isis = [SHORT_ISI_BASE] + [LONG_ISI_BASE] * 5
        self.n_trials = n_trials

class multfs_CTXDM(multfs_base):

    def __init__(self, block_path, task_name, n_trials, feature = "lco", seq_len=3, session = None, **kwargs):
        super().__init__(block_path, task_name, **kwargs)
        self.seq_len = seq_len
        self.feature = feature
        self.session = session 
        self.no_response_frames = [0, 1]
        self.trial_isis = [SHORT_ISI_BASE, SHORT_ISI_BASE, LONG_ISI_BASE]
        self.n_trials = n_trials

class multfs_interdms_ABAB(multfs_base):

    def __init__(self, block_path, task_name, n_trials, feature = "loc", pattern = "ABAB", seq_len=4, session = None, **kwargs):
        super().__init__(block_path, task_name, **kwargs)
        self.seq_len = seq_len
        self.feature = feature
        self.pattern = pattern
        self.session = session # todo: add progress bar
        self.no_response_frames = [0, 1]
        self.trial_isis = [SHORT_ISI_BASE, SHORT_ISI_BASE, LONG_ISI_BASE, LONG_ISI_BASE]
        self.n_trials = n_trials

class multfs_interdms_ABBA(multfs_base):

    def __init__(self, block_path, task_name, n_trials, feature = "loc", pattern = "ABBA", seq_len=4, session = None, **kwargs):
        super().__init__(block_path, task_name, **kwargs)
        self.seq_len = seq_len
        self.feature = feature
        self.pattern = pattern
        self.session = session 
        self.no_response_frames = [0, 1]
        self.trial_isis = [SHORT_ISI_BASE, SHORT_ISI_BASE, LONG_ISI_BASE, LONG_ISI_BASE]
        self.n_trials = n_trials

INSTRUCTIONS_DONE = """1 = yes
2 = no \n\n
"""

def instructions_converter(task_name):
    ins_dict = {
        "dms_loc": """
            In this task, trials will have 2 objects. You must do the following:\n
            - When Object 2 appears, answer whether its LOCATION matches Object 1.\n
            """,

        "dms_obj": """
            In this task, trials will have 2 objects. You must do the following:\n
            - When Object 2 appears, answer whether its IDENTITY matches Object 1.\n
            """,

        "interdms_loc_ABBA": """
            In this task, trials will have 4 objects. You must do the following:\n
            Pattern ABBA — feature: LOCATION\n
            - When Object 3 appears, answer whether its LOCATION matches Object 2.\n
            - When Object 4 appears, answer whether its LOCATION matches Object 1.\n
            """,

        "interdms_ctg_ABBA": """
            In this task, trials will have 4 objects. You must do the following:\n
            Pattern ABBA — feature: CATEGORY\n
            - When Object 3 appears, answer whether its CATEGORY matches Object 2.\n
            - When Object 4 appears, answer whether its CATEGORY matches Object 1.\n
            """,

        "interdms_obj_ABBA": """
            In this task, trials will have 4 objects. You must do the following:\n
            Pattern ABBA — feature: IDENTITY\n
            - When Object 3 appears, answer whether its IDENTITY matches Object 2.\n
            - When Object 4 appears, answer whether its IDENTITY matches Object 1.\n
            """,

        "interdms_loc_ABAB": """
            In this task, trials will have 4 objects. You must do the following:\n
            Pattern ABAB — feature: LOCATION\n
            - When Object 3 appears, answer whether its LOCATION matches Object 1.\n
            - When Object 4 appears, answer whether its LOCATION matches Object 2.\n
            """,

        "interdms_ctg_ABAB": """
            In this task, trials will have 4 objects. You must do the following:\n
            Pattern ABAB — feature: CATEGORY\n
            - When Object 3 appears, answer whether its CATEGORY matches Object 1.\n
            - When Object 4 appears, answer whether its CATEGORY matches Object 2.\n
            """,

        "interdms_obj_ABAB": """
            In this task, trials will have 4 objects. You must do the following:\n
            Pattern ABAB — feature: IDENTITY\n
            - When Object 3 appears, answer whether its IDENTITY matches Object 1.\n
            - When Object 4 appears, answer whether its IDENTITY matches Object 2.\n
            """,

        "1back_loc": """
            In this task, trials will have 6 objects. You must do the following:\n
            - For each new object (Object n+1), answer whether its LOCATION matches the previous object (Object n).\n
            """,

        "1back_obj": """
            In this task, trials will have 6 objects. You must do the following:\n
            - For each new object (Object n+1), answer whether its IDENTITY matches the previous object (Object n).\n
            """,

        "1back_ctg": """
            In this task, trials will have 6 objects. You must do the following:\n
            - For each new object (Object n+1), answer whether its CATEGORY matches the previous object (Object n).\n
            """,

        "ctxdm_col": """
            In this task, trials will have 3 objects. You must do the following:\n
            Contextual Decision-Making: CATEGORY → IDENTITY → LOCATION\n
            - If Objects 1 and 2 match in CATEGORY, answer whether Object 3 matches Object 2 by IDENTITY.\n
            - Otherwise, answer whether Object 3 matches Object 2 by LOCATION.\n
            """,

        "ctxdm_lco": """
            In this task, trials will have 3 objects. You must do the following:\n
            Contextual Decision-Making: LOCATION → CATEGORY → IDENTITY\n
            - If Objects 1 and 2 match in LOCATION, answer whether Object 3 matches Object 2 by CATEGORY.\n
            - Otherwise, answer whether Object 3 matches Object 2 by IDENTITY.\n
            """,
    }

    return ins_dict[task_name]


def abbrev_instructions_converter(task_name):
    ins_dict = {
        "dms_loc": "DMS-LOCATION",

        "dms_obj": "DMS-IDENTITY",

        "interdms_loc_ABBA": """interDMS-ABBA-LOCATION\n
                              """,
        "interdms_ctg_ABBA": """interDMS-ABBA-CATEGORY\n
                                  """,
        "interdms_obj_ABBA": """interDMS-ABBA-IDENTITY\n
                                  """,
        "interdms_loc_ABAB": """interDMS-ABAB-LOCATION\n
                              """,
        "interdms_ctg_ABAB": """interDMS-ABAB-CATEGORY\n
                                  """,
        "interdms_obj_ABAB": """interDMS-ABAB-IDENTITY\n
                                  """,
        "1back_loc": """1back-LOCATION\n
                    """,
        "1back_obj": """1back-IDENTITY\n
                    """,
        "1back_ctg": """1back-CATEGORY\n
                    """,

        "ctxdm_col": """ctxDM-CATEGORY-IDENTITY-LOCATION\n
                        """,
        "ctxdm_lco": """ctxDM-LOCATION-CATEGORY-IDENTITY\n
                    """,
    }
    return ins_dict[task_name]
