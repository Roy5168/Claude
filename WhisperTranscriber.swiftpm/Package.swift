// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "WhisperTranscriber",
    platforms: [
        .iOS(.v17)
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

