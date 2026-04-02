import AVFoundation
import Foundation

// MARK: - 核心剪輯邏輯（硬體加速 AAC 編碼）

actor AudioTrimmer {

    enum TrimError: LocalizedError {
        case sessionFailed
        case exportFailed(String)

        var errorDescription: String? {
            switch self {
            case .sessionFailed:         return "無法建立轉檔工作"
            case .exportFailed(let msg): return "匯出失敗：\(msg)"
            }
        }
    }

    /// - Parameters:
    ///   - inputURL:   來源音檔（MP3 / M4A / AAC / WAV …）
    ///   - startTime:  剪輯起點（秒）
    ///   - endTime:    剪輯終點（秒）
    ///   - onProgress: 進度 0~1 回呼
    /// - Returns: 輸出的 .m4a 檔案 URL（存於 Documents）
    func trim(
        inputURL: URL,
        startTime: Double,
        endTime: Double,
        onProgress: @Sendable @escaping (Float) -> Void
    ) async throws -> URL {

        let asset    = AVURLAsset(url: inputURL)
        let duration = try await asset.load(.duration)

        let start = CMTime(seconds: startTime, preferredTimescale: 600)
        let end   = CMTime(seconds: min(endTime, duration.seconds), preferredTimescale: 600)

        guard let session = AVAssetExportSession(asset: asset,
                                                  presetName: AVAssetExportPresetAppleM4A) else {
            throw TrimError.sessionFailed
        }

        let outputURL = buildOutputURL(for: inputURL)
        try? FileManager.default.removeItem(at: outputURL)

        session.outputURL      = outputURL
        session.outputFileType = .m4a
        session.timeRange      = CMTimeRange(start: start, end: end)

        let poll = Task {
            while !Task.isCancelled {
                onProgress(session.progress)
                try? await Task.sleep(nanoseconds: 100_000_000)
            }
        }
        await session.export()
        poll.cancel()
        onProgress(1.0)

        switch session.status {
        case .completed: return outputURL
        case .failed:    throw TrimError.exportFailed(session.error?.localizedDescription ?? "未知")
        case .cancelled: throw TrimError.exportFailed("已取消")
        default:         throw TrimError.exportFailed("未知狀態")
        }
    }

    private func buildOutputURL(for input: URL) -> URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let name = input.deletingPathExtension().lastPathComponent
        return docs.appendingPathComponent("\(name)_trimmed.m4a")
    }
}
