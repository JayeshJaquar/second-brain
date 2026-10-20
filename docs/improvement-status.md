# Requested improvement audit — updated 20 October 2026

This tracks both lists the user selected. “Implemented” describes code and the stated tests; it does not imply all setup is activated or that model quality is proven outside the fixtures.

## Foundation sequence

| Requested change | Current status | Evidence |
| --- | --- | --- |
| Labeled evaluation set with stable IDs | Implemented | `corpus-v1.json`, `answer-cases-v2.json`, `diagram-cases-v2.json`; saved rankings, labels, splits and hashes |
| Python storage, chunking and keyword retrieval | Implemented in 0.2 | `store.py`, `ingestion.py`, `retrieval.py`; migration/deletion/source-span regressions |
| Connect Swift to Python | Implemented | `PythonBridge.swift`; app-owned loopback service; native build and library integration |
| Embeddings and baseline comparisons | Implemented | Frozen MiniLM, fusion and cross-encoder; four-mode retrieval report |
| Improve grounding before further agents/fine-tuning | Grounding expanded in 0.3 | Known refusal fixed; 14 authored cases; visual-attribute guard; explanation support check. No new agent tools or LLM fine-tuning added this round. Earlier 0.2 did include an agent before the refusal was resolved; history is not rewritten. |

## Product and technical areas

| Area | Implemented and tested | Remaining boundary |
| --- | --- | --- |
| Semantic search | BM25 + transformer embeddings, reciprocal-rank fusion, optional cross-encoder, selectable baselines | Small synthetic comparison; FTS5 mirror exists but current scoring scans candidates |
| Answer quality | Clarification patterns and choices, exact evidence selection, original citations, optional claim-by-claim support check, explicit refusals and conflicts | Same-model check can fail; rules are conservative heuristics; no hallucination-free claim |
| Storage | SQLite + PNG attachments, idempotent legacy import, schema-2 migration, indexes/vectors and deletion cascades | Backups/exports remain; no app-level encryption; scale check excludes dense/image/concurrent workloads |
| Ingestion | Optional click-triggered Chrome DOM extraction, article/main HTML preference, review-only import, raw input and extraction metadata, existing OCR boxes/confidence | User reports the extension is loaded and confirmed its popup retains the 17-day fact and excludes the advertisement on the original fixture (20 October). Browser extraction tested on an original page; automated file chooser was blocked by the controlling extension, so export→paste preview→save was tested instead. Native screenshot capture still requires macOS permission. |
| Visual understanding | Local VLM; 3 labeled diagrams, 12 questions; paired exact-text versus text+image conditions | 6/12 text-only vs 12/12 image answers on these authored fixtures only. Interpretation is kept separate from grounded text evidence. |
| Personalization | Typed recall, hint count, correction text, earlier-history features, chronological recall validation | Self-assessment can be wrong; real personal training requires enough genuine history. Demo outcomes exist only in an isolated temporary store. |
| Revision | Working rule schedule; learned interval shown in shadow mode only after data, holdout, baseline and monotonic-time gates | Synthetic policy comparison is reproducible; no demonstrated benefit to human recall and no automatic replacement of the rule schedule |
| Reliability/privacy | Explicit sessions, exclusion list, review before save, retention preview, cascade deletion, auth, stop-on-error and signing readiness warning | User chose ad-hoc signing on 19 October. Stable signing intentionally deferred, and macOS may require renewed capture permission. |

## Steps taken in this pass

1. Audited code and existing reports against both lists; identified the incomplete pieces explicitly.
2. Added browser extraction/import and additive schema migration preserving old data.
3. Expanded question clarification and generated-claim support checking; fixed the fictional-source refusal.
4. Ran a broader labeled answer set; found two false-support cases on bare OCR labels. Added a visual-attribute admission guard and retained the failed report. The updated set passes 14/14.
5. Ran paired diagram evaluation using the same VLM in both conditions; kept image interpretations isolated despite the small-test success.
6. Added typed recall/correction history and gated shadow scheduling, then tested their browser and storage behaviour outside the real library.
7. Checked signing readiness; followed the user's decision to keep ad-hoc signing.
8. Updated decisions, architecture, setup, privacy, portfolio claims, CI and reproducible reports. Remote build status is linked in the final handoff.
9. On 20 October, recorded the user's extension installation report and opened the original article in Chrome for a manual popup check. The user confirmed the expected preview. Installation, extraction-function tests and user-confirmed popup verification are tracked separately.

Code verification: [GitHub checks passed for `9a845b7`](https://github.com/JayeshJaquar/second-brain/actions/runs/39270348864). The 20 October follow-up changes documentation only.
