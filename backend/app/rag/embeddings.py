from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
