import AVFoundation
import Foundation

actor VideoConverter {

    enum Quality: String, CaseIterable, Identifiable {
        case highest = "最高畫質（原始解析度）"
        case fhd     = "1080p (1920×1080)"
        case hd      = "720p (1280×720)"

        var id: String { rawValue }

        var preset: String {
            switch self {
            case .highest: return AVAssetExportPresetHEVCHighestQuality
            case .fhd:     return AVAssetExportPresetHEVC1920x1080
            case .hd:      return AVAssetExportPresetHEVC1920x1080
            }
        }
    }

    enum ConversionError: LocalizedError {
        case exportSessionFailed
        case exportFailed(String)

        var errorDescription: String? {
            switch self {
            case .exportSessionFailed:   return "無法建立轉檔工作（確認裝置支援 HEVC）"
            case .exportFailed(let msg): return "轉檔失敗：\(msg)"
            }
        }
    }

    // MARK: - 單檔轉換

    func convert(
        inputURL: URL,
        quality: Quality = .highest,
        onProgress: @Sendable @escaping (Float) -> Void
    ) async throws -> URL {

        let asset = AVURLAsset(
            url: inputURL,
            options: [AVURLAssetPreferPreciseDurationAndTimingKey: true]
        )

        let outputURL = buildOutputURL(for: inputURL)
        try? FileManager.default.removeItem(at: outputURL)

        guard let session = AVAssetExportSession(asset: asset, presetName: quality.preset) else {
            throw ConversionError.exportSessionFailed
        }

        session.outputURL                   = outputURL
        session.outputFileType              = .mp4
        session.shouldOptimizeForNetworkUse = true

        if quality == .hd {
            if let comp = try? await makeScaleComposition(asset: asset, width: 1280, height: 720) {
                session.videoComposition = comp
            }
        }

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
        case .failed:    throw ConversionError.exportFailed(session.error?.localizedDescription ?? "未知")
        case .cancelled: throw ConversionError.exportFailed("已取消")
        default:         throw ConversionError.exportFailed("未知狀態")
        }
    }

    // MARK: - 批次轉換（依序處理，每檔完成後回呼）

    /// - Parameters:
    ///   - items:       要轉換的檔案 URL 陣列
    ///   - quality:     統一套用的畫質
    ///   - onItemProgress: (index, 0~1) 單檔進度
    ///   - onItemDone:     (index, Result) 單檔完成
    func convertBatch(
        items: [URL],
        quality: Quality,
        onItemProgress: @Sendable @escaping (Int, Float) -> Void,
        onItemDone:     @Sendable @escaping (Int, Result<URL, Error>) -> Void
    ) async {
        for (index, url) in items.enumerated() {
            do {
                let out = try await convert(inputURL: url, quality: quality) { p in
                    onItemProgress(index, p)
                }
                onItemDone(index, .success(out))
            } catch {
                onItemDone(index, .failure(error))
            }
        }
    }

    // MARK: - Helpers

    private func buildOutputURL(for input: URL) -> URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let name = input.deletingPathExtension().lastPathComponent
        return docs.appendingPathComponent("\(name)_h265.mp4")
    }

    private func makeScaleComposition(
        asset: AVURLAsset, width: CGFloat, height: CGFloat
    ) async throws -> AVVideoComposition {
        let tracks  = try await asset.loadTracks(withMediaType: .video)
        let track   = tracks[0]
        let natSize = try await track.load(.naturalSize)
        let xform   = try await track.load(.preferredTransform)
        let rotated = natSize.applying(xform)
        let actual  = CGSize(width: abs(rotated.width), height: abs(rotated.height))
        let scale   = min(width / actual.width, height / actual.height)
        let render  = CGSize(width: (actual.width * scale).rounded(),
                             height: (actual.height * scale).rounded())

        let instr       = AVMutableVideoCompositionInstruction()
        instr.timeRange = CMTimeRange(start: .zero, duration: try await asset.load(.duration))
        let layer       = AVMutableVideoCompositionLayerInstruction(assetTrack: track)
        layer.setTransform(
            CGAffineTransform(scaleX: scale, y: scale).concatenating(xform), at: .zero
        )
        instr.layerInstructions = [layer]

        let comp           = AVMutableVideoComposition()
        comp.instructions  = [instr]
        comp.frameDuration = CMTime(value: 1, timescale: 30)
        comp.renderSize    = render
        return comp
    }
}
