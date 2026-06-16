"""LangChain 工具：供 Deep Agent 调用 Doc / Image 能力。"""

from langchain.tools import tool

from backend.tools.rag_tool import rag_search
from backend.tools.pageindex_tool import page_index_search
from backend.tools.image_tool import read_image

_current_image_url: str | None = None


def set_current_image_url(url: str | None) -> None:
    global _current_image_url
    _current_image_url = url


@tool
def rag_search_tool(query: str) -> str:
    """从文档库检索与用户问题相关的文档片段。输入检索关键词或完整问题。"""
    print(f"DEBUG:    [rag_search_tool] query='{query}'")
    result = rag_search(query)
    return f"【文档检索结果】\n{result}"


@tool
def page_index_search_tool(query: str) -> str:
    """通过 PageIndex 层级结构索引检索文档。适用于需要按目录/章节/页码定位的问题。"""
    print(f"DEBUG:    [page_index_search_tool] query='{query}'")
    result = page_index_search(query)
    return f"【PageIndex 检索结果】\n{result}"


@tool
def read_image_tool(prompt: str = "请详细描述这张图片的内容，并提取与问题相关的信息。") -> str:
    """识别并分析用户当前上传的图片。输入你希望图像分析侧重的提示语。"""
    if not _current_image_url:
        return "【图像识别结果】当前没有可用的图片，请提示用户上传图片。"
    print(f"DEBUG:    [read_image_tool] prompt='{prompt[:60]}...'")
    result = read_image(_current_image_url, prompt)
    return f"【图像识别结果】\n{result}"
