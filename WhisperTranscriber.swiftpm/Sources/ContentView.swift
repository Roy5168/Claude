import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @EnvironmentObject var service: WhisperService
    @State private var showFileImporter = false
    @State private var importErrorMessage: String?
    @State private var showImportError = false

    var body: some View {
        NavigationSplitView {
            FileSelectionView(showFileImporter: $showFileImporter)
        } detail: {
            detailPane
        }
        .navigationSplitViewStyle(.balanced)
        .fileImporter(
            isPresented: $showFileImporter,
            allowedContentTypes: audioContentTypes,
            allowsMultipleSelection: true
        ) { result in
            switch result {
            case .success(let urls):
                service.addAudioFiles(urls)
            case .failure(let error):
                importErrorMessage = error.localizedDescription
                showImportError = true
            }
        }
        .alert("無法開啟檔案", isPresented: $showImportError) {
            Button("確定", role: .cancel) {}
        } message: {
            Text(importErrorMessage ?? "未知錯誤")
        }
    }

    // MARK: - Detail Pane

    private var detailPane: some View {
        ScrollView {
            VStack(spacing: 24) {
                // App header
                appHeader
                // Model & Language settings
                ModelSettingsView()
                // Transcription results
                TranscriptionView()
            }
            .padding()
        }
        .navigationTitle("語音轉文字")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                modelStatusBadge
            }
        }
    }

    private var appHeader: some View {
        VStack(spacing: 6) {
            HStack(spacing: 10) {
                Image(systemName: "waveform.and.mic")
                    .font(.title)
                    .foregroundStyle(.blue)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Whisper 語音轉文字")
                        .font(.title2.bold())
                    Text("完全離線 · 由 Apple 神經引擎驅動")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
        }
        .padding()
        .background(.blue.opacity(0.07), in: RoundedRectangle(cornerRadius: 14))
    }

    @ViewBuilder
    private var modelStatusBadge: some View {
        switch service.modelLoadState {
        case .ready(let m):
            Label(m.displayName, systemImage: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(.green)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(.green.opacity(0.1), in: Capsule())
        case .loading:
            HStack(spacing: 4) {
                ProgressView().controlSize(.mini)
                Text("載入中")
                    .font(.caption)
            }
        case .notLoaded:
            Label("未載入", systemImage: "cpu")
                .font(.caption)
                .foregroundStyle(.secondary)
        case .failed:
            Label("載入失敗", systemImage: "exclamationmark.circle")
                .font(.caption)
                .foregroundStyle(.red)
        }
    }

    // MARK: - Allowed Audio Types

    private var audioContentTypes: [UTType] {
        var types: [UTType] = [.audio]
        // Explicitly add common audio types for better file picker filtering
        let extras: [UTType] = [
            .mp3,
            .mpeg4Audio,
            .wav,
            .aiff,
            UTType("public.flac") ?? .audio,
            UTType("com.apple.m4a-audio") ?? .mpeg4Audio
        ]
        types.append(contentsOf: extras)
        return types
    }
}
