import AppKit

/// "Open terminal" for a session that runs inside tmux: the hook payload says which pane
/// (TMUX_PANE), tmux says which session and which client ttys are attached to it, and
/// Terminal says which tab owns that tty. The app has no PATH, so tmux is found by path.
enum TmuxJump {
    static var tmuxPath: String? {
        ["/opt/homebrew/bin/tmux", "/usr/local/bin/tmux"]
            .first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    /// Runs tmux and returns trimmed stdout, nil on failure or after `timeout` seconds.
    /// Never call on the main thread.
    private static func tmux(_ args: [String], timeout: TimeInterval = 1) -> String? {
        guard let path = tmuxPath else { return nil }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: path)
        p.arguments = args
        let out = Pipe()
        p.standardOutput = out
        p.standardError = FileHandle.nullDevice
        let done = DispatchSemaphore(value: 0)
        p.terminationHandler = { _ in done.signal() }
        do { try p.run() } catch { return nil }
        // tmux prints a line or two: the pipe cannot fill up while we wait.
        if done.wait(timeout: .now() + timeout) == .timedOut {
            p.terminate()
            return nil
        }
        let data = out.fileHandleForReading.readDataToEndOfFile()
        guard p.terminationStatus == 0 else { return nil }
        return String(decoding: data, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Session name of a pane, nil if tmux is missing, the server is gone or the pane is closed.
    static func sessionName(pane: String) -> String? {
        guard TmuxJumpLogic.isValidPane(pane),
              let name = tmux(["display-message", "-p", "-t", pane, "#{session_name}"]),
              TmuxJumpLogic.isSafeText(name) else { return nil }
        return name
    }

    /// ttys of the clients attached to a session.
    static func clientTTYs(session: String) -> [String] {
        (tmux(["list-clients", "-t", "=" + session, "-F", "#{client_tty}"]) ?? "")
            .split(separator: "\n").map(String.init)
            .filter { $0.hasPrefix("/dev/") && TmuxJumpLogic.isSafeText($0) }
    }

    /// Brings forward the Terminal window attached to the pane's tmux session, or opens a new
    /// Terminal window attached to it. Everything (tmux, Terminal: the first run waits for the
    /// Automation permission dialog) runs off the main thread. When the pane cannot be used
    /// (not a Terminal host, tmux missing, pane closed) `fallback` runs on the main thread.
    static func open(pane: String?, bundleId: String?, fallback: @escaping () -> Void,
                     log: @escaping (String) -> Void = { appendAppLog("tt.log", $0) }) {
        guard let pane = TmuxJumpLogic.target(pane: pane, bundleId: bundleId), let tmuxBin = tmuxPath else {
            fallback()
            return
        }
        // The fallback only ever runs back on the main thread.
        nonisolated(unsafe) let mainFallback = fallback
        DispatchQueue.global(qos: .userInitiated).async {
            guard let session = sessionName(pane: pane) else {
                DispatchQueue.main.async { mainFallback() }
                return
            }
            let ttys = clientTTYs(session: session)
            let terminalRunning = NSWorkspace.shared.runningApplications
                .contains { $0.bundleIdentifier == "com.apple.Terminal" }
            if terminalRunning && !ttys.isEmpty {
                var error: NSDictionary?
                let result = NSAppleScript(source: findScript(ttys: ttys))?.executeAndReturnError(&error).stringValue ?? ""
                if result == "found" { log("tmux jump — \(session) brought forward"); return }
                if let code = error?[NSAppleScript.errorNumber] as? Int {
                    log("tmux jump — window search failed (\(code)), opening a new one")
                }
            }
            var error: NSDictionary?
            _ = NSAppleScript(source: attachScript(tmux: tmuxBin, session: session))?.executeAndReturnError(&error)
            if let code = error?[NSAppleScript.errorNumber] as? Int {
                log("tmux jump — attach failed (\(code))")
            } else {
                log("tmux jump — \(session) opened in a new window")
            }
        }
    }

    static func appleScriptString(_ s: String) -> String {
        "\"" + s.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"") + "\""
    }

    /// Finds the tab whose tty is one of `ttys` (only reads, unless `raise`), returns "found" or "none".
    static func findScript(ttys: [String], raise: Bool = true) -> String {
        let list = ttys.map(appleScriptString).joined(separator: ", ")
        let action = raise ? """
                        set selected of t to true
                        set index of w to 1
                        activate
        """ : ""
        return """
        tell application "Terminal"
            set wanted to {\(list)}
            repeat with w in windows
                repeat with t in tabs of w
                    if wanted contains (tty of t) then
        \(action)
                        return "found"
                    end if
                end repeat
            end repeat
            return "none"
        end tell
        """
    }

    static func attachScript(tmux: String, session: String) -> String {
        let shellQuoted = "'" + session.replacingOccurrences(of: "'", with: "'\\''") + "'"
        let command = "\(tmux) attach -t =\(shellQuoted)"
        return """
        tell application "Terminal"
            do script \(appleScriptString(command))
            activate
        end tell
        """
    }
}
