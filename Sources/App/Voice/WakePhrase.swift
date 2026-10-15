import Foundation

// MARK: - WakePhrase
// Pure functions — no Speech or AVFoundation dependencies.
// Compiled into both the app and standalone test scripts.

enum WakePhrase {

    // MARK: - Public API

    struct SplitResult {
        let matched: Bool
        /// Words after the LAST wake phrase occurrence, extracted from the **original** transcript
        /// (original casing, apostrophes, hyphens, accents preserved).
        /// Leading punctuation on the first word is stripped.
        let command: String
    }

    /// Scans `raw` for a wake phrase at a word boundary (anywhere in the transcript,
    /// not just the start). Returns the text following the **last** occurrence as the command,
    /// preserving the original casing and punctuation of the command portion.
    ///
    /// Accepted patterns (case-insensitive, after phonetic normalisation):
    /// - "ok ttukttak" and what an English or French recognizer writes for it:
    ///   "okay tuk tuk", "ok took tak", "OK tuk-tuk", "ok touk touk" …
    /// - "hey ttukttak"
    ///
    /// Word-boundary search means "euh ok tuk tuk add" matches and returns "add".
    /// The name alone never matches (no preceding "ok"/"hey").
    static func split(_ raw: String) -> SplitResult {
        // Split original into whitespace-separated tokens (punctuation stays attached to words)
        let originalWords = raw.components(separatedBy: .whitespaces).filter { !$0.isEmpty }
        guard !originalWords.isEmpty else { return SplitResult(matched: false, command: "") }

        // Normalise each word independently for wake-phrase matching only
        let normWords = originalWords.map(normWord)

        // Wake phrase patterns (normalised).
        // "ok ttuk ttak" is a 3-token pattern: the STT often writes the name as two words.
        let patterns: [[String]] = [
            ["ok",  "ttukttak"],
            ["ok",  "ttuk", "ttuk"],
            ["hey", "ttukttak"],
            ["hey", "ttuk", "ttuk"],
        ]

        // Find LAST occurrence of any pattern
        var lastMatchEnd: Int? = nil   // word index immediately after the matched pattern

        for pattern in patterns {
            guard normWords.count >= pattern.count else { continue }
            var i = 0
            while i <= normWords.count - pattern.count {
                if Array(normWords[i ..< i + pattern.count]) == pattern {
                    let end = i + pattern.count
                    if lastMatchEnd == nil || end > lastMatchEnd! { lastMatchEnd = end }
                    i = end   // resume search after this match
                } else {
                    i += 1
                }
            }
        }

        guard let end = lastMatchEnd else { return SplitResult(matched: false, command: "") }

        let tail = Array(originalWords[end...])
        guard !tail.isEmpty else { return SplitResult(matched: true, command: "") }

        // Strip leading punctuation from the first command word
        var first = tail[0]
        while let c = first.first, !c.isLetter && !c.isNumber { first = String(first.dropFirst()) }

        let parts = ([first] + Array(tail.dropFirst())).filter { !$0.isEmpty }
        return SplitResult(matched: true, command: parts.joined(separator: " "))
    }

    /// Normalise a string for cancel-phrase comparison: lowercase + strip punctuation.
    static func normalise(_ s: String) -> String {
        s.lowercased()
         .components(separatedBy: .punctuationCharacters)
         .joined()
         .trimmingCharacters(in: .whitespaces)
    }

    // MARK: - Private

    /// One syllable of the name as a recognizer spells it: tuk, ttuk, took, touk, tuck,
    /// tak, ttak, tack, tac, tok … (t or tt, a short vowel, k / ck / c).
    private static let syllable = "t{1,2}(?:u|oo|ou|a|o)(?:ck|k|c)"
    private static let oneSyllable = try! NSRegularExpression(pattern: "^\(syllable)$")
    private static let twoSyllables = try! NSRegularExpression(pattern: "^\(syllable)\(syllable)$")

    private static func matches(_ re: NSRegularExpression, _ t: String) -> Bool {
        re.firstMatch(in: t, range: NSRange(t.startIndex..., in: t)) != nil
    }

    /// True for a word that sounds like the name, or half of it (diagnostics: "heard
    /// something name-like but not the whole wake phrase").
    static func isNameLike(_ word: String) -> Bool {
        let t = normalise(word)
        return matches(twoSyllables, t) || matches(oneSyllable, t)
    }

    /// Normalise a single word token for wake-phrase matching: the whole name
    /// ("tuktuk", "tuk-tuk", "ttukttak") becomes "ttukttak", one syllable becomes "ttuk".
    private static func normWord(_ w: String) -> String {
        let t = normalise(w)
        if t == "okay" { return "ok" }
        if matches(twoSyllables, t) { return "ttukttak" }
        if matches(oneSyllable, t) { return "ttuk" }
        return t
    }
}
