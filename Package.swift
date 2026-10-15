// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SecondBrain",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "SecondBrain", targets: ["SecondBrain"])],
    targets: [
        .target(name: "MemoryCore"),
        .executableTarget(name: "SecondBrain", dependencies: ["MemoryCore"]),
        .executableTarget(name: "MemoryChecks", dependencies: ["MemoryCore"], path: "Tests/MemoryCoreTests")
    ]
)
