# Portfolio evidence and remaining work

## Defensible description

Built a local-first macOS learning assistant with a Python/FastAPI engine, SQLite memory, multimodal capture, hybrid transformer retrieval, evidence-constrained local LLM responses, and a bounded tool-using study agent. Implemented reproducible retrieval evaluations and trained classical and neural topic classifiers; added practice-driven recall modelling with chronological validation.

Use the accompanying results and limitations. Do not say that the system is hallucination-free, learns mastery by watching, continually trains an LLM, or achieves general-world accuracy measured by this tiny synthetic dataset.

## Concepts genuinely implemented

| Concept | Evidence |
| --- | --- |
| Python engineering | API, storage, ingestion, retrieval, generation, agent, vision, learning, evaluation and tests |
| ML | TF-IDF and embedding logistic topic classifiers; history-gated recall regression |
| DL | PyTorch nonlinear topic head, dropout, AdamW, validation loss and trained weights |
| Transformers | Frozen MiniLM embeddings and cross-encoder reranking |
| LLM / GenAI | Local Qwen evidence selection; optional explanation and generated quiz wording |
| Agentic AI | Model-selected actions with argument validation, source constraints, step budget and trace |
| Data engineering | SQLite migration, versioned chunks/vectors, image deduplication, cascading deletion |
| Evaluation | Grouped splits, held-out retrieval/classification, baseline comparison, negative grounding checks |

Swift remains the appropriate native capture/client layer. Increasing Python's line count is not the aim; ownership of the intelligence and its reproducible experiments is the substantive change.

## Questions to be ready for

- **Why is this more than an LLM wrapper?** Explain storage/migration, retrieval variants, grounding validation, learning events, tool boundaries and your measured experiments.
- **How do you know the answer came from memory?** The default output is stored excerpts selected by validated IDs. Relevance is still a model decision; citation validation is not truth validation.
- **What did you train?** Small classifiers and a neural head on pretrained embeddings. Show train/dev/test splits and loss curves; do not claim to have trained Qwen or MiniLM.
- **Does reranking always help?** No. In the recorded tiny test, reranking improves reciprocal rank slightly over fusion but loses Recall@5. The ranking mode is selectable; test data was not used to tune it.
- **How does it know weaknesses?** Genuine quiz outcomes and hint use supply limited evidence. Passive observation does not. Recall modelling is gated and experimental.
- **Can a malicious article control it?** Source text is untrusted. Patterns provide imperfect screening; the tool whitelist and explicit saving constrain effects even if a model follows bad text.
- **What happens when I delete a source?** Active dependent records and unused images are deleted, traces cleared, and in-flight answers invalidated. Legacy/system backups remain.
- **How do you handle conflicting or old news?** Preserve source dates and versions and ask the model to flag conflicts. Automated truth checking and reliable conflict detection are not established.
- **What is the bottleneck at scale?** Current lexical/dense scoring scans candidates. The 5,000-document storage test excludes images, dense inference and concurrent workloads.

## Next work requiring evidence or setup

1. Collect consented real questions, corrected topics and genuine practice events. Maintain a held-out evaluation set; compare topic/model changes against baselines.
2. Fix the recorded fictional-fact false refusal without introducing false support; expand contradiction, OCR, code and adversarial cases before claiming improvement.
3. Measure generated-claim entailment and visual relationship correctness; leave generated interpretations separate until supported by evidence.
4. Benchmark larger libraries, then adopt FTS5 candidate generation and an approximate vector index only if the measurements justify complexity.
5. Package the Python runtime and configure a stable signing identity for reliable installation and permission continuity. The current build assumes the checkout remains in place.
6. Consider LoRA fine-tuning only after data quantity, consent, evaluation and hardware budget justify it. No training for keyword coverage alone.
