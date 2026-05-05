"""Script to ingest documentation into the RAG vector store."""

import argparse
import sys
import os
from pathlib import Path

# Add the project root to the python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.utils.logger import logger
from backend.retrieval.embeddings import EmbeddingService
from backend.retrieval.ingestion import DocumentIngester
from backend.retrieval.service import RetrievalService

def ingest_all(docs_dir: str, persist_dir: str) -> None:
    path = Path(docs_dir)
    if not path.exists():
        logger.error(f"Documentation directory not found: {docs_dir}")
        return

    embeddings = EmbeddingService()
    ingester = DocumentIngester(embeddings=embeddings, chunk_size=500, chunk_overlap=50)
    service = RetrievalService(
        embeddings=embeddings, persist_dir=persist_dir, collection_name="haruquant_knowledge"
    )

    logger.info(f"Clearing existing knowledge base in {persist_dir}...")
    service.clear()

    total_chunks = 0
    total_docs = 0

    for file_path in path.rglob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Create doc_id relative to the parent of docs_dir, or just relative to docs_dir
            doc_id = str(file_path.relative_to(path.parent))
            metadata = {
                "source": "haruquant_docs",
                "filename": file_path.name,
                "doc_id": doc_id,
                "type": "documentation",
            }

            chunks = ingester.ingest(doc_id=doc_id, content=content, metadata=metadata)
            if chunks:
                added = service.add_chunks(chunks)
                total_chunks += added
                total_docs += 1
                logger.info(f"Ingested {added} chunks from {doc_id}")

        except Exception as e:
            logger.error(f"Failed to ingest {file_path}: {e}")

    logger.info(f"Ingestion complete. Added {total_chunks} chunks from {total_docs} documents.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest HaruQuant docs into knowledge base")
    parser.add_argument(
        "--docs-dir",
        type=str,
        default="docs/haruquant",
        help="Path to HaruQuant documentation directory",
    )
    parser.add_argument(
        "--db-dir",
        type=str,
        default="backend/data/knowledge_db",
        help="Path to persist ChromaDB vectors",
    )
    args = parser.parse_args()

    # Ensure persistence dir exists
    import os
    os.makedirs(args.db_dir, exist_ok=True)
    
    ingest_all(args.docs_dir, args.db_dir)
