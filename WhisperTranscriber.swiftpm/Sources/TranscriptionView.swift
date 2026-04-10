import SwiftUI
import UIKit

// MARK: - Main Transcription Panel

struct TranscriptionView: View {
    @EnvironmentObject var service: WhisperService

    var body: some View {
        GroupBox {
            VStack(spacing: 20) {
                startButton
                if service.isTranscribing {
                    ProgressView("轉錄中，請稍候…")
                        .progressViewStyle(.linear)
                        .padding(.horizontal)
                }
                resultsList
            }
            .padding(.vertical, 8)
        } label: {
            Label("轉錄結果", systemImage: "text.quote")
                .font(.title3.bold())
        }
    }

    private var startButton: some View {
        VStack(spacing: 8) {
            Button {
                Task { await service.transcribeAll() }
            } label: {
                Label("開始轉錄", systemImage: "waveform")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(!service.canTranscribe)

            if !service.modelLoadState.isReady {
                Text("請先在上方「模型設定」中載入模型")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else if service.jobs.isEmpty {
                Text("請在左側新增音檔")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else if service.pendingCount == 0 && !service.isTranscribing {
                Text("所有檔案已完成，可重新選擇檔案或重設")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder
    private var resultsList: some View {
        let completedJobs = service.jobs.filter { $0.status.isCompleted || $0.status.isFailed }
        if !completedJobs.isEmpty {
            Divider()
            VStack(spacing: 12) {
                ForEach(completedJobs) { job in
                    JobResultCard(job: job, selectedFormats: service.selectedFormats)
                }
            }
        }
    }
}

// MARK: - Result Card

struct JobResultCard: View {
    let job: TranscriptionJob
    let selectedFormats: Set<OutputFormat>

    @State private var isExpanded = true
    @State private var shareItem: ShareableURL?
    @State private var showExportError = false
    @State private var exportErrorMessage = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            Button {
                withAnimation(.easeInOut(duration: 0.2)) { isExpanded.toggle() }
            } label: {
                HStack {
                    Image(systemName: job.status.isCompleted ? "doc.waveform.fill" : "exclamationmark.circle.fill")
                        .foregroundStyle(job.status.isCompleted ? .blue : .red)
                    Text(job.fileName)
                        .font(.headline)
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                    Spacer()
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .foregroundStyle(.secondary)
                        .font(.caption)
                }
                .padding()
            }
            .buttonStyle(.plain)

            if isExpanded {
                Divider()

                // Content
                if job.status.isCompleted {
                    ScrollView {
                        Text(job.fullText.isEmpty ? "（無辨識文字）" : job.fullText)
                            .font(.body)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding()
                    }
                    .frame(maxHeight: 200)

                    // Export buttons
                    if !selectedFormats.isEmpty {
                        Divider()
                        HStack(spacing: 10) {
                            Text("匯出：")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            ForEach(sortedFormats) { fmt in
                                Button {
                                    triggerExport(format: fmt)
                                } label: {
                                    Label(
                                        fmt.fileExtension.uppercased(),
                                        systemImage: fmt.icon
                                    )
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                            }
                            Spacer()
                            copyButton
                        }
                        .padding(.horizontal)
                        .padding(.vertical, 10)
                    }

                } else if case .failed(let msg) = job.status {
                    Text(msg)
                        .font(.body)
                        .foregroundStyle(.red)
                        .padding()
                }
            }
        }
        .background(.background.secondary, in: RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(
                    job.status.isCompleted ? Color.blue.opacity(0.3) : Color.red.opacity(0.3),
                    lineWidth: 1
                )
        )
        .sheet(item: $shareItem) { item in
            ActivityViewController(activityItems: [item.url])
        }
        .alert("匯出失敗", isPresented: $showExportError) {
            Button("確定", role: .cancel) {}
        } message: {
            Text(exportErrorMessage)
        }
    }

    private var sortedFormats: [OutputFormat] {
        selectedFormats.sorted { $0.rawValue < $1.rawValue }
    }

    private var copyButton: some View {
        Button {
            UIPasteboard.general.string = job.fullText
        } label: {
            Label("複製", systemImage: "doc.on.doc")
        }
        .buttonStyle(.bordered)
        .controlSize(.small)
        .tint(.secondary)
    }

    private func triggerExport(format: OutputFormat) {
        do {
            let url = try ExportService.shared.export(job: job, format: format)
            shareItem = ShareableURL(url: url)
        } catch {
            exportErrorMessage = error.localizedDescription
            showExportError = true
        }
    }
}

// MARK: - Activity View Controller (UIKit bridge)

struct ActivityViewController: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        let controller = UIActivityViewController(
            activityItems: activityItems,
            applicationActivities: nil
        )
        // Required for iPad: attach to the source view to avoid crash
        controller.popoverPresentationController?.permittedArrowDirections = .any
        return controller
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
