import SwiftUI
import AppKit

/// The pet in the island: a TimelineView drives a Canvas that draws the pixel pet (PetSprite).
/// PetCues plays its sounds and counts slaps.
struct BotCanvasView: View {
    @ObservedObject var state: AppState
    var particleOverhang: CGFloat = 0
    /// Not drawn while true (e.g. the notch copy while the pet is on the desktop).
    var paused: Bool = false

    @StateObject private var cues = PetCues()
    @StateObject private var pet = PetPlayer()
    @Environment(\.displayScale) private var displayScale

    var body: some View {
        // The pixel pet changes picture a few times a second: 30 fps is plenty.
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: state.mode == .hidden || paused)) { timeline in
            // The Canvas must capture the frame's date, or it is not redrawn.
            let frame = timeline.date
            Canvas { context, size in
                _ = frame
                // Same footprint as the old body: its diameter was 0.6 of the canvas width.
                let cell = PetSprite.cell(fitting: size.width * 0.6, scale: displayScale)
                let center = CGPoint(x: size.width / 2, y: size.height / 2 + particleOverhang / 2)
                PetSprite.draw(pet.frame(), in: context, center: center, cell: cell)
            }
        }
        .onChange(of: state.effectiveState) { _, newState in
            cues.setState(newState)
            pet.show(PetClip(newState))
        }
        #if !APPSTORE
        .onChange(of: state.view) { _, newView in
            // The listening view plays the attentive sound and shows the question face.
            if newView == .listening {
                cues.listen()
                pet.react(.question, for: 1.6)
            }
        }
        #endif
        .onReceive(NotificationCenter.default.publisher(for: .triggerEmote)) { notif in
            if let emote = notif.object as? BotEmote {
                cues.emote(emote)
                pet.react(PetClip(reaction: emote), for: 1.6)
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .triggerSlap)) { _ in
            cues.slap()
            pet.react(.error, for: 0.6)
        }
        .onReceive(NotificationCenter.default.publisher(for: .botGreet)) { _ in
            cues.greet()
            pet.react(.petted, for: 1.4)
        }
        .onReceive(NotificationCenter.default.publisher(for: .botGulp)) { _ in
            // A file dropped on the pet: "뚝딱", coins.
            pet.react(.finished, for: 1.2)
        }
        .onAppear {
            cues.setState(state.effectiveState)
            // Naps after 90 s of idle; "petNapSeconds" in the app's defaults changes it (the demo uses a few seconds).
            pet.napAfter = UserDefaults.standard.object(forKey: "petNapSeconds") as? Double ?? 90
            pet.show(PetClip(state.effectiveState), restart: true)
        }
    }
}

extension PetClip {
    /// The pet's short reaction to one of the old emotes.
    init(reaction emote: BotEmote) {
        switch emote {
        case .love, .happy, .proud, .wink: self = .petted
        case .surprised:                   self = .approval
        case .yawn:                        self = .sleeping
        case .annoyed:                     self = .error
        case .listening:                   self = .question
        }
    }
}

/// Small pet (agent pills, the 2×2 grid next to the notch). Its fur takes the task's colour,
/// so sessions and integrations stay easy to tell apart.
struct MiniBotCanvasView: View {
    let task: AgentTask
    var isDancing: Bool = false
    @StateObject private var pet = PetPlayer()

    @Environment(\.islandViewActive) private var viewActive
    @Environment(\.displayScale) private var displayScale

    var body: some View {
        let colors = PetSprite.palette(tint: task.color)
        // Paused in island views that are not shown.
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: !viewActive)) { timeline in
            let frame = timeline.date   // see BotCanvasView: redraw on every tick
            Canvas { context, size in
                _ = frame
                let cell = PetSprite.cell(fitting: size.width * 0.6, scale: displayScale)
                PetSprite.draw(pet.frame(), in: context,
                               center: CGPoint(x: size.width / 2, y: size.height / 2),
                               cell: cell, colors: colors)
            }
        }
        .onChange(of: task.state) { _, newState in
            pet.show(PetClip(newState))
        }
        .onAppear {
            pet.show(PetClip(task.state), restart: true)
        }
    }
}
