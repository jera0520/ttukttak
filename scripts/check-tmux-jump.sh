#!/bin/bash
# Checks the pure decisions of TmuxJump (pane id, terminal host, safe text, target choice).
set -u
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
cat >"$tmp/main.swift" <<'EOF'
import Foundation
var failed = 0
@MainActor func check(_ ok: Bool, _ what: String) { if !ok { failed += 1; print("FAIL: \(what)") } }
check(TmuxJumpLogic.isValidPane("%116"), "pane %116")
check(!TmuxJumpLogic.isValidPane("116") && !TmuxJumpLogic.isValidPane("%1;ls") && !TmuxJumpLogic.isValidPane("") , "bad panes")
check(TmuxJumpLogic.isTerminalHost(bundleId: nil) && TmuxJumpLogic.isTerminalHost(bundleId: " ") && TmuxJumpLogic.isTerminalHost(bundleId: "com.apple.Terminal"), "terminal hosts")
check(!TmuxJumpLogic.isTerminalHost(bundleId: "com.googlecode.iterm2") && !TmuxJumpLogic.isTerminalHost(bundleId: "com.mitchellh.ghostty"), "other hosts")
check(TmuxJumpLogic.isSafeText("레아") && TmuxJumpLogic.isSafeText("/dev/ttys024"), "safe text")
check(!TmuxJumpLogic.isSafeText("a\nb") && !TmuxJumpLogic.isSafeText("a\rb") && !TmuxJumpLogic.isSafeText("a\u{0}b") && !TmuxJumpLogic.isSafeText("a\u{1B}b") && !TmuxJumpLogic.isSafeText(""), "control chars")
check(TmuxJumpLogic.target(pane: "%6", bundleId: "com.apple.Terminal") == "%6", "target terminal")
check(TmuxJumpLogic.target(pane: "%6", bundleId: "com.googlecode.iterm2") == nil, "target iterm")
check(TmuxJumpLogic.target(pane: nil, bundleId: nil) == nil, "target no pane")
if failed == 0 { print("tmux-jump logic OK") } else { exit(1) }
EOF
swiftc -swift-version 6 Sources/App/TmuxJumpLogic.swift "$tmp/main.swift" -o "$tmp/t" 2>"$tmp/err" && "$tmp/t" || { cat "$tmp/err"; exit 1; }
