# Security and privacy boundaries

This is a prototype and makes no security or hallucination-free guarantee.

- Only capture an explicitly selected window on demand. Review before saving.
- Saved screenshots and text are private local data and must stay out of Git.
- App file permissions restrict other ordinary local users; they do not replace encryption or defend against software running as the same user.
- Source content is untrusted. The model receives no shell, network-fetch, filesystem-write, or messaging tools.
- A conservative pattern filter excludes memories with instruction-override language. This trades recall for caution, can produce false positives, and can be bypassed by unseen attacks.
- Strict evidence mode validates citations and verbatim quotations, allowing only whitespace differences and displaying the source original; relevance, entailment, source correctness, and conflict detection still require assessment.
- Local HTTP communication assumes a trusted local Ollama service. Other software running on the Mac may be able to access or impersonate local services.
- The app does not fetch URLs found in captured content. Source strings are displayed as provenance, not automatically trusted destinations.
- Memory deletion removes stored image bytes from the current JSON store; backups and prior filesystem snapshots are outside this deletion boundary.

Avoid publishing sensitive examples in bug reports. Provide a minimal synthetic reproducer instead.
