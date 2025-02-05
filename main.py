import os
import sys

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Temporarily redirect stderr to devnull
_original_stderr = sys.stderr
devnull = open(os.devnull, 'w')
sys.stderr = devnull

try:
    import pygame
finally:
    # Restore original stderr
    sys.stderr = _original_stderr
    devnull.close()

# Now proceed normally
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module='pygame')

import pygame

from .constants import (
    PHYSICAL_WIDTH, PHYSICAL_HEIGHT, FPS,
    SETUP_COMPLETE_FLAG, APP_LOG_FILE
)
from .utils import log
from .screen_manager import ScreenManager
from .screens.welcome_screen import WelcomeScreen
from .screens.timezone_screen import EnterTimezoneScreen
from .screens.terms_screen import TermsScreen
from .screens.wifi_screen import WiFiScreen
from .screens.update_screen import UpdateScreen
from .screens.final_screen import FinalScreen

class Application:
    def __init__(self):
        # ensure logs directory
        os.makedirs(os.path.dirname(APP_LOG_FILE), exist_ok=True)

        pygame.mixer.pre_init(48000, -16, 2, 4096)
        pygame.init()
        pygame.mixer.init()
        
        # Hide the mouse cursor
        pygame.mouse.set_visible(False)

        self.display_surf = pygame.display.set_mode((PHYSICAL_WIDTH, PHYSICAL_HEIGHT))
        pygame.display.set_caption("Arcade Setup Wizard")

        self.clock = pygame.time.Clock()

        # We'll record our base_dir for get_path
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # Load fonts from arcade_wizard/fonts/
        try:
            nes_font_path_24 = self.get_path("fonts","NESCyrillic_gamelist.ttf")
            tiny_font_path_24 = self.get_path("fonts","TinyUnicode.ttf")
            self.font_NES_24 = pygame.font.Font(nes_font_path_24, 24)
            self.font_NES_20 = pygame.font.Font(nes_font_path_24, 20)
            self.font_TINY_24 = pygame.font.Font(tiny_font_path_24, 34)
            self.font_TINY_20 = pygame.font.Font(tiny_font_path_24, 20)
        except Exception as e:
            log(f"Failed to load fonts: {e}")
            self.font_NES_24 = pygame.font.SysFont(None,24)
            self.font_NES_20 = pygame.font.SysFont(None,20)
            self.font_TINY_24 = pygame.font.SysFont(None,24)
            self.font_TINY_20 = pygame.font.SysFont(None,20)

        # Load background / bubble
        self.background = self.load_bg(self.get_path("images","background_lg.png"))
        self.bubble_image = self.load_bubble(self.get_path("images","bubble_lg.png"))
        self.bubble_rect = self.bubble_image.get_rect(center=(PHYSICAL_WIDTH//2, PHYSICAL_HEIGHT//2))

        # Load music
        self.load_music(self.get_path("sounds","background_music.ogg"))

        self.screen_manager = ScreenManager(self)
        self.register_screens()

        pygame.joystick.init()
        jc = pygame.joystick.get_count()
        if jc>0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            log(f"Joystick detected: {self.joystick.get_name()}")
        else:
            self.joystick=None
            log("No joystick detected.")

    def get_path(self, *subdirs):
        """
        Build an absolute path inside arcade_wizard folder.
        e.g. self.get_path("images","background_lg.png")
        """
        return os.path.join(self.base_dir, *subdirs)

    def load_bg(self, path):
        try:
            img = pygame.image.load(path).convert()
            img = pygame.transform.scale(img, (PHYSICAL_WIDTH, PHYSICAL_HEIGHT))
            return img
        except Exception as e:
            log(f"Failed to load background image {path}: {e}")
            tmp = pygame.Surface((PHYSICAL_WIDTH, PHYSICAL_HEIGHT))
            tmp.fill((50,50,50))
            return tmp

    def load_bubble(self, path):
        try:
            img = pygame.image.load(path).convert_alpha()
            return img
        except Exception as e:
            log(f"Failed to load bubble image {path}: {e}")
            tmp = pygame.Surface((600,400), pygame.SRCALPHA)
            tmp.fill((255,255,255,220))
            return tmp

    def load_music(self, path):
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(0.2)
                pygame.mixer.music.play(-1)
            except Exception as e:
                log(f"Failed to load music {path}: {e}")
        else:
            log(f"Music file not found: {path}")

    def register_screens(self):
        welcome = WelcomeScreen(self)
        timezone = EnterTimezoneScreen(self)
        terms = TermsScreen(self)
        wifi = WiFiScreen(self)
        update = UpdateScreen(self)
        final = FinalScreen(self)

        self.screen_manager.register_screen("welcome", welcome)
        self.screen_manager.register_screen("timezone", timezone)
        self.screen_manager.register_screen("terms", terms)
        self.screen_manager.register_screen("wifi", wifi)
        self.screen_manager.register_screen("update", update)
        self.screen_manager.register_screen("final", final)

        self.screen_manager.change_screen("welcome")

    def run(self):
        running = True
        while running:
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    running=False

            self.screen_manager.handle_events(events)
            self.screen_manager.update()
            self.screen_manager.render(self.display_surf)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def remove_wizard_from_autostart(self):
        from .constants import AUTOSTART_PATH
        log(f"Removing wizard from {AUTOSTART_PATH}")
        import os
        if not os.path.exists(AUTOSTART_PATH):
            log(f"Autostart not found at {AUTOSTART_PATH}")
            return
        try:
            with open(AUTOSTART_PATH,"r") as f:
                lines = f.readlines()
            new_lines=[]
            for line in lines:
                if "arcade_wizard" not in line:
                    new_lines.append(line)
            found_es = any("emulationstation" in ln for ln in new_lines)
            if not found_es:
                new_lines.append("emulationstation #auto\n")
            with open(AUTOSTART_PATH,"w") as f:
                f.writelines(new_lines)
            log("Removed wizard from autostart and ensured EmulationStation is set.")
        except Exception as e:
            log(f"Failed to edit autostart: {e}")

    def create_setup_flag(self):
        from .constants import SETUP_COMPLETE_FLAG
        try:
            with open(SETUP_COMPLETE_FLAG, "w") as f:
                f.write("Setup completed.\n")
            log(f"Created setup completion flag at {SETUP_COMPLETE_FLAG}")
        except Exception as e:
            log(f"Failed to create setup completion flag: {e}")

    def reboot_system(self):
        import subprocess
        log("Rebooting now...")
        pygame.quit()
        subprocess.run(["sudo","reboot"])
        sys.exit()

def main():
    from .constants import SETUP_COMPLETE_FLAG
    import os

    if os.path.exists(SETUP_COMPLETE_FLAG):
        print("Setup wizard already completed.")
        sys.exit(0)

    log("Launching setup application.")
    app = Application()
    app.run()

if __name__=="__main__":
    main()