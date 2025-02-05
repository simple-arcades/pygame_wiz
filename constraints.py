import os

###############################################################################
# GLOBAL CONSTANTS
###############################################################################
PHYSICAL_WIDTH = 1920
PHYSICAL_HEIGHT = 1080
FPS = 60

LOG_DIR = "/home/pi/RetroPie/custom_scripts/logs"
APP_LOG_FILE = os.path.join(LOG_DIR, "setup_gui.log")
TERMS_LOG_FILE = os.path.join(LOG_DIR, "terms_agreement.log")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
BLUE = (0, 0, 255)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
YELLOW = (255, 255, 0)

SETUP_COMPLETE_FLAG = "/home/pi/RetroPie/custom_scripts/setup_wizard_completed"
AUTOSTART_PATH = "/opt/retropie/configs/all/autostart.sh"
AUTO_UPDATE_SCRIPT = "/home/pi/RetroPie/custom_scripts/update_system_auto.sh"
