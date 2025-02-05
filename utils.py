import os
import sys
import datetime
import pygame

from .constants import APP_LOG_FILE, PHYSICAL_WIDTH, PHYSICAL_HEIGHT, WHITE

def log(message: str):
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(APP_LOG_FILE, "a") as f:
            f.write(f"[{t}] {message}\n")
    except Exception as e:
        print(f"Logging failed: {e}")

def show_message(surface: pygame.Surface, message: str, color=WHITE, timeout=2):
    font = pygame.font.Font(None, 56)  # We'll just use a default system font here
    overlay = pygame.Surface((PHYSICAL_WIDTH, PHYSICAL_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    lines = message.strip().split("\n")
    y = PHYSICAL_HEIGHT // 2 - (len(lines) * 40) // 2
    for line in lines:
        txt_surf = font.render(line, True, color)
        txt_rect = txt_surf.get_rect(center=(PHYSICAL_WIDTH // 2, y))
        surface.blit(txt_surf, txt_rect)
        y += 50

    pygame.display.flip()

    start_time = pygame.time.get_ticks()
    waiting = True
    while waiting:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    waiting = False
            elif e.type == pygame.JOYBUTTONDOWN:
                if e.button == 0:
                    waiting = False

        elapsed_time = (pygame.time.get_ticks() - start_time) / 1000.0
        if elapsed_time > timeout:
            waiting = False
