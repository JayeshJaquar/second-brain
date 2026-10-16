import Foundation
import MemoryCore

let legacy = """
[{"id":"00000000-0000-0000-0000-000000000001","createdAt":0,"title":"Legacy","source":"test","text":"Old text"}]
"""
let decoded = try JSONDecoder().decode([Memory].self, from: Data(legacy.utf8))
precondition(decoded.first?.screenshotPNG == nil && decoded.first?.hasImage == nil)
var note = Memory(title: "Test", source: "Synthetic", text: "A base case stops recursion.")
note.hasImage = true
let reopened = try JSONDecoder().decode(Memory.self, from: JSONEncoder().encode(note))
precondition(reopened == note)
print("PASS: native memory DTO and legacy JSON compatibility. Engine tests live in backend/tests.")
