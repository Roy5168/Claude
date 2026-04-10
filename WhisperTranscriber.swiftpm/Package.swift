// swift-tools-version: 6.0
import PackageDescription
import AppleProductTypes

let package = Package(
    name: "WhisperTranscriber",
    platforms: [
        .iOS("26.0")
    ],
    products: [
        .iOSApplication(
            name: "WhisperTranscriber",
            targets: ["WhisperTranscriber"],
            displayVersion: "1.0",
            bundleVersion: "1",
            appIcon: .placeholder(icon: .microphone),
            accentColor: .presetColor(.blue),
            supportedDeviceFamilies: [
                .pad,
                .phone
            ],
            supportedInterfaceOrientations: [
                .portrait,
                .landscapeRight,
                .landscapeLeft,
                .portraitUpsideDown(.when(deviceFamilies: [.pad]))
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
            path: "Sources",
            swiftSettings: [
                .enableUpcomingFeature("BareSlashRegexLiterals")
            ]
        )
    ]
)

