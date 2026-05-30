"""
CROSSROAD — Vector Store & RAG
================================
ChromaDB + sentence-transformers (local, no API key).

Collections:
  persons_bio    — person bios + profiles
  news_articles  — full news text + summaries
  relationships  — relationship descriptions for context

RAG pipeline:
  user query → embed → ChromaDB similarity search
             → top-k docs → build context
             → Ollama qwen2.5:7b → natural language answer

NL→Cypher:
  user question → LLM → Cypher query → Neo4j → result → LLM → answer
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
EMBED_BATCH = int(os.getenv("EMBED_BATCH_SIZE", "32"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL= os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


class VectorStore:
    """Wrapper around ChromaDB with local sentence-transformer embeddings."""

    def __init__(self):
        self._client = None
        self._ef     = None
        self._cols   = {}

    def _get_client(self):
        if self._client is None:
            import chromadb
            try:
                self._client = chromadb.HttpClient(
                    host=CHROMA_HOST, port=CHROMA_PORT,
                    tenant="default_tenant",
                    database="default_database",
                )
            except TypeError:
                self._client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            except Exception as e:
                logger.warning(f"ChromaDB client init failed: {e}")
                raise
        return self._client

    def _client_ok(self) -> bool:
        """Check if ChromaDB is reachable without raising."""
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def _get_ef(self):
        if self._ef is None:
            try:
                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
                self._ef = SentenceTransformerEmbeddingFunction(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2"
                )
            except Exception as e:
                logger.warning(f"SentenceTransformer load failed: {e}. Using default embeddings.")
                # Fall back to chromadb's default embedding function
                import chromadb.utils.embedding_functions as ef
                self._ef = ef.DefaultEmbeddingFunction()
        return self._ef

    def _col(self, name: str):
        if name not in self._cols:
            client = self._get_client()
            self._cols[name] = client.get_or_create_collection(
                name=name,
                embedding_function=self._get_ef(),
                metadata={"hnsw:space": "cosine"}
            )
        return self._cols[name]

    # ── Ingestion ─────────────────────────────────────────────────────────────

    async def embed_persons(self, persons: List[Dict], batch_size: int = EMBED_BATCH):
        """Embed person bios + profiles into ChromaDB."""
        if not self._client_ok():
            logger.warning("ChromaDB unavailable — skipping person embedding")
            return
        try:
            col = self._col("persons_bio")
        except Exception as e:
            logger.warning(f"ChromaDB collection error: {e} — skipping embed")
            return
        loop = asyncio.get_event_loop()

        for i in range(0, len(persons), batch_size):
            batch = persons[i:i+batch_size]
            ids, docs, metas = [], [], []

            for p in batch:
                slug = p.get("slug","")
                if not slug:
                    continue
                # Build document text
                parts = [
                    p.get("full_name",""),
                    p.get("role_type",""),
                    p.get("party",""),
                    p.get("province",""),
                    p.get("current_position","") or p.get("position",""),
                    p.get("bio","") or "",
                ]
                edu = p.get("education") or []
                if edu:
                    parts.append("Pendidikan: " + "; ".join(
                        (e.get("institution") if isinstance(e,dict) else str(e))
                        for e in edu[:4]
                    ))
                career = p.get("career") or []
                if career:
                    parts.append("Karier: " + "; ".join(
                        (c.get("title") or c.get("org","") if isinstance(c,dict) else str(c))
                        for c in career[:5]
                    ))
                doc = " | ".join(str(x) for x in parts if x)

                ids.append(f"person:{slug}")
                docs.append(doc[:2000])
                metas.append({
                    "slug": slug,
                    "name": p.get("full_name",""),
                    "party": p.get("party","") or "",
                    "role_type": p.get("role_type","") or "",
                    "province": p.get("province","") or "",
                    "type": "person",
                })

            if ids:
                try:
                    await loop.run_in_executor(None, lambda: col.upsert(
                        ids=ids, documents=docs, metadatas=metas
                    ))
                    logger.info(f"Embedded persons batch {i//batch_size+1}: {len(ids)} docs")
                except Exception as e:
                    logger.error(f"embed_persons batch error: {e}")

    async def embed_news(self, articles: List[Dict], person_slug: str = ""):
        """Embed news articles."""
        col = self._col("news_articles")
        loop = asyncio.get_event_loop()

        ids, docs, metas = [], [], []
        for a in articles:
            url = a.get("url","")
            if not url:
                continue
            text = " | ".join(filter(None, [
                a.get("title",""),
                a.get("summary",""),
                a.get("full_text","")[:500] if a.get("full_text") else "",
            ]))
            ids.append(f"news:{hash(url) % 10**12}")
            docs.append(text[:1500])
            metas.append({
                "url": url,
                "outlet": a.get("outlet","") or "",
                "category": a.get("category","") or "",
                "sentiment": a.get("sentiment","") or "",
                "alignment_score": str(a.get("alignment_score", 0.0)),
                "person_slug": person_slug,
                "type": "news",
            })

        if ids:
            try:
                await loop.run_in_executor(None, lambda: col.upsert(
                    ids=ids, documents=docs, metadatas=metas
                ))
            except Exception as e:
                logger.error(f"embed_news error: {e}")

    # ── Query ─────────────────────────────────────────────────────────────────

    async def search_persons(self, query: str, n: int = 8) -> List[Dict]:
        col = self._col("persons_bio")
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(None, lambda: col.query(
                query_texts=[query], n_results=min(n, col.count() or 1),
                include=["metadatas","documents","distances"]
            ))
            out = []
            for meta, doc, dist in zip(
                results["metadatas"][0],
                results["documents"][0],
                results["distances"][0]
            ):
                out.append({**meta, "excerpt": doc[:300], "score": 1 - dist})
            return out
        except Exception as e:
            logger.error(f"search_persons error: {e}")
            return []

    async def search_news(self, query: str, n: int = 10) -> List[Dict]:
        col = self._col("news_articles")
        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(None, lambda: col.query(
                query_texts=[query], n_results=min(n, col.count() or 1),
                include=["metadatas","documents","distances"]
            ))
            out = []
            for meta, doc, dist in zip(
                results["metadatas"][0],
                results["documents"][0],
                results["distances"][0]
            ):
                out.append({**meta, "excerpt": doc[:400], "score": 1 - dist})
            return out
        except Exception as e:
            logger.error(f"search_news error: {e}")
            return []

    async def search_all(self, query: str, n_each: int = 5) -> Dict:
        persons = await self.search_persons(query, n_each)
        news    = await self.search_news(query, n_each)
        return {"persons": persons, "news": news}

    def count(self, collection: str) -> int:
        try:
            return self._col(collection).count()
        except Exception:
            return 0


# ── LLM Query Interface ───────────────────────────────────────────────────────

import httpx
import re


class KnowledgeInterface:
    """
    Natural language → knowledge graph answers.
    Two modes:
      1. RAG: query → ChromaDB → context → Ollama → answer
      2. Cypher: query → Ollama → Cypher → Neo4j → Ollama → answer
    """

    def __init__(self, graph_db, vector_store: VectorStore):
        self.graph  = graph_db
        self.vs     = vector_store
        self.host   = OLLAMA_HOST
        self.model  = OLLAMA_MODEL

    async def _llm(self, system: str, user: str, timeout: float = 120.0) -> str:
        payload = {
            "model": self.model, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 1024},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(f"{self.host}/api/chat", json=payload)
            r.raise_for_status()
            return r.json().get("message",{}).get("content","")

    def _extract_cypher(self, text: str) -> Optional[str]:
        """Extract Cypher query from LLM output."""
        m = re.search(r"```(?:cypher)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Try to find MATCH keyword
        m = re.search(r"(MATCH[\s\S]+RETURN[^\n]+)", text)
        return m.group(1).strip() if m else None

    # ── RAG answer ─────────────────────────────────────────────────────────────

    async def rag_answer(self, question: str) -> Dict:
        """Answer using RAG over ChromaDB."""
        ctx = await self.vs.search_all(question, n_each=5)

        person_ctx = "\n".join(
            f"- {p['name']} ({p.get('role_type','')}, {p.get('party','')}): {p.get('excerpt','')[:200]}"
            for p in ctx["persons"]
        )
        news_ctx = "\n".join(
            f"- [{n.get('outlet','')}] {n.get('excerpt','')[:200]}"
            for n in ctx["news"]
        )

        system = (
            "Kamu adalah asisten intelijen politik Indonesia. "
            "Jawab pertanyaan pengguna berdasarkan konteks yang diberikan. "
            "Selalu sebutkan sumber atau basis fakta dalam jawabanmu. "
            "Jika informasi tidak ada dalam konteks, katakan dengan jelas."
        )
        user = (
            f"Pertanyaan: {question}\n\n"
            f"Konteks Tokoh:\n{person_ctx or 'Tidak ada'}\n\n"
            f"Konteks Berita:\n{news_ctx or 'Tidak ada'}"
        )

        answer = await self._llm(system, user)
        return {
            "mode": "rag",
            "question": question,
            "answer": answer,
            "sources": {
                "persons": [{"name": p["name"], "slug": p.get("slug","")} for p in ctx["persons"]],
                "news":    [{"url": n["url"], "outlet": n.get("outlet","")} for n in ctx["news"]],
            }
        }

    # ── NL→Cypher ──────────────────────────────────────────────────────────────

    async def cypher_answer(self, question: str) -> Dict:
        """
        Convert natural language question to Cypher, run on Neo4j, return result.
        """
        # Step 1: Generate Cypher
        schema_hint = """
        Node labels: Person (slug, name, role_type, party, province),
                     Org (slug, name, org_type),
                     News (url, title, outlet, category)
        Relationship types:
          MEMBER_OF (Person→Org party)
          FAMILY_OF {subtype: spouse|child|parent} (Person→Person)
          WORKS_AT  (Person→Org)
          STUDIED_AT(Person→Org university)
          OWNS      (Person→Org company)
          ALLIED_WITH / RIVAL_OF (Person→Person)
          MENTIONED_IN {alignment: float -1..1} (Person→News)
        """
        system = (
            "You are a Neo4j Cypher expert for an Indonesian political knowledge graph. "
            f"Schema:\n{schema_hint}\n"
            "Generate a valid Cypher query to answer the question. "
            "Use LIMIT 20 for lists. Return ONLY the Cypher in a code block.\n"
            "Examples:\n"
            "Q: Siapa istri Prabowo?\n"
            "```cypher\nMATCH (p:Person {slug:'prabowo-subianto'})-[r:FAMILY_OF {subtype:'spouse'}]->(f) RETURN f.name, r.subtype\n```\n"
            "Q: Siapa yang bersekolah di tempat yang sama dengan Prabowo?\n"
            "```cypher\nMATCH (p:Person {slug:'prabowo-subianto'})-[:STUDIED_AT]->(u:Org)<-[:STUDIED_AT]-(other:Person) WHERE other.slug <> 'prabowo-subianto' RETURN DISTINCT other.name, u.name LIMIT 20\n```"
        )
        cypher_raw = await self._llm(system, f"Question: {question}")
        cypher = self._extract_cypher(cypher_raw)

        if not cypher:
            return {
                "mode": "cypher",
                "question": question,
                "cypher": None,
                "error": "Could not generate Cypher query",
                "answer": None,
            }

        # Step 2: Execute
        try:
            async with self.graph.driver.session() as s:
                result = await s.run(cypher)
                records = await result.data()

            # Step 3: Format as natural language
            records_str = json.dumps(records[:20], ensure_ascii=False, default=str)
            system2 = (
                "Kamu adalah asisten intelijen politik Indonesia. "
                "Buat jawaban natural language dari hasil query Neo4j ini. "
                "Singkat, faktual, dan sebutkan nama-nama penting."
            )
            answer = await self._llm(system2,
                f"Pertanyaan: {question}\n"
                f"Hasil query:\n{records_str}")

            return {
                "mode": "cypher",
                "question": question,
                "cypher": cypher,
                "raw_results": records[:10],
                "answer": answer,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Cypher execution error: {e}")
            return {
                "mode": "cypher",
                "question": question,
                "cypher": cypher,
                "error": str(e),
                "answer": f"Query gagal: {str(e)[:100]}",
            }

    # ── Auto-route ─────────────────────────────────────────────────────────────

    async def query(self, question: str, mode: str = "auto") -> Dict:
        """
        auto: try cypher first, fall back to RAG
        rag: always use RAG
        cypher: always use Cypher
        """
        if mode == "rag":
            return await self.rag_answer(question)
        if mode == "cypher":
            return await self.cypher_answer(question)

        # Auto: use Cypher if question mentions specific relationships
        cypher_hints = ["siapa","berapa","mana","relasi","hubungan","keluarga",
                        "istri","suami","anak","sekolah","kerja","perusahaan",
                        "who","how many","which","relation","family","company"]
        if any(h in question.lower() for h in cypher_hints):
            result = await self.cypher_answer(question)
            if not result.get("error"):
                return result
        return await self.rag_answer(question)
