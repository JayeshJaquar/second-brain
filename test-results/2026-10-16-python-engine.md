# Python engine verification — 16 October 2026

Environment: Apple M2, 16 GB RAM; Python 3.13.7; Swift 6.2. Package lock and search-model revisions are committed. Fixtures are original synthetic material; no personal captures or tokens are published.

## Automated and live checks

- Python engine: 19 unit/regression tests passing. Covers migration, image/dedup/deletion, source spans, injection screening, retrieval scopes/fallback, evidence validation, practice history, agent bounds, API authorization/origin, request limits and concurrent deletion.
- Native release build and transfer/legacy-decoding checks: passing.
- Historical research metric tests: 5 passing.
- Real local Qwen grounding: **5/6 passing**. The supported fictional-capital case still falsely abstains. The script correctly exits with failure; it is not a green suite.
- Real local agent: search → draft quiz → finish; draft cites known evidence and is not automatically saved.
- Real local vision: Study→Practice→Review labels, relationships and “17 days” recovered; image-only memory remains outside text evidence. The model also falsely claimed the title was cut off. This is one controlled diagram, not an accuracy benchmark.
- Native/Python integration: existing three memories loaded; a saved fine-tuning question produced cited source evidence through Python.
- Learning Studio: local token login, library browsing, practice-card save and answer reveal exercised. No correctness outcome was fabricated; personal recall modelling remains inactive without sufficient genuine history.

## Retrieval and training

36 synthetic documents across six topics; grouped splits of 18 train / 6 development / 12 test. Retrieval uses 24 answerable test queries. Source ranking deduplicates chunks. The test set was not used for hyperparameter or default selection.

| Search | Recall@5 | MRR@5 |
| --- | ---: | ---: |
| Lexical BM25 | 0.875 | 0.875 |
| Dense transformer | 1.000 | 0.938 |
| Hybrid rank fusion | 1.000 | 0.951 |
| Hybrid + cross-encoder | 0.958 | 0.958 |

Reranking slightly improves reciprocal rank over fusion but loses recall here. This small result cannot justify a general claim of superiority.

Topic macro-F1: TF-IDF logistic **0.600**; frozen-embedding logistic **0.911**; trained PyTorch nonlinear head **0.911**. The transformer is frozen. Only 12 test documents are involved; these results are not estimates of personal or general-world performance.

## Storage scale check

Synthetic lexical-only lookup returned the intended first result at 100, 1,000 and 5,000 documents. At 5,000 documents the database was about 6 MB and the measured query took about 49 ms on this Mac. This excludes screenshot storage, dense inference, concurrency and startup costs. BM25 currently scans candidates in Python; FTS5 is maintained but not used in the ranking query.

## Known limitations

False refusals remain. Valid evidence IDs do not prove relevance, truth or entailment. Optional explanations and visual interpretation remain explicitly unverified. Conflict detection is model-assisted; broad-question clarification is a small heuristic. The recall estimate has a minimum-data gate and evaluation code, but no genuine personal model has yet been demonstrated. Native screen capture still requires valid macOS permission; no stable signing identity was available. Packaging the Python runtime into a standalone distribution is future work.

Raw reports: [retrieval/classification](python-evaluation-v1.json), [neural training](neural-topic-v1.json), [live grounding and agent](python-live-v1.json), [vision](vision-v1.json), [storage scale](storage-scale-v1.json).
