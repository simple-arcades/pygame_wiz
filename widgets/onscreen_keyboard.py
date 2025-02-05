import pygame
import sys

from ..constants import PHYSICAL_WIDTH, PHYSICAL_HEIGHT, GRAY, LIGHT_GRAY, BLACK, BLUE

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
BLUE = (0, 0, 255)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
YELLOW = (255, 255, 0)

class OnScreenKeyboard:
    def __init__(self, initial_text=""):
        self.font = None
        self.keys_normal = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
            ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
            ["Shift", "z", "x", "c", "v", "b", "n", "m", "BS"],
            ["Special", "Space", "OK", "Back"],
        ]
        self.keys_special = [
            ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"],
            ["-", "_", "=", "+", "[", "]", "{", "}", ";", ":"],
            ['"', "'", ",", ".", "/", "\\", "|", "", "~"],
            ["Shift", "<", ">", "?", "^", "b", "n", "m", "BS"],
            ["Special", "Space", "OK", "Back"],
        ]
        self.keys = self.keys_normal
        self.shift = False
        self.special = False
        self.text = initial_text
        self.key_rects = []
        self.selected_row = 0
        self.selected_col = 0
        self.done = False
        
        # Joystick axis flags for dead-zone logic
        self.axis_left_active = False
        self.axis_right_active = False
        self.axis_up_active = False
        self.axis_down_active = False
        self.joystick_deadzone = 0.5

        self.last_move_time = 0
        self.move_interval = 150

    def set_font(self, font):
        self.font = font

    def draw(self, surface: pygame.Surface, mode, bottom_bar_rect=None):
        """
        Renders the on-screen keyboard in a bottom white bar, with 80x50 keys.
        Shows a highlight for both joystick selection and mouse hover.
        'Special' key displays "!@#$" if self.special == False, or "ABC123" if True.
        Prompt text in black, typed text in green, with vertical padding.

        :param surface: The pygame.Surface to draw onto
        :param mode: e.g. "password", "custom_ssid", etc.
        :param bottom_bar_rect: pygame.Rect defining the bottom bar area (white).
               If None, we default to a 400 px tall bar at the bottom of the screen.
        """
        import pygame
        from ..constants import PHYSICAL_WIDTH, PHYSICAL_HEIGHT  # or your own
        WHITE = (255,255,255)
        BLACK = (0,0,0)
        GREEN = (0,200,0)
        LIGHT_GRAY = (220,220,220)

        # 1) Define a default bottom bar if none provided
        if bottom_bar_rect is None:
            bar_height = 400
            bottom_bar_rect = pygame.Rect(
                0, PHYSICAL_HEIGHT - bar_height,
                PHYSICAL_WIDTH, bar_height
            )

        # Draw the white bar
        pygame.draw.rect(surface, WHITE, bottom_bar_rect)

        # 2) Use your preferred font if not set:
        if not self.font:
            # e.g. "self.font = self.app.font_NES_24" if you have it
            # or fallback to something
            self.font = pygame.font.Font(None, 36)

        # 3) Prompt text at top in black, typed text below in green
        prompt_height = 60
        prompt_rect = pygame.Rect(
            bottom_bar_rect.left, bottom_bar_rect.top,
            bottom_bar_rect.width, prompt_height
        )

        prompt_text = getattr(self, "prompt_label", "")
        if not prompt_text:
            if mode == "password":
                prompt_text = "Enter password:"
            else:
                prompt_text = "Enter SSID Name:"

        # Prompt in black
        prompt_surf = self.font.render(prompt_text, True, BLACK)
        prompt_x = prompt_rect.centerx - (prompt_surf.get_width() // 2)
        prompt_y = prompt_rect.top + 10
        surface.blit(prompt_surf, (prompt_x, prompt_y))

        # typed text in green, about 30 px below the prompt
        typed_surf = self.font.render(self.text, True, GREEN)
        typed_x = prompt_rect.centerx - (typed_surf.get_width() // 2)
        typed_y = prompt_y + prompt_surf.get_height() + 10
        surface.blit(typed_surf, (typed_x, typed_y))

        # 4) The keys area is the remainder of the bar
        keys_area = pygame.Rect(
            bottom_bar_rect.left,
            prompt_rect.bottom,
            bottom_bar_rect.width,
            bottom_bar_rect.height - prompt_height
        )

        # We'll keep the old 80x50 approach
        key_w = 80
        key_h = 50
        margin = 5
        self.key_rects = []

        # Calculate total keyboard height => rows * (key_h+margin) - margin
        num_rows = len(self.keys)
        if num_rows == 0:
            return
        total_kb_height = num_rows*(key_h+margin) - margin

        # We'll place the top of the keyboard ~10 px below typed text
        kb_start_y = typed_y + typed_surf.get_height() + 10
        if (kb_start_y + total_kb_height) > keys_area.bottom:
            # If there's not enough space, clamp
            kb_start_y = keys_area.bottom - total_kb_height - 10

        # 5) For each row in self.keys, we center them horizontally
        for row_index, row in enumerate(self.keys):
            row_len = len(row)
            total_row_width = row_len*(key_w+margin) - margin
            row_start_x = keys_area.centerx - (total_row_width//2)
            row_y = kb_start_y + row_index*(key_h + margin)

            for col_index, label in enumerate(row):
                rect = pygame.Rect(row_start_x + col_index*(key_w+margin), row_y, key_w, key_h)
                # Toggle the "Special" label => "!@#$" or "ABC123"
                display_label = label
                if label.lower() == "special":
                    if self.special:
                        display_label = "ABC123"
                    else:
                        display_label = "!@#$"

                # Check joystick selection or mouse hover
                is_selected = (
                    hasattr(self, "selected_row") and
                    hasattr(self, "selected_col") and
                    row_index == self.selected_row and
                    col_index == self.selected_col
                )
                mouse_hover = rect.collidepoint(pygame.mouse.get_pos())

                if is_selected or mouse_hover:
                    highlight_rect = rect.inflate(4,4)
                    pygame.draw.rect(surface, BLUE, highlight_rect, 3)

                # Key background
                pygame.draw.rect(surface, WHITE, rect)
                pygame.draw.rect(surface, BLACK, rect, 2)

                # SHIFT => uppercase
                disp = display_label.upper() if self.shift else display_label
                txt_surf = self.font.render(disp, True, BLACK)
                txt_rect = txt_surf.get_rect(center=rect.center)
                surface.blit(txt_surf, txt_rect)
                self.key_rects.append((rect, label, row_index, col_index))



    def handle_event(self, event):
        """
        Replaces your existing handle_event. 
        Adds joystick deadzone logic:
          - Only move once if axis < -0.5 or > 0.5, 
          - re-center to allow next move.
        """
        import pygame

        # If you haven't defined these flags, define them in __init__:
        #   self.axis_left_active = False
        #   self.axis_right_active = False
        #   self.axis_up_active = False
        #   self.axis_down_active = False
        #   self.joystick_deadzone = 0.5

        if event.type == pygame.KEYDOWN:
            # keyboard navigation
            if event.key == pygame.K_LEFT:
                self.select_previous_key()
            elif event.key == pygame.K_RIGHT:
                self.select_next_key()
            elif event.key == pygame.K_UP:
                self.select_previous_row()
            elif event.key == pygame.K_DOWN:
                self.select_next_row()
            elif event.key == pygame.K_RETURN:
                self.process_key("OK")
            elif event.key == pygame.K_BACKSPACE:
                self.process_key("BS")
            elif event.key == pygame.K_SPACE:
                self.process_key("Space")
            elif event.key == pygame.K_ESCAPE:
                self.process_key("Back")

        elif event.type == pygame.JOYAXISMOTION:
            # axis=0 => horizontal, axis=1 => vertical
            axis = event.axis
            value = event.value

            if axis == 0:  # horizontal
                if value < -self.joystick_deadzone:  # left tilt
                    if not self.axis_left_active:
                        self.axis_left_active = True
                        self.axis_right_active = False
                        self.select_previous_key()
                elif value > self.joystick_deadzone:  # right tilt
                    if not self.axis_right_active:
                        self.axis_right_active = True
                        self.axis_left_active = False
                        self.select_next_key()
                else:
                    # near zero => re-center
                    self.axis_left_active = False
                    self.axis_right_active = False

            elif axis == 1:  # vertical
                if value < -self.joystick_deadzone:  # up
                    if not self.axis_up_active:
                        self.axis_up_active = True
                        self.axis_down_active = False
                        self.select_previous_row()
                elif value > self.joystick_deadzone:  # down
                    if not self.axis_down_active:
                        self.axis_down_active = True
                        self.axis_up_active = False
                        self.select_next_row()
                else:
                    self.axis_up_active = False
                    self.axis_down_active = False

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:  
                # "A" on many controllers => OK
                self.process_key("OK")
            elif event.button == 1:
                # "B" => maybe "Back"
                self.process_key("Back")
            elif event.button == 2:
                # Another button if needed
                self.process_key("Space")
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # if you want mouse clicks on keys
            mx, my = event.pos
            if event.button == 1:
                for rect,label,r,c in self.key_rects:
                    if rect.collidepoint(mx,my):
                        self.process_key(label)
                        break


    def select_next_key(self):
        self.selected_col += 1
        if self.selected_col >= len(self.keys[self.selected_row]):
            self.selected_col = 0

    def select_previous_key(self):
        self.selected_col -= 1
        if self.selected_col < 0:
            self.selected_col = len(self.keys[self.selected_row]) - 1

    def select_next_row(self):
        self.selected_row = (self.selected_row + 1) % len(self.keys)
        # Clamp col so it's valid for the new row
        self.selected_col = min(self.selected_col, len(self.keys[self.selected_row]) - 1)

    def select_previous_row(self):
        self.selected_row = (self.selected_row - 1) % len(self.keys)
        # Clamp col so it's valid for the new row
        self.selected_col = min(self.selected_col, len(self.keys[self.selected_row]) - 1)


    def process_key(self, label):
        if label == "Shift":
            self.shift = not self.shift
        elif label == "Special":
            self.special = not self.special
            if self.special:
                self.keys = self.keys_special
            else:
                self.keys = self.keys_normal
            self.selected_row = 0
            self.selected_col = 0
        elif label == "BS":
            self.text = self.text[:-1]
        elif label == "Space":
            self.text += " "
        elif label == "OK":
            self.done = True
        elif label == "Back":
            self.done = True
        else:
            char = label.upper() if self.shift else label
            self.text += char

    def get_text(self):
        return self.text