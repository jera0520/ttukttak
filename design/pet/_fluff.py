"""털뭉치 몸의 공통 부분: 밝은 귤색 털, 붉은 갈색 테두리, 복슬한 털 끝.

몸은 20×20칸 글자 격자로 적고(build가 테두리를 두른다), 눈·입·소품은 테두리를 두른 뒤 얹는다.

그림은 MIT가 아니다: LICENSE-ASSETS. The character art here is not MIT-licensed: see LICENSE-ASSETS.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (EYE, EYE_SHAPES, MOUTH, TONGUE, WHITE, Sprite, blush, dot, eyes,  # noqa: E402,F401
                     exclaim, heart, hexrgb, outline, paint, question, spark, sweat, zzz)

STATES = ["idle", "thinking", "working", "approval", "question",
          "finished", "error", "sleeping", "petted", "waiting_long"]

PAL = {
    "h": "#FFA552",  # 털
    "H": "#FFC98A",  # 털 밝은 곳
    "o": "#F28745",  # 아랫배 털
    "k": "#E06A3A",  # 털 뭉치 사이 결
    "c": "#FFE7CC",  # 크림(뿔·주둥이·발)
    "C": "#E8C9A0",  # 크림 그늘
    "y": "#F4D57A",  # 호랑이 가죽(바랜 노랑 — 털 주황과 구분되게 밝게)
    "t": "#D9AE58",  # 가죽 닳은 곳
    "K": "#3A2A1E",  # 호랑이 줄무늬
    "W": "#6E4A2E",  # 방망이 나무(진한 밤색이라 주황 털 위에서도 보임)
    "V": "#9A6A44",  # 방망이 밝은 곳
    "g": "#FFD34E",  # 금(방망이 징·방울)
    "G": "#C98A1E",  # 금 그늘
}
LINE = "#B8432C"      # 테두리: 검은 노치 위에서도 털 끝이 보이게 붉은 갈색
STAR = "#D77757"      # Claude Code 주황 — 생각 중 별(✻)
DOTS = "#ECE9E1"      # 기다림 점(…)
KEY_BODY, KEY_CAP, KEY_HOT = "#55525C", "#A9A6B2", "#FFE2A8"  # 검은 노치 위에서 보이게 밝힌 키보드
COIN, COIN_D = "#FFD34E", "#C98A1E"


# ---------------------------------------------------------------- 격자 도구
def grid(lines):
    rows = [l.ljust(20, ".")[:20] for l in lines]
    return rows + ["." * 20] * (20 - len(rows))


def put(rows, pts, ch):
    rows = [list(r) for r in rows]
    for x, y in pts:
        if 0 <= x < 20 and 0 <= y < 20:
            rows[y][x] = ch
    return ["".join(r) for r in rows]


def shift(rows, dy, top=0, bottom=19):
    """top~bottom 줄을 dy만큼 아래로(음수면 위로) 옮긴다. 비는 줄은 빈칸."""
    band = rows[top:bottom + 1]
    blank = "." * 20
    if dy > 0:
        band = [blank] * dy + band[:-dy]
    elif dy < 0:
        band = band[-dy:] + [blank] * (-dy)
    return rows[:top] + band + rows[bottom + 1:]


def hshift(rows, dx):
    if dx > 0:
        return [("." * dx + r)[:20] for r in rows]
    if dx < 0:
        return [(r[-dx:] + "." * (-dx)) for r in rows]
    return rows


def build(rows):
    s = Sprite()
    paint(s, rows, PAL)
    return outline(s, LINE)


# ---------------------------------------------------------------- 소품 (테두리 바깥에 얹는다)
def star(s, x, y, phase):
    """Claude Code 생각 중 표시(✻ ✶ ✳)를 3×3 점으로 돌린다."""
    shapes = [[(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)],
              [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
              [(1, 0), (0, 1), (2, 1), (1, 2), (1, 1), (0, 0), (2, 2)]]
    dot(s, shapes[phase % 3], STAR, x, y)


def wait_dots(s, x, y, n):
    """기다림 점 … 을 n개(0~3)까지 하나씩."""
    dot(s, [(x + 2 * i, y) for i in range(n)], DOTS)


def keyboard(s, x, y, w=12, tap=0):
    dot(s, [(i, 0) for i in range(w)] + [(i, 1) for i in range(w)], KEY_BODY, x, y)
    dot(s, [(i, 0) for i in range(1, w - 1, 2)], KEY_CAP, x, y)
    hot = 2 if tap == 0 else w - 3
    dot(s, [(hot, 0)], KEY_HOT, x, y)


def coin(s, x, y):
    dot(s, [(0, 0), (1, 0), (0, 1)], COIN, x, y)
    dot(s, [(1, 1)], COIN_D, x, y)


def confetti(s, pts):
    cols = ["#FFD34E", "#8FD3FF", "#FF8FB1", "#B6F09C"]
    for i, (x, y) in enumerate(pts):
        dot(s, [(x, y)], cols[i % len(cols)])


def mouth(s, kind, x, y):
    """x, y = 입 가운데 두 칸 중 왼쪽 칸."""
    if kind == "tongue":     # 살짝 벌린 입 + 혀 (기본)
        dot(s, [(x, y), (x + 1, y)], MOUTH)
        dot(s, [(x, y + 1), (x + 1, y + 1)], TONGUE)
    elif kind == "laugh":    # 크게 웃는 입
        dot(s, [(x - 1, y), (x, y), (x + 1, y), (x + 2, y)], MOUTH)
        dot(s, [(x, y + 1), (x + 1, y + 1)], TONGUE)
    elif kind == "small":
        dot(s, [(x, y), (x + 1, y)], MOUTH)
    elif kind == "o":
        dot(s, [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)], MOUTH)
    elif kind == "wavy":     # 당황
        dot(s, [(x - 1, y + 1), (x, y), (x + 1, y + 1), (x + 2, y)], MOUTH)
    elif kind == "flat":
        dot(s, [(x - 1, y), (x, y), (x + 1, y), (x + 2, y)], MOUTH)


def yeopjeon(s, x, y):
    """엽전: 4×4 금화에 가운데 네모 구멍."""
    dot(s, [(x + 1, y), (x + 2, y), (x, y + 1), (x + 3, y + 1), (x, y + 2), (x + 3, y + 2), (x + 1, y + 3), (x + 2, y + 3)], COIN)
    dot(s, [(x + 1, y + 1), (x + 2, y + 2)], "#E8A93A")
    dot(s, [(x + 2, y + 1), (x + 1, y + 2)], "#3B2219")
