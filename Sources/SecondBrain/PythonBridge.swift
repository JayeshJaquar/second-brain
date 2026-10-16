import Foundation
import AppKit
import MemoryCore

struct BackendMemory: Decodable {
    let id: UUID; let title: String; let source: String; let created_at: Double; let text: String
    let has_image: Int
    func native() -> Memory {
        var m = Memory(title: title, source: source, text: text)
        m.id = id; m.createdAt = Date(timeIntervalSince1970: created_at); m.hasImage = has_image != 0
        return m
    }
}
struct BackendAnswer: Decodable {
    struct Citation: Decodable, Identifiable {
        let id: Int; let memory_id: UUID; let title: String; let source: String; let quote: String; let created_at: Double
    }
    let message: String; let citations: [Citation]; let warnings: [String]; let mode: String; let candidate_count: Int
}

@MainActor final class PythonBridge {
    static let shared = PythonBridge()
    private var process: Process?
    private let base = URL(string: "http://127.0.0.1:8765")!
    private let tokenURL = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/SecondBrain/backend.token")
    private let session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.connectionProxyDictionary = [:]
        return URLSession(configuration: config, delegate: RejectBackendRedirects(), delegateQueue: nil)
    }()
    private func healthy() async -> Bool {
        var request = URLRequest(url: base.appendingPathComponent("health")); request.timeoutInterval = 1
        guard let (data, response) = try? await session.data(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200,
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: String] else { return false }
        return object["service"] == "second-brain" && object["version"] == "0.2.0"
    }
    func connect() async throws {
        if await healthy() { return }
        if process?.isRunning != true {
            guard let root = Bundle.main.object(forInfoDictionaryKey: "SecondBrainProjectRoot") as? String else {
                throw failure("Rebuild the app with scripts/build-app.sh to configure the Python backend.")
            }
            let directory = URL(fileURLWithPath: root)
            let executable = directory.appendingPathComponent(".venv/bin/python")
            guard FileManager.default.isExecutableFile(atPath: executable.path) else { throw failure("Run scripts/setup-python.sh first.") }
            let child = Process(); child.executableURL = executable; child.arguments = ["-m", "brain"]
            child.currentDirectoryURL = directory.appendingPathComponent("backend")
            var environment = ProcessInfo.processInfo.environment
            environment["HF_HUB_OFFLINE"] = "1"; environment["TOKENIZERS_PARALLELISM"] = "false"
            child.environment = environment; child.standardOutput = FileHandle.nullDevice; child.standardError = FileHandle.nullDevice
            try child.run(); process = child
        }
        for _ in 0..<100 {
            if await healthy() { return }
            try await Task.sleep(for: .milliseconds(300))
        }
        throw failure("Python engine did not start. Run scripts/start-backend.sh to inspect its startup error.")
    }
    private func failure(_ message: String) -> NSError { NSError(domain: "PythonBackend", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
    func request(_ path: String, method: String = "GET", body: [String: Any]? = nil) async throws -> Data {
        let token = try String(contentsOf: tokenURL, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines)
        var request = URLRequest(url: base.appendingPathComponent(path)); request.httpMethod = method; request.timeoutInterval = 240
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if let body { request.httpBody = try JSONSerialization.data(withJSONObject: body); request.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        let (data, response) = try await session.data(for: request)
        guard let status = (response as? HTTPURLResponse)?.statusCode, (200..<300).contains(status) else {
            let object = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            throw failure(object?["detail"] as? String ?? "Python engine request failed.")
        }
        return data
    }
    func memories() async throws -> [Memory] {
        let data = try await request("api/memories")
        return try JSONDecoder().decode([BackendMemory].self, from: data).map { $0.native() }
    }
    func ask(_ question: String, scope: UUID?) async throws -> BackendAnswer {
        var body: [String: Any] = ["question": question, "mode": "rerank"]
        if let scope { body["memory_id"] = scope.uuidString.lowercased() }
        return try JSONDecoder().decode(BackendAnswer.self, from: await request("api/ask", method: "POST", body: body))
    }
    func openStudio() {
        do {
            let token = try String(contentsOf: tokenURL, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines)
            var parts = URLComponents(url: base, resolvingAgainstBaseURL: false)!
            parts.fragment = "token=\(token)"
            if let url = parts.url { NSWorkspace.shared.open(url) }
        } catch { /* The app's connect state reports a missing backend. */ }
    }
    func stopOwnedProcess() { process?.terminate(); process = nil }
}
private final class RejectBackendRedirects: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
}
