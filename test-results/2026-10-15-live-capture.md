# Live Chrome capture test — 15 October 2026

Source: https://huggingface.co/learn/llm-course/chapter1/4#transfer-learning

- Opened the article in Google Chrome and selected the actual visible browser tab.
- Scrolled to the explanation of fine-tuning versus pretraining.
- Used Second Brain's window picker and Capture once action (no manual article import).
- Verified OCR contained the passage explaining reuse of pretrained knowledge and lower data/time/resource requirements.
- Saved as “LLM article — Fine-tuning and transfer learning (captured excerpt)” with the source URL.
- Selected that saved memory and submitted a two-sentence question about lower fine-tuning costs to the local model.
- Storage regression checks and five retrieval-metric tests passed.

Limitations: one visible excerpt, not the complete article. OCR included browser toolbar text and partially obscured/truncated lines near the bottom. Automatic content cleanup and full-document capture remain unfinished. This is a smoke test, not an accuracy benchmark.

## Observed answer

The local model explained that fine-tuning reuses a pretrained model's foundational language understanding and therefore needs less data and computing time for a specific task. This agrees with the captured passage. It produced the requested two sentences but omitted the requested [1] citation marker, so citation formatting remains unresolved. The saved excerpt and answer were left selected in the app for the user.
