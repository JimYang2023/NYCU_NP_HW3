# tetris_logic.py
import random
import copy

BOARD_WIDTH = 10
BOARD_HEIGHT = 20

# Shapes as matrices (0/1)
SHAPES = [
    # I
    [[1,1,1,1]],
    # O
    [[1,1],
     [1,1]],
    # T
    [[0,1,0],
     [1,1,1]],
    # S
    [[0,1,1],
     [1,1,0]],
    # Z
    [[1,1,0],
     [0,1,1]],
    # J
    [[1,0,0],
     [1,1,1]],
    # L
    [[0,0,1],
     [1,1,1]],
]

def rotate_matrix(mat):
    return [list(row) for row in zip(*mat[::-1])]

class PieceBag:
    """
    Implements the 7-bag randomizer system.
    Creates a shuffled list of all 7 piece types and draws from it.
    When empty, refills with a new shuffled sequence.
    """
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.bag = []
        self.refill()

    def refill(self):
        """Refill the bag with a random sequence of all 7 pieces"""
        self.bag = list(range(len(SHAPES)))
        self.rng.shuffle(self.bag)

    def draw(self):
        """Draw the next piece from the bag, refilling if empty"""
        if not self.bag:
            self.refill()
        return self.bag.pop(0)

class TetrisGame:
    def __init__(self, seed=None):
        self.board = [[-1]*BOARD_WIDTH for _ in range(BOARD_HEIGHT)]  # -1 = empty, 0..6 = color/piece id
        self.score = 0
        self.level = 0
        self.lines = 0
        self.gameover = False

        self.current = None   # dict: {'type':int, 'shape':matrix, 'x':int, 'y':int}
        self.piece_bag = PieceBag(seed=seed)
        self.next_type = self.piece_bag.draw()
        self.spawn_piece()

        self.tick_count = 0
        self.drop_interval_ticks = 10  # gravity speed (smaller -> faster)

    def spawn_piece(self):
        t = self.next_type
        self.next_type = self.piece_bag.draw()
        shape = copy.deepcopy(SHAPES[t])
        x = (BOARD_WIDTH - len(shape[0])) // 2
        y = 0
        self.current = {'type': t, 'shape': shape, 'x': x, 'y': y}
        if self._collision(self.current['x'], self.current['y'], self.current['shape']):
            self.gameover = True

    def _collision(self, x, y, shape):
        for i, row in enumerate(shape):
            for j, v in enumerate(row):
                if not v:
                    continue
                nx = x + j
                ny = y + i
                if nx < 0 or nx >= BOARD_WIDTH or ny < 0 or ny >= BOARD_HEIGHT:
                    return True
                if self.board[ny][nx] != -1:
                    return True
        return False

    def rotate(self):
        if not self.current or self.gameover:
            return
        new_shape = rotate_matrix(self.current['shape'])
        # try wall kicks: (0,0), (-1,0), (1,0), (0,-1)
        kicks = [(0,0),(-1,0),(1,0),(0,-1)]
        for dx,dy in kicks:
            nx = self.current['x'] + dx
            ny = self.current['y'] + dy
            if not self._collision(nx, ny, new_shape):
                self.current['shape'] = new_shape
                self.current['x'] = nx
                self.current['y'] = ny
                return

    def move(self, dx):
        if not self.current or self.gameover:
            return
        nx = self.current['x'] + dx
        if not self._collision(nx, self.current['y'], self.current['shape']):
            self.current['x'] = nx

    def soft_drop(self):
        if not self.current or self.gameover:
            return
        ny = self.current['y'] + 1
        if not self._collision(self.current['x'], ny, self.current['shape']):
            self.current['y'] = ny
        else:
            self.lock_piece()

    def hard_drop(self):
        if not self.current or self.gameover:
            return
        while not self._collision(self.current['x'], self.current['y'] + 1, self.current['shape']):
            self.current['y'] += 1
        self.lock_piece()

    def lock_piece(self):
        s = self.current
        for i, row in enumerate(s['shape']):
            for j, v in enumerate(row):
                if not v:
                    continue
                bx = s['x'] + j
                by = s['y'] + i
                if 0 <= by < BOARD_HEIGHT and 0 <= bx < BOARD_WIDTH:
                    self.board[by][bx] = s['type']
        self.current = None
        cleared = self.clear_lines()
        if cleared:
            self.lines += cleared
            self.score += cleared * 100
            # speed up slightly every few lines
            self.drop_interval_ticks = max(2, 10 - (self.lines // 10))
        self.spawn_piece()

    def clear_lines(self):
        new_board = [row for row in self.board if any(cell == -1 for cell in row)]
        removed = BOARD_HEIGHT - len(new_board)
        for _ in range(removed):
            new_board.insert(0, [-1]*BOARD_WIDTH)
        self.board = new_board
        return removed

    def update(self):
        if self.gameover:
            return
        self.tick_count += 1
        if self.tick_count >= self.drop_interval_ticks:
            self.tick_count = 0
            self.soft_drop()

    def get_game_state(self, player_id=None, oppo_id=None):
        """
        Return a dict shaped for the Display.render(...) function:
        {
          'board': [[-1,...],...],
          'current': {'shape':..., 'x':int, 'y':int, 'type':int},
          'score': int,
          'speed': float,
          'player_id': str,
          'oppo_id': str,
          'gameover': bool
        }
        """
        state = {
            'board': [row[:] for row in self.board],
            'current': None,
            'score': self.score,
            'speed': max(0.0, 1.0 - (10 - self.drop_interval_ticks)/10.0),  # normalized-ish
            'player_id': player_id or '',
            'oppo_id': oppo_id or '',
            'gameover': self.gameover,
            'lines': self.lines,
            'level': max(0, (self.lines // 10))
        }
        if self.current:
            state['current'] = {
                'shape': [row[:] for row in self.current['shape']],
                'x': self.current['x'],
                'y': self.current['y'],
                'type': self.current['type']
            }
        return state