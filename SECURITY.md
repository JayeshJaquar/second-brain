# Privacy and security boundaries

The engine binds to loopback and requires a local bearer token for memory APIs, including images. The private data directory uses owner-only permissions. Host/origin checks, early authentication, request limits, static-content CSP and no-store responses reduce accidental exposure. This is not a multi-user security boundary against malicious software running as the same OS user.

No cloud fallback, arbitrary URL fetching, shell execution, messaging or remote model code is available to the agent. Search models download only during explicit setup; runtime loads pinned local weights. Ollama runs locally. Model downloads and Python package installation do require internet access.

Capture is explicit, excludes configured app names, and requires review before persistence. These exclusions are convenience controls, not sensitive-content detection. Text, images and source labels can contain private information; review the full preview before saving. Only visible window content is captured. Capture sessions stop on errors and never save automatically.

Source instructions are data. A conservative pattern filter excludes suspected overrides, and agents have a small validated tool vocabulary. This cannot prove immunity to prompt injection or irrelevant answers. Default Q&A renders original source spans; optional explanations use an additional fallible model support check, and vision outputs remain unverified interpretations. Browser import requires an explicit export and review; the optional extension has no persistent host access or backend token. Typed recall answers and corrections are private learning data and cascade with their source. Exports and browser form/session state may remain outside the database.

Deleting a memory cascades through active chunks, vectors, reviews, outcomes and vision records, removes unused PNGs and clears traces. In-flight answers/plans are invalidated if memories change. Legacy JSON, browser session state, exports and system backups are not securely erased by this operation. The database is not encrypted by the app. Use OS account protections and disk encryption as appropriate.

Do not commit private captures, tokens, databases, model weights or local environment files. Public test fixtures must be original synthetic or appropriately licensed non-sensitive material. Report security issues without posting private records or secrets; contact the repository owner through an available private channel before sharing sensitive details.
