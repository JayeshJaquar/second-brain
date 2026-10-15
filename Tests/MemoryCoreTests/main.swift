import Foundation
import MemoryCore

func check(_ condition: Bool, _ message: String) throws {
    if !condition { throw NSError(domain: "MemoryChecks", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
}

let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
defer { try? FileManager.default.removeItem(at: directory) }
let url = directory.appendingPathComponent("memories.json")
let store = try MemoryStore(url: url)
let note = Memory(title: "Recursion", source: "Lecture", text: "A base case terminates recursion.")
try check(try store.add(note), "Initial insert")
try check(try !store.add(note), "Reject duplicate")
try check(try !store.add(Memory(title: "Empty", source: "", text: "  \n")), "Reject empty text")
let reopened = try MemoryStore(url: url)
try check(reopened.search("BASE lecture").map(\.id) == [note.id], "Persist and search across fields")
try check(reopened.search("calculus").isEmpty, "Unmatched search")
try reopened.delete(id: note.id)
try check(try MemoryStore(url: url).memories.isEmpty, "Persist deletion")
let invalid = Data("broken".utf8)
try invalid.write(to: url)
var rejected = false
do { _ = try MemoryStore(url: url) } catch { rejected = true }
try check(rejected, "Reject corrupt store")
try check(try Data(contentsOf: url) == invalid, "Preserve corrupt file")
print("PASS: insert, duplicate/empty rejection, reopen, multi-term search, deletion, corrupt-data preservation")
