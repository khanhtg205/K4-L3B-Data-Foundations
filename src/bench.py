from __future__ import annotations

import re
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from src.chunking import FixedSizeChunker, HeadingChunker, RecursiveChunker, SentenceChunker
from src.embeddings import GeminiEmbedder, LocalEmbedder, OpenAIEmbedder, _mock_embed
from src.models import Document
from src.store import EmbeddingStore

DATA_DIR = Path("data/ecommerce-crawled-final")
CHUNKER = HeadingChunker(chunk_size=500)  # Change only this line for another strategy.
STRATEGIES = {
    "fixed_size": FixedSizeChunker(chunk_size=500),
    "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
    "recursive": RecursiveChunker(chunk_size=500),
}

QUERIES = [
    {
        "question": "What happens if an item does not match the listing or arrives faulty or damaged?",
        "gold": "The buyer may be eligible for eBay Money Back Guarantee and can return the item even if the seller's policy says returns are not accepted.",
        "marker": "return it even if",
        "metadata_filter": {"audience": "buyer"},
    },
    {
        "question": "How long does the seller have to respond to a buyer's return request?",
        "gold": "The seller should respond within 3 business days.",
        "marker": "seller should get back",
        "metadata_filter": {"audience": "buyer"},
    },
    {
        "question": "How long do refunds typically take to become available?",
        "gold": "Refunds are typically available within 3-5 business days.",
        "marker": "typically available",
        "metadata_filter": {"audience": "buyer"},
    },
    {
        "question": "What is the maximum transaction defect rate in the seller standards policy?",
        "gold": "The maximum transaction defect rate is 2% of transactions.",
        "marker": "No more than 2%",
        "metadata_filter": {"audience": "seller"},
    },
    {
        "question": "List the eligibility conditions for protections for Top Rated Sellers.",
        "gold": "The seller must be Top Rated, reside in the US or Canada, not have a Very High service-metrics rating, list on eBay.com, and offer 30-day or longer returns.",
        "marker": "Top Rated Seller at the time",
        "metadata_filter": {"audience": "seller"},
    },
]


def parse_markdown(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}, text.strip()

    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        match = re.match(r"^([a-z][a-z0-9_]*):\s*(.*)$", line.strip())
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1].replace('\\"', '"').replace('\\\\', '\\')
            metadata[match.group(1)] = value
    return metadata, parts[2].strip()


def load_chunks(chunker) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        frontmatter, content = parse_markdown(path)
        for index, chunk in enumerate(chunker.chunk(content)):
            metadata = {**frontmatter, "doc_id": path.stem, "chunk_index": str(index)}
            documents.append(Document(id=f"{path.stem}#{index}", content=chunk, metadata=metadata))
    return documents


def get_embedder():
    load_dotenv()
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    if provider in {"openai", "vilao"}:
        return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    if provider == "gemini":
        return GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"))
    if provider == "local":
        return LocalEmbedder()
    return _mock_embed


def print_results(strategy_name: str, chunker, include_ab: bool = False) -> None:
    documents = load_chunks(chunker)
    embedder = get_embedder()
    print(f"Embedding backend: {getattr(embedder, '_backend_name', embedder.__class__.__name__)}")
    store = EmbeddingStore(collection_name="benchmark", embedding_fn=embedder)
    store.add_documents(documents)
    print(f"\n=== Strategy: {strategy_name} ({chunker.__class__.__name__}) ===")
    print(f"Loaded {len(documents)} chunks from {len({doc.metadata['doc_id'] for doc in documents})} files")

    for index, query in enumerate(QUERIES, start=1):
        results = store.search_with_filter(query["question"], top_k=3, metadata_filter=query["metadata_filter"])
        print(f"\nQ{index}: {query['question']}")
        print(f"Filter: {query['metadata_filter']}")
        print(f"Gold: {query['gold']}")
        for rank, result in enumerate(results, start=1):
            metadata = result["metadata"]
            marker_found = query["marker"].lower() in result["content"].lower()
            print(
                f"  {rank}. score={result['score']:.4f} "
                f"doc_id={metadata.get('doc_id')} chunk={result['id']} "
                f"marker={'YES' if marker_found else 'NO'}"
            )

        if include_ab and index == 1:
            for label, metadata_filter in (("with_filter", query["metadata_filter"]), ("without_filter", None)):
                ab_results = store.search_with_filter(query["question"], top_k=3, metadata_filter=metadata_filter)
                print(f"  A/B {label}:")
                for rank, result in enumerate(ab_results, start=1):
                    print(
                        f"    {rank}. score={result['score']:.4f} "
                        f"doc_id={result['metadata'].get('doc_id')} chunk={result['id']}"
                    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", action="store_true", help="run all strategies and A/B filter comparison")
    args = parser.parse_args()
    if args.compare:
        for strategy_name, chunker in STRATEGIES.items():
            print_results(strategy_name, chunker, include_ab=True)
    else:
        print_results("selected", CHUNKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
