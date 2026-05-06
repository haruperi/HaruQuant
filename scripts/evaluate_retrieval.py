"""Benchmark evaluation script for the RAG knowledge retrieval."""

import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haruquant.utils import logger
from services.retrieval.embeddings import EmbeddingService
from services.retrieval.service import RetrievalService
from services.retrieval.evaluation import RetrievalEvaluator

def evaluate_retrieval(db_dir: str):
    embeddings = EmbeddingService()
    retrieval = RetrievalService(
        embeddings=embeddings, 
        persist_dir=db_dir, 
        collection_name="haruquant_knowledge"
    )
    evaluator = RetrievalEvaluator()

    if retrieval.count == 0:
        logger.warning(f"No documents found in knowledge base at {db_dir}. Please run ingest_docs.py first.")
        return

    # Sample evaluation dataset
    eval_set = [
        {
            "query": "What is the HaruQuant Architecture?",
            "expected_doc_ids": {"specs\\AI_Chatbot_Architecture.md", "specs/AI_Chatbot_Architecture.md"}
        },
        {
            "query": "What is the event schema format for chat?",
            "expected_doc_ids": {"specs\\AI_Chatbot_Event_Schema.md", "specs/AI_Chatbot_Event_Schema.md"}
        },
        {
            "query": "What are the goals of the chatbot implementation?",
            "expected_doc_ids": {"plans\\AI_Chatbot_Implementation_Plan.md", "plans/AI_Chatbot_Implementation_Plan.md"}
        }
    ]

    for item in eval_set:
        query = item["query"]
        expected = item["expected_doc_ids"]

        logger.info(f"Query: {query}")
        results = retrieval.search(query=query, top_k=5)
        
        # Convert results to list of dicts for evaluator
        formatted_results = [{"doc_id": r.metadata.get("doc_id", "")} for r in results]
        
        eval_metrics = evaluator.evaluate(
            query=query, 
            expected_doc_ids=expected, 
            retrieved_results=formatted_results
        )

        logger.info(f"  MRR: {eval_metrics.mrr:.4f} | NDCG: {eval_metrics.ndcg:.4f} | Recall@5: {eval_metrics.recall_at_k:.4f}")
        logger.info("-" * 40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG Retrieval quality.")
    parser.add_argument(
        "--db-dir",
        type=str,
        default="data/knowledge_db",
        help="Path to persist ChromaDB vectors",
    )
    args = parser.parse_args()

    evaluate_retrieval(args.db_dir)

