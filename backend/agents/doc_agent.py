"""DocAgent：文档检索 Agent。
调用 RAG 和 PageIndex 工具
"""
from backend.tools.langchain_tools import rag_search_tool, page_index_search_tool


class DocAgent:
    def __init__(self):
        self.name = "DocAgent"

    def run(self, query: str) -> str:
        """
        直接同时调用两个检索工具，合并结果返回
        """
        print(f"DEBUG:    [DocAgent] 开始检索 query='{query}'")

        # 调用双工具
        pageindex_result = page_index_search_tool.invoke(query)
        rag_result = rag_search_tool.invoke(query)

        combined = (
            "【文档检索结果】\n\n"
            "--- PageIndex 检索结果 ---\n"
            f"{pageindex_result}\n\n"
            "--- RAG 检索结果 ---\n"
            f"{rag_result}\n"
        )

        print(f"DEBUG:    [DocAgent] 检索完成，结果长度={len(combined)}")
        return combined

    def _fallback_search(self, query: str) -> str:
        """保留兼容接口（当前逻辑已直连工具，此方法可保留或删除）"""
        return self.run(query)