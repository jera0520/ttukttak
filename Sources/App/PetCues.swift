import Foundation
import QuartzCore

/// What the pet does besides drawing: its sounds and the slap → dizzy count.
/// The pet itself is drawn by PetSprite / PetPlayer.
@MainActor
final class PetCues: ObservableObject {
    /// The state on screen; a dizzy pet ignores slaps.
    private(set) var state: BotState = .idle
    private var slapTimes: [CFTimeInterval] = []
    /// Bumped to cancel a greeting sound that has not played yet.
    private var greetToken = 0

    func setState(_ newState: BotState) {
        state = newState
    }

    /// A slap: "slap", then "annoyed" — or, on the third slap within 1.7 s, the dizzy spell
    /// (.botDizzy; IslandWindowController shows it and recovers).
    func slap() {
        greetToken += 1   // a slap cuts the greeting short
        guard state != .dizzy else { return }
        let now = CACurrentMediaTime()
        slapTimes = slapTimes.filter { now - $0 < 1.7 }
        slapTimes.append(now)
        SoundEngine.shared.play("slap")
        if slapTimes.count >= 3 {
            slapTimes = []
            NotificationCenter.default.post(name: .botDizzy, object: nil)
        } else {
            playAnnoyed()
        }
    }

    /// The greeting sound, a quarter of a second in.
    func greet() {
        greetToken += 1
        let token = greetToken
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { [weak self] in
            guard let self, self.greetToken == token else { return }
            SoundEngine.shared.play("greet")
        }
    }

    /// The listening view opens: the attentive sound.
    func listen() {
        greetToken += 1
        SoundEngine.shared.play("question")
    }

    /// Of the emotes, only "annoyed" makes a sound.
    func emote(_ emote: BotEmote) {
        if emote == .annoyed { playAnnoyed() }
    }

    private func playAnnoyed() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.06) {
            SoundEngine.shared.play("annoyed")
        }
    }
}
