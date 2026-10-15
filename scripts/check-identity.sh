#!/usr/bin/env bash
# check-identity.sh - quick checks that this app (뚝딱, technical name Ttukttak) cannot collide with Coucou.
#
#   scripts/check-identity.sh
#
#   1. static: Coucou's file, socket, hook and internal names, and the earlier working name NotchPet,
#      must not be used in Sources/ (comments are ignored)
#   2. unit test (swiftc, no file access, no home folder): the "is this my own hook?" check accepts
#      tt-hook and rejects Coucou's nb-hook, in every form Coucou writes it
#
# If the technical name changes again, change HOOK_MARK below and the "tt-hook" strings in Sources/.
# Takes about 15 s (one small swiftc run). Exit code 0 = all good.
set -euo pipefail

HOOK_MARK=tt-hook          # what our own hook command contains (must match ClaudeHookDetection.swift)
OLD_HOOK_MARK=nb-hook      # what Coucou's hook command contains

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
fail=0

echo "==> 1. static: old Coucou names in Sources/ (comment lines ignored)"
check() {   # check <description> <extended regex>
  local hits
  hits="$(find Sources -name '*.swift' -print0 | xargs -0 grep -nE -- "$2" | grep -vE '^[^:]+:[0-9]+:[[:space:]]*//' || true)"
  if [ -n "$hits" ]; then
    echo "  FAIL  $1"; echo "$hits" | head -5 | sed 's/^/        /'; fail=1
  else
    echo "  ok    $1"
  fi
}
check "Coucou hook name ($OLD_HOOK_MARK)"                 "$OLD_HOOK_MARK"
check "Coucou socket (nb.sock)"                            'nb[.]sock'
check "Coucou support folder (Application Support/NotchBuddy)" 'Application Support/NotchBuddy|"NotchBuddy/'
check "Coucou hook folder (.claude/coucou)"                '[.]claude/coucou'
check "Coucou plugin files (plugins/coucou, coucou.js/ts/json)" 'plugins/coucou|coucou[.](js|ts|json)'
check "Coucou bundle id (fr.louisraille)"                  'fr[.]louisraille'
check "earlier working name (NotchPet, np-hook, np.sock)"   'NotchPet|notchpet|np-hook|np[.]sock'
check "Coucou's internal names (coucou_ fields, notchBuddy.*, nb.log, CoucouKit, Mochi types)" \
      'coucou_|notchBuddy[.]|NotchBuddyApp|nb[.]log|nbHook|CoucouKit|CoucouNoop|domain: "Coucou"|DesktopMochi|mochiOnDesktop|drawMochi|talkToCoucou'

echo "==> 2. unit test of the own-hook check (ClaudeHookDetection.swift)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/tt-identity.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/HookIdentityTests.swift" <<EOF
import Foundation

@main
enum HookIdentityTests {
    static func settings(_ json: String) -> [String: Any] {
        ((try? JSONSerialization.jsonObject(with: Data(json.utf8))) as? [String: Any]) ?? [:]
    }
    static func one(_ command: String) -> [String: Any] {
        settings("{\"hooks\":{\"SessionStart\":[{\"hooks\":[{\"type\":\"command\",\"command\":\"" + command + "\"}]}]}}")
    }
    static func main() {
        var n = 0
        func check(_ ok: Bool, _ what: String) { n += 1; if !ok { print("FAIL: " + what); exit(1) } }
        let own = "/Users/x/Library/Application Support/Ttukttak/$HOOK_MARK"
        let old = "/Users/x/Library/Application Support/NotchBuddy/$OLD_HOOK_MARK"
        // ours is recognised
        check(ttukttakHooksPresent(inSettings: one(own)), "own hook")
        check(ttukttakHooksPresent(inSettings: one("\$HOME/.claude/ttukttak/$HOOK_MARK")), "own App Store hook")
        // Coucou's is not ours, in each form Coucou writes it
        check(!ttukttakHooksPresent(inSettings: one(old)), "Coucou hook")
        check(!ttukttakHooksPresent(inSettings: one("\$HOME/.claude/coucou/$OLD_HOOK_MARK")), "Coucou App Store hook")
        check(!ttukttakHooksPresent(inSettings: one("/Applications/NotchBuddy.app/.../$OLD_HOOK_MARK")), "Coucou bundle path")
        // both side by side: ours is found; Coucou's entry alone is not
        let both = "{\"hooks\":{\"SessionStart\":[{\"hooks\":[{\"type\":\"command\",\"command\":\"" + old + "\"}]},"
                 + "{\"hooks\":[{\"type\":\"command\",\"command\":\"" + own + "\"}]}]}}"
        check(ttukttakHooksPresent(inSettings: settings(both)), "both installed")
        // other events and malformed input never count
        check(!ttukttakHooksPresent(inSettings: settings(
            "{\"hooks\":{\"PreToolUse\":[{\"hooks\":[{\"type\":\"command\",\"command\":\"" + own + "\"}]}]}}")), "other event")
        check(!ttukttakHooksPresent(inSettings: settings("{}")), "empty")
        check(!ttukttakHooksPresent(inSettings: settings("{\"hooks\":{\"SessionStart\":\"x\"}}")), "malformed")
        print("  ok    own-hook check: \(n) cases passed")
    }
}
EOF
if swiftc -swift-version 6 Sources/App/ClaudeHookDetection.swift "$tmp/HookIdentityTests.swift" -o "$tmp/t" 2>"$tmp/swiftc.err" && "$tmp/t"; then
  :
else
  echo "  FAIL  unit test did not pass"; tail -5 "$tmp/swiftc.err" 2>/dev/null | sed 's/^/        /'; fail=1
fi

if [ "$fail" = 0 ]; then echo "check-identity: all good"; else echo "check-identity: FAILED" >&2; exit 1; fi
