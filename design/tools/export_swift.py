"""도트 캐릭터 그림(design/pet/b_bokseul.py)을 앱이 읽는 Swift 데이터 파일로 내보낸다.

    python3 -I design/tools/export_swift.py design/pet/b_bokseul.py Sources/TtukttakKit/PetSpriteData.swift

그림 파일의 STATES마다 frames(state) -> [(Sprite, ms)]를 받아, 20×20칸을 한 줄 20글자 × 20줄 글자 그림으로 적는다.
'.'은 빈칸, 나머지 글자는 팔레트 번호다(글자표 ALPHABET 순서). 소스에서 캐릭터 모양이 그대로 보인다.
털 색(h·H·o·k)과 테두리는 역할 번호를 따로 적어, 앱이 작은 캐릭터의 털 색만 바꿀 수 있게 한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixelkit import GRID, hexrgb, load_candidate  # noqa: E402

ALPHABET = ".123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
# 털 역할: 0 털, 1 밝은 털, 2 아랫배 털, 3 털 결, 4 테두리 (나머지는 -1)
FUR_KEYS = {"h": 0, "H": 1, "o": 2, "k": 3}


def main(src: str, out: str) -> None:
    mod = load_candidate(src)
    fluff = sys.modules.get("_fluff")
    pal = getattr(mod, "PAL", None) or getattr(fluff, "PAL", {})
    line = getattr(mod, "LINE", None) or getattr(fluff, "LINE", None)

    roles: dict[tuple, int] = {hexrgb(pal[k]): r for k, r in FUR_KEYS.items() if k in pal}
    if line:
        roles[hexrgb(line)] = 4

    palette: list[tuple] = [(0, 0, 0, 0)]
    clips: list[tuple[str, list[tuple[int, list[str]]]]] = []
    for state in mod.STATES:
        frames = []
        for sprite, ms in mod.frames(state):
            rows = []
            for y in range(GRID):
                row = ""
                for x in range(GRID):
                    c = sprite.get(x, y)
                    if c is None or c[3] == 0:
                        row += "."
                        continue
                    if c not in palette:
                        palette.append(c)
                    row += ALPHABET[palette.index(c)]
                rows.append(row)
            frames.append((int(ms), rows))
        clips.append((state, frames))
    if len(palette) > len(ALPHABET):
        raise SystemExit(f"색이 너무 많다: {len(palette)}")

    name = getattr(mod, "NAME", Path(src).stem)
    lines = [
        "// 자동 생성 파일이다. 손으로 고치지 말고 그림 코드를 고친 뒤 다시 만든다.",
        f"// 만든 곳: design/tools/export_swift.py ← design/pet/{Path(src).name} ({name})",
        "//   python3 -I design/tools/export_swift.py design/pet/b_bokseul.py Sources/TtukttakKit/PetSpriteData.swift",
        "// 장면 하나는 20×20칸: 한 줄 20글자 × 20줄. '.'은 빈칸, 다른 글자는 palette 번호(alphabet 순서).",
        "// 그림(캐릭터 복슬깨비)은 MIT가 아니다: LICENSE-ASSETS. The character art in this file is not MIT-licensed: see LICENSE-ASSETS.",
        "",
        "enum PetSpriteData {",
        f"    static let grid = {GRID}",
        f'    static let alphabet = "{ALPHABET}"',
        "",
        "    /// 0xRRGGBBAA. 0번은 빈칸.",
        "    static let palette: [UInt32] = [",
    ]
    for i, (r, g, b, a) in enumerate(palette):
        role = roles.get((r, g, b, a), -1)
        note = ["털", "밝은 털", "아랫배 털", "털 결", "테두리"][role] if role >= 0 else ""
        lines.append(f"        0x{r:02X}{g:02X}{b:02X}{a:02X},  // {ALPHABET[i]}{' ' + note if note else ''}")
    lines.append("    ]")
    lines.append("")
    lines.append("    /// palette 번호마다 털 역할: 0 털, 1 밝은 털, 2 아랫배 털, 3 털 결, 4 테두리, -1 그 밖. 작은 캐릭터 털 색 바꾸기에 쓴다.")
    lines.append("    static let furRoles: [Int] = [" + ", ".join(str(roles.get(c, -1)) for c in palette) + "]")
    lines.append("")
    lines.append("    /// 상태 이름과 장면들(보여 줄 시간 ms, 20줄 글자 그림).")
    lines.append("    static let clips: [PetSpriteClipData] = [")
    for state, frames in clips:
        lines.append(f'        PetSpriteClipData(name: "{state}", frames: [')
        for ms, rows in frames:
            lines.append(f"            PetSpriteFrameData(ms: {ms}, cells: \"\"\"")
            for row in rows:
                lines.append(f"                {row}")
            lines.append("                \"\"\"),")
        lines.append("        ]),")
    lines.append("    ]")
    lines.append("}")
    lines.append("")
    lines.append("struct PetSpriteClipData {")
    lines.append("    let name: String")
    lines.append("    let frames: [PetSpriteFrameData]")
    lines.append("}")
    lines.append("")
    lines.append("struct PetSpriteFrameData {")
    lines.append("    let ms: Int")
    lines.append("    let cells: String")
    lines.append("}")
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    total = sum(len(f) for _, f in clips)
    print(f"{out}: 상태 {len(clips)}개, 장면 {total}장, 색 {len(palette) - 1}개")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
