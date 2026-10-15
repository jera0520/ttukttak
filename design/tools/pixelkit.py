"""도트 캐릭터 미리보기 도구.

캐릭터는 "색 글자" 격자로 적는다('.'은 빈칸). 테두리는 outline()이 자동으로 둘러 준다.
그림 파일(design/pet/b_bokseul.py)은 PAL(팔레트)과 frames(state) -> [(Sprite, ms)]를 정의한다.

    python3 -I design/tools/pixelkit.py design/pet/b_bokseul.py <출력폴더>
    → <이름>_sheet.png(상태별 시트), <이름>_notch.png(실제 노치 합성), <이름>_anim.gif(움직임)
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 미리보기 글자는 픽셀 글꼴 Galmuri11(OFL, github.com/quiple/galmuri)이 있으면 그걸로, 없으면 Pillow 기본 글꼴로.
# 글꼴 위치: 환경변수 PIXELKIT_FONT / PIXELKIT_FONT_BOLD (.ttf 경로)
GALMURI = Path(os.environ.get("PIXELKIT_FONT", "Galmuri11.ttf"))
GALMURI_B = Path(os.environ.get("PIXELKIT_FONT_BOLD", "Galmuri11-Bold.ttf"))
GRID = 20  # 노치 접힘 20pt = 1칸 1pt, 펼침 60pt = 1칸 3pt

# Claude Code 터미널 느낌 색
CC_ORANGE = (215, 119, 87)
CC_BG = (20, 20, 19)
CC_DIM = (125, 122, 115)
CC_TEXT = (236, 233, 225)


class Sprite:
    def __init__(self, w: int = GRID, h: int = GRID):
        self.w, self.h = w, h
        self.px: dict[tuple[int, int], tuple[int, int, int, int]] = {}

    def copy(self) -> "Sprite":
        s = Sprite(self.w, self.h)
        s.px = dict(self.px)
        return s

    def set(self, x: int, y: int, c):
        if 0 <= x < self.w and 0 <= y < self.h and c is not None:
            self.px[(x, y)] = c

    def get(self, x: int, y: int):
        return self.px.get((x, y))

    def shifted(self, dx: int, dy: int) -> "Sprite":
        s = Sprite(self.w, self.h)
        for (x, y), c in self.px.items():
            s.set(x + dx, y + dy, c)
        return s


def hexrgb(h: str):
    h = h.lstrip("#")
    a = 255 if len(h) == 6 else int(h[6:8], 16)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def paint(s: Sprite, rows: list[str], pal: dict[str, str], ox: int = 0, oy: int = 0, mirror: bool = False):
    """rows를 (ox, oy)에 칠한다. mirror=True면 왼쪽 절반만 적고 오른쪽은 거울로."""
    for r, line in enumerate(rows):
        full = line + line[::-1] if mirror else line
        for c, ch in enumerate(full):
            if ch in (".", " "):
                continue
            if ch == "_":  # 지우개
                s.px.pop((ox + c, oy + r), None)
                continue
            s.set(ox + c, oy + r, hexrgb(pal[ch]))
    return s


def outline(s: Sprite, color: str, diagonal: bool = False, skip: set | None = None) -> Sprite:
    """칠해진 칸 바깥에 한 칸 테두리를 두른다."""
    out = s.copy()
    col = hexrgb(color)
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diagonal:
        dirs += [(1, 1), (-1, 1), (1, -1), (-1, -1)]
    for (x, y), c in s.px.items():
        if skip and c in skip:
            continue
        for dx, dy in dirs:
            if (x + dx, y + dy) not in s.px:
                out.set(x + dx, y + dy, col)
    return out


def render(s: Sprite, scale: int, bg=None) -> Image.Image:
    im = Image.new("RGBA", (s.w * scale, s.h * scale), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for (x, y), c in s.px.items():
        d.rectangle([x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1], fill=c)
    return im


def font(size: int, bold: bool = False):
    p = GALMURI_B if bold else GALMURI
    if p.is_file():
        return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def spinner(scale: int, phase: int = 0) -> Image.Image:
    """Claude Code 스피너(✻) 느낌의 5×5 도트 별."""
    shapes = [
        ["..o..", "o.o.o", ".ooo.", "o.o.o", "..o.."],
        [".o.o.", "..o..", "ooooo", "..o..", ".o.o."],
        ["o...o", ".o.o.", "..o..", ".o.o.", "o...o"],
    ]
    s = Sprite(5, 5)
    paint(s, shapes[phase % 3], {"o": "#D77757"})
    return render(s, scale)


# ---------------------------------------------------------------- 시트·합성

STATE_LABELS = {
    "idle": "쉬는 중",
    "thinking": "생각 중",
    "working": "작업 중",
    "approval": "허락해 줘!",
    "question": "질문 있어",
    "finished": "끝났어",
    "error": "오류",
    "sleeping": "낮잠",
    "petted": "쓰다듬기",
    "waiting_long": "오래 기다림",
}


def load_candidate(path: str):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def sheet(mod, out: Path):
    states = [s for s in mod.STATES]
    scale = 6
    cell = GRID * scale
    pad = 28
    cols = 5
    rows = math.ceil(len(states) / cols)
    title_h = 120
    W = pad + cols * (cell + pad)
    H = title_h + rows * (cell + 56 + pad) + 190
    im = Image.new("RGB", (W, H), CC_BG)
    d = ImageDraw.Draw(im)
    d.text((pad, 24), mod.NAME, font=font(33, True), fill=CC_ORANGE)
    d.text((pad, 72), mod.CONCEPT, font=font(22), fill=CC_DIM)
    for i, st in enumerate(states):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = title_h + r * (cell + 56 + pad)
        d.rounded_rectangle([x - 6, y - 6, x + cell + 6, y + cell + 6], radius=10, outline=(48, 47, 44), width=2)
        spr = mod.frames(st)[0][0]
        im.paste(render(spr, scale), (x, y), render(spr, scale))
        d.text((x, y + cell + 14), STATE_LABELS.get(st, st), font=font(22), fill=CC_TEXT)
    # 실제 크기 미리보기 (레티나 2배: 접힘 20pt=40px, 펼침 60pt=120px)
    y0 = H - 170
    d.text((pad, y0), "실제 크기 (레티나)", font=font(22), fill=CC_DIM)
    idle = mod.frames("idle")[0][0]
    a = render(idle, 2)
    b = render(idle, 6)
    im.paste(a, (pad, y0 + 50), a)
    d.text((pad + 52, y0 + 60), "접힌 노치 20pt", font=font(22), fill=CC_DIM)
    im.paste(b, (pad + 260, y0 + 30), b)
    d.text((pad + 400, y0 + 80), "펼친 노치 60pt", font=font(22), fill=CC_DIM)
    im.save(out)


def _notch_bar(W: int, k: int, notch_w: int = 184):
    """메뉴 막대 + 노치. k = 레티나 배수."""
    im = Image.new("RGB", (W, 260 * k), (0, 0, 0))
    # 배경 화면 느낌: 은은한 세로 그라데이션
    d = ImageDraw.Draw(im)
    for y in range(260 * k):
        t = y / (260 * k)
        d.line([(0, y), (W, y)], fill=(int(58 + 40 * t), int(64 + 30 * t), int(92 + 20 * t)))
    d.rectangle([0, 0, W, 32 * k], fill=(38, 40, 52))
    return im, d


def notch_mock(mod, out: Path):
    k = 2
    W = 760 * k
    im, d = _notch_bar(W, k)
    cx = W // 2
    # --- 접힌 섬: 노치 + 양옆 귀 (캐릭터 20pt, 오른쪽에 스피너·진행)
    nw, nh = 184 * k, 32 * k
    ear = 64 * k
    left, right = cx - nw // 2 - ear, cx + nw // 2 + ear
    d.rounded_rectangle([left, -20 * k, right, nh], radius=12 * k, fill=(0, 0, 0))
    spr = mod.frames("working")[0][0]
    small = render(spr, 1 * k)  # 1칸 = 1pt
    im.paste(small, (left + 20 * k, (nh - small.height) // 2), small)
    sp = spinner(2 * k // 2 if k > 1 else 2, 0)
    im.paste(sp, (right - 58 * k, (nh - sp.height) // 2), sp)
    d.text((right - 46 * k, 9 * k), "3/7", font=font(11 * k), fill=CC_ORANGE)

    # --- 펼친 섬: 승인 카드 (캐릭터 60pt)
    top = 60 * k
    ew, eh = 640 * k, 160 * k
    ex = cx - ew // 2
    d.rounded_rectangle([ex, top, ex + ew, top + eh], radius=22 * k, fill=(0, 0, 0))
    d.text((ex + 22 * k, top + 12 * k), "Claude Code · ~/projects/my-app", font=font(11 * k), fill=CC_DIM)
    spr = mod.frames("approval")[0][0]
    big = render(spr, 3 * k)
    im.paste(big, (ex + 32 * k, top + 48 * k), big)
    tx = ex + 120 * k
    sp = spinner(2 * k, 1)
    im.paste(sp, (tx, top + 34 * k), sp)
    d.text((tx + 16 * k, top + 30 * k), "허락이 필요해요", font=font(14 * k, True), fill=CC_ORANGE)
    d.text((tx + 16 * k, top + 52 * k), "Bash  npm run build", font=font(12 * k), fill=CC_TEXT)
    d.text((tx + 16 * k, top + 70 * k), "읽기·쓰기 · 이 폴더 안에서만 · 인터넷 없음", font=font(11 * k), fill=CC_DIM)
    # Claude Code 허락 화면처럼 번호 목록 (버튼 대신)
    for i, (label, fg) in enumerate([("> 1. 허용", CC_ORANGE),
                                     ("  2. 항상 허용  규칙 추가: Bash(npm run *)", CC_TEXT),
                                     ("  3. 거부 (esc)", CC_DIM)]):
        d.text((tx, top + (94 + 18 * i) * k), label, font=font(12 * k, i == 0), fill=fg)
    d.text((ex + 22 * k, top + eh + 14 * k), f"{mod.NAME} · 실제 노치 크기 합성 (레티나 2배)", font=font(11 * k), fill=(200, 200, 210))
    im.save(out)


def anim(mod, out: Path, states=None, cols=None, scale=6, labels=True):
    states = states or [s for s in ["idle", "working", "approval", "finished", "sleeping", "petted"] if s in mod.STATES]
    cols = cols or len(states)
    rows = math.ceil(len(states) / cols)
    cell = GRID * scale
    pad = 18
    lab = 40 if labels else 0
    W = pad + cols * (cell + pad)
    H = pad + rows * (cell + pad + lab)
    seqs = [mod.frames(s) for s in states]
    # 공통 시간축 (60ms 간격으로 2.4초)
    tick, total = 60, 2400
    frames = []
    for t in range(0, total, tick):
        im = Image.new("RGB", (W, H), CC_BG)
        d = ImageDraw.Draw(im)
        for i, seq in enumerate(seqs):
            dur = sum(ms for _, ms in seq)
            tt = t % dur
            acc = 0
            spr = seq[0][0]
            for s_, ms in seq:
                if tt < acc + ms:
                    spr = s_
                    break
                acc += ms
            row, col = divmod(i, cols)
            x = pad + col * (cell + pad)
            y = pad + row * (cell + pad + lab)
            r = render(spr, scale)
            im.paste(r, (x, y), r)
            if labels:
                d.text((x, y + cell + 8), STATE_LABELS.get(states[i], states[i]), font=font(20), fill=CC_TEXT)
        frames.append(im.convert("P", palette=Image.ADAPTIVE, colors=128))
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=tick, loop=0, disposal=2)


if __name__ == "__main__":
    mod = load_candidate(sys.argv[1])
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    stem = Path(sys.argv[1]).stem
    sheet(mod, outdir / f"{stem}_sheet.png")
    notch_mock(mod, outdir / f"{stem}_notch.png")
    anim(mod, outdir / f"{stem}_anim.gif")
    print("ok", stem)
