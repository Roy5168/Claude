import SwiftUI
import AVFoundation
import UniformTypeIdentifiers

// MARK: - App 進入點

@main
struct AudioTrimmerApp: App {
    var body: some Scene {
        WindowGroup { AudioTrimmerView() }
    }
}

// MARK: - ViewModel

@MainActor
final class PlayerVM: ObservableObject {

    @Published var isPlaying   = false
    @Published var currentTime = 0.0
    @Published var duration    = 0.0
    @Published var startTrim   = 0.0
    @Published var endTrim     = 0.0
    @Published var loadError:  String?

    private var player: AVAudioPlayer?
    private var timer:  Timer?

    // 音訊資訊
    @Published var fileName   = ""
    @Published var fileSize   = ""
    @Published var sampleRate = ""

    func load(_ url: URL) {
        stop()
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback)
            try AVAudioSession.sharedInstance().setActive(true)
            player       = try AVAudioPlayer(contentsOf: url)
            player?.prepareToPlay()
            duration     = player?.duration ?? 0
            startTrim    = 0
            endTrim      = duration
            currentTime  = 0
            loadError    = nil

            // 讀取檔案資訊
            fileName     = url.lastPathComponent
            let bytes    = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
            fileSize     = fmtSize(bytes)
            sampleRate   = player.map { "\(Int($0.format.sampleRate)) Hz" } ?? ""
        } catch {
            loadError = error.localizedDescription
        }
    }

    // MARK: 播放控制

    func playPause() {
        isPlaying ? pause() : play()
    }

    func play() {
        guard let player else { return }
        if currentTime >= endTrim { seek(to: startTrim) }
        player.play()
        isPlaying = true
        startTimer()
    }

    func pause() {
        player?.pause()
        isPlaying = false
        stopTimer()
    }

    func stop() {
        player?.stop()
        isPlaying = false
        stopTimer()
        currentTime = 0
    }

    /// 預覽剪輯區段：從 startTrim 播到 endTrim
    func previewTrim() {
        guard player != nil else { return }
        seek(to: startTrim)
        play()
    }

    func seek(to time: Double) {
        let clamped = max(0, min(time, duration))
        player?.currentTime = clamped
        currentTime = clamped
    }

    // MARK: 限制 startTrim / endTrim 不交叉

    func setStart(_ v: Double) {
        startTrim = min(v, endTrim - 0.5)
        if currentTime < startTrim { seek(to: startTrim) }
    }

    func setEnd(_ v: Double) {
        endTrim = max(v, startTrim + 0.5)
    }

    // MARK: Timer

    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { [weak self] _ in
            guard let self else { return }
            Task { @MainActor [weak self] in
                guard let self, let p = self.player else { return }
                self.currentTime = p.currentTime
                if p.isPlaying && p.currentTime >= self.endTrim {
                    p.pause()
                    self.isPlaying = false
                    self.stopTimer()
                }
            }
        }
    }

    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }

    private func fmtSize(_ b: Int) -> String {
        let mb = Double(b) / 1_048_576
        return mb >= 1 ? String(format: "%.1f MB", mb) : String(format: "%d KB", b/1024)
    }
}

// MARK: - 主畫面

struct AudioTrimmerView: View {

    @StateObject private var vm          = PlayerVM()
    @State private var inputURL: URL?
    @State private var showPicker        = false
    @State private var exporting         = false
    @State private var exportProgress:   Float = 0
    @State private var outputURL: URL?
    @State private var exportError:      String?
    @State private var showShare         = false

    private let trimmer = AudioTrimmer()

    var body: some View {
        NavigationStack {
            Form {
                fileSection
                if inputURL != nil {
                    infoSection
                    trimSection
                    playbackSection
                    if exporting  { progressSection }
                    if outputURL != nil { resultSection }
                    if let err = exportError { errorSection(err) }
                    exportButton
                }
            }
            .navigationTitle("音訊剪輯器")
            .navigationBarTitleDisplayMode(.large)
        }
        .sheet(isPresented: $showPicker) {
            AudioFilePicker { url in
                inputURL  = url
                outputURL = nil
                exportError = nil
                vm.load(url)
            }
        }
        .sheet(isPresented: $showShare) {
            if let url = outputURL { ShareSheet(items: [url]) }
        }
    }

    // MARK: - Sections

    private var fileSection: some View {
        Section("來源音檔") {
            Button {
                showPicker = true
            } label: {
                Label(
                    vm.fileName.isEmpty ? "點此選擇 MP3 / M4A 音檔…" : vm.fileName,
                    systemImage: "music.note"
                )
                .lineLimit(2)
            }
            .disabled(exporting)
        }
    }

    private var infoSection: some View {
        Section("檔案資訊") {
            LabeledContent("檔名",   value: vm.fileName)
            LabeledContent("時長",   value: fmtTime(vm.duration))
            LabeledContent("大小",   value: vm.fileSize)
            LabeledContent("取樣率", value: vm.sampleRate)
        }
    }

    private var trimSection: some View {
        Section {
            VStack(spacing: 16) {
                // 視覺化時間軸
                TrimTimeline(
                    duration:    vm.duration,
                    startTrim:   vm.startTrim,
                    endTrim:     vm.endTrim,
                    currentTime: vm.currentTime
                )
                .frame(height: 56)

                // 起點滑桿
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text("起點").font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Text(fmtTime(vm.startTrim)).font(.caption.monospacedDigit()).bold()
                    }
                    Slider(value: Binding(
                        get: { vm.startTrim },
                        set: { vm.setStart($0) }
                    ), in: 0...vm.duration)
                    .tint(.green)
                }

                // 終點滑桿
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text("終點").font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Text(fmtTime(vm.endTrim)).font(.caption.monospacedDigit()).bold()
                    }
                    Slider(value: Binding(
                        get: { vm.endTrim },
                        set: { vm.setEnd($0) }
                    ), in: 0...vm.duration)
                    .tint(.red)
                }

                // 剪輯長度
                HStack {
                    Image(systemName: "scissors")
                    Text("保留長度：\(fmtTime(vm.endTrim - vm.startTrim))")
                        .font(.subheadline.bold())
                        .foregroundStyle(.blue)
                    Spacer()
                }
            }
            .padding(.vertical, 8)
        } header: {
            Text("剪輯區間")
        }
    }

    private var playbackSection: some View {
        Section("播放") {
            VStack(spacing: 12) {
                // 播放進度
                Slider(value: Binding(
                    get: { vm.currentTime },
                    set: { vm.seek(to: $0) }
                ), in: 0...max(vm.duration, 1))
                .tint(.primary)

                HStack {
                    Text(fmtTime(vm.currentTime))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(fmtTime(vm.duration))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }

                // 控制按鈕
                HStack(spacing: 32) {
                    Spacer()

                    // 跳到起點
                    Button { vm.seek(to: vm.startTrim) } label: {
                        Image(systemName: "backward.end.fill")
                            .font(.title2)
                    }

                    // 播放 / 暫停
                    Button { vm.playPause() } label: {
                        Image(systemName: vm.isPlaying ? "pause.circle.fill" : "play.circle.fill")
                            .font(.system(size: 48))
                    }

                    // 預覽剪輯段落
                    Button { vm.previewTrim() } label: {
                        Image(systemName: "scissors.circle.fill")
                            .font(.title2)
                    }
                    .help("預覽剪輯段落")

                    Spacer()
                }
                .buttonStyle(.plain)
                .padding(.vertical, 4)

                Text("✂ 按剪刀圖示可預覽剪輯後的段落")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 4)
        }
    }

    private var progressSection: some View {
        Section {
            VStack(spacing: 8) {
                ProgressView(value: exportProgress)
                Text("匯出中 \(Int(exportProgress * 100))%")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 4)
        }
    }

    private var resultSection: some View {
        Section("匯出完成") {
            if let url = outputURL {
                Label(url.lastPathComponent, systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                Button {
                    showShare = true
                } label: {
                    Label("分享 / 儲存到檔案", systemImage: "square.and.arrow.up")
                }
            }
        }
    }

    private func errorSection(_ msg: String) -> some View {
        Section {
            Label(msg, systemImage: "xmark.circle.fill")
                .foregroundStyle(.red)
        }
    }

    private var exportButton: some View {
        Section {
            Button { startExport() } label: {
                HStack {
                    Spacer()
                    Label(
                        exporting ? "匯出中…" : "匯出剪輯後的音檔",
                        systemImage: exporting ? "hourglass" : "square.and.arrow.down"
                    )
                    .font(.headline)
                    Spacer()
                }
            }
            .disabled(inputURL == nil || exporting || vm.duration == 0)
        }
    }

    // MARK: - Action

    private func startExport() {
        guard let url = inputURL else { return }
        vm.pause()
        exporting       = true
        exportProgress  = 0
        outputURL       = nil
        exportError     = nil

        Task {
            do {
                let out = try await trimmer.trim(
                    inputURL:  url,
                    startTime: vm.startTrim,
                    endTime:   vm.endTrim
                ) { p in
                    Task { @MainActor in exportProgress = p }
                }
                await MainActor.run {
                    outputURL = out
                    exporting = false
                }
            } catch {
                await MainActor.run {
                    exportError = error.localizedDescription
                    exporting   = false
                }
            }
        }
    }

    private func fmtTime(_ t: Double) -> String {
        guard t.isFinite else { return "0:00" }
        let total = Int(t)
        let m = total / 60; let s = total % 60
        let ms = Int((t - Double(total)) * 10)
        return String(format: "%d:%02d.%d", m, s, ms)
    }
}

// MARK: - 視覺化時間軸

struct TrimTimeline: View {
    let duration:    Double
    let startTrim:   Double
    let endTrim:     Double
    let currentTime: Double

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let h = geo.size.height
            let toX = { (t: Double) in CGFloat(t / max(duration, 0.001)) * w }

            ZStack(alignment: .leading) {
                // 背景
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color(.systemGray5))
                    .frame(height: h)

                // 保留區段（藍色）
                Rectangle()
                    .fill(Color.blue.opacity(0.35))
                    .frame(width: max(0, toX(endTrim) - toX(startTrim)), height: h)
                    .offset(x: toX(startTrim))

                // 起點標線（綠）
                Capsule()
                    .fill(Color.green)
                    .frame(width: 3, height: h)
                    .offset(x: toX(startTrim) - 1.5)

                // 終點標線（紅）
                Capsule()
                    .fill(Color.red)
                    .frame(width: 3, height: h)
                    .offset(x: toX(endTrim) - 1.5)

                // 播放頭（白）
                Capsule()
                    .fill(Color.white)
                    .shadow(radius: 1)
                    .frame(width: 2, height: h)
                    .offset(x: toX(currentTime) - 1)

                // 時間刻度（每 10% 一條）
                ForEach(1..<10) { i in
                    Rectangle()
                        .fill(Color(.systemGray3))
                        .frame(width: 1, height: h * 0.4)
                        .offset(x: w * CGFloat(i) / 10)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 6))
            .overlay(
                RoundedRectangle(cornerRadius: 6)
                    .stroke(Color(.systemGray3), lineWidth: 0.5)
            )
        }
    }
}

// MARK: - AudioFilePicker

struct AudioFilePicker: UIViewControllerRepresentable {
    let onPick: (URL) -> Void

    static let types: [UTType] = {
        var t: [UTType] = [.mp3, .mpeg4Audio, .audio, .aiff]
        for ext in ["m4a", "aac", "wav", "flac", "ogg", "opus", "caf", "wma"] {
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

        func documentPicker(_ controller: UIDocumentPickerViewController,
                            didPickDocumentsAt urls: [URL]) {
            guard let url = urls.first,
                  url.startAccessingSecurityScopedResource() else { return }
            defer { url.stopAccessingSecurityScopedResource() }
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
