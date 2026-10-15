import Foundation

public struct Passage: Identifiable, Equatable, Sendable {
    public let id: String
    public let memoryID: UUID
    public let title: String
    public let source: String
    public let capturedAt: Date
    public let text: String
    public let score: Double
}

public enum Retrieval {
    /// Conservative defense-in-depth. This can exclude legitimate articles discussing prompts;
    /// it is not a complete prompt-injection detector or a source-truth classifier.
    public static func containsInstructionOverride(_ text: String) -> Bool {
        let patterns = [
            #"\b(ignore|disregard|forget|override)\b[\s\S]{0,90}\b(instructions?|rules?|user|system|previous|above|prompt)\b"#,
            #"\b(system|developer|assistant)\s*(override|message|instruction|:)"#,
            #"<\|?(system|assistant|developer|im_start)\b"#,
            #"\b(mark|set)\b[\s\S]{0,40}\b(supported|conflict)\b"#,
            #"\b(return|output|respond with)\b[\s\S]{0,45}\b(json|passageID|supported)\b"#,
            #"\byou are now\b"#
        ]
        return patterns.contains { text.range(of: $0, options: [.regularExpression, .caseInsensitive]) != nil }
    }
    private static let stop = Set("a an the is are was were be been being to of and or in on at for from by with as it its this that these those i me my you your we our what which who how why when where do does did can could would should will please tell explain according about give answer saved memory memories article note notes".split(separator: " ").map(String.init))

    public static func terms(_ text: String) -> [String] {
        text.lowercased().components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { !$0.isEmpty && !stop.contains($0) }
    }

    public static func chunks(_ text: String, size: Int = 1200, overlap: Int = 200) -> [String] {
        guard size > 0, overlap >= 0, overlap < size else { return [] }
        let chars = Array(text)
        var result: [String] = [], start = 0
        while start < chars.count {
            let end = min(start + size, chars.count)
            result.append(String(chars[start..<end]))
            if end == chars.count { break }
            start = end - overlap
        }
        return result
    }

    public static func search(_ question: String, in memories: [Memory], limit: Int = 4) -> [Passage] {
        let query = Set(terms(question))
        guard !query.isEmpty, limit > 0 else { return [] }
        let candidates = memories.filter { !containsInstructionOverride($0.text) }.flatMap { memory in
            chunks(memory.text).enumerated().map { index, text in
                Passage(id: "\(memory.id.uuidString):\(index)", memoryID: memory.id,
                        title: memory.title, source: memory.source, capturedAt: memory.createdAt,
                        text: text, score: 0)
            }
        }
        guard !candidates.isEmpty else { return [] }
        let counts = candidates.map { Dictionary(terms($0.text).map { ($0, 1) }, uniquingKeysWith: +) }
        let lengths = counts.map { $0.values.reduce(0, +) }
        let average = max(1, Double(lengths.reduce(0, +)) / Double(lengths.count))
        var frequencies: [String: Int] = [:]
        for terms in counts { for term in terms.keys { frequencies[term, default: 0] += 1 } }
        return candidates.indices.compactMap { index -> Passage? in
            let candidate = candidates[index]
            var score = 0.0
            for term in query {
                let frequency = Double(counts[index][term, default: 0])
                guard frequency > 0 else { continue }
                let df = Double(frequencies[term, default: 0])
                let idf = log(1 + (Double(candidates.count) - df + 0.5) / (df + 0.5))
                score += idf * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * Double(lengths[index]) / average))
            }
            guard score > 0 else { return nil }
            // Titles help rank matches but cannot make a text-free image into textual evidence.
            score += Double(query.intersection(Set(terms(candidate.title))).count) * 0.1
            return Passage(id: candidate.id, memoryID: candidate.memoryID, title: candidate.title,
                           source: candidate.source, capturedAt: candidate.capturedAt, text: candidate.text, score: score)
        }.sorted { $0.score == $1.score ? $0.id < $1.id : $0.score > $1.score }.prefix(limit).map { $0 }
    }
}
