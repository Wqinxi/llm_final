from backend.tools.rag_tool import rag_search
from backend.tools.pageindex_tool import page_index_search


class DocAgent:
    def __init__(self):
        self.name = "DocAgent"

    def run(self, query: str) -> str:
        """
        根据查询内容，同时调用 PageIndex 和 RAG 两个工具检索文档信息，
        并将两者的检索结果合并返回给上层。
        """
        print(f"DEBUG:    [DocAgent] 开始检索 query='{query}'")

        # 1. 调用 PageIndex
        print(f"DEBUG:    [DocAgent] 调用 page_index_search ...")
        pageindex_result = page_index_search(query)
        print(f"DEBUG:    [DocAgent] page_index_search 完成，结果长度={len(pageindex_result)}")

        # 2. 调用 RAG
        print(f"DEBUG:    [DocAgent] 调用 rag_search ...")
        rag_result = rag_search(query)
        print(f"DEBUG:    [DocAgent] rag_search 完成，结果长度={len(rag_result)}")

        # 3. 合并结果
        combined = (
            "【文档检索结果】\n\n"
            "--- PageIndex 检索结果 ---\n"
            f"{pageindex_result}\n\n"
            # "--- RAG 检索结果 ---\n"
            # f"{rag_result}\n"
        )
        print(f"DEBUG:    [DocAgent] 检索完成，总结果长度={len(combined)}")
        return combined
