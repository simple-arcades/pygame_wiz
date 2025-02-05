import os
import sys
import time
import queue
import threading
import subprocess

import pygame

from ..screen_manager import Screen
from ..constants import BLACK, WHITE, YELLOW, GREEN, RED, PHYSICAL_WIDTH, PHYSICAL_HEIGHT
from ..utils import log
from ..widgets.onscreen_keyboard import OnScreenKeyboard

GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)

###############################################################################
# Toggle this to True/False if you want to enable/disable hover/click sounds
###############################################################################
SOUND_ENABLED = True

class WiFiScreen(Screen):
    """
    Revised Wi-Fi screen with:
      - Centered, scrollable SSID list inside a thin white border box
      - Hovered SSID has a thin highlight rectangle
      - OSK changes with a bottom white bar, "SPECIAL" => "ABC 123"
      - Manual SSID flow: only add to the list if connection success
      - Single-sound approach (no double-click overlap)
      - If nmcli fails, show exit code in status box
    """

    def __init__(self, app):
        super().__init__(app)

        # Data for networks
        self.networks = []
        self.connected_ssid = None
        self.selected_network_index = -1

        # OSK
        self.osk_mode = None
        self.osk = None
        self.osk_prompt_text = ""  # e.g. "Enter your custom SSID name", "Enter password for X"

        # Worker
        self.connection_thread = None
        self.message_queue = queue.Queue()

        # Status message
        self.status_message = None
        self.status_color = BLACK
        self.status_expire_time = 0

        # Selections
        self.current_selection = 'networks'
        self.prev_selection = None
        self.last_hover_time = 0
        self.hover_cooldown_ms = 300

        # Wi-Fi scanning
        self.scan_interval = 10
        self.last_scan_time = 0

        # Buttons geometry
        self.button_width = 203
        self.button_height = 61
        self.button_y = self.app.bubble_rect.top + 640

        self.rescan_button_rect = pygame.Rect(
            self.app.bubble_rect.centerx - 320, self.button_y,
            self.button_width, self.button_height
        )
        self.manual_button_rect = pygame.Rect(
            self.app.bubble_rect.centerx - 100, self.button_y,
            self.button_width, self.button_height
        )
        self.skip_button_rect = pygame.Rect(
            self.app.bubble_rect.centerx + 120, self.button_y,
            self.button_width, self.button_height
        )

        # SSID list geometry
        # We'll create a rectangular area in the bubble's center
        self.ssid_box_width = 800
        self.ssid_box_height = 300
        self.ssid_box_x = self.app.bubble_rect.centerx - (self.ssid_box_width // 2)
        self.ssid_box_y = self.app.bubble_rect.top + 275

        self.ssid_box_rect = pygame.Rect(
            self.ssid_box_x, self.ssid_box_y,
            self.ssid_box_width, self.ssid_box_height
        )
        self.ssid_scroll_offset = 0  # for scrolling if many SSIDs
        self.ssid_line_height = 30

        # Placeholders
        self.placeholder_images = []
        self.define_placeholder_images()

        # 4 button image sets
        self.rescan_images = self.load_button_images("rescan")
        self.manual_images = self.load_button_images("manual_ssid")
        self.skip_images = self.load_button_images("skip")
        self.continue_images = self.load_button_images("continue")

        # Sounds
        self.click_sound = None
        self.hover_sound = None
        self.load_sounds()

        self.user_just_clicked = False

        # Start scanning
        self.scan_wifi()

    # -------------------------------------------------------------------------
    # IMAGE LOADING
    # -------------------------------------------------------------------------
    def define_placeholder_images(self):
        configs = [
            {
                "path": "connect_to_wifi.png",
                "size": (500,165),
                "pos": (
                    self.app.bubble_rect.centerx - 250,
                    self.app.bubble_rect.top + 50,
                ),
            },
            {
                "path": "navigation_legend.png",
                "size": (896,56),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 448,
                    self.app.bubble_rect.top + 740,
                ),
            },
            {
                "path": "page_indicator_4.png",
                "size": (212,18),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 106,
                    self.app.bubble_rect.top + 880,
                ),
            },
        ]
        for cfg in configs:
            try:
                img_path = self.app.get_path("images", cfg["path"])
                img = pygame.image.load(img_path).convert_alpha()
                img = pygame.transform.scale(img, cfg["size"])
            except Exception as e:
                log(f"Failed to load WiFi placeholder {cfg['path']}: {e}")
                img = pygame.Surface(cfg["size"], pygame.SRCALPHA)
                img.fill((255,0,0,128))
            self.placeholder_images.append({"img": img, "pos": cfg["pos"]})

    def load_button_images(self, base_name):
        """
        e.g. "rescan_normal_sm.png", "rescan_hover_sm.png", "rescan_pressed_sm.png"
        """
        try:
            n = pygame.image.load(self.app.get_path("images", f"{base_name}_normal_sm.png")).convert_alpha()
            h = pygame.image.load(self.app.get_path("images", f"{base_name}_hover_sm.png")).convert_alpha()
            p = pygame.image.load(self.app.get_path("images", f"{base_name}_pressed_sm.png")).convert_alpha()
        except Exception as e:
            log(f"Failed to load {base_name} button images: {e}")
            n = pygame.Surface((203,61))
            n.fill((100,200,100))
            h = pygame.Surface((203,61))
            h.fill((200,100,200))
            p = pygame.Surface((203,61))
            p.fill((200,0,0))

        return (n, h, p)

    # -------------------------------------------------------------------------
    # SOUND
    # -------------------------------------------------------------------------
    def load_sounds(self):
        try:
            click_path = self.app.get_path("sounds","select.ogg")
            hover_path = self.app.get_path("sounds","hover.ogg")
            self.click_sound = pygame.mixer.Sound(click_path)
            self.click_sound.set_volume(0.5)
            self.hover_sound = pygame.mixer.Sound(hover_path)
            self.hover_sound.set_volume(0.1)
        except Exception as e:
            log(f"Failed to load WiFi screen sounds: {e}")
            self.click_sound = None
            self.hover_sound = None

    def play_click_sound(self):
        if SOUND_ENABLED and self.click_sound:
            self.click_sound.play()

    def play_hover_sound(self):
        if SOUND_ENABLED and self.hover_sound:
            self.hover_sound.play()

    # -------------------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------------------
    def handle_events(self, events):
        if self.osk_mode:
            self.handle_events_osk(events)
            return

        self.user_just_clicked = False
        old_selection = self.current_selection

        super().handle_events(events)

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
                mx, my = e.pos

                # Check for SSID click
                if self.ssid_box_rect.collidepoint(mx,my):
                    # We transform mouse coords to scrolled coords
                    local_y = (my - self.ssid_box_rect.top) + self.ssid_scroll_offset
                    idx = local_y // self.ssid_line_height
                    if 0 <= idx < len(self.networks):
                        self.play_click_sound()
                        self.user_just_clicked = True
                        self.selected_network_index = idx
                        # Show password OSK
                        self.ask_for_password(idx)
                        break

                # Check for scrolling: wheel up/down
                if e.button == 4:  # wheel up
                    self.ssid_scroll_offset = max(self.ssid_scroll_offset - 30, 0)
                elif e.button == 5:  # wheel down
                    max_offset = max(0, (len(self.networks)*self.ssid_line_height - self.ssid_box_rect.height))
                    self.ssid_scroll_offset = min(self.ssid_scroll_offset + 30, max_offset)

                # Check the 3 main buttons
                if self.rescan_button_rect.collidepoint(mx,my):
                    self.play_click_sound()
                    self.user_just_clicked=True
                    self.scan_wifi()
                    break
                elif self.manual_button_rect.collidepoint(mx,my):
                    self.play_click_sound()
                    self.user_just_clicked=True
                    self.ask_for_custom_ssid()
                    break
                elif self.skip_button_rect.collidepoint(mx,my):
                    self.play_click_sound()
                    self.user_just_clicked=True
                    self.on_skip_or_continue()
                    break

            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 4:  # wheel up
                    self.ssid_scroll_offset = max(self.ssid_scroll_offset - 30, 0)
                elif e.button == 5:  # wheel down
                    max_offset = max(0, (len(self.networks)*self.ssid_line_height - self.ssid_box_rect.height))
                    self.ssid_scroll_offset = min(self.ssid_scroll_offset + 30, max_offset)

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_UP:
                    if self.current_selection in ['rescan','manual','skip','continue']:
                        self.current_selection='networks'
                        if self.networks:
                            self.selected_network_index=0
                    elif self.selected_network_index>0:
                        self.selected_network_index-=1
                elif e.key == pygame.K_DOWN:
                    if self.current_selection=='networks':
                        if self.selected_network_index<len(self.networks)-1:
                            self.selected_network_index+=1
                        else:
                            self.current_selection='rescan'
                            self.selected_network_index=-1
                elif e.key == pygame.K_LEFT:
                    self.handle_left_arrow()
                elif e.key == pygame.K_RIGHT:
                    self.handle_right_arrow()
                elif e.key == pygame.K_RETURN:
                    self.play_click_sound()
                    self.user_just_clicked=True
                    self.handle_return_key()
                    break
                elif e.key == pygame.K_TAB:
                    self.tab_cycle()
                elif e.key == pygame.K_ESCAPE:
                    self.app.screen_manager.change_screen("terms")
                    break

            elif e.type == pygame.JOYBUTTONDOWN:
                if e.button==0:
                    self.play_click_sound()
                    self.user_just_clicked=True
                    self.handle_return_key()
                    break
                elif e.button==1:
                    self.app.screen_manager.change_screen("terms")
                    break

            elif e.type == pygame.JOYAXISMOTION:
                print(f"(WIFI) Joy axis {e.axis} => {e.value:.2f}")

        # If selection changed => maybe hover sound
        if self.current_selection != old_selection and not self.user_just_clicked:
            now_ms = pygame.time.get_ticks()
            if (now_ms - self.last_hover_time) > self.hover_cooldown_ms:
                self.play_hover_sound()
                self.last_hover_time = now_ms

    def handle_events_osk(self, events):
        for ev in events:
            if not self.osk:
                break
            self.osk.handle_event(ev)
            if self.osk.done:
                text = self.osk.get_text()
                if self.osk_mode=="custom_ssid":
                    # we do NOT add it to networks yet
                    # we go straight to password
                    self.osk_mode = None
                    self.osk = None
                    custom_ssid = text.strip()
                    if custom_ssid:
                        # go to ask_for_password for that custom SSID
                        self.ask_for_password(None, custom_ssid)
                    else:
                        # user typed nothing, do nothing
                        pass
                    break
                elif self.osk_mode=="password":
                    # We got the password for either an existing or custom SSID
                    pw = text.strip()
                    if self.temp_ssid_name:
                        # custom SSID
                        ssid = self.temp_ssid_name
                    else:
                        # existing index
                        ssid = self.networks[self.selected_network_index]

                    self.try_connect(ssid, pw)

                self.osk_mode = None
                self.osk = None
                break

    # -------------------------------------------------------------------------
    # SHIFTED LOGIC FOR MANUAL SSID + PASSWORD
    # -------------------------------------------------------------------------
    def ask_for_custom_ssid(self):
        """
        Prompt: "Enter your custom SSID name" in the OSK
        Then go to password OSK if not empty
        """
        self.temp_ssid_name = None
        self.osk_mode = "custom_ssid"
        self.osk = OnScreenKeyboard("")
        self.osk.prompt_label = "Enter your custom SSID name"
        self.osk.set_font(self.app.font_TINY_24)
        pygame.event.clear()

    def ask_for_password(self, index=None, custom_ssid=None):
        """
        Called if user clicks an existing SSID or after finishing custom SSID.
        - If index is not None, we use self.networks[index]
        - If custom_ssid is given, we store it in self.temp_ssid_name
        """
        if index is not None:
            ssid = self.networks[index]
            self.temp_ssid_name = None
        else:
            ssid = custom_ssid
            self.temp_ssid_name = ssid

        self.osk_mode = "password"
        self.osk = OnScreenKeyboard("")
        self.osk.prompt_label = f"Enter password for {ssid}"
        self.osk.set_font(self.app.font_TINY_24)
        pygame.event.clear()

    # -------------------------------------------------------------------------
    # LEFT/RIGHT TABBING
    # -------------------------------------------------------------------------
    def handle_left_arrow(self):
        if self.current_selection=='manual':
            self.current_selection='rescan'
        elif self.current_selection in ['skip','continue']:
            self.current_selection='manual'

    def handle_right_arrow(self):
        if self.current_selection=='rescan':
            self.current_selection='manual'
        elif self.current_selection=='manual':
            if self.connected_ssid:
                self.current_selection='continue'
            else:
                self.current_selection='skip'
        elif self.current_selection in ['skip','continue']:
            self.current_selection='rescan'

    def handle_return_key(self):
        if self.current_selection=='networks' and self.selected_network_index>=0:
            self.ask_for_password(self.selected_network_index)
        elif self.current_selection=='manual':
            self.ask_for_custom_ssid()
        elif self.current_selection=='rescan':
            self.scan_wifi()
        elif self.current_selection in ['skip','continue']:
            self.on_skip_or_continue()

    def tab_cycle(self):
        if self.current_selection=='networks':
            self.current_selection='rescan'
            self.selected_network_index=-1
        elif self.current_selection=='rescan':
            self.current_selection='manual'
        elif self.current_selection=='manual':
            if self.connected_ssid:
                self.current_selection='continue'
            else:
                self.current_selection='skip'
        else:
            self.current_selection='networks'
            if self.networks:
                self.selected_network_index=0

    # -------------------------------------------------------------------------
    # CONNECT
    # -------------------------------------------------------------------------
    def on_skip_or_continue(self):
        if self.connected_ssid:
            self.app.screen_manager.change_screen("update")
        else:
            self.app.screen_manager.change_screen("final")

    def try_connect(self, ssid, password):
        """
        Attempt to connect. If success => add to list (if not in list),
        and set connected. If fail => show error. do not add to list.
        """
        def worker():
            self.message_queue.put(("info", f"Connecting to {ssid}", BLACK))
            cmd = ["/usr/bin/nmcli","dev","wifi","connect",ssid,"password",password]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
                # if we reach here => success
                if "successfully activated" in res.stdout:
                    self.message_queue.put(("success", ssid, BLACK))
                else:
                    # Maybe it succeeded but no mention
                    self.message_queue.put(("error", f"Failed: {res.stdout}", RED))
            except subprocess.CalledProcessError as cpe:
                # e.g. exit code 10
                err_msg = f"nmcli failed (RC={cpe.returncode}): {cpe.stderr or cpe.stdout}"
                self.message_queue.put(("error", err_msg, RED))
            except subprocess.TimeoutExpired:
                self.message_queue.put(("error","Connection timed out.",RED))
            except Exception as ex:
                self.message_queue.put(("error", str(ex), RED))

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # MESSAGES
    # -------------------------------------------------------------------------
    def update(self):
        while not self.message_queue.empty():
            msg_type, content, color = self._parse_msg_tuple(self.message_queue.get())
            if msg_type=="info":
                self.set_status_message(content, color, 3)
            elif msg_type=="success":
                # connected
                if content not in self.networks:
                    self.networks.insert(0, content)
                self.connected_ssid = content
                self.set_status_message(f"Connected to {content}!", color, 3)
                self.scan_wifi()
            elif msg_type=="error":
                self.set_status_message(content, color, 4)

    def _parse_msg_tuple(self, msg_tuple):
        if len(msg_tuple)==2:
            return msg_tuple[0], msg_tuple[1], BLACK
        elif len(msg_tuple)==3:
            return msg_tuple[0], msg_tuple[1], msg_tuple[2]
        else:
            return "info","???", BLACK

    def set_status_message(self, text, color, duration=2):
        self.status_message=text
        self.status_color=color
        self.status_expire_time=time.time()+duration

    def scan_wifi(self):
        def scan_worker():
            now=time.time()
            if (now - self.last_scan_time)<self.scan_interval:
                time.sleep(self.scan_interval - (now - self.last_scan_time))

            self.message_queue.put(("info","Scanning networks...",BLACK))
            subprocess.run(["/usr/bin/nmcli","device","wifi","rescan"], capture_output=True)
            time.sleep(2)

            p = subprocess.run(
                ["/usr/bin/nmcli","-t","-f","SSID,IN-USE","device","wifi","list"],
                capture_output=True, text=True
            )
            lines = p.stdout.strip().split("\n")

            new_networks=[]
            new_connected=None

            for line in lines:
                if not line.strip():
                    continue
                parts=line.split(":",1)
                if len(parts)!=2:
                    continue
                ssid_val=parts[0].strip()
                in_use=parts[1].strip()
                if in_use=="*":
                    new_connected=ssid_val
                if ssid_val:
                    new_networks.append(ssid_val)

            self.networks=new_networks
            self.connected_ssid=new_connected
            self.last_scan_time=time.time()

            self.message_queue.put(("info",f"Found {len(new_networks)} networks.",BLACK))

        threading.Thread(target=scan_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # RENDER
    # -------------------------------------------------------------------------
    def render(self, surf):
        self.render_background_and_bubble(surf)

        for ph in self.placeholder_images:
            surf.blit(ph["img"], ph["pos"])

        # Draw the SSID label
        # We'll remove the old code that put it at left +20
        # Instead we center it above the box
        label_font = self.app.font_TINY_24
        label_txt = label_font.render("Available Wireless Networks:", True, BLACK)
        label_rect = label_txt.get_rect(midbottom=(
            self.ssid_box_rect.centerx, 
            self.ssid_box_rect.top - 10
        ))
        surf.blit(label_txt, label_rect)

        # 1) Draw a thin gray border for the SSID box
        pygame.draw.rect(surf, GRAY, self.ssid_box_rect, 2)

        # 2) We create a "clipping" region so we can scroll
        old_clip = surf.get_clip()
        surf.set_clip(self.ssid_box_rect)

        # Start from top of the box
        base_y = self.ssid_box_rect.top

        for idx, net in enumerate(self.networks):
            line_y = base_y + (idx * self.ssid_line_height) - self.ssid_scroll_offset
            # If it's outside the box, we skip rendering
            if line_y > self.ssid_box_rect.bottom - self.ssid_line_height:
                continue
            if line_y < self.ssid_box_rect.top - self.ssid_line_height:
                continue

            # Check if hovered
            is_sel = (idx==self.selected_network_index and self.current_selection=='networks')
            color = GREEN if is_sel else BLACK

            # We'll also highlight if hovered
            name_txt = self.app.font_NES_24.render(net, True, color)

            # The "CONNECTED" label if self.connected_ssid == net
            connected_txt = None
            if self.connected_ssid == net:
                connected_txt = self.app.font_NES_24.render("CONNECTED", True, GREEN)

            # Draw a small highlight rect if is_sel
            name_x = self.ssid_box_rect.left + 20
            name_y = line_y
            
            if is_sel:
                # Create a highlight rectangle with extra horizontal padding (say 8 pixels on left/right)
                padding = 8
                text_width = name_txt.get_width()
                text_height = self.ssid_line_height
                highlight_rect = pygame.Rect(name_x - padding, name_y, text_width + 2*padding, text_height)
                pygame.draw.rect(surf, LIGHT_GRAY, highlight_rect, 2)  # use LIGHT_GRAY for the border

            surf.blit(name_txt, (name_x, name_y))
            if connected_txt:
                surf.blit(connected_txt, (name_x + 300, name_y))

        surf.set_clip(old_clip)

        # 3) Draw the 3 image buttons (Rescan, Manual, Skip/Continue)
        self.draw_img_button(
            surf, self.rescan_button_rect,
            self.rescan_images[0], self.rescan_images[1], self.rescan_images[2],
            (self.current_selection=='rescan')
        )
        self.draw_img_button(
            surf, self.manual_button_rect,
            self.manual_images[0], self.manual_images[1], self.manual_images[2],
            (self.current_selection=='manual')
        )
        if self.connected_ssid:
            # continue
            self.draw_img_button(
                surf, self.skip_button_rect,
                self.continue_images[0], self.continue_images[1], self.continue_images[2],
                (self.current_selection=='continue')
            )
        else:
            # skip
            self.draw_img_button(
                surf, self.skip_button_rect,
                self.skip_images[0], self.skip_images[1], self.skip_images[2],
                (self.current_selection=='skip')
            )

        # If OSK is active, draw a bottom white bar + OSK
        if self.osk_mode:
            self.draw_osk_overlay(surf)

        # Status message
        if self.status_message and time.time()<self.status_expire_time:
            msg_font = self.app.font_NES_24
            msg_surf= msg_font.render(self.status_message, True, self.status_color)
            # place at y= (button_y - 50) => 640 - 50 = 590
            msg_rect= msg_surf.get_rect(center=(PHYSICAL_WIDTH//2, self.button_y - 50))
            surf.blit(msg_surf, msg_rect)
        elif self.status_message and time.time()>=self.status_expire_time:
            self.status_message=None

    def draw_img_button(self, surf, rect, norm, hov, press, selected):
        mx, my = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mx, my)
        if selected or is_hover:
            if pygame.mouse.get_pressed()[0]:
                surf.blit(press, rect)
            else:
                surf.blit(hov, rect)
        else:
            surf.blit(norm, rect)

    # -------------------------------------------------------------------------
    # OSK OVERLAY
    # -------------------------------------------------------------------------
    def draw_osk_overlay(self, surf):
        """
        We'll do a white bar at the bottom. The OSK will appear above it.
        We'll shift OSK up a bit so it's not flush at bottom.
        We also display self.osk.prompt_label, plus the typed text if desired.
        """
        overlay = pygame.Surface((PHYSICAL_WIDTH, PHYSICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        surf.blit(overlay,(0,0))

        # We'll define a rect for the "white bar" that might be ~ 400 px high
        # We'll put it from y= (PHYSICAL_HEIGHT - 400) to bottom
        bar_height = 400
        bar_rect = pygame.Rect(0, PHYSICAL_HEIGHT - bar_height, PHYSICAL_WIDTH, bar_height)
        pygame.draw.rect(surf, WHITE, bar_rect)

        # if the OnScreenKeyboard class supports a prompt_label, we can display it
        if hasattr(self.osk, 'prompt_label'):
            prompt_font = pygame.font.Font(None, 48)
            prompt_txt = prompt_font.render(self.osk.prompt_label, True, BLACK)
            p_rect = prompt_txt.get_rect(midtop=(PHYSICAL_WIDTH//2, bar_rect.top + 10))
            surf.blit(prompt_txt, p_rect)

        # We'll shift the OSK's y up a bit so it sits inside the bar
        self.osk.draw(surf, self.osk_mode, bottom_bar_rect=bar_rect)

    # -------------------------------------------------------------------------
    # END
    # -------------------------------------------------------------------------