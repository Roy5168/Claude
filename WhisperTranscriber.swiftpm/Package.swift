// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "WhisperTranscriber",
    platforms: [
        .iOS(.v17)
    ],
    products: [
        .iOSApplication(
            name: "WhisperTranscriber",
            targets: ["WhisperTranscriber"],
            bundleIdentifier: "com.whisper.transcriber",
            displayVersion: "1.0",
            bundleVersion: "1",
            appIcon: .placeholder(icon: .microphone),
            accentColor: .presetColor(.blue),
            supportedDeviceFamilies: [
                .pad,
                .phone
            ],
            orientation: .all,
            capabilities: [
                .outgoingNetworkConnections()
            ]
        )
    ],
    dependencies: [
        .package(
            url: "https://github.com/argmaxinc/WhisperKit.git",
            from: "0.9.0"
        )
    ],
    targets: [
        .executableTarget(
            name: "WhisperTranscriber",
            dependencies: [
                .product(name: "WhisperKit", package: "WhisperKit")
            ],
            path: "Sources"
        )
    ]
)
