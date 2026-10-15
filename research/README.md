# Research track

This directory holds offline experiments, not features already shipped in the Mac app. It uses public/synthetic fixtures only. Do not commit personal screen captures, memory-store exports, quiz histories, secrets, or copyrighted article bodies without permission.

Run from the project root, with Python 3:

```sh
python3 -m unittest discover -s research/evaluation -p 'test_*.py'
python3 research/evaluation/baseline.py
```

No downloads or extra packages are required. The six-document, five-query fixture only verifies pipeline wiring; its scores are not portfolio performance claims. Pass `--dataset path/to/labeled.json` to evaluate a properly labeled corpus with the same schema. Relevant IDs must refer to documents in that corpus.

Next: freeze a source-grouped evaluation set, implement chunking, add a pretrained transformer encoder, and compare against this lexical baseline. Pin the chosen model revision, dependencies, preprocessing, splits, and random seeds in the experiment report.

See ../PORTFOLIO_PLAN.md for milestones and honest CV scope.
