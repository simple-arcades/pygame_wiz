import pygame
import datetime
import sys

from ..screen_manager import Screen
from ..constants import BLACK, BLUE, GRAY, RED, GREEN, YELLOW, TERMS_LOG_FILE
from ..utils import log, show_message

class TermsScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.font = self.app.font_NES_20

        self.terms_lines = self.load_terms()
        self.terms_surface = None

        self.scroll_offset = 0
        self.scroll_speed = 20
        self.agree_enabled = False
        self.agree_selected = False
        self.agree_hovered = False

        self.text_box_rect = pygame.Rect(
            self.app.bubble_rect.left + 40,
            self.app.bubble_rect.top + 350,
            self.app.bubble_rect.width - 80,
            self.app.bubble_rect.height - 535,
        )
        self.agree_button_rect = pygame.Rect(
            self.text_box_rect.centerx - 111,
            self.text_box_rect.bottom + 20,
            222,
            55,
        )

        self.placeholder_images = self.load_placeholders()
        self.agree_normal, self.agree_hover, self.agree_pressed = self.load_agree_imgs()

        self.render_terms_surface()

        self.click_sound = None
        self.hover_sound = None
        self.load_sounds()

    def load_terms(self):
        lines = []
        try:
            path = self.app.get_path("terms_and_conditions.txt")
            with open(path, "r") as f:
                raw = f.readlines()
            for rl in raw:
                lines.append(rl.rstrip("\n"))
        except FileNotFoundError:
            log("Error: terms_and_conditions.txt not found.")
            lines = ["**Error: Terms and Conditions file not found.**"]
        return lines

    def load_placeholders(self):
        configs = [
            {
                "path": "user_agreement.png",
                "size": (803,205),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 401,
                    self.app.bubble_rect.top + 80,
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
                "path": "page_indicator_3.png",
                "size": (212,18),
                "pos": (
                    self.app.bubble_rect.left + 1419//2 - 106,
                    self.app.bubble_rect.top + 880,
                ),
            },
        ]
        result = []
        for cfg in configs:
            try:
                ip = self.app.get_path("images", cfg["path"])
                img = pygame.image.load(ip).convert_alpha()
                img = pygame.transform.scale(img, cfg["size"])
            except Exception as e:
                log(f"Failed to load image {cfg['path']}: {e}")
                img = pygame.Surface(cfg["size"])
                img.fill(BLUE)
            result.append({"img": img, "pos": cfg["pos"]})
        return result

    def load_agree_imgs(self):
        try:
            n = pygame.image.load(self.app.get_path("images","agree_normal_lg.png")).convert_alpha()
            h = pygame.image.load(self.app.get_path("images","agree_hover_lg.png")).convert_alpha()
            p = pygame.image.load(self.app.get_path("images","agree_pressed_lg.png")).convert_alpha()
        except Exception as e:
            log(f"Failed to load agree button images: {e}")
            n = pygame.Surface((222,55))
            n.fill(GREEN)
            h = pygame.Surface((222,55))
            h.fill(YELLOW)
            p = pygame.Surface((222,55))
            p.fill(RED)
        return n,h,p

    def load_sounds(self):
        try:
            cpath = self.app.get_path("sounds","select.ogg")
            hpath = self.app.get_path("sounds","hover.ogg")
            self.click_sound = pygame.mixer.Sound(cpath)
            self.click_sound.set_volume(0.5)
            self.hover_sound = pygame.mixer.Sound(hpath)
            self.hover_sound.set_volume(0.1)
        except Exception as e:
            log(f"Failed to load TermsScreen sounds: {e}")

    def render_terms_surface(self):
        max_width = self.text_box_rect.width - 20
        rendered_lines = []
        for line in self.terms_lines:
            if not line.strip():
                # blank line
                rendered_lines.append("")
            else:
                words = line.split(" ")
                current_line = ""
                for w in words:
                    test_line = (current_line + " " + w).strip()
                    surf_test = self.font.render(test_line, True, BLACK)
                    if surf_test.get_width() > max_width:
                        rendered_lines.append(current_line)
                        current_line = w
                    else:
                        current_line = test_line
                rendered_lines.append(current_line)

        line_height = self.font.get_linesize()
        total_height = line_height * len(rendered_lines)

        self.terms_surface = pygame.Surface((max_width,total_height), pygame.SRCALPHA)
        self.terms_surface.fill((0,0,0,0))

        y = 0
        for rl in rendered_lines:
            txt = self.font.render(rl,True,BLACK)
            self.terms_surface.blit(txt,(0,y))
            y += line_height

    def handle_events(self, events):
        super().handle_events(events)
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button==1:
                mx,my = e.pos
                if self.agree_enabled and self.agree_button_rect.collidepoint(mx,my):
                    self.on_agree()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_DOWN:
                    self.scroll_offset -= self.scroll_speed
                elif e.key == pygame.K_UP:
                    self.scroll_offset += self.scroll_speed
                elif e.key == pygame.K_RETURN:
                    if self.agree_enabled and self.agree_selected:
                        self.on_agree()
                elif e.key == pygame.K_LEFT:
                    self.agree_selected = False
                elif e.key == pygame.K_RIGHT:
                    if self.agree_enabled:
                        self.agree_selected = True
            elif e.type == pygame.JOYBUTTONDOWN:
                if e.button == 0:
                    if self.agree_enabled and self.agree_selected:
                        self.on_agree()
                elif e.button == 1:
                    self.app.screen_manager.change_screen("timezone")
            elif e.type == pygame.JOYAXISMOTION:
                if e.axis == 1:
                    if e.value > 0.5:
                        self.scroll_offset -= self.scroll_speed
                    elif e.value < -0.5:
                        self.scroll_offset += self.scroll_speed
                elif e.axis == 0:
                    if e.value < -0.5:
                        self.agree_selected = False
                    elif e.value > 0.5:
                        if self.agree_enabled:
                            self.agree_selected = True

        self.clamp_scroll()

    def on_agree(self):
        if self.click_sound:
            self.click_sound.play()
        self.log_user_agreement()
        self.app.screen_manager.change_screen("wifi")

    def log_user_agreement(self):
        import datetime
        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"User agreed on {t}\n"
        try:
            with open(TERMS_LOG_FILE,"a") as lf:
                lf.write(msg)
        except Exception as e:
            log(f"Failed to write to terms log: {e}")

    def clamp_scroll(self):
        total_h = self.terms_surface.get_height()
        visible_h = self.text_box_rect.height
        min_offset = -(total_h - visible_h)
        if min_offset>0:
            min_offset=0
        if self.scroll_offset<min_offset:
            self.scroll_offset=min_offset
        if self.scroll_offset>0:
            self.scroll_offset=0

        if self.scroll_offset<=min_offset:
            self.agree_enabled = True
        else:
            self.agree_enabled = False
            self.agree_selected = False

    def render(self, surf):
        self.render_background_and_bubble(surf)
        for p in self.placeholder_images:
            surf.blit(p["img"], p["pos"])

        old_clip = surf.get_clip()
        surf.set_clip(self.text_box_rect)

        area_y = -self.scroll_offset
        if area_y<0:
            area_y=0
        area = pygame.Rect(0, area_y, self.text_box_rect.width, self.text_box_rect.height)

        surf.blit(self.terms_surface,(self.text_box_rect.left,self.text_box_rect.top),area=area)
        surf.set_clip(old_clip)

        self.draw_scrollbar(surf)

        mx,my = pygame.mouse.get_pos()
        if self.agree_enabled:
            if self.agree_button_rect.collidepoint(mx,my):
                self.agree_hovered = True
            else:
                self.agree_hovered = False

            if self.agree_selected or self.agree_hovered:
                current = self.agree_hover
            else:
                current = self.agree_normal
        else:
            current = self.agree_normal.copy()
            current.set_alpha(100)

        surf.blit(current, self.agree_button_rect)

    def draw_scrollbar(self, surf):
        bar_w=20
        bar_x=self.text_box_rect.right - bar_w
        bar_y=self.text_box_rect.top
        bar_h=self.text_box_rect.height
        pygame.draw.rect(surf,GRAY,(bar_x,bar_y,bar_w,bar_h))

        total_h=self.terms_surface.get_height()
        if total_h<=bar_h:
            return

        frac = abs(self.scroll_offset)/(total_h-bar_h)
        frac = min(frac,1)
        scroll_h = max(int(bar_h*(bar_h/total_h)),10)
        scroll_y = bar_y + frac*(bar_h - scroll_h)
        pygame.draw.rect(surf,BLACK,(bar_x,scroll_y,bar_w,scroll_h))