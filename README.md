# Second Brain

A local macOS learning assistant with a **Python AI engine**, a Swift capture client, and a browser-based Learning Studio. Save material you read, ask questions across your memories, inspect source excerpts, and practise recall. No paid AI APIs or cloud inference are required.

## What works

- **Capture:** choose a visible Mac window, preserve a PNG and Apple Vision OCR with confidence/coordinates, then review before saving. Optional 30-second sessions pause while a draft awaits review. App exclusions and stop controls are available. Capture is not automatic surveillance or full-document ingestion.
- **Memory:** SQLite stores text, provenance, chunks, vectors, practice events and traces; hash-addressed PNGs live in a separate attachments folder. Duplicate saves are detected. Old JSON memories import once and remain as a rollback backup.
- **Question answering:** search all saved memories, or restrict to one. BM25 and transformer embeddings can be fused, with optional cross-encoder reranking. The local LLM selects evidence IDs; the app displays exact stored excerpts with citations or abstains. Optional generated explanations have a separate warning.
- **Vision:** a local vision-language model proposes diagram labels and relationships. These remain unverified and are deliberately excluded from text answers.
- **Practice:** create source-backed questions, reveal answers, record your own recall and hint use, and see due reviews. A rule-based spaced schedule works immediately; an experimental learned recall estimate requires at least 50 genuine events with both outcomes.
- **Agent:** a bounded model-driven loop searches memories, reads retrieved sources and proposes quiz drafts. Its tool trace is visible; a person must save a draft.
- **ML/DL experiments:** train TF-IDF and embedding-based logistic classifiers and a PyTorch neural topic head on frozen transformer embeddings. Reproducible synthetic fixtures, splits, baselines, loss curves and evaluations are included.

This is a research prototype. It does not continuously retrain the LLM, prove mastery from screen time, browse current news automatically, or eliminate hallucinations. Current information must be imported. A cited excerpt may be irrelevant or factually wrong.

## Setup on macOS

Tested on Apple M2, 16 GB RAM, macOS with Swift 6.2 and Python 3.13.7. The native app targets macOS 14+. Install Xcode Command Line Tools, Python 3.13, and Ollama. Start Ollama, then from the repository:

```sh
# Ensure python3 points to Python 3.13 for the tested lockfile.
sh scripts/setup-python.sh
ollama pull qwen2.5:7b-instruct
# Optional visual interpretation, approximately 3.2 GB:
ollama pull qwen2.5vl:3b
sh scripts/build-app.sh
open "dist/Second Brain.app"
```

Setup downloads Python packages and the two pinned search models. Runtime search loads local files only; inference uses Ollama on loopback. Downloaded model licences apply to their respective models. Weights, private memories, tokens and screenshots are not in Git.

The app starts the Python service and opens Learning Studio through **Open Learning Studio**. Alternatively, `sh scripts/start-backend.sh` starts it at `http://127.0.0.1:8765`. For manual browser login, the local token is in the private data directory; do not paste it into issues or commit it. The app transfers it using a URL fragment, which the page removes and keeps in session storage.

Grant Screen Recording permission to the built app when you want capture. Ad-hoc signing can require permission renewal after rebuilding. A configured stable code-signing identity can be supplied using `SECOND_BRAIN_SIGNING_IDENTITY`; the build script does not create certificates or change trust settings. No valid identity was available on the development Mac, so this remains a setup limitation.

## Your data

Default directory: `~/Library/Application Support/SecondBrain/`.

| Item | Purpose |
| --- | --- |
| `brain.sqlite3` | Active memories, chunks, embedding vectors, practice history, visual descriptions, agent traces |
| `attachments/<hash>.png` | Original saved screenshots, shared by identical images |
| `backend.token` | Local API authentication, owner-readable only |
| `memories.json` | Retained legacy backup, if present; no longer the active store |

Deleting a memory removes its dependent active records and unreferenced screenshot; it also clears agent traces to avoid retaining excerpts. **Legacy JSON, exports and system backups remain.** The database is not application-encrypted. Storage/privacy offers a retention preview before explicit deletion. `SECOND_BRAIN_DATA` can select an isolated Python data directory; the native client expects the default directory.

## Reproduce the work

```sh
(cd backend && ../.venv/bin/python -m pytest -q)
sh scripts/build-app.sh
.build/release/MemoryChecks
python3 -m unittest discover -s research/evaluation -p 'test_*.py'

# Search and ML experiments; downloaded search weights required:
.venv/bin/python backend/experiments/evaluate.py
.venv/bin/python backend/experiments/train_neural_topic.py
.venv/bin/python backend/experiments/scale_check.py

# Explicit integration tests with local Ollama:
.venv/bin/python backend/experiments/live_checks.py
.venv/bin/python backend/experiments/vision_checks.py
```

`evaluate.py` also writes the optional local topic suggestion model. It is trained on tiny synthetic data and is not a reliable personal classifier. The neural head is a measured research experiment, not the production classifier. CI runs offline unit checks and the native build, not LLM downloads or live model tests.

## Evidence and navigation

- [Architecture and database](ARCHITECTURE.md)
- [Visual explanation](docs/how-it-works.md)
- [Engineering decision history](decisions.md)
- [Latest results and known limitations](test-results/2026-10-16-python-engine.md)
- [Portfolio claims and next experiments](PORTFOLIO_PLAN.md)
- [Security and privacy boundary](SECURITY.md)
- [Contributing and validation](CONTRIBUTING.md)

The current live grounding suite passes **5 of 6** checks; one supported fictional fact still causes a false refusal. The agent integration check passes. These small synthetic checks do not establish real-world accuracy. See the full reports rather than treating any single metric as an overall quality score.
