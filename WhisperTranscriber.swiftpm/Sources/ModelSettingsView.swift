import SwiftUI

struct ModelSettingsView: View {
    @EnvironmentObject var service: WhisperService

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 20) {
                modelRow
                Divider()
                languageRow
                Divider()
                outputFormatsRow
                Divider()
                loadModelRow
            }
            .padding(.vertical, 8)
        } label: {
            Label("模型設定", systemImage: "cpu")
                .font(.title3.bold())
        }
    }

    // MARK: - Model Picker

    private var modelRow: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Whisper 模型")
                .font(.headline)
            Picker("模型", selection: $service.selectedModel) {
                ForEach(WhisperModel.allCases) { model in
                    HStack {
                        Text(model.displayName)
                        Spacer()
                        Text(model.sizeString)
                            .foregroundStyle(.secondary)
                    }
                    .tag(model)
                }
            }
            .pickerStyle(.menu)
            .disabled(service.modelLoadState.isLoading || service.isTranscribing)

            Text(modelHint)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var modelHint: String {
        let m = service.selectedModel
        switch m {
        case .tiny, .base:
            return "快速，適合短片段或即時預覽，準確度較低"
        case .small:
            return "速度與準確度的平衡，推薦日常使用"
        case .medium:
            return "高準確度，適合多語言或複雜音訊"
        case .largeV2, .largeV3:
            return "最高準確度，需較長處理時間與充足記憶體"
        case .turbo:
            return "Large v3 的加速版，準確度與速度兼顧"
        }
    }

    // MARK: - Language Picker

    private var languageRow: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("轉錄語言")
                .font(.headline)
            Picker("語言", selection: $service.selectedLanguage) {
                ForEach(WhisperLanguage.all) { lang in
                    Text(lang.name).tag(lang)
                }
            }
            .pickerStyle(.menu)
            .disabled(service.isTranscribing)
            Text("選擇「自動偵測」讓 Whisper 判斷語言")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Output Format Selection

    private var outputFormatsRow: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("輸出格式")
                .font(.headline)
            HStack(spacing: 10) {
                ForEach(OutputFormat.allCases) { fmt in
                    Toggle(isOn: formatBinding(fmt)) {
                        Label(fmt.fileExtension.uppercased(), systemImage: fmt.icon)
                            .padding(.horizontal, 2)
                    }
                    .toggleStyle(.button)
                    .tint(.blue)
                    .disabled(service.isTranscribing)
                }
            }
            Text("可同時選取多種格式，完成後逐一匯出")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func formatBinding(_ format: OutputFormat) -> Binding<Bool> {
        Binding(
            get: { service.selectedFormats.contains(format) },
            set: { isOn in
                if isOn { service.selectedFormats.insert(format) }
                else     { service.selectedFormats.remove(format) }
            }
        )
    }

    // MARK: - Load Model Button

    private var loadModelRow: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text("模型狀態")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text(service.modelLoadState.displayText)
                    .font(.body)
                    .foregroundStyle(stateColor)
            }
            Spacer()

            if service.modelLoadState.isLoading {
                ProgressView()
                    .controlSize(.regular)
            } else {
                Button {
                    Task { await service.loadModel(service.selectedModel) }
                } label: {
                    Label(
                        service.modelLoadState.isReady ? "重新載入" : "載入模型",
                        systemImage: "arrow.down.circle"
                    )
                }
                .buttonStyle(.borderedProminent)
                .disabled(service.isTranscribing)
            }
        }
    }

    private var stateColor: Color {
        switch service.modelLoadState {
        case .notLoaded: return .primary
        case .loading:   return .orange
        case .ready:     return .green
        case .failed:    return .red
        }
    }
}
