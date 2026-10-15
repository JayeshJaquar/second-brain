# Second Brain for macOS

Portfolio direction and measurable ML/AI milestones: [PORTFOLIO_PLAN.md](PORTFOLIO_PLAN.md). Offline retrieval baseline and evaluation: [research/README.md](research/README.md).

A native, local-first starting point for a personal learning assistant. Requires macOS 14 or newer and Swift 5.9 or newer. No third-party packages or API key required for this milestone.

## What works in this milestone

- Native window and menu-bar entry.
- Explicit one-shot capture of a selected window using ScreenCaptureKit.
- On-device OCR using Vision. Screenshots are held in memory, not written to disk.
- Review/edit extracted text before saving; manual notes work without screen permission.
- Local persistence, keyword search across source/title/text, exact duplicate suppression, and deletion.
- Error handling for permission failures, empty OCR, and unreadable memory files.

This is a capture-and-recall prototype with local questions about a selected memory. It does not yet include cross-memory AI retrieval, semantic retrieval, continuous observation, quizzes, mastery estimates, or news updates. OCR may lose reading order, equations, and code indentation. A screen capture provides visible content only, not an entire document or a reliable browser URL.

## Build and use

From this directory:

```sh
sh scripts/build-app.sh
```

Open `dist/Second Brain.app` in Finder. Start by saving a manual note and searching for it. To capture a window, click **Refresh windows**, grant macOS Screen Recording permission if requested, select a window, and click **Capture once**. Review the draft, add a source URL if known, and save. Clear or save an existing draft before capturing again.

If permission fails, check System Settings → Privacy & Security → Screen Recording (the label can vary with macOS version), enable Second Brain, and quit/reopen the app. Rebuilding an ad-hoc-signed app can require permission to be granted again. This prototype is not notarized or prepared for distribution.

## Data and permissions

Saved text is at `~/Library/Application Support/SecondBrain/memories.json`. Files are restricted to the local user but are **not application-encrypted**. System backups may retain deleted data. AI questions connect only to the local Ollama endpoint at 127.0.0.1:11434, using qwen2.5:7b-instruct. Redirects are rejected. There are no cloud requests, analytics, background recording, accessibility permission, microphone access, or full-disk access in this version. Window titles are listed when you request the window list; only the selected window is captured.

Do not use multiple running copies against the same store. JSON is a temporary storage implementation for a small prototype; migrate to transactional SQLite before background capture or larger-scale usage.

## Verification

```sh
CLANG_MODULE_CACHE_PATH="$PWD/.build/clang-cache" swift run --disable-sandbox --cache-path "$PWD/.build/cache" MemoryChecks
```

Tests cover persistence after reopening, multi-term search, duplicate/empty rejection, deletion, and corrupt-data preservation. Screen capture and OCR require an interactive permission-granted check on the Mac.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and staged setup.

## Local AI setup (₹0 API budget)

This Mac has an M2 chip, 16 GB RAM, and Ollama with `qwen2.5:7b-instruct` already installed. Keep Ollama running, select a saved memory, enter a question, and click **Ask local AI**. The app sends only the selected memory excerpt (first 6,000 characters) and question to the local service. Answers are not persisted; changing selection clears them. The model uses a 4,096-token context and a 600-token output limit. Large/non-Latin excerpts may exceed the token budget and be truncated by the runtime. Generated answers can be wrong; check the displayed original. This milestone does not search the web.

The model does not need an API key, subscription, or additional plugin. Local processing still consumes RAM, battery, and electricity. Avoid continuous inference; request assistance when needed.
