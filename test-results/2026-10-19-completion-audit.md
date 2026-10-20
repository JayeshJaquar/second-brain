# Completion audit and evaluation — 19 October 2026

All published data here is original synthetic material. Experiments use local models, not paid APIs. Personal study outcomes were not fabricated or changed for testing.

## Verification

- Python: **29 tests pass**, including new additive schema migration, HTML/raw preservation, clarification, generated-claim filtering, visual-attribute guards, answer/correction persistence and shadow-gate checks.
- Native release build and memory transfer/legacy compatibility check: pass.
- Browser scripts: syntax checks pass; CI includes them.
- Original live grounding regression: **6/6**, agent integration pass. The formerly refused fictional capital is now extracted from the source. The old 5/6 report remains unchanged.
- Expanded labeled answer set: **14/14**, including 6 answerable, 6 unanswerable and 2 clarification cases. On these cases: supported answer rate 6/6, false refusal 0/6, false support 0/6, correct source selection among returned answers 6/6.
- Important intermediate failure: before the visual-attribute guard, 2 of the 6 missing-evidence cases incorrectly returned OCR labels for color/arrow questions. That report is retained. The guard is conservative and does not establish general semantic entailment.

## Diagram comparison

Same `qwen2.5vl:3b`, same questions/choices, same exact authored text; image condition additionally receives pixels. Three original diagrams, 12 questions. Text labels are supplied directly, so this isolates visual information rather than OCR extraction accuracy.

| Condition | Correct diagram answers | Appropriate response given available input | Abstentions |
| --- | ---: | ---: | ---: |
| Text only | 6/12 | 5/12 | 2 |
| Image + text | 12/12 | 12/12 | 0 |

The text-only model guessed visual attributes despite instructions; this is another reason that its statements are not automatically accepted into memory evidence. Multiple choice and tiny authored diagrams can overestimate open-world capability. The result is not a guarantee for arbitrary screenshots.

## Learning and scheduling

On 500 seeded synthetic events, chronological 400/100 validation produced Brier 0.1722 versus baseline 0.2142, and log loss 0.5272 versus baseline 0.6198. The script compares the rule interval with learned suggestions across four hypothetical histories. This validates the mechanism, not human learning benefit. No active due date is changed by the shadow policy.

Shadow suggestions require ≥50 total events to fit, at least 20 held-out outcomes with both classes, lower held-out Brier than the mean baseline, and a negative elapsed-time coefficient. Personal data and a prospective study are needed to establish usefulness.

## Browser and native integration

The exact Chrome extraction function was tested on an original page: six intended content blocks retained; navigation, advertisement, hidden false fact and test controls excluded. A JSON export was downloaded. The automated file chooser was blocked by the controlling browser extension's file-URL setting; no extra browser access was granted. The same exported JSON was then pasted into Studio, previewed without saving, and explicitly saved in an isolated store on port 8767. A typed test recall, hint and correction were saved; history showed the correction and next-day due date. This did not touch the personal library.

The rebuilt native app started successfully against SQLite schema 2; all three existing memories remained and the personal practice-event count remained zero. A live Studio explanation correctly stated the 17-day cycle with its citation and support-check warning.

Activation update, 20 October: the user reported loading the optional Chrome extension. The original fixture was opened successfully in Chrome for the installed-popup check; its outcome is awaiting user confirmation. This is distinct from the already completed extraction-function and Studio import tests. Code-signing readiness found zero valid identities; the user chose to retain ad-hoc signing, so no Keychain trust or certificate changes were made.

## Reproduce and inspect

- [Live regression v2](python-live-v2.json) versus [historical v1](python-live-v1.json)
- [Expanded answers](answer-quality-v2.json) and [pre-guard failure](answer-quality-v2-before-visual-guard.json)
- [Paired vision](vision-comparison-v2.json)
- [Synthetic scheduling comparison](scheduling-comparison-v2.json)
- [Requirement-by-requirement audit](../docs/improvement-status.md)

Run the experiment scripts listed in README. Fixtures are development cases, including cases used to guide fixes; do not label them as an independent held-out answer/vision benchmark. The retrieval classifier split remains the earlier grouped experiment, separate from these new answer cases.
