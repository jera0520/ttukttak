import Foundation

/// The decisions of TmuxJump that need no tmux or Terminal, kept apart so a script can test them.
enum TmuxJumpLogic {
    /// Pane ids look like "%116"; anything else is never passed on to tmux or a script.
    static func isValidPane(_ pane: String) -> Bool {
        pane.range(of: #"^%[0-9]+$"#, options: .regularExpression) != nil
    }

    /// Only Terminal windows are searched. A session in iTerm, Ghostty... (or in VS Code)
    /// keeps the plain activation; an empty bundle id (older hooks) is taken as Terminal.
    static func isTerminalHost(bundleId: String?) -> Bool {
        let id = bundleId?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return id.isEmpty || id == "com.apple.Terminal"
    }

    /// tmux output that goes into a script: no control characters (CR, LF, NUL, ESC...).
    static func isSafeText(_ s: String) -> Bool {
        !s.isEmpty && !s.unicodeScalars.contains { $0.value < 0x20 || $0.value == 0x7F }
    }

    /// The pane the jump may use, nil when the plain activation should run instead.
    static func target(pane: String?, bundleId: String?) -> String? {
        guard let pane, isValidPane(pane), isTerminalHost(bundleId: bundleId) else { return nil }
        return pane
    }
}
