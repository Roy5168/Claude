import SwiftUI
import AVFoundation
import UniformTypeIdentifiers

// MARK: - App 進入點

@main
struct VideoConverterApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}

// MARK: - 轉換工作項目

struct ConversionItem: Identifiable {
    let id    = UUID()
    let url:  URL
    var name: String { url.lastPathComponent }

    enum Status { case pending, converting, done, failed }
    var status:    Status = .pending
    var progress:  Float  = 0
    var outputURL: URL?   = nil
    var errorMsg:  String? = nil
}

// MARK: - ContentView

struct ContentView: View {

    @State private var items:      [ConversionItem] = []
    @State private var quality     = VideoConverter.Quality.highest
    @State private var isRunning   = false
    @State private var showPicker  = false
    @State private var showShare   = false
    @State private var showDoneAlert = false

    private let converter = VideoConverter()

    // 全部完成（無 pending / converting）
    private var allDone: Bool {
        !items.isEmpty && items.allSatisfy { $0.status == .done || $0.status == .failed }
    }
    // 整體進度（完成檔數 / 總檔數）
    private var overallProgress: Float {
        guard !items.isEmpty else { return 0 }
        let total = items.reduce(Float(0)) { $0 + $1.progress }
        return total / Float(items.count)
    }
    // 成功的輸出 URL 清單（供分享全部）
    private var doneURLs: [URL] { items.compactMap(\.outputURL) }

    var body: some View {
        NavigationStack {
            Form {
                fileListSection
                qualitySection
                if isRunning  { overallProgressSection }
                if !items.isEmpty { itemListSection }
                if allDone    { completionSection }
                actionButtons
            }
            .navigationTitle("H.265 批次轉換器")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                if !items.isEmpty && !isRunning {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("清除全部", role: .destructive) {
                            items = []
                        }
                    }
                }
            }
        }
        .sheet(isPresented: $showPicker) {
            VideoPicker { urls in
                let new = urls.filter { newURL in
                    !items.contains { $0.url.lastPathComponent == newURL.lastPathComponent }
                }
                items += new.map { ConversionItem(url: $0) }
            }
        }
        .sheet(isPresented: $showShare) {
            ShareSheet(items: doneURLs)
        }
        .alert("全部轉換完成！", isPresented: $showDoneAlert) {
            Button("分享全部") { showShare = true }
            Button("完成", role: .cancel) { resetAll() }
        } message: {
            let ok  = items.filter { $0.status == .done }.count
            let err = items.filter { $0.status == .failed }.count
            Text("成功 \(ok) 個，失敗 \(err) 個")
        }
    }

    // MARK: - Sections

    private var fileListSection: some View {
        Section {
            Button {
                showPicker = true
            } label: {
                Label("新增影片（可多選）", systemImage: "plus.circle.fill")
                    .font(.subheadline.bold())
            }
            .disabled(isRunning)

            if items.isEmpty {
                Text("尚未選擇任何影片")
                    .foregroundStyle(.secondary)
                    .font(.subheadline)
            } else {
                Text("已加入 \(items.count) 個影片")
                    .foregroundStyle(.secondary)
                    .font(.subheadline)
            }
        } header: {
            Text("來源影片")
        }
    }

    private var qualitySection: some View {
        Section("輸出畫質") {
            Picker("畫質", selection: $quality) {
                ForEach(VideoConverter.Quality.allCases) {
                    Text($0.rawValue).tag($0)
                }
            }
            .pickerStyle(.inline)
            .disabled(isRunning)
        }
    }

    private var overallProgressSection: some View {
        Section {
            VStack(spacing: 8) {
                let done = items.filter { $0.status == .done || $0.status == .failed }.count
                HStack {
                    Text("整體進度")
                        .font(.subheadline)
                    Spacer()
                    Text("\(done) / \(items.count) 個")
                        .font(.subheadline.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                ProgressView(value: overallProgress)
                    .progressViewStyle(.linear)
                    .tint(.blue)
                Text("\(Int(overallProgress * 100))%")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 4)
        }
    }

    private var itemListSection: some View {
        Section("轉換清單") {
            ForEach($items) { $item in
                ItemRow(item: $item) {
                    // 刪除單一項目（未轉換中才可刪）
                    if item.status != .converting {
                        items.removeAll { $0.id == item.id }
                    }
                }
            }
        }
    }

    private var completionSection: some View {
        Section {
            VStack(spacing: 12) {
                let ok  = items.filter { $0.status == .done }.count
                let err = items.filter { $0.status == .failed }.count

                HStack {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                    Text("完成 \(ok) 個")
                        .font(.headline)
                    if err > 0 {
                        Text("失敗 \(err) 個")
                            .foregroundStyle(.red)
                            .font(.subheadline)
                    }
                    Spacer()
                }

                HStack(spacing: 12) {
                    // 分享全部
                    if !doneURLs.isEmpty {
                        Button {
                            showShare = true
                        } label: {
                            Label("分享全部", systemImage: "square.and.arrow.up")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .tint(.blue)
                    }

                    // 完成並清除
                    Button(role: .destructive) {
                        resetAll()
                    } label: {
                        Label("完成並清除", systemImage: "checkmark.circle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.green)
                }
            }
            .padding(.vertical, 4)
        }
    }

    private var actionButtons: some View {
        Section {
            // 開始批次轉換
            Button {
                startBatch()
            } label: {
                HStack {
                    Spacer()
                    Label(
                        isRunning ? "轉換中…" : "開始批次轉換",
                        systemImage: isRunning ? "hourglass" : "arrow.triangle.2.circlepath"
                    )
                    .font(.headline)
                    Spacer()
                }
            }
            .disabled(items.filter { $0.status == .pending }.isEmpty || isRunning)
        }
    }

    // MARK: - Actions

    private func startBatch() {
        let pendingURLs = items.filter { $0.status == .pending }.map(\.url)
        guard !pendingURLs.isEmpty else { return }
        isRunning = true

        Task {
            await converter.convertBatch(
                items:   pendingURLs,
                quality: quality,
                onItemProgress: { localIdx, p in
                    Task { @MainActor in
                        // 找到對應的全域 index（pending 中的第 localIdx 個）
                        let globalIdx = pendingIndex(localIdx, in: pendingURLs)
                        if let gi = globalIdx { items[gi].progress = p }
                    }
                },
                onItemDone: { localIdx, result in
                    Task { @MainActor in
                        let globalIdx = pendingIndex(localIdx, in: pendingURLs)
                        guard let gi = globalIdx else { return }
                        switch result {
                        case .success(let url):
                            items[gi].outputURL = url
                            items[gi].status    = .done
                            items[gi].progress  = 1.0
                        case .failure(let err):
                            items[gi].errorMsg  = err.localizedDescription
                            items[gi].status    = .failed
                        }
                    }
                }
            )
            await MainActor.run {
                isRunning = false
                showDoneAlert = true
            }
        }

        // 立刻把 pending 項目標為 converting（視覺回饋）
        for i in items.indices where items[i].status == .pending {
            items[i].status = .converting
        }
    }

    /// 根據 pendingURLs 的 localIdx 找回全域 items 的 index
    private func pendingIndex(_ localIdx: Int, in pendingURLs: [URL]) -> Int? {
        guard localIdx < pendingURLs.count else { return nil }
        let targetURL = pendingURLs[localIdx]
        return items.firstIndex { $0.url == targetURL }
    }

    private func resetAll() {
        items    = []
        isRunning = false
    }
}

// MARK: - 單一項目列（ItemRow）

struct ItemRow: View {
    @Binding var item: ConversionItem
    let onDelete: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // 狀態圖示
            statusIcon
                .frame(width: 24)

            // 檔名
            VStack(alignment: .leading, spacing: 2) {
                Text(item.name)
                    .font(.subheadline)
                    .lineLimit(1)

                switch item.status {
                case .pending:
                    Text("等待中").font(.caption).foregroundStyle(.secondary)
                case .converting:
                    ProgressView(value: item.progress)
                        .progressViewStyle(.linear)
                        .tint(.blue)
                case .done:
                    Text("完成").font(.caption).foregroundStyle(.green)
                case .failed:
                    Text(item.errorMsg ?? "失敗").font(.caption).foregroundStyle(.red).lineLimit(1)
                }
            }

            Spacer()

            // 刪除按鈕（轉換中不可刪）
            if item.status != .converting {
                Button(role: .destructive, action: onDelete) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.vertical, 2)
    }

    @ViewBuilder
    private var statusIcon: some View {
        switch item.status {
        case .pending:
            Image(systemName: "clock")
                .foregroundStyle(.secondary)
        case .converting:
            ProgressView()
                .scaleEffect(0.8)
        case .done:
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
        case .failed:
            Image(systemName: "xmark.circle.fill")
                .foregroundStyle(.red)
        }
    }
}

// MARK: - VideoPicker（多選）

struct VideoPicker: UIViewControllerRepresentable {
    let onPick: ([URL]) -> Void

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
        picker.allowsMultipleSelection = true          // ← 多選開啟
        return picker
    }
    func updateUIViewController(_ vc: UIDocumentPickerViewController, context: Context) {}
    func makeCoordinator() -> Coord { Coord(onPick: onPick) }

    class Coord: NSObject, UIDocumentPickerDelegate {
        let onPick: ([URL]) -> Void
        init(onPick: @escaping ([URL]) -> Void) { self.onPick = onPick }

        func documentPicker(_ controller: UIDocumentPickerViewController,
                            didPickDocumentsAt urls: [URL]) {
            var copied: [URL] = []
            for url in urls {
                guard url.startAccessingSecurityScopedResource() else { continue }
                defer { url.stopAccessingSecurityScopedResource() }
                let tmp = FileManager.default.temporaryDirectory
                            .appendingPathComponent(url.lastPathComponent)
                try? FileManager.default.removeItem(at: tmp)
                if (try? FileManager.default.copyItem(at: url, to: tmp)) != nil {
                    copied.append(tmp)
                }
            }
            onPick(copied)
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
