import SwiftUI
import AVFoundation
import UniformTypeIdentifiers

// ── App 進入點（Swift Playgrounds App 專案會自動產生，若沒有請加這段）──
@main
struct VideoConverterApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}

// MARK: - ContentView

struct ContentView: View {

    @State private var inputURL:    URL?
    @State private var quality      = VideoConverter.Quality.highest
    @State private var converting   = false
    @State private var progress:    Float = 0
    @State private var outputURL:   URL?
    @State private var errorMsg:    String?
    @State private var info:        VideoMeta?
    @State private var showPicker   = false
    @State private var showShare    = false

    private let converter = VideoConverter()

    var body: some View {
        NavigationStack {
            Form {
                // ── 選擇檔案 ──
                Section("來源影片") {
                    Button {
                        showPicker = true
                    } label: {
                        Label(
                            inputURL?.lastPathComponent ?? "點此選擇影片…",
                            systemImage: "folder.badge.plus"
                        )
                        .lineLimit(2)
                    }
                    .disabled(converting)
                }

                // ── 影片資訊 ──
                if let m = info {
                    Section("影片資訊") {
                        LabeledContent("時長",    value: m.duration)
                        LabeledContent("解析度",  value: m.resolution)
                        LabeledContent("原始編碼", value: m.codec)
                        LabeledContent("檔案大小", value: m.size)
                    }
                }

                // ── 畫質選擇 ──
                Section("輸出畫質") {
                    Picker("畫質", selection: $quality) {
                        ForEach(VideoConverter.Quality.allCases) {
                            Text($0.rawValue).tag($0)
                        }
                    }
                    .pickerStyle(.inline)
                    .disabled(converting)
                }

                // ── 轉換進度 ──
                if converting {
                    Section {
                        VStack(spacing: 8) {
                            ProgressView(value: progress)
                            Text("轉換中 \(Int(progress * 100))%")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, 4)
                    }
                }

                // ── 結果 ──
                if let url = outputURL {
                    Section("轉換完成") {
                        Label(url.lastPathComponent, systemImage: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                        Button {
                            showShare = true
                        } label: {
                            Label("分享 / 儲存到相簿或檔案", systemImage: "square.and.arrow.up")
                        }
                    }
                }

                // ── 錯誤 ──
                if let err = errorMsg {
                    Section {
                        Label(err, systemImage: "xmark.circle.fill")
                            .foregroundStyle(.red)
                    }
                }

                // ── 開始按鈕 ──
                Section {
                    Button {
                        startConvert()
                    } label: {
                        HStack {
                            Spacer()
                            Label(
                                converting ? "轉換中…" : "開始轉換為 H.265 MP4",
                                systemImage: converting ? "hourglass" : "arrow.triangle.2.circlepath"
                            )
                            .font(.headline)
                            Spacer()
                        }
                    }
                    .disabled(inputURL == nil || converting)
                }
            }
            .navigationTitle("H.265 轉換器")
            .navigationBarTitleDisplayMode(.large)
        }
        // ── 檔案選擇器 ──
        .sheet(isPresented: $showPicker) {
            VideoPicker { url in
                inputURL = url
                outputURL = nil
                errorMsg = nil
                loadMeta(url)
            }
        }
        // ── 分享 ──
        .sheet(isPresented: $showShare) {
            if let url = outputURL {
                ShareSheet(items: [url])
            }
        }
    }

    // MARK: - Actions

    private func startConvert() {
        guard let url = inputURL else { return }
        converting = true
        progress   = 0
        outputURL  = nil
        errorMsg   = nil

        Task {
            do {
                let out = try await converter.convert(inputURL: url, quality: quality) { p in
                    Task { @MainActor in progress = p }
                }
                await MainActor.run {
                    outputURL  = out
                    converting = false
                }
            } catch {
                await MainActor.run {
                    errorMsg   = error.localizedDescription
                    converting = false
                }
            }
        }
    }

    private func loadMeta(_ url: URL) {
        Task {
            let asset  = AVURLAsset(url: url)
            let dur    = (try? await asset.load(.duration)) ?? .zero
            let tracks = (try? await asset.loadTracks(withMediaType: .video)) ?? []
            let nat    = (try? await tracks.first?.load(.naturalSize)) ?? .zero
            let desc   = (try? await tracks.first?.load(.formatDescriptions))?.first
            let bytes  = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0

            let codec: String = {
                guard let d = desc else { return "未知" }
                let cc = CMFormatDescriptionGetMediaSubType(d)
                let c  = [cc>>24, cc>>16, cc>>8, cc].map {
                    Character(UnicodeScalar(UInt8($0 & 0xFF)))
                }
                return String(c).trimmingCharacters(in: .whitespaces)
            }()

            let m = VideoMeta(
                duration:   fmtTime(dur),
                resolution: nat == .zero ? "未知" : "\(Int(nat.width)) × \(Int(nat.height))",
                codec:      codec,
                size:       fmtSize(bytes)
            )
            await MainActor.run { info = m }
        }
    }

    private func fmtTime(_ t: CMTime) -> String {
        let s = Int(t.seconds); let h = s/3600; let m = (s%3600)/60; let sec = s%60
        return h > 0 ? String(format: "%d:%02d:%02d", h,m,sec) : String(format: "%02d:%02d", m,sec)
    }
    private func fmtSize(_ b: Int) -> String {
        let mb = Double(b)/1_048_576
        return mb >= 1000 ? String(format: "%.1f GB", mb/1024) : String(format: "%.1f MB", mb)
    }
}

// MARK: - VideoMeta

struct VideoMeta {
    let duration, resolution, codec, size: String
}

// MARK: - VideoPicker（支援 Files App 所有影片格式）

struct VideoPicker: UIViewControllerRepresentable {
    let onPick: (URL) -> Void

    // 使用 .movie 涵蓋 iOS 能解碼的全部格式（MOV, MP4, MKV, AVI, WMV…）
    // 加上常見副檔名的 UTType 做補充
    static let types: [UTType] = {
        var t: [UTType] = [.movie, .video, .mpeg4Movie, .quickTimeMovie]
        for ext in ["mkv", "avi", "wmv", "flv", "webm", "ts", "m2ts", "3gp"] {
            if let u = UTType(filenameExtension: ext) { t.append(u) }
        }
        return t
    }()

    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: Self.types)
        picker.delegate = context.coordinator
        picker.allowsMultipleSelection = false
        return picker
    }
    func updateUIViewController(_ vc: UIDocumentPickerViewController, context: Context) {}
    func makeCoordinator() -> Coord { Coord(onPick: onPick) }

    class Coord: NSObject, UIDocumentPickerDelegate {
        let onPick: (URL) -> Void
        init(onPick: @escaping (URL) -> Void) { self.onPick = onPick }

        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            guard let url = urls.first,
                  url.startAccessingSecurityScopedResource() else { return }
            defer { url.stopAccessingSecurityScopedResource() }
            // 複製到 temp，避免沙盒限制
            let tmp = FileManager.default.temporaryDirectory
                        .appendingPathComponent(url.lastPathComponent)
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
    func updateUIViewController(_ vc: UIActivityViewController, context: Context) {}
}
