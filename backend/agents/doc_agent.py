from backend.tools.rag_tool import rag_search, page_index_search


class DocAgent:
    def __init__(self):
        self.name = "DocAgent"

    def run(self, query: str, use_page_index: bool = False) -> str:
        """
        根据查询内容，选择合适的工具检索文档信息。
        """
        print(f"DEBUG:    [DocAgent] 开始检索 query='{query}', use_page_index={use_page_index}")
        if use_page_index:
            result = page_index_search(query, page_index="default")
        else:
            result = rag_search(query)
        print(f"DEBUG:    [DocAgent] 检索完成，结果长度={len(result)}")
        return f"【文档检索结果】\n{result}\n"
