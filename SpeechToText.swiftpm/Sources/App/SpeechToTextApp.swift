import SwiftUI

@main
struct SpeechToTextApp: App {
    @StateObject private var store = TranscriptionStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
        }
    }
}
