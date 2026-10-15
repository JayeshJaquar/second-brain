# Second Brain

A local macOS learning-memory prototype: capture selected windows, preserve screenshots and extracted text, and ask a local LLM to find supporting evidence across saved memories.

**Status:** working prototype, not a finished autonomous learning assistant. SwiftUI + ScreenCaptureKit + Vision + a dependency-free Swift retrieval engine + Ollama. No paid API required.

## Implemented

- Explicit one-shot window capture; preview before saving.
- Screenshots preserve images, diagrams and flowcharts, alongside OCR text. Image-only captures are supported. Screenshot storage can be switched off before saving.
- Existing text-only memories remain readable. Data stays in the user's Application Support directory, outside the repository.
- **Ask memories** searches all saved text by default. Selecting a memory is optional; a toggle restricts the scope when useful.
- BM25-style keyword retrieval over overlapping chunks, including content beyond the old 6,000-character cutoff. Up to four candidate passages go to the local model.
- **Strict evidence mode:** the model selects quotes using a JSON schema. The app verifies quote membership and source IDs (allowing only whitespace differences from OCR wrapping, then displaying the original source), rejects invalid evidence, and attaches clickable citations itself. It displays verified excerpts rather than unrestricted generated explanations.
- Conservative instruction-override screening excludes suspicious memories before retrieval; it can also exclude legitimate prompt-security material and is not a complete injection detector.
- No matching evidence means an abstention. No fallback to cloud AI or general pretrained answers.
- Saved screenshots can be viewed in the Saved memory tab. Deleting a memory removes its embedded screenshot from the active store.

## Important limits

The installed `qwen2.5:7b-instruct` model is **text-only**. Screenshots are retained for viewing; only OCR and user-written notes participate in AI answers. It cannot reliably interpret arrows, colors, geometry, or image meaning. A future local vision model needs its own validation. Legacy memories do not gain screenshots retroactively.

Exact-quote verification prevents invented answer wording from being displayed, but does not prove a quotation is relevant, complete, true, or free of misleading context. Retrieval can miss paraphrases, OCR can be wrong, and a source can contain false statements or hostile instructions. The app is not hallucination-free. Conflict detection is model-assisted, not guaranteed. Search is lexical, not embedding-based semantic search yet.

Only the visible window is captured. There is no automatic scrolling, background recording, continuous monitoring, quiz scheduling, trained mastery predictor, or agent execution. See [portfolio plan](PORTFOLIO_PLAN.md) for future work.

## Requirements and setup

- macOS 14+, Swift 5.9+ command-line tools (full Xcode optional).
- Ollama running locally with `qwen2.5:7b-instruct` installed for AI answers.
- Screen Recording permission for Second Brain when using screen capture. Manual notes and memory search do not need that permission.

```sh
sh scripts/build-app.sh
```

Open `dist/Second Brain.app` in Finder. This local build is ad-hoc signed, not notarized. Rebuilding may require Screen Recording permission to be granted again.

1. In **Capture**, refresh windows and choose one visible on your current desktop.
2. Click **Capture once**, inspect its screenshot and OCR, add a source URL if known, and save.
3. In **Ask memories**, enter a question without selecting any memory.
4. Follow a source button to inspect the saved text and screenshot.

If Ollama is not installed, use its [official instructions](https://docs.ollama.com/quickstart). Download the model with `ollama pull qwen2.5:7b-instruct`. The model is approximately 4.7 GB on disk; runtime memory is additional. This development machine has an M2 and 16 GB RAM, but performance varies with other applications and prompt size.

## Data and privacy

`~/Library/Application Support/SecondBrain/memories.json` holds memories, with optional PNG data encoded in each record. The store is atomically replaced and restricted to the local user; it is **not application-encrypted**. Screenshots can contain private information visible in the selected window. Backups may retain deleted data.

The embedded-image JSON format is appropriate only for a small prototype: images increase file size and rewrite costs. SQLite plus managed image attachments is a planned scaling step. Use one running app instance against a store. Do not commit or upload your memory file.

AI requests go to the fixed loopback address `127.0.0.1:11434`, with redirects rejected and explicit proxies disabled. The app selects a local model and contains no cloud integration, analytics, or outbound web search. It does not change Ollama's global settings or other apps' network behavior.

## Tests

```sh
CLANG_MODULE_CACHE_PATH="$PWD/.build/clang-cache" swift run --disable-sandbox --cache-path "$PWD/.build/cache" MemoryChecks
python3 -m unittest discover -s research/evaluation -p 'test_*.py'
python3 research/evaluation/baseline.py
```

With local Ollama running, test the actual app's retrieval/client/validator using synthetic memories:

```sh
.build/release/MemoryChecks --live
```

Live model checks can fail on false abstentions even when offline tests pass; observed runs and unresolved limitations are recorded in the report. Live tests include invented facts with/without memory, related questions with missing answers, a deliberately fictional fact that contradicts common model knowledge, and source prompt injection. They never load your personal store. See [test results](test-results/) for observed outcomes; a small smoke suite is not a comprehensive safety or quality benchmark.

## Layout

- `Sources/SecondBrain`: native interface, screenshot capture and OCR.
- `Sources/MemoryCore`: persistence, chunk retrieval, local model client and evidence validation.
- `Tests/MemoryCoreTests`: executable offline and optional live checks; works without XCTest.
- `research`: offline BM25 baseline, metrics, synthetic fixtures and research protocol.
- `.github/workflows`: build and offline checks, no secrets or cloud inference.

[Architecture](ARCHITECTURE.md) · [Portfolio and ML plan](PORTFOLIO_PLAN.md) · [Contributing](CONTRIBUTING.md) · [Security and data handling](SECURITY.md)
