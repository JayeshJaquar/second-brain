"""Dependency-free BM25 reference and ranking metrics. Not integrated into the app."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import time


def tokens(text):
    return re.findall(r"\w+", text.casefold())


class BM25:
    def __init__(self, documents, k1=1.5, b=0.75):
        self.documents = documents
        self.counts = [Counter(tokens(d["text"])) for d in documents]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.average = sum(self.lengths) / max(len(documents), 1)
        self.df = Counter(term for counts in self.counts for term in counts)
        self.k1, self.b = k1, b

    def search(self, query, k=5):
        ranked = []
        for document, counts, length in zip(self.documents, self.counts, self.lengths):
            score = 0.0
            for term in set(tokens(query)):
                frequency = counts[term]
                if not frequency:
                    continue
                df = self.df[term]
                idf = math.log(1 + (len(self.documents) - df + 0.5) / (df + 0.5))
                norm = frequency + self.k1 * (1 - self.b + self.b * length / self.average)
                score += idf * frequency * (self.k1 + 1) / norm
            if score > 0:
                ranked.append((document["id"], score))
        return sorted(ranked, key=lambda pair: (-pair[1], pair[0]))[:k]


def metrics(ranking, relevant, k=5):
    relevant = set(relevant)
    if not relevant:
        raise ValueError("Answerable retrieval queries require relevant IDs; evaluate abstention separately.")
    ids = list(dict.fromkeys(ranking))[:k]
    recall = len(set(ids) & relevant) / len(relevant)
    reciprocal = next((1 / rank for rank, doc in enumerate(ids, 1) if doc in relevant), 0.0)
    return recall, reciprocal


def evaluate(path):
    data = json.loads(path.read_text())
    documents, queries = data["documents"], data["queries"]
    ids = [d["id"] for d in documents]
    if len(ids) != len(set(ids)) or not documents or not queries:
        raise ValueError("Require nonempty documents/queries and unique document IDs")
    index = BM25(documents)
    results = []
    for query in queries:
        if not set(query["relevant"]) <= set(ids):
            raise ValueError("Unknown relevant document ID")
        start = time.perf_counter()
        ranking = [doc for doc, _ in index.search(query["text"])]
        elapsed = (time.perf_counter() - start) * 1000
        recall, reciprocal = metrics(ranking, query["relevant"])
        results.append(dict(id=query["id"], recall_at_5=recall, reciprocal_rank_at_5=reciprocal,
                            latency_ms=elapsed, ranking=ranking))
    return dict(dataset=str(path), note=data.get("description", ""), method="BM25",
                documents=len(documents), queries=len(queries),
                recall_at_5=sum(r["recall_at_5"] for r in results)/len(results),
                mrr_at_5=sum(r["reciprocal_rank_at_5"] for r in results)/len(results), results=results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parents[1]/"data/smoke.json")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset), indent=2))
