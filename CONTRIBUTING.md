# Contributing

Use small, descriptive commits with actual timestamps. Never backdate work or claim unfinished features. Run the offline checks and build before submitting changes. Changes to retrieval, prompts, or evidence handling need corresponding positive and negative tests. Report live-model results separately from deterministic unit checks.

Do not commit captures, personal memory stores, credentials, local model weights, build outputs, or scraped article bodies. Use synthetic or redistributable public fixtures. Keep sources and dates for third-party material.

For larger changes, explain the user-visible behavior, tradeoffs, data migration, and verification. Do not introduce background capture, automatic cloud transmission, or agent tool access without an explicit user-controlled boundary.
