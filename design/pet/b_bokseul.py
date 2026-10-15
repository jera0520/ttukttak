"""복슬깨비: 털뭉치 도깨비. 외뿔·덧니·호랑이 가죽, 방망이로 뚝딱.

그림은 MIT가 아니다: LICENSE-ASSETS. The character art here is not MIT-licensed: see LICENSE-ASSETS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fluff import (MOUTH, PAL, STATES, WHITE, blush, build, confetti, dot, eyes, exclaim, grid, heart,  # noqa: E402,F401
                    hshift, mouth, put, question, shift, spark, star, sweat, wait_dots, yeopjeon, zzz)

NAME = "복슬깨비"
CONCEPT = "털뭉치 도깨비 — 외뿔·덧니·호랑이 가죽, 일할 땐 방망이로 뚝딱, 끝나면 금 나와라 뚝딱"

BODY = grid([
    ".......c............",
    "......cC............",
    "......cC.h..h.......",   # 외뿔(왼쪽 위) + 머리털 두 가닥
    ".....hhhhhhhhhh.....",
    "....hhhhhhhhhhhh....",
    "...hhhhhhhhhhhhhh...",
    "...khhhhhhhhhhhhk...",
    "..hhhhhhhhhhhhhhhh..",
    "..hhhhhhhhhhhhhhhh..",
    "...khhhhhhhhhhhhk...",
    "..hhhhhhhhhhhhhhhh..",
    "...hhhhhhhhhhhhhh...",
    "...yKyyyKyyKyyyKy...",   # 호랑이 가죽 치마
    "...yyKyyKyyKyyKyy...",
    "....hh........hh....",
])
LIGHT = [(6, 4), (7, 4), (5, 5)]
# 방망이: (x, y, 글자). 나무 W·밝은 곳 V·금 징 g
CLUB = {
    "rest": [(18, 2, "W"), (19, 2, "W"), (18, 3, "c"), (19, 3, "W"), (18, 4, "W"), (19, 4, "c"), (18, 5, "c"), (19, 5, "W"),
             (18, 6, "W"), (19, 6, "W"), (18, 7, "W"), (18, 8, "W"), (18, 9, "W"), (18, 10, "W")],
    "up": [(16, 5, "W"), (17, 4, "W"), (17, 3, "W"), (18, 3, "c"), (17, 2, "c"), (18, 2, "W"), (19, 2, "W"),
           (18, 1, "W"), (19, 1, "c"), (18, 0, "c"), (19, 0, "W")],
    "down": [(17, 10, "W"), (17, 11, "W"), (16, 12, "W"), (17, 12, "c"), (18, 12, "W"), (19, 12, "c"),
             (16, 13, "c"), (17, 13, "W"), (18, 13, "c"), (19, 13, "W")],
    "ground": [(11, 15, "W"), (12, 15, "W"), (13, 15, "W"), (14, 15, "W"), (15, 15, "W"), (16, 15, "c"), (17, 15, "W"), (18, 15, "c"),
               (15, 16, "W"), (16, 16, "W"), (17, 16, "c"), (18, 16, "W")],
    "none": [],
}
ARM = {  # 방망이 쥔 오른손
    "rest": [(17, 9)], "up": [(16, 6)], "down": [(17, 9)], "ground": [], "none": [],
}
PUFF = [(4, 2), (14, 2), (11, 2), (1, 7), (18, 8), (1, 10), (18, 10)]
FRAZZLE = [(4, 2), (10, 1), (14, 2), (1, 6), (18, 7), (1, 10), (18, 11)]


def base(eye="open", mo="fang", club="rest", dy=0, dx=0, fur="", cheek=True):
    rows = put(BODY, LIGHT, "H")
    for x, y, ch in CLUB[club]:
        rows = put(rows, [(x, y)], ch)
    rows = put(rows, ARM[club], "h")
    if fur == "puff":
        rows = put(rows, PUFF, "h")
    elif fur == "frazzle":
        rows = put(rows, FRAZZLE, "h")
    if dy > 0:
        rows = shift(rows, dy, 0, 13)
    elif dy < 0:
        rows = shift(rows, dy)
    rows = hshift(rows, dx)
    s = build(rows)
    y = 7 + dy
    eyes(s, eye, 6 + dx, 11 + dx, y)
    my = 10 + dy
    if mo == "fang":       # 살짝 웃는 입 + 덧니 하나
        dot(s, [(8 + dx, my), (9 + dx, my), (10 + dx, my)], MOUTH)
        dot(s, [(8 + dx, my + 1)], WHITE)
    elif mo == "fang_laugh":
        dot(s, [(7 + dx, my), (8 + dx, my), (9 + dx, my), (10 + dx, my), (11 + dx, my)], MOUTH)
        dot(s, [(9 + dx, my + 1), (10 + dx, my + 1)], "#F27A7A")
        dot(s, [(8 + dx, my + 1)], WHITE)
    else:
        mouth(s, mo, 9 + dx, my)
    if cheek:
        blush(s, 4 + dx, 14 + dx, my)
        blush(s, 5 + dx, 15 + dx, my)
    return s


def frames(state):
    if state == "idle":
        return [(base(), 720), (base(dy=1), 600), (base(), 600), (base(eye="blink"), 120), (base(), 360)]
    if state == "thinking":
        out = []
        for i in range(3):
            s = base(eye="up", mo="small")
            star(s, 14, 0, i)
            out.append((s, 200))
        return out
    if state == "working":
        a = base(eye="open", mo="fang", club="up")
        b = base(eye="happy", mo="fang", club="down", dy=1)
        dot(b, [(15, 15), (19, 15), (16, 11)], "#FFE2A8")   # 뚝! 하고 튀는 먼지
        return [(a, 240), (b, 240)]
    if state == "approval":
        a = base(eye="sparkle", mo="fang_laugh", club="up", dy=-1, fur="puff")
        exclaim(a, 2, 0)
        b = base(eye="sparkle", mo="fang_laugh", club="rest")
        exclaim(b, 2, 0)
        return [(a, 240), (b, 240)]
    if state == "question":
        a = base(eye="side", mo="small")
        question(a, 1, 0)
        b = base(eye="side", mo="small", dx=-1)
        question(b, 0, 0)
        return [(a, 600), (b, 600)]
    if state == "finished":
        a = base(eye="happy", mo="fang_laugh", club="up")
        b = base(eye="happy", mo="fang_laugh", club="down", dy=1)
        yeopjeon(b, 13, 9)
        c = base(eye="happy", mo="fang_laugh", club="down", dy=1)
        yeopjeon(c, 14, 4)
        yeopjeon(c, 1, 8)
        d = base(eye="happy", mo="fang_laugh", club="down")
        yeopjeon(d, 15, 0)
        yeopjeon(d, 0, 3)
        spark(d, 10, 0)
        return [(a, 300), (b, 300), (c, 300), (d, 300)]
    if state == "error":
        out = []
        for dx in (-1, 1, -1, 1):
            s = base(eye="x", mo="wavy", club="ground", dx=dx, fur="frazzle")
            sweat(s, 15 + dx, 3)
            out.append((s, 120))
        s = base(eye="x", mo="wavy", club="ground", fur="frazzle")
        sweat(s, 15, 4)
        out.append((s, 720))
        return out
    if state == "sleeping":
        a = base(eye="closed", mo="small", club="ground", dy=1)
        zzz(a, 14, 1, small=True)
        b = base(eye="closed", mo="small", club="ground", dy=1)
        zzz(b, 14, 0)
        return [(a, 600), (b, 600)]
    if state == "petted":
        a = base(eye="happy", mo="fang", dy=1)
        heart(a, 13, 0)
        b = base(eye="happy", mo="fang")
        heart(b, 14, 0)
        return [(a, 300), (b, 300)]
    if state == "waiting_long":
        out = []
        for n in range(4):
            s = base(eye="down", mo="flat")
            wait_dots(s, 1, 1, n)
            out.append((s, 300))
        return out
    return [(base(), 600)]
