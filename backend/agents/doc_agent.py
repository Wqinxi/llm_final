from backend.tools.rag_tool import rag_search, page_index_search


class DocAgent:
    def __init__(self):
        self.name = "DocAgent"

    def run(self, query: str, use_page_index: bool = False) -> str:
        """
        根据查询内容，选择合适的工具检索文档信息。
        """
        if use_page_index:
            result = page_index_search(query, page_index="default")
        else:
            result = rag_search(query)
        return f"【文档检索结果】\n{result}\n"
