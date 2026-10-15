import Foundation

// Stand-in for Voice/VoiceBrain.swift when building without Xcode:
// the Command Line Tools ship FoundationModels but not its macro plugin.
// Every call reports "no local model", so callers fall back to IntentParser.
enum LocalModelStatus {
    case available
    case notMacOS26
    case appleIntelligenceOff
}

struct BrainResult {
    let intents: [VoiceIntent]
    let text: String
}

@MainActor
final class VoiceBrain {
    static let shared = VoiceBrain()
    private(set) var modelStatus: LocalModelStatus = .notMacOS26
    private init() {}
    func beginConversation() {}
    func endConversation() {}
    func prewarmSession() {}
    var isSessionReady: Bool { false }
    func resolve(_ transcript: String, pills: [PillDefinition]) async -> BrainResult? { nil }
    func resolveWithStreaming(
        _ transcript: String,
        pills: [PillDefinition],
        onSentence: @escaping @MainActor (_ sentence: String, _ hasActions: Bool) -> Void
    ) async -> BrainResult? { nil }
    static func draftMail(to recipient: String, about instruction: String) async -> String? { nil }
}
