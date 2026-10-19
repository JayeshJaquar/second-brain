# Browser extraction fixture

Run `python3 scripts/serve-import-fixture.py`, open `http://127.0.0.1:8766/article.html`, and click **Extract article**. It exercises the exact extraction function used by the Chrome extension against original semantic article markup, a hidden fake fact, navigation, an advertisement, a figure caption and code. Expect six retained blocks and no forbidden boilerplate. Export the original fixture if you want to test the Studio preview; importing must not save automatically.

This checks browser extraction, not the Chrome permission/install lifecycle. The server binds to loopback and serves only a temporary copy of the two fixture files. Stop it when finished.
