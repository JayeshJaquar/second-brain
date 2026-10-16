# Contributing

Use Python 3.13 for the tested dependency lock and the macOS Swift toolchain for the capture client. Run `sh scripts/setup-python.sh` for the Python environment and pinned local search weights. Do not modify real user memories to create test fixtures.

Run the Python unit suite from `backend` with `../.venv/bin/python -m pytest -q`, build with `sh scripts/build-app.sh`, run `.build/release/MemoryChecks`, and run the historical metric tests with `python3 -m unittest discover -s research/evaluation -p 'test_*.py'`.

Live Ollama experiments are explicit, separate checks; a model outage must not silently fall back to a paid or remote provider. Keep known failures in reports. Never weaken an expected result just to produce a green test report.

Add an append-only entry to `decisions.md` for architectural changes, including motivation, evidence, tradeoffs and remaining uncertainty. Update architecture/setup documentation when boundaries change. Keep dependencies and model revisions reproducible and record dataset hashes, splits, model settings and limitations in experiments.

Do not add personal data, tokens, model weights, build output or screenshots to Git. Changes involving deletion, retrieval grounding, model actions or learning estimates need focused tests of user-visible behaviour, not only tests mirroring implementation.
