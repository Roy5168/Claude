// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SpeechToText",
    platforms: [
        .iOS(.v16),
        .macOS(.v13)
    ],
    dependencies: [
        .package(
            url: "https://github.com/argmaxinc/WhisperKit",
            from: "0.9.0"
        )
    ],
    targets: [
        .executableTarget(
            name: "App",
            dependencies: [
                .product(name: "WhisperKit", package: "WhisperKit")
            ],
            path: "Sources/App"
        )
    ]
)
