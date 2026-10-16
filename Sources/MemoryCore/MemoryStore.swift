import Foundation

public struct Memory: Codable, Identifiable, Equatable {
    public var id: UUID
    public var createdAt: Date
    public var title: String
    public var source: String
    public var text: String
    public var screenshotPNG: Data?
    public var hasImage: Bool?
    public init(title: String, source: String, text: String, screenshotPNG: Data? = nil) {
        id = UUID(); createdAt = Date()
        self.title = title; self.source = source; self.text = text
        self.screenshotPNG = screenshotPNG
    }
}
