import pygame
import time

# Tetromino Colors (0-6) + empty (-1)
COLORS = {
    -1: (30, 30, 30),      # Empty
    0: (0, 240, 240),      # I
    1: (240, 240, 0),      # O
    2: (160, 0, 240),      # T
    3: (0, 240, 0),        # S
    4: (240, 0, 0),        # Z
    5: (0, 0, 240),        # J
    6: (240, 160, 0),      # L
}

CELL_SIZE = 28
BORDER = 3

class Display:
    def __init__(self):
        pygame.init()
        
        self.board_width = 10
        self.board_height = 20
        self.board_pixel_width = self.board_width * CELL_SIZE
        self.board_pixel_height = self.board_height * CELL_SIZE
        
        # Layout: sidebar + board + gap + board + sidebar
        self.sidebar_width = 180
        self.gap = 30
        self.screen_width = (self.sidebar_width * 2) + (self.board_pixel_width * 2) + self.gap
        self.screen_height = self.board_pixel_height + 120
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Tetris Online - 2 Players")
        
        self.title_font = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        self.blink_start_time = None

    def render(self, player_state, opponent_state):
        self.screen.fill((18, 18, 20))
        game_over = player_state.get('gameover', False) if player_state else False
        
        # Blink effect for game over
        should_show = True
        if game_over:
            if self.blink_start_time is None:
                self.blink_start_time = time.time()
            elapsed = time.time() - self.blink_start_time
            should_show = (int(elapsed * 2) % 2) == 0
        else:
            self.blink_start_time = None
        
        if should_show:
            # Player 1: Sidebar + Board
            sidebar_x1 = 20
            board_x1 = sidebar_x1 + self.sidebar_width + 10
            self._draw_sidebar(player_state, sidebar_x1, 70, is_player=True)
            self._draw_board(player_state, board_x1, 70, is_player=True)
            
            # Player 2: Board + Sidebar
            board_x2 = board_x1 + self.board_pixel_width + self.gap
            sidebar_x2 = board_x2 + self.board_pixel_width + 10
            self._draw_board(opponent_state, board_x2, 70, is_player=False)
            self._draw_sidebar(opponent_state, sidebar_x2, 70, is_player=False)
        
        # pygame.display.flip()

    def _draw_sidebar(self, state, x_offset, y_offset, is_player=True):
        if not state:
            return
        
        # Draw sidebar background
        sidebar_rect = pygame.Rect(x_offset, y_offset, self.sidebar_width, self.board_pixel_height)
        pygame.draw.rect(self.screen, (28, 28, 32), sidebar_rect)
        pygame.draw.rect(self.screen, (90, 90, 100), sidebar_rect, 2)
        
        text_y = y_offset + 20
        
        def draw_stat(title, value, color=(200, 200, 200)):
            nonlocal text_y
            title_surf = self.small_font.render(title, True, (150, 150, 150))
            value_surf = self.font.render(str(value), True, color)
            self.screen.blit(title_surf, (x_offset + 12, text_y))
            self.screen.blit(value_surf, (x_offset + 12, text_y + 22))
            text_y += 65
        
        # Draw stats
        player_label = "PLAYER 1" if is_player else "PLAYER 2"
        label_surf = self.font.render(player_label, True, (255, 255, 255))
        self.screen.blit(label_surf, (x_offset + 12, text_y))
        text_y += 40
        
        draw_stat("SCORE", state.get('score', 0), (200, 220, 255))
        draw_stat("LINES", state.get('lines', 0), (200, 220, 255))
        draw_stat("LEVEL", state.get('level', 0), (200, 220, 255))

    def _draw_board(self, state, x_offset, y_offset, is_player=True):
        if not state:
            return
        board = state.get('board', [])
        current = state.get('current')
        player_id = state.get('player_id', '')
        gameover = state.get('gameover', False)
        
        # Draw board background with subtle shadow
        bg_rect = pygame.Rect(x_offset-3, y_offset-3, self.board_pixel_width+6, self.board_pixel_height+6)
        pygame.draw.rect(self.screen, (15, 15, 18), bg_rect)
        pygame.draw.rect(self.screen, (80, 80, 90), bg_rect, 2)
        
        # Draw title
        title = f"{'PLAYER 1' if is_player else 'PLAYER 2'}"
        title_surf = self.title_font.render(title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(x_offset + self.board_pixel_width // 2, y_offset - 35))
        self.screen.blit(title_surf, title_rect)
        
        # Draw locked pieces
        for r, row in enumerate(board):
            for c, val in enumerate(row):
                color = COLORS.get(val, COLORS[-1])
                cell_rect = pygame.Rect(x_offset + c*CELL_SIZE, y_offset + r*CELL_SIZE, CELL_SIZE-1, CELL_SIZE-1)
                pygame.draw.rect(self.screen, color, cell_rect)
                pygame.draw.rect(self.screen, (50, 50, 50), cell_rect, 1)
        
        # Draw current falling piece
        if current and not gameover:
            shape = current.get('shape', [])
            piece_x = current.get('x', 0)
            piece_y = current.get('y', 0)
            piece_type = current.get('type', 0)
            base_color = COLORS.get(piece_type, COLORS[0])
            for i, row in enumerate(shape):
                for j, cell in enumerate(row):
                    if cell:
                        cx = x_offset + (piece_x + j) * CELL_SIZE
                        cy = y_offset + (piece_y + i) * CELL_SIZE
                        rect = pygame.Rect(cx, cy, CELL_SIZE-1, CELL_SIZE-1)
                        pygame.draw.rect(self.screen, base_color, rect)
                        pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)
        
        # Game over overlay
        if gameover:
            overlay = pygame.Surface((self.board_pixel_width, self.board_pixel_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (x_offset, y_offset))
            go_text = self.title_font.render("GAME OVER", True, (255, 50, 50))
            text_rect = go_text.get_rect(center=(x_offset + self.board_pixel_width//2, y_offset + self.board_pixel_height//2))
            self.screen.blit(go_text, text_rect)