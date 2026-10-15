import SwiftUI
import QuartzCore

// 도트 캐릭터(복슬깨비) 그리기.
// 그림은 PetSpriteData.swift(자동 생성)에 있고, 여기서는 그 글자 그림을 읽어 칸 단위로 칠한다.
// 칸 크기는 화면 픽셀의 정수배로 맞춰서(접힌 노치 1칸 = 1pt = 레티나 2픽셀) 테두리가 번지지 않게 한다.

/// 캐릭터 장면. 앱 상태(BotState) 하나가 장면 하나로 간다.
enum PetClip: String, CaseIterable, Sendable {
    case idle, thinking, working, approval, question, finished, error, sleeping, petted
    case waitingLong = "waiting_long"

    init(_ state: BotState) {
        switch state {
        case .idle:                 self = .idle
        case .working:              self = .working
        case .thinking, .searching: self = .thinking
        case .approval:             self = .approval
        case .question:             self = .question
        case .finished:             self = .finished
        case .error, .dizzy:        self = .error
        case .ratelimit:            self = .waitingLong
        case .sleeping:             self = .sleeping
        }
    }
}

/// 한 줄에서 같은 색이 이어진 칸들.
struct PetRun: Sendable {
    let x: Int, y: Int, width: Int, color: Int
}

/// 장면 한 장: 보여 줄 시간(초)과 칠할 칸.
struct PetFrame: Sendable {
    let duration: Double
    let runs: [PetRun]
}

enum PetSprite {
    static let grid = PetSpriteData.grid

    /// 장면별 그림(처음 쓸 때 한 번 읽는다).
    static let clips: [PetClip: [PetFrame]] = {
        let index: [Character: Int] = Dictionary(uniqueKeysWithValues: PetSpriteData.alphabet.enumerated().map { ($1, $0) })
        var out: [PetClip: [PetFrame]] = [:]
        for clip in PetSpriteData.clips {
            guard let name = PetClip(rawValue: clip.name) else { continue }
            out[name] = clip.frames.map { data in
                var runs: [PetRun] = []
                let rows = data.cells.split(separator: "\n", omittingEmptySubsequences: true)
                for (y, row) in rows.enumerated() {
                    var x = 0, start = 0, current = 0
                    for ch in row {
                        let c = index[ch] ?? 0
                        if c != current {
                            if current != 0 { runs.append(PetRun(x: start, y: y, width: x - start, color: current)) }
                            current = c
                            start = x
                        }
                        x += 1
                    }
                    if current != 0 { runs.append(PetRun(x: start, y: y, width: x - start, color: current)) }
                }
                return PetFrame(duration: Double(data.ms) / 1000, runs: runs)
            }
        }
        return out
    }()

    /// 그림의 원래 색.
    static let colors: [Color] = PetSpriteData.palette.map(color)

    /// 같은 장면을 반복할 때 elapsed초 뒤의 장면.
    static func frame(_ clip: PetClip, elapsed: Double) -> PetFrame {
        guard let list = clips[clip] ?? clips[.idle], !list.isEmpty else {
            return PetFrame(duration: 1, runs: [])
        }
        let total = list.reduce(0) { $0 + $1.duration }
        var t = max(0, elapsed).truncatingRemainder(dividingBy: max(total, 0.001))
        for f in list {
            if t < f.duration { return f }
            t -= f.duration
        }
        return list[list.count - 1]
    }

    /// 지름 diameter(pt) 자리에 20칸이 들어가는 가장 큰 칸 크기. 화면 픽셀의 정수배라서 번지지 않는다.
    /// 지름은 보통 그림판 폭 × 0.6으로 되돌려 받는데, SwiftUI가 그림판 폭을 화소에 맞춰 반올림한다
    /// (접힌 노치: 20 / 0.6 = 33.33 → 33.0, × 0.6 = 19.8). 그래서 내림 전에 0.1화소의 여유를 둔다.
    /// 여유가 없으면 접힌 노치의 캐릭터가 1pt 칸이 아닌 0.5pt 칸, 절반 크기로 그려진다.
    static func cell(fitting diameter: CGFloat, scale: CGFloat) -> CGFloat {
        let s = max(scale, 1)
        return max(1, floor(diameter * s / CGFloat(grid) + 0.1)) / s
    }

    /// 몸(위에서 0~15줄)의 가운데가 center에 오게 하는 그림 왼쪽 위.
    static func origin(center: CGPoint, cell: CGFloat) -> CGPoint {
        CGPoint(x: center.x - cell * CGFloat(grid) / 2, y: center.y - cell * 8)
    }

    /// SwiftUI Canvas에 그린다.
    static func draw(_ frame: PetFrame, in context: GraphicsContext, center: CGPoint, cell: CGFloat,
                     colors: [Color] = PetSprite.colors) {
        let o = origin(center: center, cell: cell)
        var paths = [Path](repeating: Path(), count: colors.count)
        for r in frame.runs where r.color < colors.count {
            paths[r.color].addRect(CGRect(x: o.x + CGFloat(r.x) * cell, y: o.y + CGFloat(r.y) * cell,
                                          width: CGFloat(r.width) * cell, height: cell))
        }
        for (i, p) in paths.enumerated() where !p.isEmpty {
            context.fill(p, with: .color(colors[i]))
        }
    }

    /// CGContext(위가 0인 좌표)에 그린다. 인사 화면처럼 CG로 그리는 곳에서 쓴다.
    static func draw(_ frame: PetFrame, in ctx: CGContext, center: CGPoint, cell: CGFloat,
                     colors: [CGColor] = PetSprite.cgColors) {
        let o = origin(center: center, cell: cell)
        for r in frame.runs where r.color < colors.count {
            ctx.setFillColor(colors[r.color])
            ctx.fill(CGRect(x: o.x + CGFloat(r.x) * cell, y: o.y + CGFloat(r.y) * cell,
                            width: CGFloat(r.width) * cell, height: cell))
        }
    }

    static let cgColors: [CGColor] = PetSpriteData.palette.map(cgColor)

    // MARK: - 털 색 바꾸기 (작은 캐릭터: 세션·연동마다 다른 색)

    /// 털과 테두리만 tint 색 계열로 바꾼 팔레트. tint가 없거나 읽을 수 없으면 원래 색.
    static func palette(tint hex: String?) -> [Color] {
        guard let rgb = hex.flatMap(rgb(fromHex:)) else { return colors }
        return PetSpriteData.palette.indices.map { i in
            guard let shade = tintedShade(rgb, role: PetSpriteData.furRoles[i]) else { return colors[i] }
            return Color(red: shade.r, green: shade.g, blue: shade.b)
        }
    }

    static func cgPalette(tint hex: String?) -> [CGColor] {
        guard let rgb = hex.flatMap(rgb(fromHex:)) else { return cgColors }
        return PetSpriteData.palette.indices.map { i in
            guard let shade = tintedShade(rgb, role: PetSpriteData.furRoles[i]) else { return cgColors[i] }
            return CGColor(red: shade.r, green: shade.g, blue: shade.b, alpha: 1)
        }
    }

    private typealias RGB = (r: Double, g: Double, b: Double)

    private static func tintedShade(_ t: RGB, role: Int) -> RGB? {
        func mix(_ other: Double, _ k: Double) -> RGB {
            (t.r + (other - t.r) * k, t.g + (other - t.g) * k, t.b + (other - t.b) * k)
        }
        switch role {
        case 0: return t                // 털
        case 1: return mix(1, 0.4)      // 밝은 털
        case 2: return mix(0, 0.08)     // 아랫배 털
        case 3: return mix(0, 0.18)     // 털 결
        case 4: return mix(0, 0.45)     // 테두리
        default: return nil
        }
    }

    private static func rgb(fromHex hex: String) -> RGB? {
        var s = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.hasPrefix("#") { s.removeFirst() }
        guard s.count == 6 || s.count == 8, let v = UInt32(s.prefix(6), radix: 16) else { return nil }
        return (Double((v >> 16) & 0xFF) / 255, Double((v >> 8) & 0xFF) / 255, Double(v & 0xFF) / 255)
    }

    private static func color(_ rgba: UInt32) -> Color {
        Color(.sRGB,
              red: Double((rgba >> 24) & 0xFF) / 255,
              green: Double((rgba >> 16) & 0xFF) / 255,
              blue: Double((rgba >> 8) & 0xFF) / 255,
              opacity: Double(rgba & 0xFF) / 255)
    }

    private static func cgColor(_ rgba: UInt32) -> CGColor {
        CGColor(srgbRed: CGFloat((rgba >> 24) & 0xFF) / 255,
                green: CGFloat((rgba >> 16) & 0xFF) / 255,
                blue: CGFloat((rgba >> 8) & 0xFF) / 255,
                alpha: CGFloat(rgba & 0xFF) / 255)
    }
}

/// 장면 재생기. 상태가 바뀌면 새 장면을 처음부터 틀고, 잠깐 반응(쓰다듬기·툭 치기 등)은 정해진 시간만 보여 준다.
/// 그리는 도중에 바꿔도 되도록 SwiftUI 상태가 아닌 보통 객체로 둔다(@StateObject로 붙잡아 둔다).
@MainActor
final class PetPlayer: ObservableObject {
    private(set) var clip: PetClip = .idle
    private var clipStart = CACurrentMediaTime()
    private var reaction: PetClip?
    private var reactionStart: CFTimeInterval = 0
    private var reactionEnd: CFTimeInterval = 0
    /// After this many seconds of idle the pet naps (Zzz) until something happens. nil: never.
    var napAfter: Double?

    func show(_ next: PetClip, restart: Bool = false) {
        guard next != clip || restart else { return }
        clip = next
        clipStart = CACurrentMediaTime()
    }

    func react(_ clip: PetClip, for seconds: Double) {
        let now = CACurrentMediaTime()
        reaction = clip
        reactionStart = now
        reactionEnd = now + seconds
        if self.clip == .idle { clipStart = now + seconds }   // a reaction wakes it up
    }

    func frame(now: CFTimeInterval = CACurrentMediaTime()) -> PetFrame {
        if let r = reaction {
            if now < reactionEnd { return PetSprite.frame(r, elapsed: now - reactionStart) }
            reaction = nil
        }
        let elapsed = now - clipStart
        if clip == .idle, let nap = napAfter, elapsed >= nap {
            return PetSprite.frame(.sleeping, elapsed: elapsed - nap)
        }
        return PetSprite.frame(clip, elapsed: elapsed)
    }
}
