# Milestone evaluation protocol

## What is and is not independent

`backend/data/milestone-v3/benchmark.json` was frozen in commit `8cf97e7` on 20 October, before implementation and first execution. Its SHA-256 is recorded in `manifest.json` and checked by the evaluator and CI. The agent authored the questions, documents and labels. They were not independently human reviewed. This supplies a reproducible held-out fixture, **not an independent real-world benchmark**.

Development has four source documents and six questions. Test has sixteen different source documents and twenty-four questions; each split is searched only against its own source pool. Cases cover code, college exercises, news, explicit diagram captions, absent visual information, a screened instruction injection, negation, missing facts, near-matches and fictional facts. No personal memories enter these experiments. Diagram cases do not evaluate pixels or OCR quality.

## Frozen scoring rules

- Retrieve top-five *passages*, not deduplicated documents. Recall@5 is the fraction of annotated `(document, exact excerpt)` pairs retrieved. MRR@5 uses the first matching passage. Only cases with gold evidence enter retrieval metrics (17 test questions).
- Strict answer pass requires the exact gold citation set and `supported` status. A conflict case additionally requires the conflict flag. Missing-evidence/clarification cases require their expected status and no citations.
- Gold excerpt match precision counts returned citation pairs matching the gold labels divided by all returned citations. It is not semantic entailment or truth verification. Additional useful but unlabelled context can lower it.
- Unsupported-answer rate counts returned citations on cases annotated missing-evidence, divided by those cases (six test cases).
- False-refusal rate counts abstained/clarify/rejected statuses on annotated answerable cases (seventeen test cases). Errors are reported separately, not hidden as refusals or removed from strict pass counts.
- Answer p50/p95 includes retrieval and local generation/model loading. No generated explanations were requested. Retrieval-load performance is measured in a separate run without concurrent LLM work.

The first run is retained unchanged. No answering prompt, evidence guard or labels were altered after inspecting it. Code and dataset hashes are in the report. Future work may use these observed failures as development cases, but must then evaluate against a *new* unseen test set.

## Baseline and performance comparison

The historical retriever is loaded from commit `18e9e59`, with a recorded code hash. Historical and current retrieval use the same source passages, pinned encoder/reranker revisions and prebuilt vectors. The answering model is recorded by Ollama tag, not an immutable LLM digest; a later tag change is a reproducibility limit.

The performance experiment uses 1,000 and 5,000 original synthetic memories (two chunks each), 20 warm queries per mode/engine, and alternating engine order. The first query has an already-loaded encoder and a cold retrieval cache; it is not cold app startup. Reported p95 is an empirical percentile from a small single-machine run. SQLite and Python BM25 tokenize/score differently, so speed does not imply ranking equivalence. Exact dense scoring remains linear; images, LLM generation, power consumption and large concurrent workloads are outside this measurement.

Unit tests separately verify that saving/deleting can proceed while embedding encoding is deliberately blocked and that deleting during indexing does not resurrect vectors. These are synchronization checks, not throughput benchmarks.

## Human review and the next dataset

Give a separate reviewer the source documents, questions and `human-review-template.json`, ideally without model outputs. Ask them to check answerability, minimal supporting excerpts, ambiguity and whether a conflict flag is justified. For example, test-12 expects a conflict flag for two dated schedule revisions; a reviewer may reasonably distinguish historical change from contradiction. Preserve this original score and record any revised label in a new dataset version.

For stronger external validity, collect consented real questions and document-disjoint sources from coding, college material and news; include independent question authors, adversarial near-matches and ambiguous questions. Predeclare scoring and thresholds before running the next frozen test. Neither adding a human review template nor having CI check its hash counts as completed human validation.
