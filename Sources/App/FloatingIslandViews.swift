import SwiftUI

// Screens without a notch (menu-bar look): the island only shows while open. Its home and
// permission cards are lighter than the notch ones, after CodeIsland, Open Island and
// MioIsland: the pet moves into the header, sessions are rows with a status tag, and a
// request reads as tag · project · command · buttons. Three looks (FloatingTheme): ink hangs
// from the top of the screen like a notch; glass and hanji float below the menu bar.

enum FloatingLayout {
    /// Narrower than the notch card: it covers windows rather than dead space by a notch.
    static let width: CGFloat = 520
    static let rowHeight: CGFloat = 50
    static let rowSpacing: CGFloat = 6
    static let maxRows = 3
    /// Space between a card floating below the menu bar and the menu bar.
    static let menuBarGap: CGFloat = 6

    /// Views drawn for a black card only: they keep the ink look on every floating theme.
    static let inkOnlyViews: Set<IslandView> = [.upload, .uploading, .choose, .mail, .greeting,
                                                 .recap, .listening, .voiceResult]

    /// Views with a floating layout; the others keep the notch layout.
    static func isFloatingView(_ view: IslandView) -> Bool {
        view == .overview || view == .approval
    }

    /// Content top padding + header + bottom padding + ears (IslandContentView, IslandContainer).
    @MainActor
    private static var chrome: CGFloat { 8 + 34 + 10 + AppState.shared.floatingTheme.earRadius }

    /// Agent sessions shown as rows: the Claude Code pill and the other agents (Codex,
    /// Cursor…). Service integrations (GitHub, Vercel…) stay out of the floating card.
    @MainActor
    static func sessions(_ state: AppState) -> [AgentTask] {
        state.tasks.filter { $0.id == "integration_claude" || $0.id.hasPrefix("agent_") }
    }

    @MainActor
    static func overviewHeight(_ state: AppState) -> CGFloat {
        let rows = CGFloat(max(1, min(maxRows, sessions(state).count)))
        return chrome + rows * rowHeight + (rows - 1) * rowSpacing
    }

    @MainActor
    static var approvalHeight: CGFloat { chrome + 98 }

    /// The pet sits small at the left of the header (y below the ears, if any).
    static func petCenter(ear: CGFloat) -> CGPoint { CGPoint(x: 28, y: 8 + 17 + ear) }
    static let petDiameter: CGFloat = 20
}

extension FloatingTheme {
    /// Ink hangs from the screen top with concave ears; the others are plain rounded cards.
    var earRadius: CGFloat { self == .ink ? IslandConst.floatingEarRadius : 0 }
    var hangsFromTop: Bool { self == .ink }
}

// MARK: - Palette

/// Colours of a floating card. The notch cards keep their own black look.
struct FloatingPalette {
    var isLight: Bool
    var text: Color
    var secondary: Color
    var tertiary: Color
    var rowFill: Color
    var rowHover: Color
    var rowStroke: Color
    var chipFill: Color
    var codeFill: Color
    var codeText: Color
    var tabOnFill: Color
    var link: Color

    static func of(_ theme: FloatingTheme) -> FloatingPalette {
        switch theme {
        case .ink:
            return FloatingPalette(
                isLight: false,
                text: Color(hex: "#F5F6F8"), secondary: Color(hex: "#A3A8B0"), tertiary: Color(hex: "#8E939C"),
                rowFill: Color.white.opacity(0.08), rowHover: Color.white.opacity(0.12),
                rowStroke: Color.white.opacity(0.08), chipFill: Color.white.opacity(0.1),
                codeFill: Color.white.opacity(0.09), codeText: Color(hex: "#E8E9EC"),
                tabOnFill: Color(hex: "#1D1F23"), link: Color(hex: "#60A5FA"))
        case .glass:
            // Adaptive: dark text on light glass, light text in dark mode.
            return FloatingPalette(
                isLight: true,
                text: Color.primary, secondary: Color.primary.opacity(0.62), tertiary: Color.primary.opacity(0.5),
                rowFill: Color.primary.opacity(0.06), rowHover: Color.primary.opacity(0.1),
                rowStroke: Color.primary.opacity(0.07), chipFill: Color.primary.opacity(0.08),
                codeFill: Color.primary.opacity(0.07), codeText: Color.primary.opacity(0.88),
                tabOnFill: Color.primary.opacity(0.1), link: Color(hex: "#2F6FEB"))
        case .hanji:
            // Warm paper with ink-brown text; the pet's orange is the one accent.
            return FloatingPalette(
                isLight: true,
                text: Color(hex: "#2B2520"), secondary: Color(hex: "#6F655B"), tertiary: Color(hex: "#8E8377"),
                rowFill: Color(hex: "#F3ECE0"), rowHover: Color(hex: "#EEE4D4"),
                rowStroke: Color(hex: "#E5D9C6"), chipFill: Color(hex: "#EAE0CF"),
                codeFill: Color(hex: "#F1E9DC"), codeText: Color(hex: "#3A322B"),
                tabOnFill: Color(hex: "#EBDFCB"), link: Color(hex: "#C8641E"))
        }
    }
}

private struct FloatingPaletteKey: EnvironmentKey {
    static let defaultValue = FloatingPalette.of(.ink)
}

extension EnvironmentValues {
    var floatingPalette: FloatingPalette {
        get { self[FloatingPaletteKey.self] }
        set { self[FloatingPaletteKey.self] = newValue }
    }
}

// MARK: - Card background

/// The floating card itself: black ink, Liquid Glass, or hanji paper.
struct FloatingCardBackground: View {
    let theme: FloatingTheme
    let width: CGFloat
    let height: CGFloat
    let cornerRadius: CGFloat
    let topRadius: CGFloat
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        let shape = IslandShape(width: width, height: height, cornerRadius: cornerRadius, topRadius: topRadius)
        switch theme {
        case .ink:
            shape.fill(Color.black)
                .shadow(color: .black.opacity(0.28), radius: 14, y: 6)
        case .glass:
            if #available(macOS 26.0, *) {
                let tintColor = colorScheme == .dark ? Color.black.opacity(0.45) : Color.white.opacity(0.45)
                Color.clear
                    .frame(width: width, height: height)
                    .glassEffect(.regular.tint(tintColor), in: shape)
                    .shadow(color: .black.opacity(0.2), radius: 16, y: 6)
            } else {
                shape.fill(.regularMaterial)
                    .overlay(shape.stroke(colorScheme == .dark ? Color.white.opacity(0.14) : Color.white.opacity(0.35), lineWidth: 1))
                    .shadow(color: .black.opacity(0.18), radius: 16, y: 6)
            }
        case .hanji:
            shape.fill(Color(hex: "#FBF7EF"))
                .overlay(shape.stroke(Color(hex: "#E2D5C1"), lineWidth: 1))
                .shadow(color: Color(hex: "#5A4630").opacity(0.18), radius: 18, y: 8)
        }
    }
}

// MARK: - Status tag

/// Small coloured tag for a session state ("작업 중", "확인 필요"…).
struct FloatingStateTag: View {
    let state: BotState
    @Environment(\.floatingPalette) private var palette

    var body: some View {
        let (label, color) = Self.style(state, light: palette.isLight)
        Text(LocalizedStringKey(label))
            .font(.system(size: 11, weight: .bold))
            .foregroundColor(color)
            .padding(.horizontal, 7)
            .frame(height: 19)
            .background(color.opacity(palette.isLight ? 0.14 : 0.2))
            .clipShape(RoundedRectangle(cornerRadius: 5))
            .fixedSize()
    }

    /// Bright hues on ink; deeper ones that stay readable on light cards.
    static func style(_ state: BotState, light: Bool = false) -> (String, Color) {
        switch state {
        case .approval, .question: return ("island.tag.needs-you", Color(hex: light ? "#C86A12" : "#F5A524"))
        case .working:             return ("island.tag.working", Color(hex: light ? "#17895C" : "#34D399"))
        case .thinking:            return ("island.tag.thinking", Color(hex: light ? "#6B4FC8" : "#A78BFA"))
        case .searching:           return ("island.tag.searching", Color(hex: light ? "#2F6FEB" : "#60A5FA"))
        case .finished:            return ("island.tag.done", Color(hex: light ? "#6F655B" : "#C9CDD3"))
        case .error, .dizzy:       return ("island.tag.error", Color(hex: light ? "#C93C3C" : "#F4505E"))
        case .ratelimit:           return ("island.tag.limit", Color(hex: light ? "#B86E0A" : "#F59E0B"))
        case .idle, .sleeping:     return ("island.tag.idle", Color(hex: light ? "#7D746A" : "#A3A8B0"))
        }
    }
}

// MARK: - Sessions (home)

struct FloatingSessionsView: View {
    @ObservedObject var state: AppState
    /// Brings the session's terminal or app forward (OverviewView.openAgentTarget).
    let open: (AgentTask) -> Void
    @Environment(\.floatingPalette) private var palette

    var body: some View {
        let rows = Array(FloatingLayout.sessions(state).prefix(FloatingLayout.maxRows))
        VStack(spacing: FloatingLayout.rowSpacing) {
            if rows.isEmpty {
                Text("Nothing running right now.")
                    .font(.system(size: 12))
                    .foregroundColor(palette.tertiary)
                    .frame(maxWidth: .infinity, minHeight: FloatingLayout.rowHeight)
            }
            ForEach(rows) { task in
                FloatingSessionRow(task: task, open: { open(task) })
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }
}

private struct FloatingSessionRow: View {
    let task: AgentTask
    let open: () -> Void
    @State private var hovered = false
    @Environment(\.floatingPalette) private var palette

    /// What the session is doing now, else its last words.
    private var detail: String? {
        if task.steps.indices.contains(task.stepIndex) { return task.steps[task.stepIndex] }
        return task.finalLine
    }

    private var host: String? {
        switch task.source {
        case .claudeCode:
            // The pill may already be named after its host ("VS Code"): no second label.
            let name = ClaudeHost.name(for: task.hostApp)
            return name == task.name ? nil : name
        case .agent, .n8n: return nil
        }
    }

    var body: some View {
        let accent = FloatingStateTag.style(task.state, light: palette.isLight).1
        Button(action: open) {
            HStack(spacing: 10) {
                RoundedRectangle(cornerRadius: 1.5)
                    .fill(accent)
                    .frame(width: 3, height: 28)
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        FloatingStateTag(state: task.state)
                        Text(task.name)
                            .font(.system(size: 13.5, weight: .semibold))
                            .foregroundColor(palette.text)
                            .lineLimit(1)
                            .truncationMode(.tail)
                        Spacer(minLength: 4)
                        if let host {
                            Text(host)
                                .font(.system(size: 11.5))
                                .foregroundColor(palette.secondary)
                                .padding(.horizontal, 7)
                                .frame(height: 19)
                                .background(palette.chipFill)
                                .clipShape(RoundedRectangle(cornerRadius: 5))
                                .fixedSize()
                        }
                    }
                    if let detail, !detail.isEmpty {
                        Text(detail)
                            // Tool lines read as code; sentences (last words) in the normal face.
                            .font(.system(size: 12, design: detail.allSatisfy(\.isASCII) ? .monospaced : .default))
                            .foregroundColor(palette.secondary)
                            .lineLimit(1)
                            .truncationMode(.tail)
                    }
                }
                Image(systemName: "arrow.up.right")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundColor(hovered ? palette.text : palette.secondary)
                    .frame(width: 22, height: 22)
                    .background(hovered ? palette.rowHover : palette.chipFill)
                    .clipShape(Circle())
            }
            .padding(.horizontal, 10)
            .frame(height: FloatingLayout.rowHeight)
            .background(hovered ? palette.rowHover : palette.rowFill)
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(palette.rowStroke, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .contentShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .onHover { hovered = $0 }
        .help(String(localized: "Open terminal"))
    }
}

// MARK: - Permission request

struct FloatingApprovalView: View {
    @ObservedObject var state: AppState
    @Environment(\.floatingPalette) private var palette

    var body: some View {
        let approval = state.pendingApproval
        // A click answers the request that was on screen, never the next one in the queue.
        let shownId = approval?.id
        let project = approval.map { $0.projectName.isEmpty ? (state.focusTask?.name ?? "") : $0.projectName } ?? ""
        let hideAlways = approval?.pillId == "agent_codex"
            || approval?.pillId == "agent_copilot"
            || approval?.pillId == "agent_muse"
        let deny = Color(hex: palette.isLight ? "#C93C3C" : "#F4505E")
        let allow = Color(hex: palette.isLight ? "#1E8E50" : "#22A35A")

        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 7) {
                FloatingStateTag(state: .approval)
                Text(project)
                    .font(.system(size: 13.5, weight: .semibold))
                    .foregroundColor(palette.text)
                    .lineLimit(1)
                Text(approval?.tool ?? "")
                    .font(.system(size: 12.5))
                    .foregroundColor(palette.secondary)
                    .lineLimit(1)
                Spacer(minLength: 4)
                if let count = approval?.queueCount, count > 1 {
                    Text(verbatim: "1/\(count)")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(palette.tertiary)
                        .monospacedDigit()
                }
            }

            Text(approval?.command.isEmpty == false ? approval!.command : (approval?.tool ?? "…"))
                .font(.system(size: 12.5, design: .monospaced))
                .foregroundColor(palette.codeText)
                .lineLimit(2)
                .truncationMode(.middle)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(palette.codeFill)
                .clipShape(RoundedRectangle(cornerRadius: 9))

            HStack(spacing: 8) {
                if !hideAlways {
                    Button(action: { HookServer.shared.sendApprovalDecision("always", for: shownId) }) {
                        Text("island.always-allow")
                            .font(.system(size: 12.5))
                            .foregroundColor(palette.link)
                            .underline()
                    }
                    .buttonStyle(.plain)
                }
                Spacer()
                FloatingDecisionButton(title: "Deny", tint: deny, filled: false) {
                    HookServer.shared.sendApprovalDecision("deny", for: shownId)
                }
                FloatingDecisionButton(title: "island.allow-once", tint: allow, filled: true) {
                    HookServer.shared.sendApprovalDecision("allow", for: shownId)
                }
            }
        }
        .padding(.horizontal, 6)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }
}

private struct FloatingDecisionButton: View {
    let title: String
    let tint: Color
    let filled: Bool
    let action: () -> Void
    @State private var hovered = false

    var body: some View {
        Button(action: action) {
            Text(LocalizedStringKey(title))
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(filled ? .white : tint)
                .padding(.horizontal, 15)
                .frame(height: 28)
                .background(filled ? tint.opacity(hovered ? 1 : 0.9) : tint.opacity(hovered ? 0.12 : 0))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(tint.opacity(filled ? 0 : 0.6), lineWidth: 1))
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .buttonStyle(.plain)
        .onHover { hovered = $0 }
    }
}

// MARK: - Ink colours for the light looks

/// A colour of the island views (designed light-on-black), translated for the light floating
/// looks (glass, hanji): light greys become dark text, dark panels become soft fills, bright
/// accents get deeper. On the notch and on ink it is the colour itself.
@MainActor
func ink(_ hex: String) -> Color {
    let s = AppState.shared
    guard s.islandFloats, s.floatingSkin != .ink else { return Color(hex: hex) }
    let p = FloatingPalette.of(s.floatingSkin)
    switch hex.uppercased() {
    case "#F5F6F8", "#F1F2F4", "#F2F3F5", "#FFFFFF": return p.text
    case "#E8E9EC":                                   return p.codeText
    case "#C5C8CD", "#A9ADB5", "#C8CDD4", "#C9CDD4",
         "#D5D7DB", "#B9BDC4", "#B0B5BE", "#E8E8E8": return p.text.opacity(0.78)
    case "#9398A1", "#8E939C", "#8A8F98", "#7C818A",
         "#9AA0A8", "#80858E", "#7B8089":             return p.secondary
    case "#6B7079", "#5F646D", "#4B5563", "#454850",
         "#6E737C", "#5C6370", "#4D5159":             return p.tertiary
    case "#141518", "#0E0F11", "#1D1F23", "#252830": return p.rowFill
    // The model picker popover is its own window, not glass: let the system popover show
    // on glass, paper on hanji.
    case "#16171B":                                   return s.floatingSkin == .hanji ? Color(hex: "#FBF7F0") : .clear
    case "#0B0C0E":
        if s.floatingSkin == .glass { return Color(nsColor: .windowBackgroundColor) }
        return Color.white   // text on a primary button
    case "#F4505E", "#FF8D97", "#FA2D48", "#FCA5A5": return Color(hex: "#C93C3C")
    case "#22C55E", "#34D399":                        return Color(hex: "#17895C")
    case "#F5A524", "#F7B32B":                        return Color(hex: "#C86A12")
    case "#22D3EE", "#67E8F9":                        return Color(hex: "#0E8FA8")
    case "#A78BFA", "#7C5CFF":                        return Color(hex: "#6B4FC8")
    case "#60A5FA":                                   return Color(hex: "#2F6FEB")
    default:                                          return Color(hex: hex)
    }
}

/// `Color.white.opacity(x)` of the island views: dark ink at the same strength on light looks.
@MainActor
func inkWhite(_ opacity: Double) -> Color {
    let s = AppState.shared
    guard s.islandFloats, s.floatingSkin != .ink else { return Color.white.opacity(opacity) }
    return FloatingPalette.of(s.floatingSkin).text.opacity(opacity * 0.9)
}
