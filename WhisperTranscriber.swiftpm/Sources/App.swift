import SwiftUI

@main
struct WhisperTranscriberApp: App {
    @StateObject private var whisperService = WhisperService()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(whisperService)
        }
    }
}
