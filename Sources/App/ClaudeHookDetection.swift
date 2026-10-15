import Foundation

/// True when a parsed ~/.claude/settings.json routes Claude Code SessionStart events to this app.
///
/// Kept free of file access so it can be tested on fixtures instead of the real settings file.
/// The match is on the command text "tt-hook": a hook written by this app runs
/// .../Application Support/Ttukttak/tt-hook (App Store build: ~/.claude/ttukttak/tt-hook).
/// A hook written by Coucou (nb-hook / NotchBuddy) never matches, and the other way round.
func ttukttakHooksPresent(inSettings settings: [String: Any]) -> Bool {
    guard let hooks = settings["hooks"] as? [String: Any],
          let sessionStart = hooks["SessionStart"] as? [[String: Any]] else { return false }
    return sessionStart.contains { group in
        (group["hooks"] as? [[String: Any]])?.contains { hook in
            guard let command = hook["command"] as? String else { return false }
            return command.contains("tt-hook")
        } ?? false
    }
}
