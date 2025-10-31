import os, time, pandas,re
import warnings
from psychopy import logging

warnings.filterwarnings("ignore")             # suppress Python warnings
logging.console.setLevel(logging.CRITICAL+1) 
from psychopy import prefs
prefs.hardware['audioLib'] = ['ptb']


from psychopy import visual, sound, event, core, logging

from ..tasks import video, task_base


from .task_base import Task
from ..shared import config, utils
from ..shared.eyetracking import fixation_dot
import pandas as pd
from pathlib import Path
from datetime import datetime

#task : 1 run = 1 playlist = around 10 audio tracks
#repeat for n songs in subXX_runXX.csv :
#   step 1: DEFAULT_INSTRUCTION
#   step 2: display audio
#   step 3: Auditory imagery assessment
#   step 4: Familiarity assessment

#Global Variables if multiples tasks

QUESTION_DURATION = 10 #5
INSTRUCTION_DURATION = 25
MUSIC_DURATION = 30
SONG_RAITING_BUFFER = 2
ISI = 5
FINAL_WAIT = 10
DEFAULT_INSTRUCTION = (
    f"You will hear a {MUSIC_DURATION} second music excerpt.\n"
    "Listen to the music without closing your eyes.\n"
    f"At the end of the {MUSIC_DURATION} seconds, you will be prompted to indicate how much you enjoyed the music "
    "by pressing one of the 5 buttons on the controller:\n\n"
    "1 - didn't like it at all\n"
    "2 - somewhat disliked it\n"
    "3 - neutral\n"
    "4 - somewhat liked it\n"
    "5 - really liked it\n\n"
    "Press 1 when ready."
)

RATING_PROMPT = (
    "Please indicate this by pressing one of the 5 buttons on the controller:\n\n"
    "1 - didn't like it at all\n"
    "2 - somewhat disliked it\n"
    "3 - neutral\n"
    "4 - somewhat liked it\n"
    "5 - really liked it\n\n"
)

AUDITORY_IMAGERY_ASSESSMENT = (
    "How much did you enjoy the music?",
    RATING_PROMPT,
    ["didn't like it at all", "", "neutral", "", "really liked it"]
)

def pause_screen(exp_win, ctl_win, text="We are setting up the scanner for the next block.\n\nPlease wait...",
                 wait_key='8', height=0.045):
    """Show a full-screen message until `wait_key` is pressed. If wait_key=None, show indefinitely."""

    msg = visual.TextStim(
        exp_win, text=text, color="white", units="height",
        height=height, wrapWidth=1.6, alignText="center",
        flipHoriz=config.MIRROR_X
    )
    msg_ctl = None
    if ctl_win:
        msg_ctl = visual.TextStim(
            ctl_win, text=text, color="white", units="height",
            height=height, wrapWidth=1.6, alignText="center",
            flipHoriz=config.MIRROR_X
        )

    event.clearEvents()
    while True:
        msg.draw(exp_win)
        if msg_ctl:
            msg_ctl.draw(ctl_win)
        yield True
        if wait_key:
            if wait_key in event.getKeys([wait_key]):
                break
        else:
            # no key configured → just keep showing (caller controls timing)
            pass
class Playlist(Task):
#Derived from SoundTaskBase (Narratives task)
    def __init__(self, tsv_path, initial_wait=ISI, final_wait=FINAL_WAIT, question_duration = QUESTION_DURATION, sr_buffer=SONG_RAITING_BUFFER, isi=ISI ,block_dir=None, **kwargs):
        super().__init__(**kwargs)

        if not os.path.exists(tsv_path):
            raise ValueError("File %s does not exists" % tsv_path)
        else :
            self.tsv_path = tsv_path
            file = open(tsv_path, "r")
            self.playlist = pandas.read_table(file, sep='\t')
            file.close()
            parent = os.path.basename(os.path.dirname(self.tsv_path))  # e.g., "B3"
            m = re.match(r"[Bb](\d+)$", parent)
            self.block_id = int(m.group(1)) if m else None

        self.initial_wait = initial_wait
        self.block_dir = block_dir
        self.final_wait = final_wait
        self.sr_buffer = sr_buffer
        self.isi = isi
        self.question_duration = question_duration
        self.instruction = DEFAULT_INSTRUCTION

        self.duration = self.playlist.shape[0]
        self._progress_bar_refresh_rate = None

    def _instructions(self, exp_win, ctl_win):
        screen_text = visual.TextStim(
            exp_win,
            text=self.instruction,
            alignText="center",
            color="white",
            units='height',
            flipHoriz=config.MIRROR_X,
            height=0.03
        )

        for flip_idx, _ in enumerate(utils.wait_until_yield(
            core.monotonicClock,
            core.getTime()+ INSTRUCTION_DURATION,
            keyboard_accuracy=.1)):
            keys = event.getKeys(keyList=['1'])
            if keys:
                break

            if flip_idx < 2:
                screen_text.draw(exp_win)
                if ctl_win:
                    screen_text.draw(ctl_win)
                yield True
            yield
        yield True

        

        label = f"Block {self.block_id} will begin shortly..." if self.block_id is not None else "Block"
        block_text = visual.TextStim(
            exp_win,
            text=label,
            color="white",
            units='height',
            height=0.06,
            flipHoriz=config.MIRROR_X,
            alignText="center",
        )

        deadline = core.getTime() + 2.0  # ~2 seconds
        event.clearEvents()
        #while True:
        while core.getTime()<deadline:
            #if event.getKeys(keyList=['1']):
                #break
            block_text.draw(exp_win)
            if ctl_win:
                block_text.draw(ctl_win)
            yield True


    def _setup(self, exp_win):
        super()._setup(exp_win)
        self.fixation = fixation_dot(exp_win)
        label_end = f"End of block.    Waiting for scanner to finish cycle..." if self.block_id is not None else "Block"
        self.block_end_text = visual.TextStim(
            exp_win,
            text=label_end,
            color="white",
            units='height',
            height=0.06,
            flipHoriz=config.MIRROR_X,
            alignText="center",
        )
    
    def _questionnaire(self, exp_win, ctl_win, question, prompt, answers):
        # Clear previous key events
        event.clearEvents()

        # Setup parameters
        num_options = len(answers)
        default_index = num_options // 2
        selected_index = default_index
        last_key = None
        KEY_TO_SCORE = {'1': 1, '2': 2, '3': 3, '4': 4, '6': 5}

        # ------------------------------
        # Consistent, proportional layout
        # ------------------------------
        win_w, win_h = exp_win.size
        aspect = win_w / win_h
        num_options = len(answers)  # e.g., 5

        # Put a dark background so white text pops
        # (Uncomment if needed)
        # exp_win.color = 'black'
        # exp_win.flip()

        # Section Y anchors (in "height" units; 1.0 = full screen height)
        QUESTION_Y = 0.32    # top section (top-anchored)
        PROMPT_Y   = 0.24     # middle section (top-anchored)
        SCALE_Y    = -0.10    # baseline for the rating line

        # Width of the rating scale (fraction of full width)
        scale_frac   = 0.60                     # 60% of screen width
        scale_width  = aspect * scale_frac      # width in "height" units
        half_w       = scale_width / 2.0
        left_x, right_x = -half_w, +half_w
        x_spacing = (right_x - left_x) / (num_options - 1)

        # ------------------------------
        # Question (top)
        # ------------------------------
        question_text = visual.TextStim(
            exp_win,
            text=question,
            units="height",
            pos=(0, QUESTION_Y),
            height=0.03,                         # 5% of screen height
            wrapWidth=aspect * 0.95,             # wrap at ~95% of screen width
            color="white",
            alignText="center",
            anchorVert="top",                    # keep TOP at QUESTION_Y
            font="Arial Bold",
            flipHoriz=config.MIRROR_X
        )

        # ------------------------------
        # Prompt (middle)
        # ------------------------------
        prompt_text = visual.TextStim(
            exp_win,
            text=prompt,
            units="height",
            pos=(0, PROMPT_Y),
            height=0.028,
            wrapWidth=aspect * 0.95,
            color="white",
            alignText="center",
            anchorVert="top",
            font="Arial",
            flipHoriz=config.MIRROR_X
        )

        # ------------------------------
        # Rating UI (bottom)
        # ------------------------------
        # Line (NOTE: lineWidth is in **pixels**, not "height")
        line = visual.Line(
            exp_win,
            start=(left_x, SCALE_Y),
            end=(right_x, SCALE_Y),
            units="height",
            lineWidth=4,                         # px; make it clearly visible
            lineColor=(-1, -1, -1),
            autoLog=False,
        )

        # Bullets (Circle lineWidth is also in px)
        bullets = [
            visual.Circle(
                exp_win,
                units="height",
                radius=0.015,                    # ~1.5% of screen height
                pos=(left_x + i * x_spacing, SCALE_Y),
                fillColor=(1, 1, 1),             # white fill for visibility
                lineColor=(1, 1, 1),
                lineWidth=2,                     # px
                autoLog=False,
            )
            for i in range(num_options)
        ]

        # Legends under the bullets
        legend_y = SCALE_Y - 0.06               # ~6% below the line
        legends = [
            visual.TextStim(
                exp_win,
                text=label,
                units="height",
                pos=(left_x + i * x_spacing, legend_y),
                wrapWidth=scale_width * 0.30,    # wrap relative to the scale width
                height=0.028,
                alignText="center",
                color="white",
                bold=True,
                flipHoriz=config.MIRROR_X,
                anchorVert="center",
            )
            for i, label in enumerate(answers)
        ]

        # Main loop
        flip_count = 0
        final_press = None
        end_time = self.task_timer.getTime() + self.question_duration

        for _ in utils.wait_until_yield(self.task_timer, end_time, keyboard_accuracy=0.0001):
            keys = event.getKeys(['1', '2', '3', '4', '6'])
            if keys:
                key = keys[-1]
                last_key = key
                selected_index = min(int(key) - 1, num_options - 1)
                score = KEY_TO_SCORE.get(key, selected_index + 1)

                # Update bullet colors: selected is white fill with red border
                for i, bullet in enumerate(bullets):
                    if i == selected_index:
                        bullet.fillColor = (1, 1, 1)
                        bullet.lineColor = (1, 0, 0)
                    else:
                        bullet.fillColor = (-1, -1, -1)
                        bullet.lineColor = (1, 1, 1)

                # Draw updated screen
                line.draw(exp_win)
                question_text.draw(exp_win)
                prompt_text.draw(exp_win)
                for legend, bullet in zip(legends, bullets):
                    legend.draw(exp_win)
                    bullet.draw(exp_win)
                yield True

                # Wait 2 seconds before feedback
                core.wait(2.0)

                # Log response
                final_press = {
                    "track": self._current_seg["track_name"],
                    "path": self._current_seg["path"],
                    "segment_start": float(self._current_seg["segment_start"]),
                    "segment_len": float(self._current_seg["segment_len"]),
                    "onset": float(self._current_seg['onset']),
                    "offset": float(self._current_seg['offset']),
                    "question": question,
                    "value": score,
                    "confirmation": "yes"
                }
                
            if flip_count > 1:
                time.sleep(0.01)
                continue

            exp_win.logOnFlip(level=logging.EXP, msg=f"rating {selected_index}")

            # Update bullet colors: default state
            for i, bullet in enumerate(bullets):
                bullet.fillColor = (-1, -1, -1)
                bullet.lineColor = (1, 1, 1)

            # Draw all elements
            line.draw(exp_win)
            question_text.draw(exp_win)
            prompt_text.draw(exp_win)
            for legend, bullet in zip(legends, bullets):
                legend.draw(exp_win)
                bullet.draw(exp_win)

            yield True

            flip_count += 1
            

        if final_press == None:
            # Timeout: record default response
            self._events.append({
                "track": self._current_seg["track_name"],
                "path": self._current_seg["path"],
                "segment_start": float(self._current_seg["segment_start"]),
                "segment_len": float(self._current_seg["segment_len"]),
                "onset": float(self._current_seg['onset']),
                "offset": float(self._current_seg['offset']),
                "question": question,
                "value": -1,
                "confirmation": "no"
            })
        else:
            self._events.append(final_press)

        # Clear screen
        yield True
    
    
    

    def _run(self, exp_win, ctl_win):
        previous_track_offset = 0
        #first bullseye
        for stim in self.fixation:
            stim.draw(exp_win)
        yield True
        next_onset = self.initial_wait

        for index, track in self.playlist.iterrows():
           
            
            #setup track
            track_path = track['path']
            seg_start = float(track.get('start', 10))
            seg_dur   = float(track.get('dur', MUSIC_DURATION))
            seg_stop  = seg_start + seg_dur
            self.track_name = os.path.split(track_path)[1]
                        
            self.sound = sound.Sound(track_path,startTime=seg_start,stopTime=seg_stop,volume=5)
            self.duration = self.sound.duration

            self.progress_bar.set_description(
                f"Trial {index}:: {self.track_name}"
            )
            self.progress_bar.update(1)

            #initial wait (bullseye)
            for _ in utils.wait_until_yield(
                self.task_timer,
                next_onset,
                keyboard_accuracy=.1):
                yield

            #Flush bullseye from screen before track
            yield True

            #track playing (variable timing)
            track_onset = self.task_timer.getTime(applyZero=True)
            self.sound.play()
            
            #sound.duration 
            for _ in utils.wait_until_yield(self.task_timer,
                                            track_onset + self.sound.duration + self.sr_buffer,
                                            keyboard_accuracy=.1):
                yield

            #ensure music track has been completely played
            while self.sound.status > 0:
                pass

            #display Questionnaire (variable timing, max 5s)
            self._current_seg = {
                "path": os.path.abspath(track_path),
                "segment_start": seg_start,
                "segment_len": seg_dur,
                "track_name": self.track_name,
                "onset": track_onset,
                "offset": track_onset + self.sound.duration
                

            }

            yield from self._questionnaire(exp_win, ctl_win,
                                           question=AUDITORY_IMAGERY_ASSESSMENT[0],
                                           prompt=AUDITORY_IMAGERY_ASSESSMENT[1],
                                           answers=AUDITORY_IMAGERY_ASSESSMENT[2])

            #display bullseye for netx iteration
            for stim in self.fixation:
                stim.draw(exp_win)
            yield True

            previous_track_offset = self.task_timer.getTime(applyZero=True)
            next_onset = previous_track_offset + self.isi

        self.block_end_text.draw(exp_win)
        if ctl_win:
            self.block_end_text.draw(ctl_win)
        yield True

        yield from pause_screen(
            exp_win, ctl_win,
            text="We are setting up the scanner for the next block.\n\nPlease wait...",
            wait_key='8'
        )


        #print(f"{'*'*25} PREPARE TO STOP {'*'*25}")
        yield from utils.wait_until_yield(self.task_timer, previous_track_offset + self.final_wait)
        #print(f"{'#'*25} STOP SCANNER    {'#'*25}")

    def _stop(self, exp_win, ctl_win):
        if hasattr(self, 'sound'):
            self.sound.stop()
        yield True

    def _save(self):   
        block_dir = Path(self.block_dir)
        fname_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_csv = block_dir / f"results_{fname_time}.csv"

        # Build events df
        ev_rows = []
        for e in self._events:
            ev_rows.append({
                "path": e.get("path"),
                "segment_start": float(e.get("segment_start", 0.0)),
                "segment_len": float(e.get("segment_len", 0.0)),
                "rating_value": e.get("value"),
                "confirmation": e.get("confirmation"),
                "onset": float(e.get("onset")),
                "offset": float(e.get("offset")),
            })
        ev_df = pd.DataFrame(ev_rows)

        # import pdb;pdb.set_trace()
        ev_df.to_csv(results_csv, index=False)