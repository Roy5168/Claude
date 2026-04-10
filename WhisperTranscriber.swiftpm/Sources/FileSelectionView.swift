import SwiftUI
import UniformTypeIdentifiers

struct FileSelectionView: View {
    @EnvironmentObject var service: WhisperService
    @Binding var showFileImporter: Bool

    var body: some View {
        Group {
            if service.jobs.isEmpty {
                emptyState
            } else {
                jobList
            }
        }
        .navigationTitle("音檔列表")
        .toolbar {
            ToolbarItemGroup(placement: .navigationBarTrailing) {
                if !service.jobs.isEmpty {
                    Button(role: .destructive) {
                        service.clearAllJobs()
                    } label: {
                        Label("清除全部", systemImage: "trash")
                    }
                }
                Button {
                    showFileImporter = true
                } label: {
                    Label("新增音檔", systemImage: "plus")
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "waveform.badge.plus")
                .font(.system(size: 56))
                .foregroundStyle(.blue)
            Text("尚未選取音檔")
                .font(.title2.bold())
            Text("支援 MP3、M4A、WAV、FLAC、AIFF 格式")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button {
                showFileImporter = true
            } label: {
                Label("選取音檔", systemImage: "folder.badge.plus")
                    .font(.headline)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            Spacer()
        }
        .padding()
    }

    private var jobList: some View {
        List {
            ForEach(service.jobs) { job in
                JobRowView(job: job)
            }
            .onDelete { offsets in
                service.removeJobs(at: offsets)
            }

            Button {
                showFileImporter = true
            } label: {
                Label("新增更多音檔…", systemImage: "plus.circle")
                    .foregroundStyle(.blue)
            }
        }
    }
}

// MARK: - Job Row

struct JobRowView: View {
    let job: TranscriptionJob

    var body: some View {
        HStack(spacing: 12) {
            statusIcon
                .frame(width: 24, height: 24)

            VStack(alignment: .leading, spacing: 3) {
                Text(job.fileName)
                    .font(.body)
                    .lineLimit(2)
                Text(job.status.displayText)
                    .font(.caption)
                    .foregroundStyle(statusColor)
            }
        }
        .padding(.vertical, 4)
    }

    @ViewBuilder
    private var statusIcon: some View {
        switch job.status {
        case .pending:
            Image(systemName: "clock.fill")
                .foregroundStyle(.secondary)
        case .transcribing:
            ProgressView()
                .controlSize(.small)
        case .completed:
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
        case .failed:
            Image(systemName: "exclamationmark.circle.fill")
                .foregroundStyle(.red)
        }
    }

    private var statusColor: Color {
        switch job.status {
        case .pending:      return .secondary
        case .transcribing: return .orange
        case .completed:    return .green
        case .failed:       return .red
        }
    }
}
