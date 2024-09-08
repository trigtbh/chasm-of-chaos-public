import curses

class Format:
    def __init__(self, bold, italic, underline):
        self.bold = bold
        self.italic = italic
        self.underline = underline

BOLD_ON = Format(1, 0, 0)
BOLD_OFF = Format(-1, 0, 0)
ITALIC_ON = Format(0, 1, 0)
ITALIC_OFF = Format(0, -1, 0)
UNDERLINE_ON = Format(0, 0, 1)
UNDERLINE_OFF = Format(0, 0, -1)