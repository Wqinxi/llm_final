"""DocAgent：文档检索 Agent。
调用 RAG 和 PageIndex 工具
"""
import asyncio
from backend.tools.langchain_tools import rag_search_tool, page_index_search_tool


class DocAgent:
    def __init__(self):
        self.name = "DocAgent"

    async def run(self, query: str, log_callback=None):
        """
        直接同时调用两个检索工具，合并结果返回
        以 async generator 形式产出日志和结果，工具调用放入线程池避免阻塞事件循环
        """
        print(f"DEBUG:    [DocAgent] 开始检索 query='{query}'")

        if log_callback:
            yield ("log", log_callback("    调用pageindex tool"))
        pageindex_result = await asyncio.get_running_loop().run_in_executor(
            None, page_index_search_tool.invoke, query
        )

        if log_callback:
            yield ("log", log_callback("    调用rag tool"))
        rag_result = await asyncio.get_running_loop().run_in_executor(
            None, rag_search_tool.invoke, query
        )

        combined = (
            "【文档检索结果】\n\n"
            "--- PageIndex 检索结果 ---\n"
            f"{pageindex_result}\n\n"
            "--- RAG 检索结果 ---\n"
            f"{rag_result}\n"
        )

        print(f"DEBUG:    [DocAgent] 检索完成，结果长度={len(combined)}")
        yield ("result", combined)

    async def _fallback_search(self, query: str) -> str:
        """保留兼容接口（当前逻辑已直连工具，此方法可保留或删除）"""
        async for tag, value in self.run(query):
            if tag == "result":
                return value
        return ""