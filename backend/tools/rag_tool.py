"""
RAG 工具集
- 普通 RAG：基于向量检索返回相关文档片段（当前为 mock 实现）
- PageIndex RAG：针对结构文档的页码索引检索（预留）
"""


def rag_search(query: str, top_k: int = 3) -> str:
    """
    普通 RAG 检索工具。
    当前为模拟实现，返回示例文本片段。
    后续可替换为真实向量数据库检索（如 Chroma、Milvus）。
    """
    docs = [
        "文档片段1：智谱AI（Zhipu AI）成立于2019年，致力于打造新一代认知智能大模型。",
        "文档片段2：ChatGLM 系列模型包括 ChatGLM-6B、ChatGLM2-6B、ChatGLM3-6B 及最新的 GLM-4。",
        "文档片段3：GLM-4 具备强大的多模态理解能力和长文本处理能力，支持 128K 上下文窗口。",
    ]
    # 简单关键词匹配示例
    results = [d for d in docs if any(k in d for k in query.split())] or docs[:top_k]
    return "\n".join(results[:top_k])


def page_index_search(query: str, page_index: str = "default", top_k: int = 3) -> str:
    """
    结构文档 PageIndex RAG 检索工具。
    当前预留，暂未实现真实检索逻辑。
    """
    return "[PageIndex RAG] 预留功能，暂未实现。"
