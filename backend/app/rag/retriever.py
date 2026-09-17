from sqlalchemy.orm import Session

from app.db.models import Chunk
from app.rag.embeddings import embed_query


def retrieve(db: Session, query: str, top_k: int = 5) -> list[Chunk]:
    query_vector = embed_query(query)
    return (
        db.query(Chunk)
        .order_by(Chunk.embedding.cosine_distance(query_vector))
        .limit(top_k)
        .all()
    )
