import Foundation
import WhisperKit

struct SRTFormatter {

    /// Convert WhisperKit segments to SRT subtitle format.
    static func format(segments: [TranscriptionSegment]) -> String {
        guard !segments.isEmpty else { return "" }
        var lines: [String] = []
        for (index, segment) in segments.enumerated() {
            let text = segment.text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !text.isEmpty else { continue }
            lines.append("\(index + 1)")
            lines.append("\(timestamp(Double(segment.start))) --> \(timestamp(Double(segment.end)))")
            lines.append(text)
            lines.append("")
        }
        return lines.joined(separator: "\n")
    }

    /// Convert seconds to SRT timestamp string: HH:MM:SS,mmm
    static func timestamp(_ seconds: Double) -> String {
        let total = max(0, seconds)
        let hours   = Int(total) / 3600
        let minutes = (Int(total) % 3600) / 60
        let secs    = Int(total) % 60
        let millis  = Int((total.truncatingRemainder(dividingBy: 1)) * 1000)
        return String(format: "%02d:%02d:%02d,%03d", hours, minutes, secs, millis)
    }
}
