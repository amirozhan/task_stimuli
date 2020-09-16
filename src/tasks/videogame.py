import os, sys, time, queue
import numpy as np
import threading

from psychopy import visual, core, data, logging, event, sound, constants
from .task_base import Task

from ..shared import config

import retro

DEFAULT_GAME_NAME = 'ShinobiIIIReturnOfTheNinjaMaster-Genesis'

#KEY_SET = 'zx__abudlr_y'
#KEY_SET = 'zx__udlry___'
#KEY_SET = ['a','b','c','d','up','down','left','right','x','y','z','k']
#KEY_SET = ['x','z','_','_','up','down','left','right','c','_','_','_']
KEY_SET = ['y','a','_','_','u','d','l','r','b','_','_','_']

#KEY_SET = '0123456789'

_keyPressBuffer = []
_keyReleaseBuffer = []
import pyglet

def _onPygletKeyPress(symbol, modifier):
    if modifier:
        event._onPygletKey(symbol, modifier)
    global _keyPressBuffer
    keyTime = core.getTime()
    key = pyglet.window.key.symbol_string(symbol).lower().lstrip('_').lstrip('NUM_')
    _keyPressBuffer.append((key, keyTime))

def _onPygletKeyRelease(symbol, modifier):
    global _keyReleaseBuffer
    keyTime = core.getTime()
    key = pyglet.window.key.symbol_string(symbol).lower().lstrip('_').lstrip('NUM_')
    _keyReleaseBuffer.append((key, keyTime))

class SoundDeviceBlockStream(sound.backend_sounddevice.SoundDeviceSound):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocks = queue.Queue()
        self.lock = threading.Lock()

    def add_block(self, block):
        with self.lock:
            self.blocks.put(block)

    def _nextBlock(self):
        if self.status == constants.STOPPED:
            return
        if self.blocks.empty():
            block = np.zeros((self.blockSize,2),dtype=np.float)
        else:
            with self.lock:
                block = self.blocks.get()
        self.t += self.blockSize/float(self.sampleRate)
        return block

class VideoGameBase(Task):


    def _setup(self, exp_win):
        self.game_vis_stim = visual.ImageStim(
            exp_win,
            size=exp_win.size,
            units='pixels',
            interpolate=False,
            flipVert=True,
            autoLog=False)
        self.game_sound = SoundDeviceBlockStream(stereo=True, blockSize=735)
        self._first_frame = self.emulator.reset()

    def _transform_soundblock(self, sound_block):
        return sound_block[:735]/float(2**15)

    def _render_graphics_sound(self, obs, sound_block, exp_win, ctl_win):
        self.game_vis_stim.image = obs/255. #np.flip(obs, 0)/255.
        self.game_vis_stim.draw(exp_win)
        if ctl_win:
            self.game_vis_stim.draw(ctl_win)
        self.game_sound.add_block(self._transform_soundblock(sound_block))
        if not self.game_sound.status == constants.PLAYING:
            print("start sound")
            self.game_sound.play()

    def _stop(self, exp_win, ctl_win):
        self.game_sound.stop()
        yield True

    def unload(self):
        self.emulator.close()

class VideoGame(VideoGameBase):

    DEFAULT_INSTRUCTION = "Let's play a video game.\n%s: %s\nHave fun!"

    def __init__(self,
        game_name=DEFAULT_GAME_NAME,
        state_name=None,
        scenario=None,
        repeat_scenario=True,
        max_duration=0,
        post_level_ratings=None,
        *args,**kwargs):

        super().__init__(**kwargs)
        self.game_name = game_name
        self.state_name = state_name
        self.scenario = scenario
        self.repeat_scenario = repeat_scenario
        self.max_duration = max_duration
        self.post_level_ratings = post_level_ratings

    def _instructions(self, exp_win, ctl_win):

        instruction = self.instruction%(self.game_name, self.state_name)

        screen_text = visual.TextStim(
            exp_win, text=instruction,
            alignText="center", color = 'white', wrapWidth=config.WRAP_WIDTH)

        for frameN in range(config.FRAME_RATE * config.INSTRUCTION_DURATION):
            screen_text.draw(exp_win)
            if ctl_win:
                screen_text.draw(ctl_win)
            yield frameN < 2
        yield True

    def _setup(self, exp_win):

        self.emulator = retro.make(
            self.game_name,
            state=self.state_name,
            scenario=self.scenario,
            record=False)

        super()._setup(exp_win)

        self._set_recording_file()

    def _set_recording_file(self):
        nnn = 0
        while True:
            self.movie_path = os.path.join(
                self.output_path,
                "%s_%s_%s_%03d.bk2"%(self.output_fname_base, self.game_name, self.state_name, nnn))
            if not os.path.exists(self.movie_path):
                break
            nnn += 1
        logging.exp('VideoGame: recording movie in %s'%self.movie_path)
        self.emulator.record_movie(self.movie_path)

    def _handle_controller_presses(self):
        global _keyPressBuffer, _keyReleaseBuffer

        for k in _keyReleaseBuffer:
            #print('release',k)
            self.pressed_keys.discard(k[0])
        _keyReleaseBuffer.clear()
        for k in _keyPressBuffer:
            #print('press',k)
            self.pressed_keys.add(k[0])
        _keyPressBuffer.clear()
        return self.pressed_keys

    def _run_emulator(self, exp_win, ctl_win):

        total_reward = 0
        _done = False
        level_step = 0
        keys = [False]*12

        # render the initial frame and audio
        self._render_graphics_sound(self._first_frame, self.emulator.em.get_audio(), exp_win, ctl_win)
        exp_win.logOnFlip(level=logging.EXP, msg="level step: %d"%level_step)
        yield
        while not _done:
            level_step += 1
            self._handle_controller_presses()
            keys = [k in self.pressed_keys for k in KEY_SET]

            _obs, _rew, _done, _info = self.emulator.step(keys)
            total_reward += _rew
            if _rew > 0 :
                exp_win.logOnFlip(level=logging.EXP, msg='Reward %f'%(total_reward))
            self._render_graphics_sound(_obs, self.emulator.em.get_audio(), exp_win, ctl_win)
            if _done:
                exp_win.logOnFlip(
                    level=logging.EXP,
                    msg='VideoGame %s: %s stopped at %f'%(self.game_name, self.state_name, time.time()))
            if not level_step%config.FRAME_RATE:
                exp_win.logOnFlip(level=logging.EXP, msg="level step: %d"%level_step)
            yield

    def _set_key_handler(self, exp_win):
        # activate repeat keys
        exp_win.winHandle.on_key_press = _onPygletKeyPress
        exp_win.winHandle.on_key_release = _onPygletKeyRelease
        self.pressed_keys = set()

    def _unset_key_handler(self, exp_win):
        # deactivate custom keys handling
        exp_win.winHandle.on_key_press = event._onPygletKey
        del exp_win.winHandle.on_key_release

    def _run(self, exp_win, ctl_win):

        self._set_key_handler(exp_win)
        exp_win.waitBlanking = False
        self._nlevels = 0

        while True:
            self._nlevels += 1
            exp_win.logOnFlip(
                level=logging.EXP,
                msg='VideoGame %s: %s starting at %f'%(self.game_name, self.state_name, time.time()))

            yield from self._run_emulator(exp_win, ctl_win)
            if self.post_level_ratings:
                yield from self._run_ratings(exp_win, ctl_win)
            if not self.repeat_scenario or \
                (self.max_duration and
                self.task_timer.getTime() > self.max_duration): # stop if we are above the planned duration
                break
            self.emulator.reset()

    def _run_ratings(self, exp_win, ctl_win):
        for question, n_pts in self.post_level_ratings:
            yield from self._likert_scale_answer(exp_win, ctl_win, question, n_pts)

        text = visual.TextStim(exp_win, 'Thanks for you answers', pos=(0, .5))
        for i in range(config.FRAME_RATE):
            text.draw(exp_win)
            yield i<2

    def _likert_scale_answer(self, exp_win, ctl_win, question, n_pts=7, extent=.6):
        extent *= config.EXP_WINDOW['size'][0]
        value = n_pts//2
        answered = False
        text = visual.TextStim(exp_win, question, pos=(0, .5))
        line = visual.Line(exp_win, (-extent, 0), (extent, 0), units='pixels', lineWidth=2, autoLog=False)
        x_spacing = extent*2/(n_pts-1)
        circles = [
            visual.Circle(
                exp_win,
                units='pixels',
                radius=40, pos=(-extent+i*x_spacing, 0),
                fillColor=(-1,-1,-1), lineColor=(-1,-1,-1), lineWidth=10,
                autoLog=False)
                for i in range(n_pts)
            ]
        circles[value].fillColor = (1,1,1)
        while not answered:
            self._handle_controller_presses()
            if 'r' in self.pressed_keys and value < n_pts-1:
                value+=1
                self.pressed_keys.discard('r')
            elif 'l' in self.pressed_keys and value > 0:
                value-=1
                self.pressed_keys.discard('l')
            for c in circles:
                c.fillColor = (-1,-1,-1)
            circles[value].fillColor = (1,1,1)

            if 'a' in self.pressed_keys:
                exp_win.logOnFlip(
                    level=logging.EXP,
                    msg='nlevel: %d, question: %s, answer: %d'%(self._nlevels, question, value))
                for i in range(config.FRAME_RATE):
                    yield i<2
                break
                self.pressed_keys.clear()

            for stim in [text, line] + circles:
                stim.draw(exp_win)
            yield True

    def _stop(self, exp_win, ctl_win):
        self._unset_key_handler(exp_win)
        exp_win.waitBlanking = True
        yield from super()._stop(exp_win, ctl_win)

class VideoGameMultiLevel(VideoGame):

    def __init__(self, *args,**kwargs):

        self._state_names = kwargs.pop('state_names')
        self._scenarii = kwargs.pop('scenarii')
        self._repeat_scenario_multilevel = kwargs.get('repeat_scenario', False)

        kwargs['repeat_scenario'] = False
        super().__init__(
            state_name = self._state_names[0],
            scenario=self._scenarii[0],
            **kwargs)

    def _run(self, exp_win, ctl_win):

        self._set_key_handler(exp_win)
        exp_win.waitBlanking = False

        self._nlevels = 0
        while True:
            for level, scenario in zip(self._state_names, self._scenarii):
                self._nlevels += 1
                self.state_name = level
                self.emulator.load_state(level)
                self.emulator.data.load(
                    retro.data.get_file_path(self.game_name, 'data.json'),
                    scenario)
                self._first_frame = self.emulator.reset()
                if self._nlevels > 1:
                    self._set_recording_file()
                    yield from self._instructions(exp_win, ctl_win)

                yield from super()._run_emulator(exp_win, ctl_win)
                self.game_sound.stop()
                if self.post_level_ratings:
                    yield from self._run_ratings(exp_win, ctl_win)

                time_exceeded = self.max_duration and self.task_timer.getTime() > self.max_duration
                if time_exceeded: # stop if we are above the planned duration
                    break
            if time_exceeded or not self._repeat_scenario_multilevel:
                break

        self._unset_key_handler(exp_win)
        exp_win.waitBlanking = True

class VideoGameReplay(VideoGameBase):

    def __init__(self, movie_filename, game_name=DEFAULT_GAME_NAME, scenario=None, *args, **kwargs):
        super().__init__(**kwargs)
        self.game_name = game_name
        self.scenario = scenario
        self.movie_filename = movie_filename
        if not os.path.exists(self.movie_filename):
            raise ValueError('file %s does not exists'%self.movie_filename)

    def instructions(self, exp_win, ctl_win):
        instruction_text = "You are going to watch someone play %s."%self.game_name
        screen_text = visual.TextStim(
            exp_win, text=instruction_text,
            alignText="center", color = 'white')

        for frameN in range(config.FRAME_RATE * INSTRUCTION_DURATION):
            screen_text.draw(exp_win)
            if ctl_win:
                screen_text.draw(ctl_win)
            yield

    def _setup(self, exp_win):
        super().setup(exp_win, output_path, output_fname_base)
        self.movie = retro.Movie(self.movie_filename)
        self.emulator = retro.make(
            self.game_name,
            record=False,
            state=retro.State.NONE,
            scenario=self.scenario,
            #use_restricted_actions=retro.Actions.ALL,
            players=self.movie.players)

        self.emulator.initial_state = self.movie.get_state()
        super()._setup(exp_win)


    def _run(self, exp_win, ctl_win):
        # give the original size of the movie in pixels:
        #print(self.movie_stim.format.width, self.movie_stim.format.height)
        total_reward = 0
        exp_win.logOnFlip(
            level=logging.EXP,
            msg='VideoGameReplay %s starting at %f'%(self.game_name, time.time()))
        while self.movie.step():
            keys = []
            for p in range(self.movie.players):
                for i in range(self.emulator.num_buttons):
                    keys.append(self.movie.get_key(i, p))

            _obs, _rew, _done, _info = self.emulator.step(keys)

            total_reward += _rew
            if _rew > 0 :
                exp_win.logOnFlip(level=logging.EXP, msg='Reward %f'%(total_reward))

            self._render_graphics_sound(_obs,self.emulator.em.get_audio(), exp_win, ctl_win)
            yield
