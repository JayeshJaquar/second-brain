import SwiftUI
import ScreenCaptureKit
import MemoryCore

@MainActor final class BrainModel: ObservableObject {
    @Published var memories: [Memory] = []
    @Published var allMemories: [Memory] = []
    @Published var windows: [SCWindow] = []
    @Published var selectedWindow: UInt32 = 0
    @Published var draft = ""
    @Published var draftPNG: Data?
    @Published var keepScreenshot = true
    @Published var title = ""
    @Published var source = "Manual note"
    @Published var query = "" { didSet { refresh() } }
    @Published var status = "Local only · Capture starts when you click Capture once."
    @Published var busy = false
    @Published var revision = 0
    private var store: MemoryStore?

    init() {
        do {
            let base = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                                  appropriateFor: nil, create: true)
            store = try MemoryStore(url: base.appendingPathComponent("SecondBrain/memories.json"))
            refresh()
        } catch { status = "Cannot open memory store: \(error.localizedDescription). Existing data has not been replaced." }
    }
    func refresh() { allMemories = store?.memories ?? []; memories = store?.search(query) ?? [] }
    func loadWindows() async {
        busy = true; defer { busy = false }
        do {
            windows = try await Capture.windows()
            selectedWindow = windows.first?.windowID ?? 0
            status = windows.isEmpty ? "No visible windows. Bring the window onto this desktop and refresh." : "Choose a window, then capture once."
        } catch { status = "Window access failed: \(error.localizedDescription). Check Screen Recording permission and relaunch if needed." }
    }
    func capture() async {
        guard let window = windows.first(where: { $0.windowID == selectedWindow }) else { return }
        busy = true; status = "Capturing the window, including images, and reading text…"
        defer { busy = false }
        do {
            let capture = try await Capture.snapshot(from: window)
            draft = capture.text; draftPNG = capture.png
            title = window.title ?? "Captured window"; source = Capture.label(window)
            status = "Review the screenshot and text before saving. Only visible content was captured."
        } catch { status = "Capture failed: \(error.localizedDescription)" }
    }
    func clearDraft() { draft = ""; title = ""; source = "Manual note"; draftPNG = nil }
    func save() {
        guard let store else { status = "Memory store unavailable. Nothing saved."; return }
        do {
            let memory = Memory(title: title.isEmpty ? "Untitled memory" : title, source: source,
                                text: draft, screenshotPNG: keepScreenshot ? draftPNG : nil)
            if try store.add(memory) {
                clearDraft(); refresh(); revision += 1; status = "Saved on this Mac. Find it in Memories or ask across all memories."
            } else { status = "Empty or duplicate memory. Nothing added." }
        } catch { status = "Save failed: \(error.localizedDescription)" }
    }
    func delete(_ id: UUID) {
        do { try store?.delete(id: id); refresh(); revision += 1; status = "Memory and its stored image deleted from the active store." }
        catch { status = "Delete failed: \(error.localizedDescription)" }
    }
}

@main struct SecondBrainApp: App {
    @StateObject private var model = BrainModel()
    var body: some Scene {
        WindowGroup("Second Brain", id: "main") { BrainView(model: model) }
            .defaultSize(width: 1180, height: 820)
        MenuBarExtra("Second Brain", systemImage: "brain.head.profile") { MenuContent() }
    }
}
struct MenuContent: View {
    @Environment(\.openWindow) private var openWindow
    var body: some View {
        Button("Open Second Brain") { openWindow(id: "main"); NSApp.activate(ignoringOtherApps: true) }
        Text("Manual capture only")
        Divider()
        Button("Quit") { NSApp.terminate(nil) }
    }
}

struct BrainView: View {
    @ObservedObject var model: BrainModel
    @State private var selected: UUID?
    @State private var tab = 0
    @State private var pendingDelete: UUID?
    var body: some View {
        NavigationSplitView {
            List(model.memories, selection: $selected) { memory in
                VStack(alignment: .leading, spacing: 5) {
                    Label(memory.title, systemImage: memory.screenshotPNG == nil ? "doc.text" : "photo.on.rectangle")
                        .font(.headline).lineLimit(2)
                    Text(memory.source).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                    Text(memory.createdAt, style: .date).font(.caption2)
                }.padding(.vertical, 4).tag(memory.id)
            }
            .searchable(text: $model.query, prompt: "Filter memories")
            .navigationTitle("Memories (\(model.memories.count))")
            .navigationSplitViewColumnWidth(min: 220, ideal: 280)
        } detail: {
            VStack(alignment: .leading, spacing: 12) {
                Text("Your learning, remembered.").font(.largeTitle.bold())
                Text(model.status).font(.callout).foregroundStyle(.secondary).textSelection(.enabled)
                TabView(selection: $tab) {
                    CaptureView(model: model).tabItem { Label("Capture", systemImage: "camera") }.tag(0)
                    AskView(model: model, selected: $selected, tab: $tab)
                        .tabItem { Label("Ask memories", systemImage: "bubble.left.and.text.bubble.right") }.tag(1)
                    ScrollView {
                        if let memory = model.allMemories.first(where: { $0.id == selected }) {
                            VStack(alignment: .leading, spacing: 14) {
                                HStack {
                                    Text(memory.title).font(.title2)
                                    Spacer()
                                    Button("Delete", role: .destructive) { pendingDelete = memory.id }
                                }
                                Text("\(memory.source) · \(memory.createdAt.formatted())").font(.caption).textSelection(.enabled)
                                if let data = memory.screenshotPNG, let image = NSImage(data: data) {
                                    Text("Stored screenshot · diagrams and images preserved").font(.headline)
                                    Image(nsImage: image).resizable().scaledToFit()
                                }
                                Text("Extracted text / notes").font(.headline)
                                Text(memory.text.isEmpty ? "No text extracted. The image is available for viewing." : memory.text)
                                    .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                            }.padding()
                        } else {
                            ContentUnavailableView("Select a memory to inspect", systemImage: "doc.text.image",
                                                   description: Text("You can ask across all memories without selecting one."))
                        }
                    }.tabItem { Label("Saved memory", systemImage: "book") }.tag(2)
                }
            }.padding(22).frame(minWidth: 650, minHeight: 620)
        }
        .onChange(of: selected) { _, _ in tab = 2 }
        .confirmationDialog("Delete this memory and its image?", isPresented: Binding(get: { pendingDelete != nil }, set: { if !$0 { pendingDelete = nil } })) {
            Button("Delete memory", role: .destructive) { if let id = pendingDelete { model.delete(id) }; pendingDelete = nil }
            Button("Cancel", role: .cancel) { pendingDelete = nil }
        }
    }
}

struct CaptureView: View {
    @ObservedObject var model: BrainModel
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Button("Refresh windows") { Task { await model.loadWindows() } }
                    Picker("Window", selection: $model.selectedWindow) {
                        Text("Choose a window").tag(UInt32(0))
                        ForEach(model.windows, id: \.windowID) { Text(Capture.label($0)).tag($0.windowID) }
                    }
                    Button("Capture once") { Task { await model.capture() } }
                        .disabled(model.selectedWindow == 0 || !model.draft.isEmpty || model.draftPNG != nil)
                }.disabled(model.busy)
                if model.busy { ProgressView() }
                Toggle("Save screenshot with this memory (includes images and diagrams)", isOn: $model.keepScreenshot)
                Text("Screenshots can include browser tabs and other visible private details. Review before saving. Everything stays on this Mac.")
                    .font(.caption).foregroundStyle(.secondary)
                TextField("Title", text: $model.title)
                TextField("Source or URL", text: $model.source)
                if let data = model.draftPNG, let image = NSImage(data: data) {
                    Image(nsImage: image).resizable().scaledToFit().frame(maxHeight: 300)
                }
                Text("Review extracted text, or write a note").font(.headline)
                TextEditor(text: $model.draft).font(.system(.body, design: .monospaced)).frame(height: 180).border(.quaternary)
                HStack {
                    Button("Save memory") { model.save() }.buttonStyle(.borderedProminent)
                        .disabled(model.busy || (model.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !(model.keepScreenshot && model.draftPNG != nil)))
                    Button("Clear draft") { model.clearDraft() }.disabled(model.busy)
                }
            }.padding()
        }
    }
}

struct AskView: View {
    @ObservedObject var model: BrainModel
    @Binding var selected: UUID?
    @Binding var tab: Int
    @State private var question = ""
    @State private var selectedOnly = false
    @State private var result: GroundedAnswer?
    @State private var errorMessage = ""
    @State private var task: Task<Void, Never>?
    @State private var busy = false
    private func cancel() { task?.cancel(); task = nil; busy = false }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Ask across all saved memories").font(.title2)
            Text("Strict evidence mode: answers are verified excerpts, not free-form guesses. No matching evidence means no answer. Keyword retrieval may miss paraphrases.")
                .foregroundStyle(.secondary)
            Toggle("Search only the selected memory", isOn: $selectedOnly).disabled(selected == nil)
            TextField("Ask a question — no memory selection required", text: $question)
                .textFieldStyle(.roundedBorder)
            HStack {
                Button(busy ? "Finding evidence…" : "Ask local AI") {
                    let memories = selectedOnly ? model.allMemories.filter { $0.id == selected } : model.allMemories
                    task = Task { @MainActor in
                        busy = true; result = nil; errorMessage = ""
                        do {
                            let response = try await GroundedAssistant.answer(question: question, memories: memories)
                            if !Task.isCancelled { result = response }
                        } catch { if !Task.isCancelled { errorMessage = error.localizedDescription } }
                        if !Task.isCancelled { busy = false }
                    }
                }.buttonStyle(.borderedProminent).disabled(busy || question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                if busy { Button("Cancel") { cancel() }; ProgressView().controlSize(.small) }
            }
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if !errorMessage.isEmpty { Text(errorMessage).foregroundStyle(.red) }
                    if let result {
                        Text(result.message).textSelection(.enabled)
                        ForEach(result.citations) { citation in
                            Button {
                                selected = citation.passage.memoryID; tab = 2
                            } label: {
                                VStack(alignment: .leading) {
                                    Text("[\(citation.id)] \(citation.passage.title)")
                                    Text("\(citation.passage.source) · \(citation.passage.capturedAt.formatted())").font(.caption)
                                }
                            }.buttonStyle(.link)
                        }
                        Text("Searched \(result.candidates.count) candidate passages. Verified quotations show what the source says; they do not prove that the source is correct or fully answers your question.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            Text("Local Qwen · images preserved for viewing; AI uses extracted text only").font(.caption).foregroundStyle(.secondary)
        }.padding()
        .onChange(of: model.revision) { _, _ in cancel(); result = nil; errorMessage = "" }
        .onChange(of: selectedOnly) { _, _ in cancel(); result = nil }
        .onChange(of: selected) { _, _ in if selectedOnly { cancel(); result = nil } }
        .onDisappear { cancel() }
    }
}
