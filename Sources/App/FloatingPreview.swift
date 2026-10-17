import AppKit
import SwiftUI

/// Renders the floating (no notch) cards with sample sessions to PNG files and quits, so
/// their design can be checked without opening the island on screen.
/// Run: TT_RENDER_FLOATING_PREVIEW=<folder> <app>/Contents/MacOS/Ttukttak
@MainActor
enum FloatingPreview {
    static func renderIfRequested() {
        guard let dir = ProcessInfo.processInfo.environment["TT_RENDER_FLOATING_PREVIEW"],
              !dir.isEmpty else { return }
        let s = AppState.shared
        s.hasNotch = false
        s.tasks = [
            AgentTask(id: "integration_claude", name: "munlink-work", color: "#E879F9", state: .working,
                      stepIndex: 0, steps: ["Edit · tools/delivery_check.py"], source: .claudeCode,
                      isIntegration: true, hostApp: "com.apple.Terminal"),
            AgentTask(id: "agent_codex", name: "hongbo-chukchuk", color: "#60A5FA", state: .approval,
                      steps: ["Bash · npm run build"], source: .agent, isIntegration: true),
            AgentTask(id: "agent_cursor", name: "portfolio", color: "#22C55E", state: .finished,
                      steps: [], source: .agent, isIntegration: true,
                      finalLine: "사이트 첫 화면 글꼴을 바꾸고 배포했어요."),
        ]
        s.focusId = "integration_claude"
        s.pendingQuestion = AskQuestion(questions: [AskQuestionItem(
            question: "상세페이지 첫 화면을 어떤 분위기로 할까요?", header: "분위기",
            options: [AskQuestionOption(label: "따뜻한 한지", description: ""),
                      AskQuestionOption(label: "깔끔한 흰색", description: ""),
                      AskQuestionOption(label: "사진 크게", description: "")],
            multiSelect: false)])
        s.pendingApproval = ApprovalInfo(sessionId: "preview", tool: "Bash",
                                         command: "npm run build && npx wrangler deploy",
                                         inputKey: "", pillId: "integration_claude",
                                         queueCount: 2, projectName: "hongbo-chukchuk")
        s.mode = .expanded
        // The theme is persisted on every change: put the user's back before quitting.
        let savedTheme = s.floatingTheme
        for theme in FloatingTheme.allCases {
        s.floatingTheme = theme
        for view in [IslandView.overview, .approval, .question, .finished, .error, .empty, .settings, .prompt] {
            s.view = view
            s.focusId = view == .finished ? "agent_cursor" : "integration_claude"
            if view == .error {
                s.tasks[0].state = .error
                s.tasks[0].errorKind = "rate_limit"
                s.tasks[0].finalLine = "API Error: 429 rate limit"
            } else {
                s.tasks[0].state = .working
                s.tasks[0].errorKind = nil
                s.tasks[0].finalLine = nil
            }
            let (w, h) = islandSize(mode: .expanded, view: view, nw: s.notchWidth, nh: s.notchHeight)
            let ear = theme.earRadius
            let card = ZStack(alignment: .topLeading) {
                FloatingCardBackground(theme: s.floatingSkin, width: w, height: h, cornerRadius: IslandConst.expandedCorner,
                                       topRadius: theme.hangsFromTop ? -ear : IslandConst.expandedCorner)
                VStack(spacing: 0) {
                    IslandHeader(state: s).frame(height: 34)
                    Group {
                        if view == .overview {
                            FloatingSessionsView(state: s, open: { _ in })
                        } else if view == .approval {
                            FloatingApprovalView(state: s).frame(height: 98)
                        } else {
                            IslandViewContent(view: view, state: s).frame(height: 98)
                        }
                    }
                    .padding(.horizontal, 10)
                    .frame(maxHeight: .infinity, alignment: .top)
                }
                .padding(.top, 8).padding(.bottom, 10)
                .frame(width: w, height: h - ear)
                .offset(y: ear)
                .foregroundColor(FloatingPalette.of(s.floatingSkin).text)
                BotPlacement(state: s, islandW: w, islandH: h)
            }
            .frame(width: w, height: h, alignment: .topLeading)
            .environment(\.floatingPalette, FloatingPalette.of(s.floatingSkin))
            .padding(.horizontal, 40).padding(.vertical, theme.hangsFromTop ? 0 : 20).padding(.bottom, 20)
            .background(Color(hex: "#7F93A8"))
            .environment(\.locale, Locale(identifier: "ko"))
            let renderer = ImageRenderer(content: card)
            renderer.scale = 1
            if let cg = renderer.cgImage {
                let rep = NSBitmapImageRep(cgImage: cg)
                let url = URL(fileURLWithPath: dir).appendingPathComponent("floating-\(theme.rawValue)-\(view.rawValue).png")
                try? rep.representation(using: .png, properties: [:])?.write(to: url)
            }
        }
        }
        s.floatingTheme = savedTheme
        exit(0)
    }
}
