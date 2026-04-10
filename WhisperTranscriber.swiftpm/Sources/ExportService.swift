import Foundation

enum ExportError: LocalizedError {
    case emptyContent
    case writeFailed(String)

    var errorDescription: String? {
        switch self {
        case .emptyContent:         return "沒有可匯出的內容"
        case .writeFailed(let msg): return "寫入失敗：\(msg)"
        }
    }
}

final class ExportService {
    static let shared = ExportService()
    private init() {}

    private let tempDir = FileManager.default.temporaryDirectory

    // MARK: - Public

    func export(job: TranscriptionJob, format: OutputFormat) throws -> URL {
        guard !job.fullText.isEmpty else { throw ExportError.emptyContent }
        switch format {
        case .txt:      return try exportTXT(job: job)
        case .srt:      return try exportSRT(job: job)
        case .markdown: return try exportMarkdown(job: job)
        }
    }

    // MARK: - Formats

    private func exportTXT(job: TranscriptionJob) throws -> URL {
        let url = tempDir.appendingPathComponent("\(job.baseName).txt")
        do {
            try job.fullText.write(to: url, atomically: true, encoding: .utf8)
        } catch {
            throw ExportError.writeFailed(error.localizedDescription)
        }
        return url
    }

    private func exportSRT(job: TranscriptionJob) throws -> URL {
        var lines: [String] = []
        let source = job.segments.isEmpty ? syntheticSegments(from: job.fullText) : job.segments

        for (idx, seg) in source.enumerated() {
            lines.append("\(idx + 1)")
            lines.append("\(srtTimestamp(seg.start)) --> \(srtTimestamp(seg.end))")
            lines.append(seg.text.trimmingCharacters(in: .whitespaces))
            lines.append("")
        }

        let url = tempDir.appendingPathComponent("\(job.baseName).srt")
        do {
            try lines.joined(separator: "\n").write(to: url, atomically: true, encoding: .utf8)
        } catch {
            throw ExportError.writeFailed(error.localizedDescription)
        }
        return url
    }

    private func exportMarkdown(job: TranscriptionJob) throws -> URL {
        var lines: [String] = [
            "# \(job.baseName)",
            "",
            "---",
            ""
        ]

        let source = job.segments.isEmpty ? syntheticSegments(from: job.fullText) : job.segments

        for seg in source {
            let ts = shortTimestamp(seg.start)
            let text = seg.text.trimmingCharacters(in: .whitespaces)
            lines.append("**[\(ts)]** \(text)")
            lines.append("")
        }

        let url = tempDir.appendingPathComponent("\(job.baseName).md")
        do {
            try lines.joined(separator: "\n").write(to: url, atomically: true, encoding: .utf8)
        } catch {
            throw ExportError.writeFailed(error.localizedDescription)
        }
        return url
    }

    // MARK: - Timestamp Helpers

    /// SRT format: 00:00:01,500
    private func srtTimestamp(_ seconds: Float) -> String {
        let total = max(0, Int(seconds))
        let ms    = max(0, Int((seconds - Float(Int(seconds))) * 1000))
        return String(
            format: "%02d:%02d:%02d,%03d",
            total / 3600, (total % 3600) / 60, total % 60, min(ms, 999)
        )
    }

    /// Short display: 1:23 or 1:23:45
    private func shortTimestamp(_ seconds: Float) -> String {
        let total = max(0, Int(seconds))
        let h = total / 3600
        let m = (total % 3600) / 60
        let s = total % 60
        return h > 0
            ? String(format: "%d:%02d:%02d", h, m, s)
            : String(format: "%d:%02d", m, s)
    }

    // MARK: - Fallback

    /// When no segment timestamps exist, treat the whole text as one block.
    private func syntheticSegments(from text: String) -> [SegmentData] {
        [SegmentData(start: 0, end: 0, text: text)]
    }
}
