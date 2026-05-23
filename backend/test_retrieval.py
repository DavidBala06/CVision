"""Standalone retrieval test — bypasses the LLM entirely.

Loads the persisted Chroma vector DB, runs a similarity search for a query,
and prints the matched chunks. Useful to verify the RAG retrieval works
without needing a HuggingFace API token.
"""
import sys
import os
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_storage")


def main():
    query = " ".join(sys.argv[1:]) or "AI engineer cu experienta in LangChain in Cluj"

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    db = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=embeddings)
    print(f"Vector DB has {db._collection.count()} chunks")
    print(f"Query: {query}\n")
    print("=" * 80)

    results = db.similarity_search_with_score(query, k=5)
    for i, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        candidate = os.path.basename(os.path.dirname(source)) if source else "unknown"
        print(f"\n--- MATCH #{i}  (distance={score:.4f})  source={candidate} ---")
        content = doc.page_content
        if len(content) > 1200:
            content = content[:1200] + "\n... [truncated]"
        print(content)
        print()


if __name__ == "__main__":
    main()
