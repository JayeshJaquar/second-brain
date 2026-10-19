# Explicit article capture for Chrome

This optional Manifest V3 extension reads the active tab only after you click **Read selected tab**. It prefers selected text, otherwise article/main text, excludes navigation/forms/hidden blocks, and preserves source, date and figure captions. It does not collect browsing history, run in the background, fetch resources, send data to a server, or receive the backend token. It needs only `activeTab` and `scripting`; there are no host permissions.

Install locally: open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select this `extensions/chrome` directory. This browser setup is performed by you; copying the repository does not install the extension.

Open an article, click the extension, read the selected tab, inspect/edit the preview, and export. In Learning Studio → Library → **Import browser article file**, choose the JSON (or paste the export JSON into the fallback form), review it, and save. Keep exported files private and remove them yourself when no longer needed. URL queries/fragments are omitted to reduce accidental tracking-token capture. Loaded article text can still contain private data or source instructions.

This captures DOM text rather than OCR, so it can include loaded content below the viewport. It cannot extract an unloaded or inaccessible article, PDF canvas text or iframe contents. It does not download image pixels; use the native screenshot feature for diagrams. Semantic article selection is heuristic and may include or miss material.

Chrome's permissions model: [activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab) and [scripting](https://developer.chrome.com/docs/extensions/reference/api/scripting). Browser extraction is exercised by the local fixture described in `research/fixtures/browser-import/README.md`; extension installation itself requires a manual Chrome smoke check.
