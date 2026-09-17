import io

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_texts


def extract_text(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return data.decode("utf-8", errors="ignore")


def ingest_document(db: Session, filename: str, data: bytes) -> Document:
    text = extract_text(filename, data)
    pieces = chunk_text(text)
    if not pieces:
        raise ValueError("No extractable text found in file")

    document = Document(filename=filename)
    db.add(document)
    db.flush()

    vectors = embed_texts(pieces)
    for index, (content, vector) in enumerate(zip(pieces, vectors)):
        db.add(Chunk(document_id=document.id, chunk_index=index, content=content, embedding=vector))

    db.commit()
    db.refresh(document)
    return document
