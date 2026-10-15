import Foundation

public struct Memory: Codable, Identifiable, Equatable {
    public var id: UUID
    public var createdAt: Date
    public var title: String
    public var source: String
    public var text: String
    public var screenshotPNG: Data?
    public init(title: String, source: String, text: String, screenshotPNG: Data? = nil) {
        id = UUID(); createdAt = Date()
        self.title = title; self.source = source; self.text = text
        self.screenshotPNG = screenshotPNG
    }
}

public final class MemoryStore {
    public private(set) var memories: [Memory]
    private let url: URL

    public init(url: URL) throws {
        self.url = url
        if FileManager.default.fileExists(atPath: url.path) {
            memories = try JSONDecoder().decode([Memory].self, from: Data(contentsOf: url))
        } else { memories = [] }
    }

    @discardableResult public func add(_ memory: Memory) throws -> Bool {
        guard !memory.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || memory.screenshotPNG != nil else { return false }
        guard !memories.contains(where: { $0.text == memory.text && $0.source == memory.source && $0.screenshotPNG == memory.screenshotPNG }) else { return false }
        try persist([memory] + memories)
        return true
    }

    public func delete(id: UUID) throws {
        try persist(memories.filter { $0.id != id })
    }

    public func search(_ query: String) -> [Memory] {
        let words = query.split(whereSeparator: { $0.isWhitespace }).map(String.init)
        return memories.filter { memory in
            let content = "\(memory.title) \(memory.source) \(memory.text)"
            return words.allSatisfy { content.localizedCaseInsensitiveContains($0) }
        }
    }

    private func persist(_ updated: [Memory]) throws {
        let directory = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true,
                                               attributes: [.posixPermissions: 0o700])
        let data = try JSONEncoder().encode(updated)
        try data.write(to: url, options: .atomic)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
        memories = updated
    }
}
