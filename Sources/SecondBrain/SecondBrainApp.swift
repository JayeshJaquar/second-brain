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
    @Published var query = "" { didSet { filter() } }
    @Published var status = "Local only · Capture starts when you click Capture once."
    @Published var busy = false
    @Published var revision = 0
    @Published var ready = false
    @Published var sessionActive = false
    @Published var excludedApps = UserDefaults.standard.string(forKey: "excludedApps") ?? "1Password,Keychain Access,System Settings"
    @Published var draftOCR: [[String: Any]] = []
    private var sessionTask: Task<Void, Never>?
    private let backend = PythonBridge.shared
    init() {
        Task { await connect() }
    }
    func connect() async {
        do {
            status = "Starting the local Python engine…"
            try await backend.connect(); try await refresh(); ready = true
            status = "Python engine connected · SQLite memory · Local AI"
        } catch { status = "Cannot connect: \(error.localizedDescription)" }
    }
    func filter() {
        let words = query.split(whereSeparator: { $0.isWhitespace })
        memories = allMemories.filter { m in words.allSatisfy { "\(m.title) \(m.source) \(m.text)".localizedCaseInsensitiveContains($0) } }
    }
    func refresh() async throws {
        let updated = try await backend.memories()
        if updated.map(\.id) != allMemories.map(\.id) { revision += 1 }
        allMemories = updated; filter()
    }
    func loadImage(_ id: UUID?) async {
        guard let id, let index = allMemories.firstIndex(where: { $0.id == id }), allMemories[index].hasImage == true else { return }
        do {
            let data = try await backend.request("api/memories/\(id.uuidString.lowercased())/image")
            if let current = allMemories.firstIndex(where: { $0.id == id }) { allMemories[current].screenshotPNG = data; filter() }
        } catch { status = "Image unavailable: \(error.localizedDescription)" }
    }
    func allowed(_ window: SCWindow) -> Bool {
        let blocked = excludedApps.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces).lowercased() }.filter { !$0.isEmpty }
        let app = window.owningApplication?.applicationName.lowercased() ?? ""
        return !blocked.contains(where: { app.contains($0) })
    }
    func stopSession() { sessionTask?.cancel(); sessionTask = nil; sessionActive = false }
    func startSession() {
        guard selectedWindow != 0 else { return }
        sessionActive = true
        sessionTask = Task { @MainActor in
            while !Task.isCancelled {
                if draft.isEmpty && draftPNG == nil && !busy { await capture() }
                do { try await Task.sleep(for: .seconds(30)) } catch { break }
            }
        }
    }
    func loadWindows() async {
        busy = true; defer { busy = false }
        do {
            UserDefaults.standard.set(excludedApps, forKey: "excludedApps")
            windows = try await Capture.windows().filter { allowed($0) }
            if !windows.contains(where: { $0.windowID == selectedWindow }) { selectedWindow = 0 }
            status = windows.isEmpty ? "No visible windows. Bring the window onto this desktop and refresh." : "Choose a window, then capture once."
        } catch { status = "Window access failed: \(error.localizedDescription). Check Screen Recording permission and relaunch if needed." }
    }
    func capture() async {
        guard let window = windows.first(where: { $0.windowID == selectedWindow }), allowed(window) else { status = "This application is excluded from capture."; stopSession(); return }
        busy = true; status = "Capturing the window, including images, and reading text…"
        defer { busy = false }
        do {
            guard let currentWindow = try await Capture.windows().first(where: { $0.windowID == window.windowID }), allowed(currentWindow) else {
                stopSession(); status = "The selected window is no longer available."; return
            }
            let capture = try await Capture.snapshot(from: currentWindow)
            if Task.isCancelled { return }
            draft = capture.text; draftPNG = capture.png; draftOCR = capture.regions
            title = currentWindow.title ?? "Captured window"; source = Capture.label(currentWindow)
            status = "Review the screenshot and text before saving. Only visible content was captured."
        } catch { stopSession(); status = "Capture failed: \(error.localizedDescription)" }
    }
    func clearDraft() { draft = ""; title = ""; source = "Manual note"; draftPNG = nil; draftOCR = [] }
    func save() async {
        guard ready else { return }
        busy = true; defer { busy = false }
        do {
            var body: [String: Any] = ["title": title.isEmpty ? "Untitled memory" : title, "source": source, "text": draft,
                                       "kind": draftPNG == nil ? "note" : "ocr", "ocr": draftOCR]
            if keepScreenshot, let data = draftPNG { body["screenshotPNG"] = data.base64EncodedString() }
            _ = try await backend.request("api/memories", method: "POST", body: body)
            clearDraft(); try await refresh(); revision += 1; status = "Saved in local SQLite memory."
        } catch { status = "Save failed: \(error.localizedDescription)" }
    }
    func delete(_ id: UUID) async {
        do {
            _ = try await backend.request("api/memories/\(id.uuidString.lowercased())", method: "DELETE")
            try await refresh(); revision += 1; status = "Deleted from the active database, including dependent images, indexes and practice records."
        } catch { status = "Delete failed: \(error.localizedDescription)" }
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
        Text("Review captures before saving")
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
                    Label(memory.title, systemImage: memory.hasImage != true ? "doc.text" : "photo.on.rectangle")
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
                HStack { Button("Open Learning Studio") { PythonBridge.shared.openStudio() }.disabled(!model.ready)
                    Button("Refresh memories") { Task { try? await model.refresh() } }
                    if !model.ready { Button("Reconnect") { Task { await model.connect() } } } }
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
        .onChange(of: selected) { _, value in tab = 2; Task { await model.loadImage(value) } }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in if model.ready { Task { try? await model.refresh() } } }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in model.stopSession(); PythonBridge.shared.stopOwnedProcess() }
        .confirmationDialog("Delete this memory and its image?", isPresented: Binding(get: { pendingDelete != nil }, set: { if !$0 { pendingDelete = nil } })) {
            Button("Delete memory", role: .destructive) { if let id = pendingDelete { Task { await model.delete(id) } }; pendingDelete = nil }
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
                TextField("Excluded apps (comma-separated)", text: $model.excludedApps)
                HStack {
                    Button(model.sessionActive ? "Stop capture session" : "Start review-before-save session") {
                        if model.sessionActive { model.stopSession() } else { model.startSession() }
                    }.disabled(model.selectedWindow == 0 && !model.sessionActive)
                    Text(model.sessionActive ? "Session active · checks every 30s; waits for draft review" : "Session stopped")
                        .font(.caption)
                }
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
                    Button("Save memory") { Task { await model.save() } }.buttonStyle(.borderedProminent)
                        .disabled(!model.ready || model.busy || (model.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !(model.keepScreenshot && model.draftPNG != nil)))
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
    @State private var result: BackendAnswer?
    @State private var errorMessage = ""
    @State private var task: Task<Void, Never>?
    @State private var busy = false
    private func cancel() { task?.cancel(); task = nil; busy = false }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Ask across all saved memories").font(.title2)
            Text("Strict evidence mode: answers are verified excerpts, not free-form guesses. No matching evidence means no answer. Python combines keyword and semantic search, then reranks evidence.")
                .foregroundStyle(.secondary)
            Toggle("Search only the selected memory", isOn: $selectedOnly).disabled(selected == nil)
            TextField("Ask a question — no memory selection required", text: $question)
                .textFieldStyle(.roundedBorder)
            HStack {
                Button(busy ? "Finding evidence…" : "Ask local AI") {
                    let scope = selectedOnly ? selected : nil
                    task = Task { @MainActor in
                        busy = true; result = nil; errorMessage = ""
                        do {
                            let response = try await PythonBridge.shared.ask(question, scope: scope)
                            if !Task.isCancelled { result = response }
                        } catch { if !Task.isCancelled { errorMessage = error.localizedDescription } }
                        if !Task.isCancelled { busy = false }
                    }
                }.buttonStyle(.borderedProminent).disabled(!model.ready || busy || question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                if busy { Button("Cancel") { cancel() }; ProgressView().controlSize(.small) }
            }
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if !errorMessage.isEmpty { Text(errorMessage).foregroundStyle(.red) }
                    if let result {
                        Text(result.message).textSelection(.enabled)
                        ForEach(result.citations) { citation in
                            Button {
                                selected = citation.memory_id; tab = 2
                            } label: {
                                VStack(alignment: .leading) {
                                    Text("[\(citation.id)] \(citation.title)")
                                    Text("\(citation.source) · \(Date(timeIntervalSince1970: citation.created_at).formatted())").font(.caption)
                                }
                            }.buttonStyle(.link)
                        }
                        ForEach(result.warnings, id: \.self) { Text($0).font(.caption) }
                        Text("Search: \(result.mode). Searched \(result.candidate_count) candidate passages. Verified quotations show what the source says; they do not prove that the source is correct or fully answers your question.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            Text("Python + local Qwen · diagram interpretation and practice in Learning Studio").font(.caption).foregroundStyle(.secondary)
        }.padding()
        .onChange(of: model.revision) { _, _ in cancel(); result = nil; errorMessage = "" }
        .onChange(of: selectedOnly) { _, _ in cancel(); result = nil }
        .onChange(of: selected) { _, _ in if selectedOnly { cancel(); result = nil } }
        .onDisappear { cancel() }
    }
}
