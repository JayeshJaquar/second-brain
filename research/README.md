# Research track

This directory preserves the original offline lexical baseline and browser fixtures. The current Python engine and model evaluations live in `backend/`; some fixture code exercises shipped features. It uses public/synthetic fixtures only. Do not commit personal screen captures, memory-store exports, quiz histories, secrets, or copyrighted article bodies without permission.

Run from the project root, with Python 3:

```sh
python3 -m unittest discover -s research/evaluation -p 'test_*.py'
python3 research/evaluation/baseline.py
```

No downloads or extra packages are required. The six-document, five-query fixture only verifies pipeline wiring; its scores are not portfolio performance claims. Pass `--dataset path/to/labeled.json` to evaluate a properly labeled corpus with the same schema. Relevant IDs must refer to documents in that corpus.

The source-grouped corpus, chunking, pinned transformer models and comparisons are now implemented in `backend/data` and `backend/experiments`. See `test-results/2026-10-19-completion-audit.md` for current evidence and `docs/improvement-status.md` for remaining setup boundaries.

See ../PORTFOLIO_PLAN.md for milestones and honest CV scope.
