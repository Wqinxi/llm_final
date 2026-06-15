"""
RAG 工具集
- 普通 RAG：基于 ChromaDB 向量检索返回相关文档片段
- PageIndex RAG：针对结构文档的页码索引检索（预留）
"""
import os
import chromadb
from openai import OpenAI

from backend.config import ZHIPU_API_KEY, ZHIPU_BASE_URL

EMBEDDING_MODEL = "embedding-3"

# 向量数据库持久化路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")

_chroma_client = None
_docs_collection = None


class ZhipuEmbeddingFunction:
    """调用智谱 Embedding API 生成向量"""

    def __init__(self):
        self.client = OpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)
        self.model = EMBEDDING_MODEL

    def __call__(self, input):
        return self.embed_documents(input)

    def embed_documents(self, input):
        if isinstance(input, str):
            response = self.client.embeddings.create(model=self.model, input=input)
            return [response.data[0].embedding]
        elif isinstance(input, list):
            results = []
            for text in input:
                response = self.client.embeddings.create(model=self.model, input=text)
                results.append(response.data[0].embedding)
            return results
        else:
            raise ValueError(f"Unsupported input type: {type(input)}")

    def embed_query(self, input):
        response = self.client.embeddings.create(model=self.model, input=input)
        emb = response.data[0].embedding
        print(f"DEBUG: embed_query type={type(emb)}, len={len(emb)}, preview={str(emb)[:80]}")
        return emb

    def name(self):
        return "zhipu_embedding"


def _init_chroma():
    """初始化 ChromaDB 客户端和文档集合（项目启动时调用）"""
    global _chroma_client, _docs_collection
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _docs_collection = _chroma_client.get_or_create_collection(
            name="docs",
            embedding_function=ZhipuEmbeddingFunction(),
        )


def rag_search(query: str, top_k: int = 3) -> str:
    """
    普通 RAG 检索工具。
    基于 ChromaDB 向量数据库检索相关文档片段。
    """
    _init_chroma()

    count = _docs_collection.count()
    if count == 0:
        return "【RAG 检索结果】\n暂无索引文档，请先运行 scripts/build_index.py 构建索引。\n"

    # 手动获取 embedding 并传给 ChromaDB，避免自动调用 embed_query 的兼容问题
    ef = ZhipuEmbeddingFunction()
    query_embedding = ef.embed_query(query)

    # 防御：确保传给 ChromaDB Rust 后端的是 List[List[float]]
    if isinstance(query_embedding, list) and len(query_embedding) > 0 and isinstance(query_embedding[0], float):
        query_embeddings = [query_embedding]
    else:
        query_embeddings = query_embedding

    print(f"DEBUG: final query_embeddings type={type(query_embeddings)}, preview={str(query_embeddings)[:80]}")

    results = _docs_collection.query(
        query_embeddings=query_embeddings,
        n_results=top_k,
    )
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return "【RAG 检索结果】\n未找到相关文档片段。\n"

    lines = []
    for i, doc in enumerate(documents):
        meta = metadatas[i] if i < len(metadatas) else {}
        source = meta.get("source", "未知")
        lines.append(f"文档片段{i + 1}（来源：{source}）：{doc}")
    formatted = "\n".join(lines)
    return formatted


def page_index_search(query: str, page_index: str = "default", top_k: int = 3) -> str:
    """
    结构文档 PageIndex RAG 检索工具。
    当前预留，暂未实现真实检索逻辑。
    """
    return "[PageIndex RAG] 预留功能，暂未实现。"
