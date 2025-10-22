import os, time, pandas,re
from psychopy import prefs
prefs.hardware['audioLib'] = ['ptb']
#prefs.hardware['audioLib'] = ['sounddevice','ptb']  # try sounddevice first

from psychopy import visual, sound, event, core, logging
#import sounddevice as sd
#sd.default.device = (None, 3)

from .task_base import Task
from ..shared import config, utils
from ..shared.eyetracking import fixation_dot
import pandas as pd
from pathlib import Path

#task : 1 run = 1 playlist = around 10 audio tracks
#repeat for n songs in subXX_runXX.csv :
#   step 1: DEFAULT_INSTRUCTION
#   step 2: display audio
#   step 3: Auditory imagery assessment
#   step 4: Familiarity assessment

#Global Variables if multiples tasks

QUESTION_DURATION = 7 #5
INSTRUCTION_DURATION = 25
MUSIC_DURATION = 20
FEEDBACK_DURATION = 10
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

AUDITORY_IMAGERY_ASSESSMENT = (
    "How much did you enjoy the music?",
    ["didn't like it at all", "", "neutral", "", "really liked it"]
)
class Playlist(Task):
#Derived from SoundTaskBase (Narratives task)
    def __init__(self, tsv_path, initial_wait=6, final_wait=9, question_duration = 5, isi=2,block_dir=None, **kwargs):
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
        self.isi = 2
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

        label = f"Block {self.block_id}" if self.block_id is not None else "Block"
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

    def _handle_controller_presses(self):
        #self._new_key_pressed = event.getKeys('lra')
        self._new_key_pressed = event.getKeys(['1','2','3','4','5'])

    """
    def _questionnaire(self, exp_win, ctl_win, question, answers):
        # flush keys
        event.getKeys(['1','2','3','4','5'])
        n_pts = len(answers)
        default_response = n_pts // 2
        response = default_response

        KEY_TO_SCORE = {'1':1, '2':2, '3':3, '4':4, '5':6}
        last_numeric_key = None

        exp_win.setColor([0] * 3, colorSpace='rgb')
        win_width = exp_win.size[0]
        y_spacing=80
        scales_block_x = win_width * 0.25
        scales_block_y = exp_win.size[1] * 0.1
        extent = win_width * 0.2
        x_spacing= (scales_block_x  + extent) * 2 / (n_pts - 1)
        y_pos = scales_block_y - y_spacing

        #----------setup-Questionnaire-------------------------
        line = visual.Line(
            exp_win,
            (-(scales_block_x + extent), y_pos),
            (scales_block_x + extent, y_pos),
            units="pix",
            lineWidth=6,
            autoLog=False,
            lineColor=(-1, -1, -1)
        )

        bullets = [
            visual.Circle(
                exp_win,
                units="pix",
                radius=10,
                pos=(-(scales_block_x + extent) + i * x_spacing, y_pos),
                fillColor=(1, 1, 1) if default_response == i else (-1, -1, -1),
                lineColor=(-1, -1, -1),
                lineWidth=10,
                autoLog=False,
            )
            for i in range(n_pts)
        ]

        legends = [
            visual.TextStim(
                exp_win,
                text=answer,
                units="pix",
                pos=(-(scales_block_x + extent) + i * x_spacing, exp_win.size[1] * 0.1),
                wrapWidth=win_width * 0.12,
                height=y_spacing / 4.5,
                anchorHoriz="center",
                alignText="center",
                bold=True
            )
            for i, answer in enumerate(answers)
        ]

        text = visual.TextStim(
            exp_win,
            text=question,
            units="pix",
            pos=(-(scales_block_x + extent), y_pos + exp_win.size[1] * 0.30),
            wrapWidth=win_width-(win_width*0.1),
            height=y_spacing / 3,
            anchorHoriz="left",
            alignText="left"
        )

        #---run-Questionnaire--------------------------------------
        n_flips = 0
        for _ in utils.wait_until_yield(
            self.task_timer,
            self.task_timer.getTime() + self.question_duration,
            keyboard_accuracy=.0001):

            # immediate-submit on 1..5
            new_keys = event.getKeys(['1','2','3','4','5'])
            if new_keys:
                k = new_keys[-1][0]  # most recent
                last_numeric_key = k
                response = min(int(k) - 1, n_pts - 1)
                stored_value = KEY_TO_SCORE.get(k, response + 1)
                self._events.append({
                    "track": self._current_seg["track_name"],
                    "path": self._current_seg["path"],
                    "segment_start": float(self._current_seg["segment_start"]),
                    "segment_len": float(self._current_seg["segment_len"]),
                    "question": question,
                    "value": stored_value,
                    "confirmation": "yes"
                })
                break

            if n_flips > 1:
                time.sleep(.01)
                continue

            exp_win.logOnFlip(level=logging.EXP, msg="rating %s" % response)

            for bullet_n, bullet in enumerate(bullets):
                bullet.fillColor = (1, 1, 1) if response == bullet_n else (-1, -1, -1)

            line.draw(exp_win)
            text.draw(exp_win)
            for legend, bullet in zip(legends, bullets):
                legend.draw(exp_win)
                bullet.draw(exp_win)

            yield True
            n_flips += 1

        else:
            # timeout -> take current response
            stored_value = KEY_TO_SCORE.get(last_numeric_key, response + 1)
            self._events.append({
                "track": self._current_seg["track_name"],
                "path": self._current_seg["path"],
                "segment_start": float(self._current_seg["segment_start"]),
                "segment_len": float(self._current_seg["segment_len"]),
                "question": question,
                "value": stored_value,
                "confirmation": "no"
            })

        # Flush questionnaire from screen
        yield True
    """
    
    def _questionnaire(self, exp_win, ctl_win, question, answers):
        # Clear previous key events
        event.clearEvents()

        # Setup parameters
        num_options = len(answers)
        default_index = num_options // 2
        selected_index = default_index
        last_key = None
        KEY_TO_SCORE = {'1': 1, '2': 2, '3': 3, '4': 4, '5': 6}

        # Layout calculations
        win_width, win_height = exp_win.size
        y_spacing = 80
        block_x = win_width * 0.25
        block_y = win_height * 0.1
        extent = win_width * 0.2
        x_spacing = (block_x + extent) * 2 / (num_options - 1)
        y_pos = block_y - y_spacing

        # Create visual elements
        line = visual.Line(
            exp_win,
            start=(-block_x - extent, y_pos),
            end=(block_x + extent, y_pos),
            units="pix",
            lineWidth=6,
            autoLog=False,
            lineColor=(-1, -1, -1),
        )

        bullets = [
            visual.Circle(
                exp_win,
                units="pix",
                radius=10,
                pos=(-block_x - extent + i * x_spacing, y_pos),
                fillColor=(-1, -1, -1),  # black fill
                lineColor=(1, 1, 1),     # white border
                lineWidth=10,
                autoLog=False,
            )
            for i in range(num_options)
        ]

        legends = [
            visual.TextStim(
                exp_win,
                text=label,
                units="pix",
                pos=(-block_x - extent + i * x_spacing, block_y),
                wrapWidth=win_width * 0.12,
                height=y_spacing / 4.5,
                anchorHoriz="center",
                alignText="center",
                bold=True
            )
            for i, label in enumerate(answers)
        ]

        question_text = visual.TextStim(
            exp_win,
            text=question,
            units="pix",
            pos=(-block_x - extent, y_pos + win_height * 0.30),
            wrapWidth=win_width * 0.9,
            height=y_spacing / 3,
            anchorHoriz="left",
            alignText="left"
        )

        # Main loop
        flip_count = 0
        end_time = self.task_timer.getTime() + self.question_duration

        for _ in utils.wait_until_yield(self.task_timer, end_time, keyboard_accuracy=0.0001):
            keys = event.getKeys(['1', '2', '3', '4', '5'])
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
                for legend, bullet in zip(legends, bullets):
                    legend.draw(exp_win)
                    bullet.draw(exp_win)
                yield True

                # Wait 2 seconds before feedback
                core.wait(2.0)

                # Log response
                self._events.append({
                    "track": self._current_seg["track_name"],
                    "path": self._current_seg["path"],
                    "segment_start": float(self._current_seg["segment_start"]),
                    "segment_len": float(self._current_seg["segment_len"]),
                    "question": question,
                    "value": score,
                    "confirmation": "yes"
                })

                # Show feedback and exit
                yield from self._feedback_screen(exp_win, ctl_win, question, answers, selected_index)
                break
            

            if flip_count > 1:
                time.sleep(0.01)
                continue
            """
            exp_win.logOnFlip(level=logging.EXP, msg=f"rating {selected_index}")

            # Update bullet colors: default state
            for i, bullet in enumerate(bullets):
                bullet.fillColor = (-1, -1, -1)
                bullet.lineColor = (1, 1, 1)

            # Draw all elements
            line.draw(exp_win)
            question_text.draw(exp_win)
            for legend, bullet in zip(legends, bullets):
                legend.draw(exp_win)
                bullet.draw(exp_win)

            yield True
            """
            flip_count += 1
            

        else:
            # Timeout: record default response
            score = KEY_TO_SCORE.get(last_key, selected_index + 1)
            self._events.append({
                "track": self._current_seg["track_name"],
                "path": self._current_seg["path"],
                "segment_start": float(self._current_seg["segment_start"]),
                "segment_len": float(self._current_seg["segment_len"]),
                "question": question,
                "value": score,
                "confirmation": "no"
            })

        # Clear screen
        yield True

    def _feedback_screen(self, exp_win, ctl_win, question, answers, choice_idx):
        """
        Show a brief confirmation screen highlighting the chosen rating.
        """
        n_pts = len(answers)
        win_width = exp_win.size[0]
        y_spacing = 80
        scales_block_x = win_width * 0.25
        scales_block_y = exp_win.size[1] * 0.1
        extent = win_width * 0.2
        x_spacing = (scales_block_x + extent) * 2 / (n_pts - 1)
        y_pos = scales_block_y - y_spacing

        line = visual.Line(
            exp_win,
            (-(scales_block_x + extent), y_pos),
            (scales_block_x + extent, y_pos),
            units="pix",
            lineWidth=6,
            autoLog=False,
            lineColor=(-1, -1, -1)
        )

        bullets = [
            visual.Circle(
                exp_win,
                units="pix",
                radius=10,
                pos=(-(scales_block_x + extent) + i * x_spacing, y_pos),
                fillColor=(1, 1, 1) if choice_idx == i else (-1, -1, -1),
                lineColor=(-1, -1, -1),
                lineWidth=10,
                autoLog=False,
            )
            for i in range(n_pts)
        ]

        legends = [
            visual.TextStim(
                exp_win,
                text=answers[i],
                units="pix",
                pos=(-(scales_block_x + extent) + i * x_spacing, exp_win.size[1] * 0.1),
                wrapWidth=win_width * 0.12,
                height=y_spacing / 4.5,
                anchorHoriz="center",
                alignText="center",
                bold=True
            )
            for i in range(n_pts)
        ]

        header = visual.TextStim(
            exp_win,
            text=question,
            units="pix",
            pos=(-(scales_block_x + extent), y_pos + exp_win.size[1] * 0.30),
            wrapWidth=win_width - (win_width * 0.1),
            height=y_spacing / 3,
            anchorHoriz="left",
            alignText="left"
        )

        confirm = visual.TextStim(
            exp_win,
            text=f"Selected: {choice_idx + 1}",
            color="yellow",
            units="height",
            height=0.035,
            pos=(0, 0.32),
            alignText="center"
        )

        deadline = self.task_timer.getTime() + FEEDBACK_DURATION
        while self.task_timer.getTime() < deadline:
            
            line.draw(exp_win)
            header.draw(exp_win)
            confirm.draw(exp_win)
            for legend, bullet in zip(legends, bullets):
                legend.draw(exp_win)
                bullet.draw(exp_win)
            if ctl_win:
                line.draw(ctl_win)
                header.draw(ctl_win)
                confirm.draw(ctl_win)
                for legend, bullet in zip(legends, bullets):
                    legend.draw(ctl_win)
                    bullet.draw(ctl_win)
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
            #track_path =  r'C:\Users\Bashivan Lab\Desktop\NACC\task_stimuli\blues.00001.wav'
            seg_start = float(track.get('start', 0.0))
            seg_dur   = float(track.get('dur', MUSIC_DURATION))
            seg_stop  = seg_start + seg_dur
            self.track_name = os.path.split(track_path)[1]
            print('playing sound')
            print('track path',track_path)
            
            self.sound = sound.Sound(track_path,startTime=seg_start,stopTime=seg_stop,volume=1)

            
            planned_duration = seg_dur
            #self.duration = self.sound.duration

            self.progress_bar.set_description(
                f"Trial {index}:: {self.track_name}"
            )
            self.progress_bar.update(1)

            #initial wait (bullseye 2s)
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
            for _ in utils.wait_until_yield(self.task_timer,
                                            next_onset + self.initial_wait + self.sound.duration,
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
}
            yield from self._questionnaire(exp_win, ctl_win,
                                           question=AUDITORY_IMAGERY_ASSESSMENT[0],
                                           answers=AUDITORY_IMAGERY_ASSESSMENT[1])

            #display bullseye for netx iteration
            for stim in self.fixation:
                stim.draw(exp_win)
            yield True

            self.playlist.at[index, 'onset']=track_onset
            previous_track_offset = self.task_timer.getTime(applyZero=True)
            next_onset = previous_track_offset + self.isi
        #final wait
        print(f"{'*'*25} PREPARE TO STOP {'*'*25}")
        yield from utils.wait_until_yield(self.task_timer, previous_track_offset + self.final_wait)
        print(f"{'#'*25} STOP SCANNER    {'#'*25}")

    def _stop(self, exp_win, ctl_win):
        if hasattr(self, 'sound'):
            self.sound.stop()
        yield True

    def _save(self):
        if not self.block_dir:
            # fallback: old behavior
            self.playlist.to_csv(self._generate_unique_filename("events", "tsv"), sep='\t', index=False)
            return
   
        block_dir = Path(self.block_dir)
        plan_csv = block_dir / "plan.csv"
        results_csv = block_dir / "results.csv"

        # Build events df
        ev_rows = []
        for e in self._events:
            ev_rows.append({
                "path": e.get("path"),
                "segment_start": float(e.get("segment_start", 0.0)),
                "segment_len": float(e.get("segment_len", 0.0)),
                "rating_value": e.get("value"),
                "confirmation": e.get("confirmation"),
                "played": 1,
            })
        ev_df = pd.DataFrame(ev_rows)

        # Load plan + left-join on (path, start, len)
        plan_df = pd.read_csv(plan_csv)
        # plan has song_relpath; build absolute path column to match events
        subj_root = block_dir.parents[2]  # .../Sub-XX
        plan_df["path"] = plan_df["song_relpath"].apply(
            lambda p: str((Path(p) if Path(p).is_absolute() else (subj_root / p)).resolve())
        )

        merged = plan_df.merge(
            ev_df,
            how="left",
            left_on=["path","segment_start","segment_len"],
            right_on=["path","segment_start","segment_len"]
        )
        merged.to_csv(results_csv, index=False)