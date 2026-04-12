"""
Tripitaka MCP Server — Embedding Model

โมดูลสำหรับสร้าง text embeddings ด้วย sentence-transformers
ใช้สำหรับ semantic search ในพระไตรปิฎก

Default model: paraphrase-multilingual-MiniLM-L12-v2
- รองรับ 50+ ภาษา (รวมไทย)
- 384 dimensions
- ขนาดเล็ก (~118MB) เหมาะสำหรับเริ่มต้น
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)


@lru_cache(maxsize=1)
def _load_model():
    """โหลด sentence-transformers model (cache ไว้ใช้ซ้ำ)

    Returns:
        SentenceTransformer model instance
    """
    from sentence_transformers import SentenceTransformer

    print(f"🔄 กำลังโหลด embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print(f"✅ โหลด model เรียบร้อย (dimensions: {model.get_sentence_embedding_dimension()})")
    return model


def generate_embedding(text: str) -> list[float]:
    """สร้าง embedding vector จากข้อความ

    Args:
        text: ข้อความที่ต้องการสร้าง embedding

    Returns:
        list of float — embedding vector

    Example:
        embedding = generate_embedding("อริยสัจ 4")
        # [0.012, -0.034, 0.056, ...]
    """
    model = _load_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_embeddings_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """สร้าง embedding vectors จากข้อความหลายรายการ (batch processing)

    Args:
        texts: รายการข้อความที่ต้องการสร้าง embedding
        batch_size: จำนวนข้อความที่ประมวลผลต่อ batch (default: 64)

    Returns:
        list of embedding vectors

    Example:
        embeddings = generate_embeddings_batch(["อริยสัจ 4", "มรรค 8"])
        # [[0.012, ...], [0.034, ...]]
    """
    model = _load_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def get_dimensions() -> int:
    """คืนจำนวน dimensions ของ embedding model ปัจจุบัน

    Returns:
        int — จำนวน dimensions
    """
    model = _load_model()
    return model.get_sentence_embedding_dimension()
