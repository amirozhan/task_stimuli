from psychopy import prefs

# avoids delay in movie3 audio seek
prefs.hardware['audioLib'] = ['sounddevice']
#prefs.hardware['general'] = ['glfw']

OUTPUT_DIR = 'output'

EYETRACKING_ROI = (60,30,660,450)

EXP_WINDOW = dict(
#    winType='glfw',
    size = (1280,1024),
#    size = (800, 600),
#    size = (1920, 1080),
    screen=0,
    fullscr=True,
    gammaErrorPolicy='warn',
    waitBlanking=False,
)

CTL_WINDOW = dict(
#    winType='glfw',
#    size = (1920, 1080),
    size = (1280, 1024),
#    size = (1024, 768),
    pos = (100,0),
    screen=0,
    gammaErrorPolicy='warn',
#    swapInterval=0.,
    waitBlanking=False, # avoid ctrl window to block the script in case of differing refresh rate.
)

FRAME_RATE=60

# task parameters
INSTRUCTION_DURATION = 6

WRAP_WIDTH = 1

# port for meg setup
PARALLEL_PORT_ADDRESS = '/dev/parport0'
