#!/usr/bin/env python3
"""Draw the app icon and the menu bar glyph from the pet's own pixels (Sources/TtukttakKit/PetSpriteData.swift).

  Resources/AppIcon.icns         Bokseul-kkaebi's first "idle" frame, whole pixels, on a dark rounded square
                                 (the notch is black: the pet sits on the dark like it does there)
  Resources/MenuBarIcon.png      24x18 px  \\ black + transparent template image: the pet's silhouette
  Resources/MenuBarIcon@2x.png   48x36 px  /  with its eyes and mouth cut out, centred on a 24x18 pt canvas

Why 24x18 and not 18x18: AppDelegate does NSImage(named: "MenuBarIcon") and then forces
size = 24 x 18 pt with isTemplate = true, so a square image would be stretched.

Every size is drawn on its own with a whole number of pixels per cell (nearest neighbour, no blur);
only the 16 px icon, too small for one pixel per cell, is a smooth reduction of the 32 px one.

Usage: make_icons.py [--sprite Sources/TtukttakKit/PetSpriteData.swift] [--out-dir Resources]
                     [--only-missing] [--preview DIR] [--docs docs]   (needs Pillow; the .icns needs macOS's iconutil)
--only-missing writes just the files that do not exist yet, so hand-made replacements survive.
--preview also saves the 1024 px icon and the glyphs as PNG files to look at.
--docs also draws the README pictures: one looping GIF per state (pet-<state>.gif) and icon.png.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

SS = 4                      # supersampling for the rounded square's smooth edge
BG_TOP = (0x2B, 0x20, 0x1C)  # warm near-black, a little lighter at the top
BG_BOTTOM = (0x14, 0x0E, 0x0C)
CUT_OUT = {"8", "9", "b"}   # eyes (highlight, pupil) and mouth: holes in the menu bar glyph


# --- the pet's pixels ------------------------------------------------------------

def load_clips(path: Path) -> tuple[dict[str, list[tuple[int, list[str]]]], dict[str, tuple[int, int, int, int]]]:
    """Every clip as {state: [(ms, rows of palette letters)]}, and the letter -> RGBA table."""
    src = path.read_text(encoding="utf-8")
    alphabet = re.search(r'static let alphabet = "([^"]+)"', src).group(1)
    block = re.search(r"static let palette: \[UInt32\] = \[(.*?)\]", src, re.S).group(1)
    colours = [int(h, 16) for h in re.findall(r"0x([0-9A-Fa-f]{8})", block)]
    palette = {alphabet[i]: ((c >> 24) & 255, (c >> 16) & 255, (c >> 8) & 255, c & 255)
               for i, c in enumerate(colours)}
    clips: dict[str, list[tuple[int, list[str]]]] = {}
    for part in re.split(r'PetSpriteClipData\(name: ', src)[1:]:
        name = re.match(r'"([^"]+)"', part).group(1)
        clips[name] = [(int(ms), [r.strip() for r in cells.splitlines() if r.strip()])
                       for ms, cells in re.findall(r'PetSpriteFrameData\(ms: (\d+), cells: """\n(.*?)"""', part, re.S)]
    if not clips.get("idle"):
        sys.exit(f"make_icons: no idle frame in {path}")
    return clips, palette


def load_sprite(path: Path) -> tuple[list[str], dict[str, tuple[int, int, int, int]]]:
    """First frame of the "idle" clip as rows of palette letters, and the letter -> RGBA table."""
    clips, palette = load_clips(path)
    return clips["idle"][0][1], palette


def sprite_image(rows: list[str], palette: dict) -> Image.Image:
    """One pixel per cell, cropped to the drawn cells."""
    img = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                img.putpixel((x, y), palette[ch])
    return img.crop(img.getbbox())


def silhouette(rows: list[str]) -> Image.Image:
    """Black where the pet is, transparent elsewhere and in the eyes and mouth; cropped like sprite_image."""
    img = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != "." and ch not in CUT_OUT:
                img.putpixel((x, y), (0, 0, 0, 255))
    bbox = Image.new("L", img.size)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                bbox.putpixel((x, y), 255)
    return img.crop(bbox.getbbox())


# --- app icon ----------------------------------------------------------------------

def background(px: int) -> Image.Image:
    """macOS icon grid: body 824/1024 of the canvas, 100/1024 margin, corner radius ~22.4 % of the body."""
    big = px * SS
    margin, body = round(big * 100 / 1024), round(big * 824 / 1024)
    grad = Image.new("RGBA", (big, big))
    d = ImageDraw.Draw(grad)
    for y in range(big):
        t = min(max((y - margin) / max(body - 1, 1), 0), 1)
        d.line([(0, y), (big, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)) + (255,))
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle([margin, margin, margin + body - 1, margin + body - 1],
                                           radius=round(body * 0.224), fill=255)
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    return img.resize((px, px), Image.LANCZOS)


def app_icon(px: int, pet: Image.Image) -> Image.Image:
    """The pet at a whole number of pixels per cell: 32 per cell at 1024 px (about 74 % of the body wide)."""
    cell = px * 32 // 1024
    if cell < 1:                       # 16 px: smooth reduction of the 32 px icon
        return app_icon(32, pet).resize((px, px), Image.LANCZOS)
    img = background(px)
    big = pet.resize((pet.width * cell, pet.height * cell), Image.NEAREST)
    x = (px - big.width) // 2
    y = (px - big.height) // 2 + cell // 2   # half a cell low: the horns weigh less than the body
    img.alpha_composite(big, (x, y))
    return img


def write_icns(pet: Image.Image, out: Path) -> None:
    sizes = [(16, 1), (16, 2), (32, 1), (32, 2), (128, 1), (128, 2), (256, 1), (256, 2), (512, 1), (512, 2)]
    if shutil.which("iconutil") is None:
        sys.exit("make_icons: iconutil not found (needs macOS)")
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "AppIcon.iconset"
        iconset.mkdir()
        for base, scale in sizes:
            name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
            app_icon(base * scale, pet).save(iconset / name)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True)


# --- menu bar glyph ------------------------------------------------------------------

def menubar(scale: int, glyph: Image.Image) -> Image.Image:
    """scale 1 -> 24x18 px, scale 2 -> 48x36 px: the silhouette at `scale` pixels per cell, centred."""
    w, h = 24 * scale, 18 * scale
    big = glyph.resize((glyph.width * scale, glyph.height * scale), Image.NEAREST)
    if big.width > w or big.height > h:
        sys.exit(f"make_icons: the pet ({glyph.width}x{glyph.height} cells) does not fit the 24x18 menu bar glyph")
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.alpha_composite(big, ((w - big.width) // 2, (h - big.height) // 2))
    return img


# --- README pictures -------------------------------------------------------------------

DOC_SCALE, DOC_PAD = 6, 12          # 20x20 cells -> 120x120 px, on a 144x144 px tile
DOC_BG = (0x0B, 0x0B, 0x0B)         # the notch's black


def doc_frame(rows: list[str], palette: dict) -> Image.Image:
    """One scene on the black tile, the whole 20x20 grid (not cropped, so the frames of a clip line up)."""
    size = len(rows[0]) * DOC_SCALE + 2 * DOC_PAD
    img = Image.new("RGB", (size, size), DOC_BG)
    d = ImageDraw.Draw(img)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                x0, y0 = DOC_PAD + x * DOC_SCALE, DOC_PAD + y * DOC_SCALE
                d.rectangle([x0, y0, x0 + DOC_SCALE - 1, y0 + DOC_SCALE - 1], fill=palette[ch][:3])
    return img


def readme_pictures(clips: dict, palette: dict, pet: Image.Image, out: Path) -> list[str]:
    """out/pet-<state>.gif for every state (its own frame times, looping) and out/icon.png (256 px)."""
    out.mkdir(parents=True, exist_ok=True)
    colours = [DOC_BG] + sorted({c[:3] for c in palette.values() if c[3] == 255})
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette([v for c in colours for v in c] + [0, 0, 0] * (256 - len(colours)))
    written = []
    for state, frames in clips.items():
        pics = [doc_frame(rows, palette).quantize(palette=pal_img, dither=Image.Dither.NONE) for _, rows in frames]
        pics[0].save(out / f"pet-{state}.gif", save_all=True, append_images=pics[1:],
                     duration=[ms for ms, _ in frames], loop=0, disposal=1, optimize=False)
        written.append(f"pet-{state}.gif")
    app_icon(256, pet).save(out / "icon.png")
    written.append("icon.png")
    return written


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sprite", type=Path, default=here.parent / "Sources/TtukttakKit/PetSpriteData.swift")
    ap.add_argument("--out-dir", type=Path, default=here.parent / "Resources")
    ap.add_argument("--only-missing", action="store_true", help="skip files that already exist")
    ap.add_argument("--preview", type=Path, help="also save the 1024 px icon and the glyphs as PNG here")
    ap.add_argument("--docs", type=Path, help="also draw the README pictures (pet-<state>.gif, icon.png) here")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    clips, palette = load_clips(args.sprite)
    rows = clips["idle"][0][1]
    pet, glyph = sprite_image(rows, palette), silhouette(rows)

    def wanted(name: str) -> bool:
        return not (args.only_missing and (args.out_dir / name).is_file())

    done = []
    if wanted("AppIcon.icns"):
        write_icns(pet, args.out_dir / "AppIcon.icns")
        done.append("AppIcon.icns")
    if wanted("MenuBarIcon.png"):
        menubar(1, glyph).save(args.out_dir / "MenuBarIcon.png", dpi=(72, 72))
        done.append("MenuBarIcon.png (24x18)")
    if wanted("MenuBarIcon@2x.png"):
        menubar(2, glyph).save(args.out_dir / "MenuBarIcon@2x.png", dpi=(144, 144))
        done.append("MenuBarIcon@2x.png (48x36)")
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        app_icon(1024, pet).save(args.preview / "AppIcon-1024.png")
        app_icon(64, pet).save(args.preview / "AppIcon-64.png")
        app_icon(32, pet).save(args.preview / "AppIcon-32.png")
        menubar(2, glyph).save(args.preview / "MenuBarIcon@2x.png")
        done.append(f"previews -> {args.preview}")
    if args.docs:
        pics = readme_pictures(clips, palette, pet, args.docs)
        done.append(f"{len(pics)} README pictures -> {args.docs}")
    print(f"make_icons: {', '.join(done) if done else 'nothing to do (all exist)'} -> {args.out_dir}")


if __name__ == "__main__":
    main()
