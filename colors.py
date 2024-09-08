import curses

class Color:
    def __init__(self, fg: int):
        self.fg = fg
    

BLACK = Color(curses.COLOR_BLACK)
RED = Color(curses.COLOR_RED)
GREEN = Color(curses.COLOR_GREEN)
YELLOW = Color(curses.COLOR_YELLOW)
BLUE = Color(curses.COLOR_BLUE)
MAGENTA = Color(curses.COLOR_MAGENTA)
CYAN = Color(curses.COLOR_CYAN)
WHITE = Color(curses.COLOR_WHITE)

# optional
ORANGE = Color(208)
PURPLE = Color(129)
BROWN = Color(94)
PINK = Color(217)
GRAY = Color(8)
GREY = Color(GRAY)
