import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @EnvironmentObject var store: TranscriptionStore

    var body: some View {
        HStack(spacing: 0) {
            ControlPanel()
                .frame(width: 280)
                .padding()
                .background(Color(.systemGroupedBackground))

            Divider()

            OutputPanel()
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .navigationTitle("Speech to Text")
        .alert("Error", isPresented: Binding(
            get: { store.errorMessage != nil },
            set: { if !$0 { store.errorMessage = nil } }
        )) {
            Button("OK") { store.errorMessage = nil }
        } message: {
            Text(store.errorMessage ?? "")
        }
        .fileImporter(
            isPresented: $store.showFilePicker,
            allowedContentTypes: [.audio, .mpeg4Audio, .wav, .aiff, .mp3],
            allowsMultipleSelection: false
        ) { result in
            switch result {
            case .success(let urls):
                guard let url = urls.first else { return }
                let accessed = url.startAccessingSecurityScopedResource()
                defer { if accessed { url.stopAccessingSecurityScopedResource() } }
                store.setAudioFile(url: url)
            case .failure(let error):
                store.errorMessage = error.localizedDescription
            }
        }
        .fileExporter(
            isPresented: $store.showExporter,
            document: TranscriptionDocument(store.exportContent()),
            contentType: store.outputFormat == .txt ? .plainText : .plainText,
            defaultFilename: defaultExportName
        ) { result in
            if case .failure(let error) = result {
                store.errorMessage = error.localizedDescription
            }
        }
    }

    private var defaultExportName: String {
        let base = store.selectedAudioName
            .components(separatedBy: ".").dropLast().joined(separator: ".")
        let name = base.isEmpty ? "transcription" : base
        return "\(name).\(store.outputFormat.rawValue.lowercased())"
    }
}

// MARK: - Control Panel (left column)

private struct ControlPanel: View {
    @EnvironmentObject var store: TranscriptionStore

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Speech to Text")
                .font(.title2.bold())

            // Audio file section
            GroupBox("Audio File") {
                VStack(alignment: .leading, spacing: 8) {
                    Button {
                        store.showFilePicker = true
                    } label: {
                        Label("Select File", systemImage: "waveform.circle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)

                    if !store.selectedAudioName.isEmpty {
                        Label(store.selectedAudioName, systemImage: "music.note")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                }
                .padding(.top, 4)
            }

            // Model section
            GroupBox("Whisper Model") {
                Picker("Model", selection: $store.selectedModel) {
                    ForEach(TranscriptionStore.availableModels, id: \.identifier) { item in
                        Text(item.display).tag(item.identifier)
                    }
                }
                .pickerStyle(.menu)
                .labelsHidden()
            }

            // Language section
            GroupBox("Language") {
                Picker("Language", selection: $store.selectedLanguage) {
                    ForEach(TranscriptionStore.languageOptions, id: \.code) { item in
                        Text(item.display).tag(item.code)
                    }
                }
                .pickerStyle(.menu)
                .labelsHidden()
            }

            // Output format section
            GroupBox("Output Format") {
                Picker("Format", selection: $store.outputFormat) {
                    ForEach(OutputFormat.allCases) { format in
                        Text(format.rawValue).tag(format)
                    }
                }
                .pickerStyle(.segmented)
                .labelsHidden()
            }

            // Transcribe button
            Button {
                Task { await store.transcribe() }
            } label: {
                HStack {
                    if store.isTranscribing {
                        ProgressView().controlSize(.small)
                    } else {
                        Image(systemName: "play.fill")
                    }
                    Text(store.isTranscribing ? "Transcribing…" : "Transcribe")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(store.selectedAudioURL == nil || store.isTranscribing)

            // Status message
            Text(store.statusMessage)
                .font(.caption)
                .foregroundStyle(.secondary)

            Spacer()
        }
    }
}

// MARK: - Output Panel (right column)

private struct OutputPanel: View {
    @EnvironmentObject var store: TranscriptionStore

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Transcription")
                    .font(.headline)
                Spacer()
                if !store.transcriptionText.isEmpty {
                    Button {
                        store.showExporter = true
                    } label: {
                        Label("Export", systemImage: "square.and.arrow.down")
                    }
                    .buttonStyle(.bordered)
                }
            }

            if store.transcriptionText.isEmpty {
                Spacer()
                VStack(spacing: 12) {
                    Image(systemName: "waveform.and.mic")
                        .font(.system(size: 48))
                        .foregroundStyle(.tertiary)
                    Text(store.isTranscribing
                         ? store.statusMessage
                         : "Select an audio file and press Transcribe")
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
                Spacer()
            } else {
                ScrollView {
                    Text(store.transcriptionText)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                }
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }
    }
}

// MARK: - UTType extensions for audio

extension UTType {
    static let mp3 = UTType("public.mp3") ?? .audio
    static let wav = UTType("public.wav") ?? .audio
}
