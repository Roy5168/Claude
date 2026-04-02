# H.265 影片轉換器

使用 VideoToolbox 硬體加速（M5 晶片），將任意格式影片轉為 H.265 (HEVC) MP4。

## 支援格式

| 輸入 | 輸出 |
|------|------|
| MOV, MP4, MKV, AVI, WMV, FLV, M4V | H.265 HEVC MP4 |

## 建置步驟（Xcode on Mac 或 iPad）

### Mac + Xcode
1. 開啟 Xcode → File → New → Project → iOS App
2. 命名為 `VideoConverter`，語言選 Swift，介面選 SwiftUI
3. 將 `Sources/VideoConverter/` 下的三個 `.swift` 檔案拖入專案
4. 刪除預設產生的 `ContentView.swift`（已被取代）
5. `Info.plist` 加入以下 key：
   - `NSDocumentsFolderUsageDescription` → "用於讀取影片檔案"
   - `UIFileSharingEnabled` → YES
   - `LSSupportsOpeningDocumentsInPlace` → YES
6. 選擇目標裝置為你的 M5 iPad Pro，Build & Run

### Swift Playgrounds（iPad 直接執行）
1. 建立新 App Playground
2. 將三個 Swift 檔案的內容貼入對應頁面
3. 注意：Swift Playgrounds 不支援 `@main`，請手動呼叫 `ContentView()`

## 架構說明

```
VideoConverterApp.swift   ← App 進入點
ContentView.swift         ← SwiftUI 介面（檔案選擇、畫質選擇、進度、分享）
VideoConverter.swift      ← 核心轉換邏輯（actor，執行緒安全）
```

## 技術重點

- **AVAssetExportSession** + HEVC preset → 自動啟用 VideoToolbox 硬體加速
- **actor** 封裝轉換邏輯 → Swift Concurrency 安全
- `shouldOptimizeForNetworkUse = true` → moov atom 移至檔頭，適合串流播放
- 720p 模式使用 `AVMutableVideoComposition` 等比縮放
- `UIDocumentPickerViewController` 支援 iCloud Drive、Files App 任意來源
