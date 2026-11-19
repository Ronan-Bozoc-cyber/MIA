import json
import os
import re
import threading


class RAGCache:
    """Cache mémoire thread-safe pour les bases ChromaDB et les index BM25Okapi."""

    def __init__(self):
        self._lock = threading.Lock()
        self._chroma = {}
        self._bm25 = {}

    def invalidate(self, db_dir=None):
        with self._lock:
            if db_dir is None:
                self._chroma.clear()
                self._bm25.clear()
            else:
                norm = os.path.abspath(db_dir)
                for k in [k for k in self._chroma if k[0] == norm]:
                    del self._chroma[k]
                self._bm25.pop(norm, None)

    def get_chroma(self, db_dir, embed_model, ollama_url, embeddings_obj):
        from langchain_community.vectorstores import Chroma

        norm = os.path.abspath(db_dir)
        key = (norm, embed_model, ollama_url.rstrip("/"))
        with self._lock:
            db = self._chroma.get(key)
            if db is not None:
                return db
        db = Chroma(
            persist_directory=norm,
            embedding_function=embeddings_obj,
            collection_name=os.path.basename(norm),
        )
        with self._lock:
            self._chroma[key] = db
        return db

    def get_bm25(self, db_dir):
        """Retourne (bm25_instance, corpus_list) mis en cache par date de modification du JSON."""
        from rank_bm25 import BM25Okapi

        norm = os.path.abspath(db_dir)
        bm25_file = os.path.join(norm, "bm25_corpus.json")
        if not os.path.exists(bm25_file):
            return None, []

        mtime = os.path.getmtime(bm25_file)
        with self._lock:
            cached = self._bm25.get(norm)
            if cached and cached[0] == mtime:
                return cached[1], cached[2]

        with open(bm25_file, "r", encoding="utf-8") as f:
            corpus = json.load(f)
        if not corpus:
            return None, []

        tokenized_corpus = [re.findall(r"\w+", doc["page_content"].lower()) for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        with self._lock:
            self._bm25[norm] = (mtime, bm25, corpus)
        return bm25, corpus


rag_cache = RAGCache()
