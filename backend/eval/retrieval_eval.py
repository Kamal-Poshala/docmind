"""Evaluate retrieval quality against the fixed dataset in eval/dataset.py.

This exercises the real chunking + embedding pipeline (app.rag) but keeps the index
in memory, so it runs without Postgres or an LLM API key:

    cd backend && python -m eval.retrieval_eval
"""

import sys
from dataclasses import dataclass

import numpy as np

from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_query, embed_texts
from eval.dataset import DOCUMENTS, EVAL_CASES

DEFAULT_TOP_K = 3
PASS_THRESHOLD = 0.9


@dataclass
class IndexedChunk:
    document_id: str
    text: str
    vector: np.ndarray


def build_index() -> list[IndexedChunk]:
    index: list[IndexedChunk] = []
    for document in DOCUMENTS:
        pieces = chunk_text(document.text, chunk_size=300, overlap=50)
        for piece, vector in zip(pieces, embed_texts(pieces), strict=True):
            index.append(IndexedChunk(document.id, piece, np.array(vector)))
    return index


def top_k(index: list[IndexedChunk], query: str, k: int) -> list[IndexedChunk]:
    query_vector = np.array(embed_query(query))
    # Embeddings are normalized, so dot product is cosine similarity.
    scored = sorted(index, key=lambda chunk: -np.dot(chunk.vector, query_vector))
    return scored[:k]


def run(k: int = DEFAULT_TOP_K) -> tuple[float, list[str]]:
    index = build_index()
    misses = []
    for case in EVAL_CASES:
        retrieved_ids = {chunk.document_id for chunk in top_k(index, case.query, k)}
        if case.expected_document_id not in retrieved_ids:
            misses.append(
                f"  MISS: '{case.query}' -> expected '{case.expected_document_id}', "
                f"got {sorted(retrieved_ids)}"
            )
    hit_rate = (len(EVAL_CASES) - len(misses)) / len(EVAL_CASES)
    return hit_rate, misses


def main() -> None:
    hit_rate, misses = run()
    print(f"Retrieval hit_rate@{DEFAULT_TOP_K}: {hit_rate:.0%} ({len(EVAL_CASES)} cases)")
    for line in misses:
        print(line)

    if hit_rate < PASS_THRESHOLD:
        print(f"FAILED: hit_rate below threshold ({PASS_THRESHOLD:.0%})")
        sys.exit(1)
    print("PASSED")


if __name__ == "__main__":
    main()
