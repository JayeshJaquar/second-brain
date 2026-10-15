import SwiftUI
import ScreenCaptureKit
import MemoryCore

@MainActor final class BrainModel: ObservableObject {
    @Published var memories: [Memory] = []
    @Published var windows: [SCWindow] = []
    @Published var selectedWindow: UInt32 = 0
    @Published var draft = ""
    @Published var title = ""
    @Published var source = "Manual note"
    @Published var query = "" { didSet { refresh() } }
    @Published var status = "Local only · Capture is off until you click Capture once."
    @Published var busy = false
    private var store: MemoryStore?

    init() {
        do {
            let base = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                                  appropriateFor: nil, create: true)
            store = try MemoryStore(url: base.appendingPathComponent("SecondBrain/memories.json"))
            refresh()
        } catch { status = "Cannot open memory store: \(error.localizedDescription). Existing data has not been replaced." }
    }
    func refresh() { memories = store?.search(query) ?? [] }
    func loadWindows() async {
        busy = true; defer { busy = false }
        do {
            windows = try await Capture.windows()
            selectedWindow = windows.first?.windowID ?? 0
            status = windows.isEmpty ? "No eligible windows. Open a window and refresh." : "Choose a window, then capture once."
        } catch { status = "Window access failed: \(error.localizedDescription). Check Screen Recording permission in System Settings and relaunch if needed." }
    }
    func capture() async {
        guard let window = windows.first(where: { $0.windowID == selectedWindow }) else { return }
        busy = true; status = "Capturing selected window and reading text…"
        defer { busy = false }
        do {
            let text = try await Capture.text(from: window)
            draft = text; title = window.title ?? "Captured window"; source = Capture.label(window)
            status = text.isEmpty ? "No text detected. Nothing was saved." : "Review and edit the text, then save. The screenshot is not stored."
        } catch { status = "Capture failed: \(error.localizedDescription)" }
    }
    func save() {
        guard let store else { status = "Memory store unavailable. Nothing saved."; return }
        do {
            let memory = Memory(title: title.isEmpty ? "Untitled memory" : title, source: source, text: draft)
            if try store.add(memory) {
                draft = ""; title = ""; source = "Manual note"; refresh(); status = "Saved on this Mac."
            } else { status = "Empty or duplicate memory. Nothing added." }
        } catch { status = "Save failed: \(error.localizedDescription)" }
    }
    func delete(_ id: UUID) {
        do { try store?.delete(id: id); refresh(); status = "Memory deleted from the app’s active store." }
        catch { status = "Delete failed: \(error.localizedDescription)" }
    }
}

@main struct SecondBrainApp: App {
    @StateObject private var model = BrainModel()
    var body: some Scene {
        WindowGroup("Second Brain", id: "main") { BrainView(model: model) }
            .defaultSize(width: 1100, height: 740)
        MenuBarExtra("Second Brain", systemImage: "brain.head.profile") {
            MenuContent()
        }
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
    @State private var pendingDelete: UUID?
    @State private var question = ""
    @State private var answer = ""
    @State private var answering = false
    @State private var answerTask: Task<Void, Never>?
    var body: some View {
        NavigationSplitView {
            List(model.memories, selection: $selected) { memory in
                VStack(alignment: .leading, spacing: 5) {
                    Text(memory.title).font(.headline).lineLimit(2)
                    Text(memory.source).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                    Text(memory.createdAt, style: .date).font(.caption2)
                }.padding(.vertical, 4).tag(memory.id)
            }
            .searchable(text: $model.query, prompt: "Search memories")
            .navigationTitle("Memories (\(model.memories.count))")
            .navigationSplitViewColumnWidth(min: 240, ideal: 280)
        } detail: {
            VStack(alignment: .leading, spacing: 14) {
                Text("Your learning, remembered.").font(.largeTitle.bold())
                Text(model.status).font(.callout).foregroundStyle(.secondary).textSelection(.enabled)
                HStack {
                    Button("Refresh windows") { Task { await model.loadWindows() } }
                    Picker("Window", selection: $model.selectedWindow) {
                        Text("Choose a window").tag(UInt32(0))
                        ForEach(model.windows, id: \.windowID) { window in
                            Text(Capture.label(window)).tag(window.windowID)
                        }
                    }
                    Button("Capture once") { Task { await model.capture() } }
                        .disabled(model.selectedWindow == 0 || !model.draft.isEmpty)
                }.disabled(model.busy)
                if model.busy { ProgressView().controlSize(.small) }
                Text("Capture or write a note").font(.headline)
                TextField("Title", text: $model.title)
                TextField("Source or URL (optional)", text: $model.source)
                TextEditor(text: $model.draft).font(.system(.body, design: .monospaced))
                    .frame(minHeight: 120, maxHeight: 200).border(.quaternary)
                HStack {
                    Button("Save memory") { model.save() }.buttonStyle(.borderedProminent)
                        .disabled(model.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || model.busy)
                    Button("Clear draft") { model.draft = ""; model.title = ""; model.source = "Manual note" }
                        .disabled(model.busy)
                    Spacer()
                    Text("No cloud requests • No stored screenshots").font(.caption).foregroundStyle(.secondary)
                }
                Divider()
                if let memory = model.memories.first(where: { $0.id == selected }) {
                    HStack {
                        Text(memory.title).font(.title2)
                        Spacer()
                        Button("Delete", role: .destructive) { pendingDelete = memory.id }
                    }
                    Text("\(memory.source) · \(memory.createdAt.formatted())").font(.caption).textSelection(.enabled)
                    ScrollView { Text(memory.text).frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled) }
                    HStack {
                        TextField("Ask about this memory", text: $question)
                        Button(answering ? "Thinking…" : "Ask local AI") {
                            answerTask = Task { @MainActor in
                                answering = true; answer = ""
                                do {
                                    let result = try await LocalAssistant.answer(question: question, memory: memory)
                                    if !Task.isCancelled { answer = result }
                                } catch {
                                    if !Task.isCancelled { answer = "Could not answer: \(error.localizedDescription)" }
                                }
                                if !Task.isCancelled { answering = false }
                            }
                        }.disabled(answering || question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                    Text("Local AI · qwen2.5:7b-instruct · First 6,000 characters · [1] refers to the selected memory")
                        .font(.caption).foregroundStyle(.secondary)
                    if !answer.isEmpty {
                        ScrollView { Text(answer).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
                            .frame(minHeight: 80, maxHeight: 160)
                    }
                } else {
                    ContentUnavailableView("Your memory starts here", systemImage: "brain.head.profile",
                        description: Text("Save a note or capture a selected window. Choose a memory to read it."))
                }
            }.padding(24).frame(minWidth: 650, minHeight: 650)
        }
        .onChange(of: selected) { _, _ in
            answerTask?.cancel(); answer = ""; answering = false
        }
        .onChange(of: model.memories) { _, _ in
            answerTask?.cancel(); answer = ""; answering = false
        }
        .onDisappear { answerTask?.cancel() }
        .confirmationDialog("Delete this memory?", isPresented: Binding(get: { pendingDelete != nil }, set: { if !$0 { pendingDelete = nil } })) {
            Button("Delete memory", role: .destructive) { if let id = pendingDelete { model.delete(id) }; pendingDelete = nil }
            Button("Cancel", role: .cancel) { pendingDelete = nil }
        }
    }
}
