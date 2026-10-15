#!/usr/bin/env python3
"""Generate the app's 8-bit style sound effects (made here from scratch; nothing is copied from Coucou).

SoundEngine loads Bundle.main/sounds/<name>.wav for each name in
SoundEngine.soundNames, so one file per name is written to Resources/sounds/.

Sounds are built from square (50 / 25 / 12.5 % duty) and triangle waves only
(the triangle is quantised to 16 steps, like an old console's triangle channel),
each with a short attack/release so nothing clicks. Every name has its own
pitch / shape / rhythm. 44.1 kHz, 16-bit, mono, 0.05 - 0.4 s, peak -12 dBFS.

Usage
  make_sounds.py [--out DIR] [--peak-db -12] [--swift Sources/App/SoundEngine.swift]
                             [--only-missing]

--only-missing writes just the names that have no .wav yet, so hand-made replacements survive.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
MIN_SEC, MAX_SEC = 0.05, 0.40

_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(name: str) -> float:
    """'A4' -> 440.0, 'C#5', 'Bb3' ..."""
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", name)
    if not m:
        raise ValueError(f"bad note name {name!r}")
    semi = _SEMI[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    midi = 12 * (int(m.group(3)) + 1) + semi
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


class Note:
    """One tone. f1 != f0 makes a (geometric) pitch slide. decay = exp. time constant (s)."""

    def __init__(self, f0, dur, wave="sq50", f1=None, decay=None, vib=None):
        self.f0 = hz(f0)
        self.f1 = hz(f1) if f1 else self.f0
        self.dur, self.wave, self.decay, self.vib = dur, wave, decay, vib


def N(f0, dur, wave="sq50", **kw):
    return Note(f0, dur, wave, **kw)


def SLIDE(f0, f1, dur, wave="sq50", **kw):
    return Note(f0, dur, wave, f1=f1, **kw)


class Rest:
    def __init__(self, dur):
        self.dur = dur


_DUTY = {"sq50": 0.5, "sq25": 0.25, "sq12": 0.125}
_WAVE_GAIN = {"sq50": 0.55, "sq25": 0.6, "sq12": 0.7, "tri": 1.0}  # rough loudness balance inside one file


def _osc(wave_kind: str, phase: np.ndarray) -> np.ndarray:
    cyc = phase % 1.0
    if wave_kind == "tri":
        tri = 4.0 * np.abs(cyc - 0.5) - 1.0                      # -1 .. 1
        return np.round((tri + 1.0) * 7.5) / 7.5 - 1.0            # 16 steps (4-bit)
    duty = _DUTY[wave_kind]
    sq = np.where(cyc < duty, 1.0, -1.0)
    return sq - (2.0 * duty - 1.0)                                # zero mean over one cycle


def render_note(n: Note) -> np.ndarray:
    count = max(int(round(n.dur * SR)), 1)
    t = np.arange(count) / SR
    f = n.f0 * (n.f1 / n.f0) ** (t / n.dur)
    if n.vib:
        rate, depth = n.vib
        f = f * (1.0 + depth * np.sin(2 * np.pi * rate * t))
    phase = np.cumsum(f) / SR
    x = _osc(n.wave, phase) * _WAVE_GAIN[n.wave]
    env = np.ones(count)
    if n.decay:
        env = np.exp(-t / n.decay)
    a = min(int(0.002 * SR), count // 2)      # 2 ms attack
    r = min(int(0.008 * SR), count // 2)      # 8 ms release
    if a:
        env[:a] *= np.linspace(0.0, 1.0, a, endpoint=False)
    if r:
        env[-r:] *= np.linspace(1.0, 0.0, r)
    return x * env


def render(seq) -> np.ndarray:
    parts = []
    for item in seq:
        if isinstance(item, Rest):
            parts.append(np.zeros(int(round(item.dur * SR))))
        else:
            parts.append(render_note(item))
    return np.concatenate(parts)


# --- the sounds ----------------------------------------------------------------
# name -> note list. The comment says when SoundEngine plays it.
SOUNDS: dict[str, list] = {
    # island peeks out / creature peeks: quick rising chirp
    "peek":     [SLIDE("E5", "A5", 0.09, "sq25")],
    # island expands: up two-note
    "open":     [N("C5", 0.07, "tri"), N("G5", 0.13, "tri", decay=0.08)],
    # island collapses: down two-note
    "close":    [N("G5", 0.07, "tri"), N("C5", 0.13, "tri", decay=0.08)],
    # pointer enters the island: tiny high tap
    "hover":    [N("E6", 0.05, "tri", decay=0.02)],
    # generic UI blip
    "blip":     [N("A5", 0.07, "sq50", decay=0.04)],
    # poked / slapped: pitch-dropping thwack
    "slap":     [SLIDE("D4", "A2", 0.12, "sq50", decay=0.05)],
    # annoyed: low buzzy grumble
    "annoyed":  [N("A3", 0.12, "sq12"), N("F#3", 0.20, "sq12", vib=(30, 0.03))],
    # dizzy: wobbling tone
    "dizzy":    [N("A4", 0.36, "tri", vib=(9, 0.07))],
    # greeting hop: cheerful 3 notes
    "greet":    [N("C5", 0.07, "sq25"), N("E5", 0.07, "sq25"), N("G5", 0.12, "sq25", decay=0.07)],
    # agent started working: little typing pattern
    "work":     [N("G4", 0.06, "tri"), N("B4", 0.06, "tri"), N("G4", 0.06, "tri")],
    # agent finished: rising arpeggio
    "finish":   [N("C5", 0.08, "sq25"), N("E5", 0.08, "sq25"), N("G5", 0.08, "sq25"),
                 N("C6", 0.14, "sq25", decay=0.09)],
    # error: down, low
    "error":    [N("C4", 0.12, "sq50"), N("G3", 0.22, "sq50", decay=0.15)],
    # approval needed: attention two-note
    "approval": [N("E5", 0.10, "sq25"), N("A5", 0.20, "sq25", decay=0.12)],
    # question: rising "huh?"
    "question": [SLIDE("A4", "A5", 0.25, "tri")],
    # approved: bright confirm
    "approve":  [N("G5", 0.06, "sq25"), N("C6", 0.14, "sq25", decay=0.08)],
    # gulp: two falling glugs
    "gulp":     [SLIDE("G4", "D3", 0.12, "tri"), Rest(0.03), SLIDE("E4", "C3", 0.10, "tri")],
    # tick: very short dry click-tone
    "tick":     [N("C6", 0.05, "sq12", decay=0.02)],
    # send: whoosh up + blip
    "send":     [SLIDE("G4", "G6", 0.15, "sq25"), N("C7", 0.05, "sq25", decay=0.03)],
    # love (petting): soft rising major triad
    "love":     [N("A5", 0.09, "tri"), N("C#6", 0.09, "tri"), N("E6", 0.18, "tri", decay=0.12)],
    # pop: bubble pop, falling
    "pop":      [SLIDE("A6", "A4", 0.08, "sq50", decay=0.04)],
    # proud: tiny fanfare
    "proud":    [N("C5", 0.07, "sq25"), N("C5", 0.07, "sq25"), N("G5", 0.07, "sq25"),
                 N("C6", 0.18, "sq25", decay=0.11)],
    # wink: two quick chirps
    "wink":     [N("F6", 0.05, "tri"), Rest(0.02), N("A6", 0.07, "tri", decay=0.04)],
    # yawn: long slow fall
    "yawn":     [SLIDE("C5", "G3", 0.39, "tri", vib=(5, 0.02))],
    # attach: clip-on
    "attach":   [N("E5", 0.04, "sq50"), Rest(0.02), N("B5", 0.07, "sq50", decay=0.04)],
    # think: wondering three notes
    "think":    [N("D5", 0.08, "tri"), N("F5", 0.08, "tri"), N("E5", 0.12, "tri", decay=0.08)],
    # search: scan up and back
    "search":   [SLIDE("C5", "G5", 0.14, "tri"), SLIDE("G5", "C5", 0.14, "tri")],
    # rate: star ting
    "rate":     [N("E6", 0.05, "sq25", decay=0.03), N("A6", 0.20, "sq25", decay=0.10)],
    # sleep: slow lullaby fall
    "sleep":    [SLIDE("E4", "C4", 0.20, "tri"), SLIDE("C4", "G3", 0.18, "tri")],
    # greeting animation start: longer arpeggio
    "greeting": [N("C5", 0.05, "sq25"), N("E5", 0.05, "sq25"), N("G5", 0.05, "sq25"),
                 N("E5", 0.05, "sq25"), N("G5", 0.05, "sq25"), N("C6", 0.13, "sq25", decay=0.08)],
}


def write_wav(path: Path, x: np.ndarray, peak_db: float) -> tuple[float, float, float]:
    peak = float(np.max(np.abs(x)))
    if peak <= 0:
        raise ValueError(f"{path.name}: silent")
    target = 10.0 ** (peak_db / 20.0) * 32768.0
    pcm = np.round(x / peak * target).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    f = pcm.astype(np.float64) / 32768.0
    peak_out = 20 * math.log10(np.max(np.abs(f)))
    rms_out = 20 * math.log10(math.sqrt(np.mean(f ** 2)))
    return len(pcm) / SR, peak_out, rms_out


def verify(path: Path, peak_db: float) -> None:
    with wave.open(str(path), "rb") as w:
        assert w.getnchannels() == 1, f"{path.name}: not mono"
        assert w.getsampwidth() == 2, f"{path.name}: not 16-bit"
        assert w.getframerate() == SR, f"{path.name}: not {SR} Hz"
        sec = w.getnframes() / SR
        assert MIN_SEC <= sec <= MAX_SEC, f"{path.name}: {sec:.3f}s outside {MIN_SEC}-{MAX_SEC}s"
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
    pk = 20 * math.log10(np.max(np.abs(pcm)))
    assert abs(pk - peak_db) < 0.05, f"{path.name}: peak {pk:.2f} dBFS, wanted {peak_db}"


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=here.parent / "Resources" / "sounds")
    ap.add_argument("--peak-db", type=float, default=-12.0)
    ap.add_argument("--only-missing", action="store_true", help="skip names whose .wav already exists")
    ap.add_argument("--swift", type=Path, default=here.parent / "Sources" / "App" / "SoundEngine.swift",
                    help="SoundEngine.swift, to check the list of names (skipped if missing)")
    args = ap.parse_args()

    if args.swift.is_file():
        text = args.swift.read_text(encoding="utf-8")
        m = re.search(r"static let soundNames\s*=\s*\[(.*?)\]", text, re.S)
        if m:
            wanted = re.findall(r'"([^"]+)"', m.group(1))
            missing = [n for n in wanted if n not in SOUNDS]
            extra = [n for n in SOUNDS if n not in wanted]
            if missing:
                print(f"make_sounds: error: SoundEngine wants sounds not defined here: {missing}", file=sys.stderr)
                sys.exit(1)
            if extra:
                print(f"make_sounds: note: sounds nobody asks for: {extra}", file=sys.stderr)

    args.out.mkdir(parents=True, exist_ok=True)
    rendered = {}
    for name, seq in SOUNDS.items():
        if args.only_missing and (args.out / f"{name}.wav").is_file():
            continue
        x = render(seq)
        if not (MIN_SEC <= len(x) / SR <= MAX_SEC):
            print(f"make_sounds: error: {name} is {len(x) / SR:.3f}s", file=sys.stderr)
            sys.exit(1)
        rendered[name] = x
    # Every name must really differ from every other (not just in the file name).
    names = list(rendered)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            xa, xb = rendered[a], rendered[b]
            if len(xa) == len(xb) and np.allclose(xa, xb):
                print(f"make_sounds: error: {a} and {b} are identical", file=sys.stderr)
                sys.exit(1)

    if not rendered:
        print(f"make_sounds: all {len(SOUNDS)} files already exist in {args.out}")
        return
    print(f"{'name':<10} {'sec':>6} {'peak':>8} {'rms':>8}")
    for name, x in rendered.items():
        path = args.out / f"{name}.wav"
        sec, pk, rms = write_wav(path, x, args.peak_db)
        verify(path, args.peak_db)
        print(f"{name:<10} {sec:6.3f} {pk:7.2f}  {rms:7.2f}")
    print(f"make_sounds: {len(rendered)} files -> {args.out}")


if __name__ == "__main__":
    main()
