import Foundation

// MARK: - Whisper Model

enum WhisperModel: String, CaseIterable, Identifiable {
    case tiny
    case base
    case small
    case medium
    case largeV2
    case largeV3
    case turbo

    var id: String { modelId }

    var modelId: String {
        switch self {
        case .tiny:    return "openai_whisper-tiny"
        case .base:    return "openai_whisper-base"
        case .small:   return "openai_whisper-small"
        case .medium:  return "openai_whisper-medium"
        case .largeV2: return "openai_whisper-large-v2"
        case .largeV3: return "openai_whisper-large-v3"
        case .turbo:   return "openai_whisper-large-v3-turbo"
        }
    }

    var displayName: String {
        switch self {
        case .tiny:    return "Tiny"
        case .base:    return "Base"
        case .small:   return "Small"
        case .medium:  return "Medium"
        case .largeV2: return "Large v2"
        case .largeV3: return "Large v3"
        case .turbo:   return "Turbo"
        }
    }

    var sizeMB: Int {
        switch self {
        case .tiny:    return 75
        case .base:    return 145
        case .small:   return 466
        case .medium:  return 1_500
        case .largeV2: return 2_900
        case .largeV3: return 2_900
        case .turbo:   return 810
        }
    }

    var sizeString: String {
        sizeMB < 1000
            ? "\(sizeMB) MB"
            : String(format: "%.1f GB", Double(sizeMB) / 1000.0)
    }
}

// MARK: - Output Format

enum OutputFormat: String, CaseIterable, Identifiable {
    case txt
    case srt
    case markdown

    var id: String { rawValue }

    var fileExtension: String {
        switch self {
        case .txt:      return "txt"
        case .srt:      return "srt"
        case .markdown: return "md"
        }
    }

    var displayName: String {
        switch self {
        case .txt:      return "純文字 (.txt)"
        case .srt:      return "字幕 (.srt)"
        case .markdown: return "Markdown (.md)"
        }
    }

    var icon: String {
        switch self {
        case .txt:      return "doc.text"
        case .srt:      return "captions.bubble"
        case .markdown: return "doc.richtext"
        }
    }
}

// MARK: - Model Load State

enum ModelLoadState: Equatable {
    case notLoaded
    case loading
    case ready(WhisperModel)
    case failed(String)

    var isReady: Bool {
        if case .ready = self { return true }
        return false
    }

    var isLoading: Bool {
        if case .loading = self { return true }
        return false
    }

    var displayText: String {
        switch self {
        case .notLoaded:       return "尚未載入模型"
        case .loading:         return "下載並載入中…"
        case .ready(let m):    return "\(m.displayName) 已就緒"
        case .failed(let err): return "載入失敗：\(err)"
        }
    }

    static func == (lhs: ModelLoadState, rhs: ModelLoadState) -> Bool {
        switch (lhs, rhs) {
        case (.notLoaded, .notLoaded): return true
        case (.loading, .loading):     return true
        case (.ready(let a), .ready(let b)): return a == b
        case (.failed(let a), .failed(let b)): return a == b
        default: return false
        }
    }
}

// MARK: - Job Status

enum JobStatus {
    case pending
    case transcribing
    case completed
    case failed(String)

    var displayText: String {
        switch self {
        case .pending:         return "等待中"
        case .transcribing:    return "轉錄中…"
        case .completed:       return "已完成"
        case .failed(let err): return "失敗：\(err)"
        }
    }

    var isCompleted: Bool {
        if case .completed = self { return true }
        return false
    }

    var isFailed: Bool {
        if case .failed = self { return true }
        return false
    }

    var isPending: Bool {
        if case .pending = self { return true }
        return false
    }
}

// MARK: - Segment

struct SegmentData: Identifiable {
    let id = UUID()
    let start: Float
    let end: Float
    let text: String
}

// MARK: - Transcription Job

struct TranscriptionJob: Identifiable {
    let id: UUID
    let audioURL: URL
    var status: JobStatus
    var segments: [SegmentData]
    var fullText: String

    init(audioURL: URL) {
        self.id = UUID()
        self.audioURL = audioURL
        self.status = .pending
        self.segments = []
        self.fullText = ""
    }

    var fileName: String { audioURL.lastPathComponent }
    var baseName: String { audioURL.deletingPathExtension().lastPathComponent }
}

// MARK: - Language

struct WhisperLanguage: Identifiable, Hashable {
    let id: String   // Whisper language code, or "auto"
    let name: String

    static let autoDetect = WhisperLanguage(id: "auto", name: "自動偵測")

    static let all: [WhisperLanguage] = [
        .autoDetect,
        WhisperLanguage(id: "zh", name: "中文"),
        WhisperLanguage(id: "en", name: "英語"),
        WhisperLanguage(id: "ja", name: "日語"),
        WhisperLanguage(id: "ko", name: "韓語"),
        WhisperLanguage(id: "fr", name: "法語"),
        WhisperLanguage(id: "de", name: "德語"),
        WhisperLanguage(id: "es", name: "西班牙語"),
        WhisperLanguage(id: "pt", name: "葡萄牙語"),
        WhisperLanguage(id: "it", name: "義大利語"),
        WhisperLanguage(id: "ru", name: "俄語"),
        WhisperLanguage(id: "ar", name: "阿拉伯語"),
        WhisperLanguage(id: "hi", name: "印地語"),
        WhisperLanguage(id: "th", name: "泰語"),
        WhisperLanguage(id: "vi", name: "越南語"),
        WhisperLanguage(id: "id", name: "印尼語"),
        WhisperLanguage(id: "ms", name: "馬來語"),
        WhisperLanguage(id: "nl", name: "荷蘭語"),
        WhisperLanguage(id: "pl", name: "波蘭語"),
        WhisperLanguage(id: "tr", name: "土耳其語"),
        WhisperLanguage(id: "sv", name: "瑞典語"),
        WhisperLanguage(id: "da", name: "丹麥語"),
        WhisperLanguage(id: "fi", name: "芬蘭語"),
        WhisperLanguage(id: "no", name: "挪威語"),
        WhisperLanguage(id: "uk", name: "烏克蘭語"),
    ]
}

// MARK: - Share Helper

struct ShareableURL: Identifiable {
    let id = UUID()
    let url: URL
}
