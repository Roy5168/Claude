import Foundation
import WhisperKit

enum OutputFormat: String, CaseIterable, Identifiable {
    case txt = "TXT"
    case srt = "SRT"
    var id: String { rawValue }
}

@MainActor
final class TranscriptionStore: ObservableObject {

    // MARK: - Input State
    @Published var selectedAudioURL: URL?
    @Published var selectedAudioName: String = ""
    @Published var selectedModel: String = "openai_whisper-base"
    @Published var selectedLanguage: String = "auto"
    @Published var outputFormat: OutputFormat = .txt

    // MARK: - Output State
    @Published var transcriptionText: String = ""
    @Published var segments: [TranscriptionSegment] = []

    // MARK: - UI State
    @Published var isTranscribing: Bool = false
    @Published var statusMessage: String = "Ready"
    @Published var errorMessage: String?
    @Published var showFilePicker: Bool = false
    @Published var showExporter: Bool = false

    // MARK: - Private
    private var whisperKit: WhisperKit?
    private var loadedModelName: String?

    // MARK: - Constants

    static let availableModels: [(display: String, identifier: String)] = [
        ("Tiny (~75 MB)",     "openai_whisper-tiny"),
        ("Base (~150 MB)",    "openai_whisper-base"),
        ("Small (~500 MB)",   "openai_whisper-small"),
        ("Medium (~1.5 GB)",  "openai_whisper-medium"),
        ("Large v2 (~3 GB)", "openai_whisper-large-v2"),
        ("Large v3 (~3 GB)", "openai_whisper-large-v3"),
    ]

    static let languageOptions: [(display: String, code: String)] = [
        ("Auto Detect", "auto"),
        ("English",     "en"),
        ("Chinese",     "zh"),
        ("Japanese",    "ja"),
        ("Korean",      "ko"),
        ("French",      "fr"),
        ("German",      "de"),
        ("Spanish",     "es"),
    ]

    // MARK: - Actions

    func setAudioFile(url: URL) {
        // Copy to temp dir so security-scoped access is no longer needed during transcription
        let dest = FileManager.default.temporaryDirectory
            .appendingPathComponent(url.lastPathComponent)
        try? FileManager.default.removeItem(at: dest)
        do {
            try FileManager.default.copyItem(at: url, to: dest)
            selectedAudioURL = dest
            selectedAudioName = url.lastPathComponent
            transcriptionText = ""
            segments = []
            statusMessage = "Ready"
            errorMessage = nil
        } catch {
            errorMessage = "Failed to load file: \(error.localizedDescription)"
        }
    }

    func transcribe() async {
        guard let audioURL = selectedAudioURL else {
            errorMessage = "Please select an audio file first."
            return
        }
        guard !isTranscribing else { return }

        isTranscribing = true
        errorMessage = nil
        transcriptionText = ""
        segments = []

        defer { isTranscribing = false }

        do {
            // Load model (re-use cached instance if model hasn't changed)
            if whisperKit == nil || loadedModelName != selectedModel {
                whisperKit = nil
                loadedModelName = nil
                statusMessage = "Loading model \(selectedModel)…"
                let pipe = try await WhisperKit(model: selectedModel)
                whisperKit = pipe
                loadedModelName = selectedModel
            }

            guard let pipe = whisperKit else { return }

            statusMessage = "Transcribing…"

            var options = DecodingOptions()
            if selectedLanguage != "auto" {
                options.language = selectedLanguage
            }

            let results = try await pipe.transcribe(
                audioPath: audioURL.path,
                decodeOptions: options
            )

            let allSegments = results.flatMap { $0.segments }
            let fullText = results.map { $0.text.trimmingCharacters(in: .whitespacesAndNewlines) }
                .joined(separator: "\n")

            segments = allSegments
            transcriptionText = fullText
            statusMessage = "Done — \(allSegments.count) segment(s)"

        } catch {
            errorMessage = error.localizedDescription
            statusMessage = "Error"
        }
    }

    func exportContent() -> String {
        switch outputFormat {
        case .txt:
            return transcriptionText
        case .srt:
            return SRTFormatter.format(segments: segments)
        }
    }
}
