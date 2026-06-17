"""工具封装：供 Agent 调用 Doc / Image 能力。"""

from backend.tools.rag_tool import rag_search
from backend.tools.pageindex_tool import page_index_search
from backend.tools.image_tool import read_image

_current_image_url: str | None = None


def set_current_image_url(url: str | None) -> None:
    global _current_image_url
    _current_image_url = url


class SimpleTool:
    """简单的工具封装类，模拟 LangChain Tool 的接口。"""
    
    def __init__(self, name: str, description: str, func):
        self.name = name
        self.description = description
        self._func = func
    
    def invoke(self, *args, **kwargs):
        return self._func(*args, **kwargs)
    
    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)


def _rag_search_wrapper(query: str) -> str:
    """从文档库检索与用户问题相关的文档片段。输入检索关键词或完整问题。"""
    print(f"DEBUG:    [rag_search_tool] query='{query}'")
    result = rag_search(query)
    return f"【文档检索结果】\n{result}"


def _page_index_search_wrapper(query: str) -> str:
    """通过 PageIndex 层级结构索引检索文档。适用于需要按目录/章节/页码定位的问题。"""
    print(f"DEBUG:    [page_index_search_tool] query='{query}'")
    result = page_index_search(query)
    return f"【PageIndex 检索结果】\n{result}"


def _read_image_wrapper(prompt: str = "请详细描述这张图片的内容，并提取与问题相关的信息。") -> str:
    """识别并分析用户当前上传的图片。输入你希望图像分析侧重的提示语。"""
    global _current_image_url
    if not _current_image_url:
        return "【图像识别结果】当前没有可用的图片，请提示用户上传图片。"
    print(f"DEBUG:    [read_image_tool] prompt='{prompt[:60]}...'")
    result = read_image(_current_image_url, prompt)
    return f"【图像识别结果】\n{result}"


# 创建工具实例
rag_search_tool = SimpleTool(
    name="rag_search_tool",
    description="从文档库检索与用户问题相关的文档片段。输入检索关键词或完整问题。",
    func=_rag_search_wrapper
)

page_index_search_tool = SimpleTool(
    name="page_index_search_tool",
    description="通过 PageIndex 层级结构索引检索文档。适用于需要按目录/章节/页码定位的问题。",
    func=_page_index_search_wrapper
)

read_image_tool = SimpleTool(
    name="read_image_tool",
    description="识别并分析用户当前上传的图片。输入你希望图像分析侧重的提示语。",
    func=_read_image_wrapper
)
