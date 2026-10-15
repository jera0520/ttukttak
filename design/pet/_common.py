"""복슬깨비 그림이 쓰는 눈·입·소품. 좌표는 20×20칸 기준.

그림은 MIT가 아니다: LICENSE-ASSETS. The character art here is not MIT-licensed: see LICENSE-ASSETS.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from pixelkit import Sprite, hexrgb, outline, paint  # noqa: E402,F401

INK = "#3B2219"     # 테두리: 검정보다 부드러운 진갈색
EYE = "#1E1412"
WHITE = "#FFFFFF"
BLUSH = "#F7898B"
SPARK = "#FFD66B"
HEART = "#FF6F91"
SWEAT = "#8FD3FF"
ZZZ = "#C9DDFF"
MARK = "#FFC46B"
MOUTH = "#5A1E1A"
TONGUE = "#F27A7A"
KEY_DARK = "#2E2D33"
KEY_LIGHT = "#8C8A94"

STATES = ["idle", "thinking", "working", "approval", "question",
          "finished", "error", "sleeping", "petted", "waiting_long"]


def dot(s, pts, color, dx=0, dy=0):
    c = hexrgb(color)
    for x, y in pts:
        s.set(x + dx, y + dy, c)


# 눈: 왼쪽 위 기준 (x, y, 색). 기본 2칸 너비·3칸 높이
EYE_SHAPES = {
    "open":    [(0, 0, WHITE), (1, 0, EYE), (0, 1, EYE), (1, 1, EYE), (0, 2, EYE), (1, 2, EYE)],
    "sparkle": [(0, 0, WHITE), (1, 0, EYE), (0, 1, EYE), (1, 1, EYE), (0, 2, EYE), (1, 2, WHITE)],
    "up":      [(0, 0, EYE), (1, 0, WHITE), (0, 1, EYE), (1, 1, EYE)],
    "side":    [(0, 0, EYE), (1, 0, WHITE), (0, 1, EYE), (1, 1, EYE), (0, 2, EYE), (1, 2, EYE)],
    "blink":   [(0, 2, EYE), (1, 2, EYE)],
    "happy":   [(-1, 2, EYE), (0, 1, EYE), (1, 1, EYE), (2, 2, EYE)],          # ∩ 웃는 눈
    "closed":  [(-1, 1, EYE), (0, 2, EYE), (1, 2, EYE), (2, 1, EYE)],          # ∪ 자는 눈
    "x":       [(-1, 0, EYE), (2, 0, EYE), (0, 1, EYE), (1, 1, EYE), (-1, 2, EYE), (2, 2, EYE)],
    "teary":   [(0, 0, WHITE), (1, 0, EYE), (0, 1, EYE), (1, 1, EYE), (0, 2, EYE), (1, 2, WHITE), (1, 3, SWEAT)],
    "down":    [(0, 1, EYE), (1, 1, EYE), (0, 2, EYE), (1, 2, EYE)],          # 아래(키보드) 보기
}


def eyes(s, kind, lx, rx, y):
    for ex in (lx, rx):
        for ox, oy, c in EYE_SHAPES[kind]:
            s.set(ex + ox, y + oy, hexrgb(c))


def mouth(s, kind, x, y):
    """x, y = 입 가운데 두 칸 중 왼쪽 칸."""
    if kind == "smile":     # ◡
        dot(s, [(x - 1, y), (x, y + 1), (x + 1, y + 1), (x + 2, y)], MOUTH)
    elif kind == "flat":
        dot(s, [(x, y), (x + 1, y)], MOUTH)
    elif kind == "open":    # 크게 웃는 입
        dot(s, [(x - 1, y), (x, y), (x + 1, y), (x + 2, y), (x, y + 1), (x + 1, y + 1)], MOUTH)
        dot(s, [(x, y + 1), (x + 1, y + 1)], TONGUE)
    elif kind == "o":
        dot(s, [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)], MOUTH)
    elif kind == "wavy":    # 당황
        dot(s, [(x - 1, y + 1), (x, y), (x + 1, y + 1), (x + 2, y)], MOUTH)
    elif kind == "cat":     # ω
        dot(s, [(x - 1, y), (x, y + 1), (x + 1, y + 1), (x + 2, y)], MOUTH)
        dot(s, [(x, y - 1), (x + 1, y - 1)], "#E57C7C")


def blush(s, lx, rx, y):
    dot(s, [(lx, y), (rx, y)], BLUSH)


# ---------------------------------------------------------------- 소품 (테두리 바깥에 얹는다)
def heart(s, x, y, color=HEART):
    dot(s, [(0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (1, 2)], color, x, y)


def spark(s, x, y, color=SPARK, big=True):
    pts = [(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)] if big else [(0, 0)]
    dot(s, pts, color, x, y)


def exclaim(s, x, y, color=MARK):
    dot(s, [(0, 0), (0, 1), (0, 2), (0, 4)], color, x, y)


def question(s, x, y, color=MARK):
    dot(s, [(0, 0), (1, 0), (2, 1), (1, 2), (1, 4)], color, x, y)


def zzz(s, x, y, small=False, color=ZZZ):
    """4×4 'Z' 글자, small이면 2×2 거품(3×3 z는 I처럼 보인다)."""
    pts = ([(0, 0), (1, 0), (0, 1), (1, 1)] if small
           else [(0, 0), (1, 0), (2, 0), (3, 0), (2, 1), (1, 2), (0, 3), (1, 3), (2, 3), (3, 3)])
    dot(s, pts, color, x, y)


def sweat(s, x, y):
    dot(s, [(1, 0), (0, 1), (1, 1)], SWEAT, x, y)


def keyboard(s, x, y, w=10, tap=0):
    """작은 키보드(w칸). tap=0/1 이면 왼손/오른손이 누른 자리를 밝게."""
    dot(s, [(i, 0) for i in range(w)], KEY_DARK, x, y)
    dot(s, [(i, 1) for i in range(w)], KEY_DARK, x, y)
    dot(s, [(i, 0) for i in range(1, w - 1, 2)], KEY_LIGHT, x, y)
    hot = 2 if tap == 0 else w - 3
    dot(s, [(hot, 0)], "#FFE2A8", x, y)


def finish(body: Sprite) -> Sprite:
    return outline(body, INK)
