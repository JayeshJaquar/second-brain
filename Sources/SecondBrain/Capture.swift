import AppKit
import ScreenCaptureKit
import Vision

enum Capture {
    static func windows() async throws -> [SCWindow] {
        let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
        return content.windows.filter {
            $0.owningApplication?.processID != ProcessInfo.processInfo.processIdentifier &&
            $0.frame.width > 80 && $0.frame.height > 80 && $0.windowLayer == 0
        }.sorted { label($0).localizedCaseInsensitiveCompare(label($1)) == .orderedAscending }
    }

    static func label(_ window: SCWindow) -> String {
        "\(window.owningApplication?.applicationName ?? "App") — \(window.title ?? "Untitled window")"
    }

    struct Result { let text: String; let png: Data; let regions: [[String: Any]] }

    static func snapshot(from window: SCWindow) async throws -> Result {
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let config = SCStreamConfiguration()
        let scale = min(2.0, 4096.0 / max(window.frame.width, window.frame.height))
        config.width = max(1, Int(window.frame.width * scale))
        config.height = max(1, Int(window.frame.height * scale))
        config.showsCursor = false
        let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        return try await Task.detached(priority: .userInitiated) {
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = false
            try VNImageRequestHandler(cgImage: image).perform([request])
            let text = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
            guard let png = NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:]) else {
                throw NSError(domain: "Capture", code: 1, userInfo: [NSLocalizedDescriptionKey: "Could not encode the screenshot."])
            }
            let regions: [[String: Any]] = (request.results ?? []).compactMap { observation in
                guard let candidate = observation.topCandidates(1).first else { return nil }
                let box = observation.boundingBox
                return ["text": candidate.string, "confidence": candidate.confidence,
                        "x": box.minX, "y": box.minY, "width": box.width, "height": box.height]
            }
            return Result(text: text, png: png, regions: regions)
        }.value
    }
}
