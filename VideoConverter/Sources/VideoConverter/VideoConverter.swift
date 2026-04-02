import AVFoundation
import Foundation

/// 使用 VideoToolbox 硬體加速，將任意影片轉為 H.265 (HEVC) MP4
actor VideoConverter {

    enum Quality: String, CaseIterable, Identifiable {
        case highest  = "最高畫質（原始解析度）"
        case uhd      = "4K (3840×2160)"
        case fhd      = "1080p (1920×1080)"
        case hd       = "720p (1280×720)"

        var id: String { rawValue }

        /// 對應 AVAssetExportSession preset
        var preset: String {
            switch self {
            case .highest: return AVAssetExportPresetHEVCHighestQuality
            case .uhd:     return AVAssetExportPresetHEVC3840x2160
            case .fhd:     return AVAssetExportPresetHEVC1920x1080
            case .hd:      return AVAssetExportPresetHEVC1920x1080  // 自訂縮放
            }
        }
    }

    enum ConversionError: LocalizedError {
        case unsupportedFormat
        case exportSessionFailed
        case exportFailed(String)
        case outputURLUnavailable

        var errorDescription: String? {
            switch self {
            case .unsupportedFormat:       return "不支援的影片格式"
            case .exportSessionFailed:     return "無法建立轉檔工作（此裝置可能不支援 HEVC）"
            case .exportFailed(let msg):   return "轉檔失敗：\(msg)"
            case .outputURLUnavailable:    return "無法取得輸出路徑"
            }
        }
    }

    // MARK: - 主要轉換方法

    /// - Parameters:
    ///   - inputURL:    原始影片檔案 URL（任意格式）
    ///   - outputDir:   輸出目錄（預設為 Documents）
    ///   - quality:     輸出畫質
    ///   - onProgress:  進度回呼 0.0 ~ 1.0
    /// - Returns: 轉換後的 MP4 檔案 URL
    func convert(
        inputURL: URL,
        outputDir: URL? = nil,
        quality: Quality = .highest,
        onProgress: @Sendable @escaping (Float) -> Void
    ) async throws -> URL {

        let asset = AVURLAsset(url: inputURL, options: [AVURLAssetPreferPreciseDurationAndTimingKey: true])

        // 確認 HEVC 可用
        guard await isHEVCSupported(for: asset, preset: quality.preset) else {
            throw ConversionError.exportSessionFailed
        }

        // 建立輸出 URL（同名，副檔名改為 .mp4）
        let outputURL = try buildOutputURL(for: inputURL, outputDir: outputDir)
        // 若舊檔存在先刪除
        try? FileManager.default.removeItem(at: outputURL)

        // 建立 ExportSession
        guard let session = AVAssetExportSession(asset: asset, presetName: quality.preset) else {
            throw ConversionError.exportSessionFailed
        }

        session.outputURL          = outputURL
        session.outputFileType     = .mp4
        session.shouldOptimizeForNetworkUse = true   // 將 moov atom 移到檔頭（適合串流）

        // 720p 需要額外加 videoComposition 做縮放
        if quality == .hd {
            session.videoComposition = try await buildScaleComposition(asset: asset, targetWidth: 1280, targetHeight: 720)
        }

        // 啟動進度輪詢
        let progressTask = Task {
            while !Task.isCancelled {
                onProgress(session.progress)
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
            }
        }

        // 非同步執行轉檔
        await session.export()
        progressTask.cancel()
        onProgress(1.0)

        switch session.status {
        case .completed:
            return outputURL
        case .failed:
            throw ConversionError.exportFailed(session.error?.localizedDescription ?? "未知錯誤")
        case .cancelled:
            throw ConversionError.exportFailed("使用者取消")
        default:
            throw ConversionError.exportFailed("未知狀態")
        }
    }

    // MARK: - 中止轉換（傳入 session 由外部保存）
    // 若需中止，可在 UI 層保存 AVAssetExportSession 並呼叫 .cancelExport()

    // MARK: - Private Helpers

    private func isHEVCSupported(for asset: AVURLAsset, preset: String) async -> Bool {
        let compatible = await AVAssetExportSession.compatibleFileTypes(with: preset)
        return compatible.contains(.mp4)
    }

    private func buildOutputURL(for inputURL: URL, outputDir: URL?) throws -> URL {
        let dir: URL
        if let outputDir {
            dir = outputDir
        } else {
            guard let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
                throw ConversionError.outputURLUnavailable
            }
            dir = documents
        }

        let baseName = inputURL.deletingPathExtension().lastPathComponent
        return dir.appendingPathComponent("\(baseName)_h265.mp4")
    }

    /// 針對 720p 建立縮放 videoComposition
    private func buildScaleComposition(asset: AVURLAsset, targetWidth: CGFloat, targetHeight: CGFloat) async throws -> AVVideoComposition {
        let tracks = try await asset.loadTracks(withMediaType: .video)
        guard let track = tracks.first else {
            throw ConversionError.unsupportedFormat
        }

        let naturalSize = try await track.load(.naturalSize)
        let transform   = try await track.load(.preferredTransform)

        // 計算旋轉後的實際尺寸
        let videoSize = naturalSize.applying(transform)
        let actualSize = CGSize(width: abs(videoSize.width), height: abs(videoSize.height))

        // 等比縮放
        let scale = min(targetWidth / actualSize.width, targetHeight / actualSize.height)
        let renderSize = CGSize(
            width:  (actualSize.width  * scale).rounded(),
            height: (actualSize.height * scale).rounded()
        )

        let instruction = AVMutableVideoCompositionInstruction()
        instruction.timeRange = CMTimeRange(start: .zero, duration: try await asset.load(.duration))

        let layerInstruction = AVMutableVideoCompositionLayerInstruction(assetTrack: track)
        // 套用原始 transform + 縮放
        let scaleTransform = CGAffineTransform(scaleX: scale, y: scale).concatenating(transform)
        layerInstruction.setTransform(scaleTransform, at: .zero)
        instruction.layerInstructions = [layerInstruction]

        let composition = AVMutableVideoComposition()
        composition.instructions         = [instruction]
        composition.frameDuration        = CMTime(value: 1, timescale: 30)
        composition.renderSize           = renderSize

        return composition
    }
}
