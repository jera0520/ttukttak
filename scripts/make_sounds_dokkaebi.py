#!/usr/bin/env python3
"""복슬깨비 alert sounds: a dokkaebi's club and Korean percussion, synthesised here from scratch.

Replaces the 8-bit alerts with wood and drum sounds that fit the character (a dokkaebi
with a magic club, "금 나와라 뚝딱"):
  approval   똑똑 — a knock on the door: may I?
  question   똑·딱? — two rising knocks and a curious bell
  finish     뚝딱! — club thump + crack, then coins sparkle out
  error      쿵… 뿌웅 — a drum drop and a goofy slide down
  approve    딱! — one crisp club crack and a bell
  rate       쿵 쿵 — two slow low drum beats (limit reached)
  open/close a small moktak tap, high / low
  greet(ing) 덩 기덕 쿵 더러러 — a short janggu phrase
  slap       a club bonk
  work       one soft moktak

Building blocks: modal wood (decaying partials of a wood block), janggu skin (pitch-dropping
sine + soft noise), stick crack (filtered noise burst), small bells (inharmonic partials).
44.1 kHz, 16-bit, mono, peak -12 dBFS (finish -10). The other sounds stay as make_sounds.py
draws them.

Usage: make_sounds_dokkaebi.py [--out Resources/sounds] [--only name,name]
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

SR = 44100
RNG = np.random.default_rng(7)   # fixed: the same files on every run


def silence(sec: float) -> np.ndarray:
    return np.zeros(int(SR * sec))


def t_axis(sec: float) -> np.ndarray:
    return np.arange(int(SR * sec)) / SR


def fade(x: np.ndarray, attack=0.002, release=0.01) -> np.ndarray:
    n = len(x)
    a, r = min(n, int(SR * attack)), min(n, int(SR * release))
    env = np.ones(n)
    if a:
        env[:a] = np.linspace(0, 1, a)
    if r:
        env[-r:] *= np.linspace(1, 0, r)
    return x * env


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    # one-pole, enough to soften noise
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    prev = 0.0
    for i, v in enumerate(x):
        prev = (1 - a) * v + a * prev
        y[i] = prev
    return y


def highpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    return x - lowpass(x, cutoff)


def wood(f: float, dur=0.12, tau=0.035, gain=1.0) -> np.ndarray:
    """Moktak / wood block: a few inharmonic partials that die fast, plus a tiny click."""
    t = t_axis(dur)
    partials = [(1.0, 1.0, tau), (2.57, 0.45, tau * 0.6), (4.4, 0.2, tau * 0.4)]
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in partials)
    click = highpass(RNG.standard_normal(len(t)), 2500) * np.exp(-t / 0.003) * 0.35
    return fade(gain * (x + click), attack=0.0005, release=0.02)


def drum(f0: float, f1: float, dur=0.35, tau=0.12, gain=1.0) -> np.ndarray:
    """Janggu bass skin (덩/쿵): a sine whose pitch drops, with a soft skin noise."""
    t = t_axis(dur)
    freq = f1 + (f0 - f1) * np.exp(-t / 0.04)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t / tau)
    skin = lowpass(lowpass(RNG.standard_normal(len(t)), 700), 700) * np.exp(-t / 0.025) * 0.6
    return fade(gain * (body + skin), attack=0.001, release=0.03)


def crack(dur=0.06, gain=1.0, ring=1800.0) -> np.ndarray:
    """Stick on the janggu's rim (딱): a bright noise burst with a short ring."""
    t = t_axis(dur)
    noise = highpass(RNG.standard_normal(len(t)), 1500) * np.exp(-t / 0.008)
    tone = np.sin(2 * np.pi * ring * t) * np.exp(-t / 0.015) * 0.6
    return fade(gain * (noise * 0.7 + tone), attack=0.0005, release=0.01)


def bell(f: float, dur=0.35, tau=0.12, gain=0.5) -> np.ndarray:
    """Small bell / coin: inharmonic partials with a longer ring."""
    t = t_axis(dur)
    partials = [(1.0, 1.0), (2.76, 0.4), (5.4, 0.15)]
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (tau / r ** 0.5)) for r, a in partials)
    return fade(gain * x, attack=0.001, release=0.05)


def slide(f0: float, f1: float, dur: float, gain=0.5, wobble=0.0) -> np.ndarray:
    """A soft triangle sliding from f0 to f1 (the goofy 뿌웅), optional wobble."""
    t = t_axis(dur)
    freq = f0 * (f1 / f0) ** (t / dur)
    if wobble:
        freq = freq * (1 + wobble * np.sin(2 * np.pi * 9 * t))
    phase = np.cumsum(freq) / SR
    tri = 2 * np.abs(2 * (phase % 1) - 1) - 1
    return fade(gain * tri * np.exp(-t / (dur * 0.7)), attack=0.01, release=0.06)


def mix(*parts: tuple[float, np.ndarray]) -> np.ndarray:
    """(start seconds, signal) pairs laid on one track."""
    end = max(int(SR * s) + len(x) for s, x in parts)
    out = np.zeros(end)
    for s, x in parts:
        i = int(SR * s)
        out[i:i + len(x)] += x
    return out


def note(name: str) -> float:
    semi = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    pitch, octave = name[:-1], int(name[-1])
    midi = 12 * (octave + 1) + semi[pitch[0]] + (1 if pitch.endswith("#") else 0)
    return 440.0 * 2 ** ((midi - 69) / 12)


SOUNDS = {
    "approval": lambda: mix((0.0, wood(720)), (0.13, wood(720)), (0.27, bell(note("E6"), gain=0.35))),
    "question": lambda: mix((0.0, wood(820)), (0.11, wood(1100)),
                            (0.22, slide(note("C6"), note("G6"), 0.16, gain=0.25))),
    "finish": lambda: mix((0.0, drum(170, 95, tau=0.14)), (0.10, crack(gain=0.9)),
                          (0.20, bell(note("C6"), gain=0.35)), (0.26, bell(note("E6"), gain=0.35)),
                          (0.32, bell(note("G6"), gain=0.35)), (0.38, bell(note("C7"), dur=0.45, gain=0.4))),
    "error": lambda: mix((0.0, drum(130, 60, dur=0.4, tau=0.16)),
                         (0.14, slide(330, 110, 0.36, gain=0.45, wobble=0.04))),
    "approve": lambda: mix((0.0, crack(gain=0.9)), (0.05, bell(note("G6"), dur=0.25, gain=0.3))),
    "rate": lambda: mix((0.0, drum(120, 70, tau=0.12)), (0.32, drum(110, 65, tau=0.12))),
    "open": lambda: wood(1150, dur=0.09, tau=0.022, gain=0.8),
    "close": lambda: wood(760, dur=0.09, tau=0.022, gain=0.8),
    "greet": lambda: mix((0.0, drum(180, 100, tau=0.12)), (0.16, crack(gain=0.7)),
                         (0.24, crack(gain=0.55)), (0.32, drum(150, 80, tau=0.1)),
                         (0.46, crack(gain=0.45)), (0.50, crack(gain=0.5)), (0.54, crack(gain=0.6))),
    "slap": lambda: mix((0.0, wood(420, tau=0.05)), (0.0, drum(200, 120, dur=0.15, tau=0.05, gain=0.6))),
    "work": lambda: wood(540, dur=0.18, tau=0.06, gain=0.7),
}
SOUNDS["greeting"] = SOUNDS["greet"]

LOUDER = {"finish": -10.0}


def write(path: Path, x: np.ndarray, peak_db: float) -> None:
    x = x / (np.max(np.abs(x)) or 1) * 10 ** (peak_db / 20)
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "Resources" / "sounds"))
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = [n for n in args.only.split(",") if n] or list(SOUNDS)
    for name in names:
        x = SOUNDS[name]()
        write(out / f"{name}.wav", x, LOUDER.get(name, -12.0))
        print(f"{name:9s} {len(x) / SR:.2f}s")


if __name__ == "__main__":
    main()
