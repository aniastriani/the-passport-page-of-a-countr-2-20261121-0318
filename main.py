"""Pure-stdlib passport spread renderer.

Draws one deterministic 1024x1024 PNG: an open passport for the
Republic of Caldoria (a country that is not there). Left page is the
data page, right page is the visa page. Only the Python standard
library is used: the picture is painted pixel by pixel into a
bytearray and written out with a hand-rolled PNG encoder.
"""

import binascii
import math
import os
import struct
import sys
import zlib

W = 1024
H = 1024

NAVY = (31, 51, 80)
DARK_NAVY = (35, 42, 59)
CREAM = (245, 237, 217)
GOLD = (185, 168, 107)
GOLD_DARK = (160, 140, 80)
GREY = (110, 110, 110)
LIGHT_GREY = (154, 163, 181)
GUILLOCHE = (228, 214, 176)
MRZ_BG = (239, 228, 200)
GREEN = (46, 93, 67)
GREEN_LIGHT = (234, 243, 228)
GREEN_MID = (46, 125, 79)
BLUE = (31, 78, 156)
RED = (176, 42, 42)
PURPLE = (106, 63, 160)
SKIN = (232, 195, 154)
HAIR = (58, 42, 30)
SUIT = (34, 48, 74)
PHOTO_BG = (201, 214, 228)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
MAP_BG = (220, 233, 242)
TAN = (232, 217, 168)


class Canvas:
    """An RGB picture held in a flat bytearray."""

    def __init__(self, width, height, colour):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 3)
        self.fill_rect(0, 0, width, height, colour)

    def set_pixel(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i] = colour[0]
            self.pixels[i + 1] = colour[1]
            self.pixels[i + 2] = colour[2]

    def fill_rect(self, x0, y0, x1, y1, colour):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.width, x1)
        y1 = min(self.height, y1)
        for y in range(y0, y1):
            base = (y * self.width + x0) * 3
            for x in range(x0, x1):
                j = base + (x - x0) * 3
                self.pixels[j] = colour[0]
                self.pixels[j + 1] = colour[1]
                self.pixels[j + 2] = colour[2]

    def rect_border(self, x0, y0, x1, y1, colour, thick=1):
        for t in range(thick):
            self.hline(x0 + t, x1 - t, y0 + t, colour)
            self.hline(x0 + t, x1 - t, y1 - t, colour)
            self.vline(x0 + t, y0 + t, y1 - t, colour)
            self.vline(x1 - t, y0 + t, y1 - t, colour)

    def hline(self, x0, x1, y, colour):
        if x0 > x1:
            x0, x1 = x1, x0
        for x in range(x0, x1 + 1):
            self.set_pixel(x, y, colour)

    def vline(self, x, y0, y1, colour):
        if y0 > y1:
            y0, y1 = y1, y0
        for y in range(y0, y1 + 1):
            self.set_pixel(x, y, colour)

    def line(self, x0, y0, x1, y1, colour):
        """Bresenham line between two points."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.set_pixel(x, y, colour)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, colour, thick=1):
        for t in range(thick):
            rr = r - t
            if rr <= 0:
                break
            steps = max(8, int(2 * math.pi * rr))
            for i in range(steps):
                a = 2 * math.pi * i / steps
                self.set_pixel(cx + int(rr * math.cos(a)),
                               cy + int(rr * math.sin(a)), colour)

    def filled_circle(self, cx, cy, r, colour):
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            half = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline(cx - half, cx + half, y, colour)

    def filled_polygon(self, points, colour):
        """Scanline fill for a simple polygon."""
        if not points:
            return
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    if y1 != y0:
                        x = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                        xs.append(x)
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(xs[i]), int(xs[i + 1]), y, colour)

    def polygon_outline(self, points, colour):
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            self.line(x0, y0, x1, y1, colour)

    def vertical_gradient(self, x0, y0, x1, y1, top, bottom):
        span = max(1, y1 - y0)
        for y in range(y0, y1):
            f = (y - y0) / span
            c = tuple(int(top[i] + (bottom[i] - top[i]) * f)
                      for i in range(3))
            self.hline(x0, x1 - 1, y, c)

    def wavy_hline(self, x0, x1, y, amp, period, colour, phase=0.0):
        for x in range(x0, x1 + 1):
            yy = y + int(amp * math.sin(2 * math.pi * (x - x0) / period
                                        + phase))
            self.set_pixel(x, yy, colour)

    def star(self, cx, cy, r, colour):
        """A small five-point star drawn with lines."""
        outer = []
        inner = []
        for i in range(5):
            a = -math.pi / 2 + i * 2 * math.pi / 5
            outer.append((cx + int(r * math.cos(a)),
                          cy + int(r * math.sin(a))))
            a2 = a + math.pi / 5
            inner.append((cx + int(r * 0.45 * math.cos(a2)),
                          cy + int(r * 0.45 * math.sin(a2))))
        pts = []
        for i in range(5):
            pts.append(outer[i])
            pts.append(inner[i])
        self.filled_polygon(pts, colour)


# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows of 5 characters; "1" is ink.
# Only uppercase letters, digits and a small punctuation set are needed,
# because every label on the spread is written in capitals.
# ---------------------------------------------------------------------------
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", "01100"),
    ",": (".....", ".....", ".....", ".....", ".....", "01100", "00100"),
    "-": (".....", ".....", ".....", "01110", ".....", ".....", "....."),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    ":": (".....", "01100", "01100", ".....", "01100", "01100", "....."),
    "'": ("00100", "00100", "01000", ".....", ".....", ".....", "....."),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "+": (".....", "00100", "00100", "01110", "00100", "00100", "....."),
    "=": (".....", ".....", "01110", ".....", "01110", ".....", "....."),
    "*": (".....", ".....", "01110", "01110", "01110", ".....", "....."),
}


def text_width(s, scale, gap=1):
    """Pixel width of a string at the given scale."""
    if not s:
        return 0
    return len(s) * (5 * scale + gap) - gap


def draw_text(canvas, s, x, y, scale, colour, bold=False, gap=1):
    """Draw a string; (x, y) is the top-left corner of the first glyph."""
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    canvas.fill_rect(cx + col * scale,
                                     y + row * scale,
                                     cx + col * scale + scale,
                                     y + row * scale + scale, colour)
                    if bold:
                        canvas.fill_rect(cx + col * scale + 1,
                                         y + row * scale,
                                         cx + col * scale + scale + 1,
                                         y + row * scale + scale, colour)
        cx += 5 * scale + gap
    return cx


def draw_text_centered(canvas, s, cx, y, scale, colour, bold=False, gap=1):
    w = text_width(s, scale, gap)
    draw_text(canvas, s, cx - w // 2, y, scale, colour, bold, gap)


# ---------------------------------------------------------------------------
# PNG encoder: raw scanlines (filter 0), one IDAT chunk, CRC32 checksums.
# ---------------------------------------------------------------------------

def _chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(
        ">I", binascii.crc32(body) & 0xFFFFFFFF)


def encode_png(canvas):
    raw = bytearray()
    row_bytes = canvas.width * 3
    for y in range(canvas.height):
        raw.append(0)
        start = y * row_bytes
        raw += canvas.pixels[start:start + row_bytes]
    ihdr = struct.pack(">IIBBBBB", canvas.width, canvas.height,
                       8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png


# ---------------------------------------------------------------------------
# ICAO machine-readable-zone check digits.
# Digit values: 0-9 as themselves, A=10 .. Z=35, "<"=0.
# Weights repeat 7, 3, 1. Check digit is the weighted sum mod 10.
# ---------------------------------------------------------------------------

def _mrz_value(ch):
    if ch == "<":
        return 0
    if "0" <= ch <= "9":
        return ord(ch) - 48
    return ord(ch) - 55


def check_digit(text):
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(text):
        total += _mrz_value(ch) * weights[i % 3]
    return str(total % 10)


def build_mrz():
    """Return the two 44-character MRZ lines for this passport."""
    doc = "CLD847291"
    dob = "940314"
    expiry = "360601"
    line1 = "P<CLDMARLOWE<<JULIAN<AUREL" + "<" * 18
    body = (doc + check_digit(doc) + "CLD" + dob + check_digit(dob)
            + "M" + expiry + check_digit(expiry) + "<" * 14)
    composite = check_digit(body)
    line2 = body + composite + "0"
    return line1, line2


# ---------------------------------------------------------------------------
# Drawing the spread.
# ---------------------------------------------------------------------------

def draw_guilloche(canvas, x0, x1, y0, y1):
    y = y0 + 6
    phase = 0.0
    while y < y1:
        canvas.wavy_hline(x0, x1, y, 3, 46, GUILLOCHE, phase)
        y += 14
        phase += 1.1


def draw_emblem(canvas, cx, cy):
    canvas.circle(cx, cy, 46, GOLD, 3)
    canvas.circle(cx, cy, 40, GOLD, 2)
    for i in range(8):
        a = i * math.pi / 4
        length = 36 if i % 2 == 0 else 24
        x2 = cx + int(length * math.cos(a))
        y2 = cy + int(length * math.sin(a))
        canvas.line(cx, cy, x2, y2, NAVY)
        # small gold tip on each compass point
        tx = cx + int((length + 4) * math.cos(a))
        ty = cy + int((length + 4) * math.sin(a))
        canvas.filled_circle(tx, ty, 2, GOLD)
    canvas.filled_circle(cx, cy, 7, NAVY)
    canvas.circle(cx, cy, 7, GOLD, 1)
    for dx in (-52, 0, 52):
        canvas.star(cx + dx, cy - 58, 6, GOLD)
    canvas.wavy_hline(cx - 34, cx + 34, cy + 56, 2, 22, NAVY)
    canvas.wavy_hline(cx - 34, cx + 34, cy + 62, 2, 22, GOLD)


def draw_portrait(canvas, x0, y0, x1, y1):
    canvas.fill_rect(x0, y0, x1, y1, PHOTO_BG)
    canvas.rect_border(x0, y0, x1, y1, NAVY, 2)
    cx = (x0 + x1) // 2
    # shoulders / suit
    canvas.filled_polygon([(x0 + 8, y1), (cx - 34, y1 - 52),
                           (cx - 30, y1 - 78), (cx + 30, y1 - 78),
                           (cx + 34, y1 - 52), (x1 - 8, y1)], SUIT)
    # white shirt triangle and tie
    canvas.filled_polygon([(cx - 14, y1 - 76), (cx + 14, y1 - 76),
                           (cx, y1 - 44)], WHITE)
    canvas.filled_polygon([(cx - 5, y1 - 62), (cx + 5, y1 - 62),
                           (cx + 8, y1 - 30), (cx - 8, y1 - 30)], NAVY)
    # neck and face
    canvas.fill_rect(cx - 11, y1 - 96, cx + 11, y1 - 72, SKIN)
    canvas.filled_circle(cx, y0 + 52, 30, SKIN)
    # hair: cap over the top of the head
    canvas.filled_polygon([(cx - 30, y0 + 52), (cx - 28, y0 + 26),
                           (cx - 12, y0 + 14), (cx + 12, y0 + 14),
                           (cx + 28, y0 + 26), (cx + 30, y0 + 52),
                           (cx + 18, y0 + 38), (cx, y0 + 32),
                           (cx - 18, y0 + 38)], HAIR)
    # eyes, nose, mouth
    canvas.hline(cx - 16, cx - 6, y0 + 50, BLACK)
    canvas.hline(cx + 6, cx + 16, y0 + 50, BLACK)
    canvas.vline(cx, y0 + 52, y0 + 64, BLACK)
    canvas.hline(cx - 8, cx + 8, y0 + 72, BLACK)


def draw_field(canvas, x, y, label, value):
    draw_text(canvas, label, x, y, 1, GREY)
    draw_text(canvas, value, x, y + 14, 2, NAVY, bold=True)


def draw_left_page(canvas):
    # page + inner border
    canvas.fill_rect(60, 126, 508, 890, CREAM)
    canvas.rect_border(68, 134, 500, 882, GOLD, 1)
    canvas.rect_border(72, 138, 496, 878, GOLD, 1)
    draw_guilloche(canvas, 76, 494, 140, 876)
    draw_emblem(canvas, 284, 205)
    draw_text_centered(canvas, "REPUBLIC OF CALDORIA", 284, 272, 3,
                       NAVY, bold=True)
    draw_text_centered(canvas, "PASSPORT - PASSEPORT", 284, 300, 2, NAVY)
    canvas.hline(100, 468, 318, GOLD_DARK)
    canvas.hline(100, 468, 319, GOLD_DARK)
    # info row
    draw_text(canvas, "TYPE / TYPE", 100, 340, 1, GREY)
    draw_text(canvas, "CODE / CODE", 250, 340, 1, GREY)
    draw_text(canvas, "NO. / NO", 380, 340, 1, GREY)
    draw_text(canvas, "P", 100, 356, 2, NAVY, bold=True)
    draw_text(canvas, "CLD", 250, 356, 2, NAVY, bold=True)
    draw_text(canvas, "CLD 847 291", 370, 356, 2, NAVY, bold=True)
    # photo
    draw_portrait(canvas, 100, 392, 216, 552)
    draw_text_centered(canvas, "PHOTOGRAPH", 158, 558, 1, GREY)
    # data fields: pitch 48 so the last row (sex / signature) ends
    # well above the issue / expiry block at the bottom of the page.
    draw_field(canvas, 236, 392, "SURNAME / NOM", "MARLOWE")
    draw_field(canvas, 236, 440, "GIVEN NAMES / PRENOMS", "JULIAN AUREL")
    draw_field(canvas, 236, 488, "NATIONALITY / NATIONALITE", "CALDORIAN")
    draw_field(canvas, 236, 536, "DATE OF BIRTH / NE(E) LE", "14 MAR 1994")
    draw_field(canvas, 236, 584, "PLACE OF BIRTH / LIEU DE NAISSANCE",
               "PORT AURELINE")
    draw_text(canvas, "SEX / SEXE", 236, 632, 1, GREY)
    draw_text(canvas, "M", 236, 646, 2, NAVY, bold=True)
    draw_text(canvas, "HOLDER'S SIGNATURE / SIGNATURE", 300, 632, 1, GREY)
    canvas.wavy_hline(300, 480, 668, 3, 30, NAVY)
    canvas.wavy_hline(300, 480, 674, 2, 26, NAVY)
    # bottom row: issue / expiry stacked on the left, authority in
    # the middle, gold seal on the right, issued-at line below them.
    draw_text(canvas, "DATE OF ISSUE / DELIVRE LE", 100, 692, 1, GREY)
    draw_text(canvas, "02 JUN 2026", 100, 706, 2, NAVY, bold=True)
    draw_text(canvas, "DATE OF EXPIRY / EXPIRE LE", 100, 734, 1, GREY)
    draw_text(canvas, "01 JUN 2036", 100, 748, 2, NAVY, bold=True)
    draw_text(canvas, "AUTHORITY / AUTORITE", 280, 692, 1, GREY)
    draw_text(canvas, "MINISTRY OF", 280, 706, 2, NAVY, bold=True)
    draw_text(canvas, "THE INTERIOR", 280, 728, 2, NAVY, bold=True)
    canvas.circle(440, 720, 18, GOLD, 2)
    canvas.circle(440, 720, 14, GOLD, 1)
    canvas.star(440, 720, 8, GOLD_DARK)
    draw_text(canvas, "ISSUED AT / DELIVRE A PORT AURELINE", 100, 768,
              1, GREY)
    # MRZ strip: full page width, so the 44-char lines (440 px at
    # scale 2, gap 0) fit inside it starting at x 64.
    canvas.fill_rect(60, 786, 508, 852, MRZ_BG)
    line1, line2 = build_mrz()
    draw_text(canvas, line1, 64, 796, 2, NAVY, gap=0)
    draw_text(canvas, line2, 64, 824, 2, NAVY, gap=0)


def draw_stamp_circle(canvas, cx, cy, place, date):
    canvas.circle(cx, cy, 42, BLUE, 2)
    canvas.circle(cx, cy, 37, BLUE, 1)
    draw_text_centered(canvas, place, cx, cy - 26, 1, BLUE, bold=True)
    draw_text_centered(canvas, "DEPARTURE", cx, cy - 8, 2, BLUE, bold=True)
    draw_text_centered(canvas, date, cx, cy + 12, 1, BLUE)
    canvas.star(cx, cy + 28, 5, BLUE)


def draw_stamp_rect(canvas, x0, y0, x1, y1, colour, place, line, date):
    canvas.rect_border(x0, y0, x1, y1, colour, 2)
    canvas.rect_border(x0 + 5, y0 + 5, x1 - 5, y1 - 5, colour, 1)
    cy = (y0 + y1) // 2
    draw_text_centered(canvas, place, (x0 + x1) // 2, cy - 26, 2, colour,
                       bold=True)
    draw_text_centered(canvas, line, (x0 + x1) // 2, cy - 4, 1, colour)
    draw_text_centered(canvas, date, (x0 + x1) // 2, cy + 12, 2, colour,
                       bold=True)


def draw_right_page(canvas):
    canvas.fill_rect(516, 126, 964, 890, CREAM)
    canvas.rect_border(524, 134, 956, 882, GOLD, 1)
    canvas.rect_border(528, 138, 952, 878, GOLD, 1)
    draw_guilloche(canvas, 532, 950, 140, 876)
    # faint compass watermark, bottom-left of the right page
    for r in (52, 40, 26):
        canvas.circle(600, 820, r, (232, 222, 190), 1)
    canvas.line(600, 768, 600, 872, (232, 222, 190))
    canvas.line(548, 820, 652, 820, (232, 222, 190))
    draw_text_centered(canvas, "VISAS", 740, 168, 3, NAVY, bold=True)
    draw_text_centered(canvas, "- PAGES 12 - 13 -", 740, 194, 1, GREY)
    draw_text(canvas, "CLD847291", 850, 160, 2, NAVY)
    # visa sticker
    canvas.fill_rect(545, 208, 935, 392, GREEN_LIGHT)
    canvas.rect_border(545, 208, 935, 392, GREEN, 2)
    canvas.fill_rect(545, 208, 935, 240, GREEN)
    draw_text_centered(canvas, "REPUBLIC OF MERIDIA", 740, 218, 2, WHITE,
                       bold=True)
    draw_text_centered(canvas, "VISITOR VISA - SINGLE ENTRY", 740, 258, 2,
                       GREEN, bold=True)
    draw_text(canvas, "HOLDER:", 560, 286, 1, GREY)
    draw_text(canvas, "MARLOWE, JULIAN AUREL", 640, 286, 2, GREEN, bold=True)
    draw_text(canvas, "VALID:", 560, 310, 1, GREY)
    draw_text(canvas, "15 JUN 2026 - 15 SEP 2026", 640, 310, 2, GREEN,
              bold=True)
    draw_text(canvas, "FEE PAID:", 560, 334, 1, GREY)
    draw_text(canvas, "40 MERIDIAN CROWNS", 640, 334, 2, GREEN, bold=True)
    draw_text(canvas, "VISA NO.:", 560, 358, 1, GREY)
    draw_text(canvas, "MV-2214", 640, 358, 2, GREEN, bold=True)
    # "M" stamp low in the sticker's right corner, clear of the
    # long Valid line above it.
    canvas.circle(898, 368, 22, GREEN, 2)
    canvas.circle(898, 368, 17, GREEN, 1)
    draw_text_centered(canvas, "M", 898, 360, 3, GREEN, bold=True)
    # conditions box
    canvas.rect_border(545, 404, 935, 452, GREEN, 1)
    draw_text(canvas, "CONDITIONS OF STAY - MERIDIA", 560, 414, 1, GREEN,
              bold=True)
    draw_text(canvas, "EMPLOYMENT PROHIBITED. HOLDER MUST DEPART BY",
              560, 430, 1, GREEN)
    draw_text(canvas, "15 SEP 2026. REPORT TO THE HARBOUR OFFICE",
              560, 444, 1, GREEN)
    # departure stamps, left column
    draw_stamp_circle(canvas, 615, 500, "CALDORIA", "18 JUN 2026")
    draw_stamp_circle(canvas, 615, 585, "MERIDIA", "04 JUL 2026")
    draw_stamp_circle(canvas, 615, 670, "TARNOVIA", "21 JUL 2026")
    # arrival stamps, right column
    draw_stamp_rect(canvas, 700, 462, 935, 538, RED, "SARN",
                    "ARRIVAL - PORT OF SARN", "19 JUN 2026")
    draw_stamp_rect(canvas, 700, 547, 935, 623, GREEN_MID, "KESTREL GATE",
                    "ARRIVAL - KESTREL GATE", "05 JUL 2026")
    draw_stamp_rect(canvas, 700, 632, 935, 708, RED, "PORT AURELINE",
                    "ARRIVAL - PORT AURELINE", "22 JUL 2026")
    # stamp duty box
    canvas.rect_border(560, 730, 740, 775, PURPLE, 2)
    draw_text_centered(canvas, "STAMP DUTY PAID", 650, 738, 2, PURPLE,
                       bold=True)
    draw_text_centered(canvas, "40 AURELS - 22 JUL 2026", 650, 758, 1,
                       PURPLE)
    # map panel
    canvas.fill_rect(745, 716, 935, 838, MAP_BG)
    canvas.rect_border(745, 716, 935, 838, NAVY, 2)
    island = [(780, 800), (800, 760), (850, 745), (895, 760),
              (910, 795), (880, 825), (830, 830), (795, 822)]
    canvas.filled_polygon(island, TAN)
    canvas.polygon_outline(island, GOLD_DARK)
    draw_text(canvas, "PORT AURELINE", 760, 724, 1, NAVY, bold=True)
    canvas.star(845, 790, 7, RED)
    draw_text(canvas, "KELD", 752, 780, 1, NAVY)
    draw_text(canvas, "SORA", 905, 780, 1, NAVY)
    draw_text(canvas, "N", 915, 724, 1, NAVY, bold=True)
    canvas.line(918, 736, 918, 748, NAVY)
    canvas.filled_polygon([(918, 734), (913, 744), (923, 744)], NAVY)


def build_spread():
    canvas = Canvas(W, H, DARK_NAVY)
    # spine strip between the two pages
    canvas.fill_rect(508, 126, 516, 890, (20, 26, 38))
    canvas.vline(508, 126, 890, GOLD)
    canvas.vline(515, 126, 890, GOLD)
    draw_left_page(canvas)
    draw_right_page(canvas)
    draw_text_centered(canvas,
                       "THE REPUBLIC OF CALDORIA - PASSPORT OF "
                       "JULIAN AUREL MARLOWE", 512, 922, 2, LIGHT_GREY)
    draw_text_centered(canvas, "ISSUED 02 JUN 2026 - PORT AURELINE",
                       512, 946, 1, LIGHT_GREY)
    return canvas


def main():
    canvas = build_spread()
    data = encode_png(canvas)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "out"
    out_path = os.path.join(out_dir, "entry.png")
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)
    print("Wrote %s (%d bytes)" % (out_path, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
