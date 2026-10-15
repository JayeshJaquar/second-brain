# Second Brain: local adaptive learning assistant

## Objective

Build and evaluate a system that captures user-approved learning material, retrieves relevant evidence, generates grounded explanations, estimates recall from actual practice, and plans bounded learning workflows. Target: Apple M2, 16 GB RAM, zero paid API usage.

ML, deep learning, transformers, LLMs, and generative AI overlap. Describe the actual model, task, data, training/inference procedure, and measured result rather than treating each as an independent feature.

## Capability map

| Area | Implementation target | Evaluation | Status |
| --- | --- | --- | --- |
| Computer vision | Apple Vision OCR of selected windows | Character error rate on manually transcribed samples | Implemented, not benchmarked |
| LLM / transformer inference | Local Qwen 2.5 7B via Ollama | Groundedness, abstention, latency | Single-memory Q&A implemented; one smoke test |
| Information retrieval | BM25 baseline; chunking with source offsets | Recall@5, MRR@5 | Offline baseline implemented |
| Deep learning / NLP | Pretrained sentence-transformer embeddings; optional cross-encoder reranker | Compare dense, lexical, hybrid, reranked retrieval | Planned |
| Generative AI / RAG | Cross-memory explanations, summaries, flashcards with citations | Citation support, answer correctness, unanswerable cases | Planned |
| Classical ML | Logistic regression predicting next recall from quiz evidence | Time-split Brier score, log loss, calibration, baseline comparison | Planned; needs genuine review history |
| Agentic AI | Bounded model-driven tool selection, observations, replanning, stop conditions | Task success, tool validity, unnecessary calls, injection resistance | Planned |
| Training experiment | Train a small topic classifier; compare TF-IDF + linear classifier to frozen transformer embeddings + linear head | Source-grouped macro-F1 and confusion matrix | Planned |
| Optional fine-tuning | Small encoder or LoRA experiment after identifying a measurable failure | Held-out improvement versus unchanged baseline | Stretch goal; not required or implemented |

Using a pretrained deep-learning model is not training one. The classifier experiment trains a small task-specific head; do not describe it as training a transformer. Do not claim the app continually retrains the LLM from screen content.

## Architecture evolution

- Keep SwiftUI, ScreenCaptureKit, and Vision as the native client.
- Introduce a Python research package for reproducible retrieval, classification, and evaluation. Initially run offline on explicit exports or public fixtures.
- Migrate persistence to SQLite with stable document/chunk IDs, versions, provenance, and deletion cascades before automatic ingestion.
- Build BM25 and dense indexes over the same chunks. Fuse rankings, then optionally rerank a small candidate set. Measure quality and latency before adopting the more complex path.
- Keep Ollama inference local and bounded; load one large model at a time. Benchmark memory pressure with normal college/coding apps running.
- Only introduce a loopback Python service when the native app needs the measured research pipeline. Authenticate that service with an app-generated token and keep it off public interfaces.

## Agent design

One orchestrator initially, with structured actions: `search_memory`, `read_source`, `get_due_reviews`, `draft_quiz`, and `finish`. The model selects an allowed action, receives its result, and chooses the next action. Validate arguments and record each step. Maximum five steps and one active workflow. Invalid actions or exhausted budget terminate with a useful explanation. Read-only tools first; saving proposed quizzes requires an explicit app interaction. Captured content cannot grant permissions or execute commands.

A fixed sequence of function calls is a workflow, not evidence of autonomous agent reasoning. Evaluate the model-driven decision loop separately. No multi-agent implementation is required for this design.

## Data and experimental protocol

1. Start with 30–50 non-sensitive documents across coding, college topics, and dated news articles. Store source URL, publication date where available, retrieval date, and redistribution permission. Commit only redistributable fixtures; keep personal captures out of Git.
2. Write at least 50 queries with relevant document IDs and reference answers. Include paraphrases, cross-document questions, dates, ambiguity, and questions the collection cannot answer. The small synthetic fixture in this repository is only a smoke test.
3. Freeze train/development/test splits by source before tuning. Keep duplicate documents and chunks from the same source in one split. Do not use test queries to design prompts or thresholds.
4. Compare lexical, dense, hybrid, and reranked retrieval on identical chunks and queries. Report Recall@5, MRR@5, p50/p95 latency, model/index size, and machine details.
5. Evaluate generation separately: human-rated answer support, correct citations, unsupported assertions, refusal on unanswerable questions, latency. An LLM judge can assist but is not the sole source of truth.
6. Record recall events with timestamps, concept IDs, hints, correctness, and previous review history. Fit the recall predictor only after collecting enough data for meaningful chronological holdout evaluation. Cold-start uses transparent rules. Synthetic records test code but cannot establish learning effectiveness.
7. Evaluate agent tasks with expected outcomes and allowed tools, including hostile instructions embedded in source text. Report success and failure traces.

## Ordered milestones

1. **Now: research foundation.** Run the baseline smoke evaluation; collect a small public corpus and establish labels. Existing native app remains usable.
2. **Retrieval milestone.** SQLite chunk storage, BM25, transformer embeddings, hybrid ranking, offline comparisons, then native cross-memory Q&A.
3. **Learning milestone.** Quiz events, rule-based revision, trained recall predictor when evidence is sufficient, topic-classifier experiment.
4. **Agent milestone.** Validated tool loop, bounded execution, trace viewer, and adversarial tests.
5. **Portfolio release.** Reproducible environment, dataset notes, model cards, experiment report, architecture, limitations, demo video, and setup instructions. Publish only code and permitted fixtures.

## What to put on a CV

Current defensible scope: native macOS capture and OCR, local memory search, and selected-memory Q&A using a pretrained local LLM. Planned features must not be presented as finished.

After evaluation, write bullets around measured outcomes: corpus size, retrieval improvement against BM25, grounded-answer score, and latency on the specified Mac. Never fill these with invented numbers. Be ready to explain chunking, embeddings, attention at a conceptual level, retrieval versus fine-tuning, leakage, calibration, and tool permission boundaries.

## References

- Semantic retrieval: https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html
- Retrieve and rerank: https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html
- Optional parameter-efficient training: https://huggingface.co/docs/peft/en/developer_guides/lora
