from __future__ import annotations

import hashlib
import json
from typing import Literal

import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

EmbeddingProvider = Literal["sentence_transformers", "openai"]

_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2


class EmbeddingService:
    """Compute text embeddings with optional Redis caching.

    Default provider: sentence-transformers (local, free, 384 dims).
    Set EMBEDDING_PROVIDER=openai in .env to use text-embedding-3-small (1536 dims).
    """

    def __init__(self, redis_client=None) -> None:
        self._redis = redis_client
        self._provider: EmbeddingProvider = getattr(settings, "embedding_provider", "sentence_transformers")
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        if self._provider == "sentence_transformers":
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                log.info("embedding_model_loaded", provider="sentence_transformers", model="all-MiniLM-L6-v2")
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                ) from exc
        return self._model

    async def embed(self, text: str) -> list[float]:
        """Embed a single text. Uses Redis cache keyed by SHA256 of the text."""
        cache_key = f"embed:{hashlib.sha256(text.encode()).hexdigest()}"

        if self._redis is not None:
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        vector = await self._compute(text)

        if self._redis is not None:
            try:
                await self._redis.setex(cache_key, 86400, json.dumps(vector))
            except Exception:
                pass

        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        if self._provider == "sentence_transformers":
            model = self._get_model()
            import asyncio
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(None, lambda: model.encode(texts).tolist())
            return embeddings
        return [await self.embed(t) for t in texts]

    async def _compute(self, text: str) -> list[float]:
        if self._provider == "sentence_transformers":
            model = self._get_model()
            import asyncio
            loop = asyncio.get_event_loop()
            vector = await loop.run_in_executor(None, lambda: model.encode(text).tolist())
            return vector
        if self._provider == "openai":
            return await self._openai_embed(text)
        raise ValueError(f"Unknown embedding provider: {self._provider}")

    async def _openai_embed(self, text: str) -> list[float]:
        import httpx
        api_key = getattr(settings, "openai_api_key", None)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"input": text, "model": "text-embedding-3-small"},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
