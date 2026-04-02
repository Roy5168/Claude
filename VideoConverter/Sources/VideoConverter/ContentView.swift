import SwiftUI
import AVFoundation
import UniformTypeIdentifiers

struct ContentView: View {

    // MARK: - State
    @State private var selectedFileURL: URL?
    @State private var selectedQuality: VideoConverter.Quality = .highest
    @State private var isConverting   = false
    @State private var progress: Float = 0
    @State private var resultURL: URL?
    @State private var errorMessage: String?
    @State private var showFilePicker  = false
    @State private var showShareSheet  = false
    @State private var videoInfo: VideoInfo?

    private let converter = VideoConverter()

    // MARK: - Body
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    headerView
                    filePickerSection
                    if videoInfo != nil { videoInfoSection }
                    qualitySection
                    if isConverting { progressSection }
                    if let url = resultURL { resultSection(url: url) }
                    if let err = errorMessage { errorSection(err) }
                    convertButton
                }
                .padding()
            }
            .navigationTitle("H.265 影片轉換器")
            .navigationBarTitleDisplayMode(.large)
        }
        .sheet(isPresented: $showFilePicker) {
            DocumentPicker(
                allowedTypes: [.movie, .video, .mpeg4Movie,
                               UTType(filenameExtension: "mkv")!,
                               UTType(filenameExtension: "avi")!,
                               UTType(filenameExtension: "wmv")!,
                               UTType(filenameExtension: "flv")!,
                               UTType(filenameExtension: "mov")!].compactMap { $0 }
            ) { url in
                selectedFileURL = url
                resultURL = nil
                errorMessage = nil
                loadVideoInfo(url: url)
            }
        }
        .sheet(isPresented: $showShareSheet) {
            if let url = resultURL {
                ShareSheet(items: [url])
            }
        }
    }

    // MARK: - Subviews

    private var headerView: some View {
        VStack(spacing: 8) {
            Image(systemName: "film.stack")
                .font(.system(size: 56))
                .foregroundStyle(.blue.gradient)
            Text("支援 MOV、MKV、AVI、WMV、FLV 等格式")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top)
    }

    private var filePickerSection: some View {
        GroupBox {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("來源影片")
                        .font(.headline)
                    Text(selectedFileURL?.lastPathComponent ?? "尚未選擇檔案")
                        .font(.subheadline)
                        .foregroundStyle(selectedFileURL == nil ? .secondary : .primary)
                        .lineLimit(2)
                }
                Spacer()
                Button {
                    showFilePicker = true
                } label: {
                    Label("選擇", systemImage: "folder.badge.plus")
                        .font(.subheadline.bold())
                }
                .buttonStyle(.bordered)
                .disabled(isConverting)
            }
        }
    }

    @ViewBuilder
    private var videoInfoSection: some View {
        if let info = videoInfo {
            GroupBox("影片資訊") {
                Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 8) {
                    infoRow("時長",    info.duration)
                    infoRow("解析度",  info.resolution)
                    infoRow("原始編碼", info.codec)
                    infoRow("檔案大小", info.fileSize)
                }
                .font(.subheadline)
            }
        }
    }

    private func infoRow(_ label: String, _ value: String) -> some View {
        GridRow {
            Text(label).foregroundStyle(.secondary)
            Text(value).bold()
        }
    }

    private var qualitySection: some View {
        GroupBox("輸出畫質") {
            Picker("畫質", selection: $selectedQuality) {
                ForEach(VideoConverter.Quality.allCases) { q in
                    Text(q.rawValue).tag(q)
                }
            }
            .pickerStyle(.wheel)
            .frame(height: 120)
            .disabled(isConverting)
        }
    }

    private var progressSection: some View {
        GroupBox {
            VStack(spacing: 12) {
                HStack {
                    ProgressView()
                    Text("轉換中，請稍候...")
                        .font(.subheadline)
                }
                ProgressView(value: progress)
                    .progressViewStyle(.linear)
                Text("\(Int(progress * 100))%")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func resultSection(url: URL) -> some View {
        GroupBox {
            VStack(spacing: 12) {
                Label("轉換完成！", systemImage: "checkmark.circle.fill")
                    .font(.headline)
                    .foregroundStyle(.green)
                Text(url.lastPathComponent)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                HStack(spacing: 16) {
                    Button {
                        showShareSheet = true
                    } label: {
                        Label("分享 / 儲存", systemImage: "square.and.arrow.up")
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
            .padding(.vertical, 4)
        }
    }

    private func errorSection(_ message: String) -> some View {
        GroupBox {
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .foregroundStyle(.red)
                .font(.subheadline)
        }
    }

    private var convertButton: some View {
        Button {
            startConversion()
        } label: {
            Label(isConverting ? "轉換中..." : "開始轉換為 H.265 MP4",
                  systemImage: isConverting ? "hourglass" : "arrow.triangle.2.circlepath")
                .frame(maxWidth: .infinity)
                .font(.headline)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
        .disabled(selectedFileURL == nil || isConverting)
    }

    // MARK: - Actions

    private func startConversion() {
        guard let url = selectedFileURL else { return }
        isConverting  = true
        progress      = 0
        resultURL     = nil
        errorMessage  = nil

        Task {
            do {
                let output = try await converter.convert(
                    inputURL: url,
                    quality: selectedQuality
                ) { p in
                    Task { @MainActor in
                        self.progress = p
                    }
                }
                await MainActor.run {
                    resultURL   = output
                    isConverting = false
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    isConverting = false
                }
            }
        }
    }

    private func loadVideoInfo(url: URL) {
        Task {
            let asset = AVURLAsset(url: url)
            async let durationLoad  = asset.load(.duration)
            async let tracksLoad    = asset.loadTracks(withMediaType: .video)

            let duration = (try? await durationLoad) ?? .zero
            let tracks   = (try? await tracksLoad) ?? []
            let size     = (try? await tracks.first?.load(.naturalSize)) ?? .zero
            let desc     = (try? await tracks.first?.load(.formatDescriptions))?.first
            let codecStr = desc.map { formatCodecName($0) } ?? "未知"
            let fileSize = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0

            let info = VideoInfo(
                duration:   formatDuration(duration),
                resolution: size == .zero ? "未知" : "\(Int(size.width)) × \(Int(size.height))",
                codec:      codecStr,
                fileSize:   formatFileSize(fileSize)
            )
            await MainActor.run { videoInfo = info }
        }
    }

    // MARK: - Helpers

    private func formatDuration(_ time: CMTime) -> String {
        let total = Int(time.seconds)
        let h = total / 3600
        let m = (total % 3600) / 60
        let s = total % 60
        return h > 0 ? String(format: "%d:%02d:%02d", h, m, s)
                     : String(format: "%02d:%02d", m, s)
    }

    private func formatFileSize(_ bytes: Int) -> String {
        let mb = Double(bytes) / 1_048_576
        return mb >= 1000 ? String(format: "%.1f GB", mb / 1024)
                          : String(format: "%.1f MB", mb)
    }

    private func formatCodecName(_ desc: CMFormatDescription) -> String {
        let fourCC = CMFormatDescriptionGetMediaSubType(desc)
        let chars  = [
            Character(UnicodeScalar((fourCC >> 24) & 0xFF)!),
            Character(UnicodeScalar((fourCC >> 16) & 0xFF)!),
            Character(UnicodeScalar((fourCC >>  8) & 0xFF)!),
            Character(UnicodeScalar( fourCC        & 0xFF)!)
        ]
        return String(chars).trimmingCharacters(in: .whitespaces)
    }
}

// MARK: - VideoInfo

struct VideoInfo {
    let duration: String
    let resolution: String
    let codec: String
    let fileSize: String
}

// MARK: - DocumentPicker

struct DocumentPicker: UIViewControllerRepresentable {
    let allowedTypes: [UTType]
    let onPick: (URL) -> Void

    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: allowedTypes)
        picker.delegate = context.coordinator
        picker.allowsMultipleSelection = false
        return picker
    }

    func updateUIViewController(_ uiViewController: UIDocumentPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(onPick: onPick) }

    class Coordinator: NSObject, UIDocumentPickerDelegate {
        let onPick: (URL) -> Void
        init(onPick: @escaping (URL) -> Void) { self.onPick = onPick }

        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            guard let url = urls.first else { return }
            // 取得安全存取授權
            guard url.startAccessingSecurityScopedResource() else { return }
            // 複製到 temp，釋放 scoped access
            defer { url.stopAccessingSecurityScopedResource() }
            let tmp = FileManager.default.temporaryDirectory.appendingPathComponent(url.lastPathComponent)
            try? FileManager.default.removeItem(at: tmp)
            try? FileManager.default.copyItem(at: url, to: tmp)
            onPick(tmp)
        }
    }
}

// MARK: - ShareSheet

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
