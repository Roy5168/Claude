import Foundation
import WhisperKit

@MainActor
class WhisperService: ObservableObject {

    // MARK: - Settings (bound to UI)
    @Published var selectedModel: WhisperModel = .base
    @Published var selectedLanguage: WhisperLanguage = .autoDetect
    @Published var selectedFormats: Set<OutputFormat> = [.txt, .srt]

    // MARK: - State
    @Published var modelLoadState: ModelLoadState = .notLoaded
    @Published var jobs: [TranscriptionJob] = []
    @Published var isTranscribing = false

    private var whisperKit: WhisperKit?

    // MARK: - Computed

    var canTranscribe: Bool {
        modelLoadState.isReady && !jobs.isEmpty && !isTranscribing
    }

    var pendingCount: Int {
        jobs.filter { $0.status.isPending }.count
    }

    // MARK: - Model Loading

    func loadModel(_ model: WhisperModel) async {
        guard !modelLoadState.isLoading else { return }
        modelLoadState = .loading
        whisperKit = nil
        do {
            // WhisperKit automatically downloads the CoreML model from Hugging Face
            // if not already cached on device, then loads it into the Neural Engine.
            let kit = try await WhisperKit(model: model.modelId, verbose: false)
            whisperKit = kit
            modelLoadState = .ready(model)
        } catch {
            modelLoadState = .failed(error.localizedDescription)
        }
    }

    // MARK: - File Management

    func addAudioFiles(_ urls: [URL]) {
        let uniqueURLs = urls.filter { url in
            !jobs.contains { $0.audioURL == url }
        }
        let newJobs = uniqueURLs.map { url -> TranscriptionJob in
            // Maintain security-scoped access for the lifetime of the job
            _ = url.startAccessingSecurityScopedResource()
            return TranscriptionJob(audioURL: url)
        }
        jobs.append(contentsOf: newJobs)
    }

    func removeJobs(at offsets: IndexSet) {
        for idx in offsets {
            jobs[idx].audioURL.stopAccessingSecurityScopedResource()
        }
        jobs.remove(atOffsets: offsets)
    }

    func clearAllJobs() {
        jobs.forEach { $0.audioURL.stopAccessingSecurityScopedResource() }
        jobs.removeAll()
    }

    func resetJob(id: UUID) {
        guard let idx = jobs.firstIndex(where: { $0.id == id }) else { return }
        jobs[idx].status = .pending
        jobs[idx].fullText = ""
        jobs[idx].segments = []
    }

    // MARK: - Transcription

    func transcribeAll() async {
        guard let whisperKit else { return }
        isTranscribing = true
        defer { isTranscribing = false }

        let langCode: String? = selectedLanguage.id == "auto" ? nil : selectedLanguage.id
        let options = DecodingOptions(task: .transcribe, language: langCode)

        for i in jobs.indices {
            guard jobs[i].status.isPending else { continue }

            jobs[i].status = .transcribing

            do {
                let audioPath = jobs[i].audioURL.path(percentEncoded: false)
                let results = try await whisperKit.transcribe(
                    audioPath: audioPath,
                    decodeOptions: options
                )

                guard let result = results.first else {
                    jobs[i].status = .failed("未取得轉錄結果")
                    continue
                }

                jobs[i].fullText = result.text.trimmingCharacters(in: .whitespacesAndNewlines)
                jobs[i].segments = result.segments.map {
                    SegmentData(start: $0.start, end: $0.end, text: $0.text)
                }
                jobs[i].status = .completed

            } catch {
                jobs[i].status = .failed(error.localizedDescription)
            }
        }
    }
}
