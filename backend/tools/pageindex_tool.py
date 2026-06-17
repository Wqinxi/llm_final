"""
PageIndex 工具集
封装 PageIndexClient 的三个核心工具，并提供 agentic 层级结构检索：
  - get_document()           — 文档元数据（状态、页数等）
  - get_document_structure() — 文档树形结构索引
  - get_page_content()       — 按页码/行号读取正文
"""
import json
import os
import sys

from openai import OpenAI

from backend.config import (
    ZHIPU_API_KEY,
    ZHIPU_BASE_URL,
    MAIN_MODEL,
    PAGEINDEX_PATH,
    PAGEINDEX_WORKSPACE,
    PAGEINDEX_MODEL,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DOCS_DIR = os.path.join(PROJECT_ROOT, "data", "raw_docs")
SUPPORTED_EXTS = {".md", ".markdown"}

_pageindex_client = None
_llm_client = None

PAGEINDEX_AGENT_PROMPT = """你是 PageIndex 文档检索助手，通过层级结构索引进行无向量检索。

工具使用规范：
1. 先调用 list_documents 了解可用文档及 doc_id
2. 调用 get_document(doc_id) 确认文档状态与页数/行数
3. 调用 get_document_structure(doc_id) 定位相关章节与页码范围
4. 调用 get_page_content(doc_id, pages) 获取精确页面内容，范围尽量小，如 "5-7"、"3,8"、"12"
5. 每次调用工具前，用一句话说明调用原因

请仅基于工具返回的内容回答，保持简洁准确。"""

PAGEINDEX_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": "列出 workspace 中所有已索引文档及其 doc_id、名称、类型。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_document",
            "description": "获取文档元数据：状态、页数/行数、名称、描述。",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string", "description": "文档 ID"},
                },
                "required": ["doc_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_document_structure",
            "description": "获取文档完整树形结构（不含正文），用于定位相关章节。",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string", "description": "文档 ID"},
                },
                "required": ["doc_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_content",
            "description": (
                "获取指定页码或行号的正文。"
                "PDF 用页码，如 '5-7'、'3,8'、'12'；"
                "Markdown 用 structure 中 line_num 字段对应的行号。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string", "description": "文档 ID"},
                    "pages": {"type": "string", "description": "页码或行号范围，如 '5-7'"},
                },
                "required": ["doc_id", "pages"],
            },
        },
    },
]


def _ensure_pageindex_importable():
    if PAGEINDEX_PATH not in sys.path:
        sys.path.insert(0, PAGEINDEX_PATH)


def _get_llm_client() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)
    return _llm_client


def get_pageindex_client():
    """获取 PageIndexClient 单例，并配置智谱 API 供 litellm 使用。"""
    global _pageindex_client
    if _pageindex_client is None:
        _ensure_pageindex_importable()
        from pageindex import PageIndexClient

        os.environ.setdefault("OPENAI_API_KEY", ZHIPU_API_KEY)
        os.environ.setdefault("OPENAI_API_BASE", ZHIPU_BASE_URL.rstrip("/"))

        os.makedirs(PAGEINDEX_WORKSPACE, exist_ok=True)
        _pageindex_client = PageIndexClient(
            api_key=ZHIPU_API_KEY,
            model=PAGEINDEX_MODEL,
            retrieve_model=PAGEINDEX_MODEL,
            workspace=PAGEINDEX_WORKSPACE,
        )
    return _pageindex_client


def list_documents() -> str:
    """列出所有已索引文档，doc_name 包含扩展名。"""
    client = get_pageindex_client()
    catalog = []
    for doc_id, doc in client.documents.items():
        # 从文件路径获取带扩展名的文件名
        doc_path = doc.get("path", "")
        doc_name_with_ext = os.path.basename(doc_path)

        entry = {
            "doc_id": doc_id,
            "doc_name": doc_name_with_ext,
            "type": doc.get("type", ""),
            "doc_description": doc.get("doc_description", ""),
        }
        if doc.get("type") == "pdf":
            entry["page_count"] = doc.get("page_count")
        elif doc.get("type") == "md":
            entry["line_count"] = doc.get("line_count")
        catalog.append(entry)
    return json.dumps(catalog, ensure_ascii=False)


def get_document(doc_id: str) -> str:
    """获取文档元数据：状态、页数、名称、描述。"""
    client = get_pageindex_client()
    return client.get_document(doc_id)


def get_document_structure(doc_id: str) -> str:
    """获取文档树形结构索引（不含正文）。"""
    client = get_pageindex_client()
    return client.get_document_structure(doc_id)


def get_page_content(doc_id: str, pages: str) -> str:
    """
    获取指定页码或行号的正文。
    示例：'5-7'、'3,8'、'12'；Markdown 使用 structure 中的 line_num。
    """
    client = get_pageindex_client()
    return client.get_page_content(doc_id, pages)


def ensure_documents_indexed() -> list[str]:
    """将 raw_docs 中支持的 Markdown 文件索引到 PageIndex workspace（递归遍历子目录）。"""
    client = get_pageindex_client()
    indexed_ids = []

    if not os.path.isdir(RAW_DOCS_DIR):
        return indexed_ids

    # 递归遍历所有子目录
    abs_paths = set()
    for root, dirs, files in os.walk(RAW_DOCS_DIR):
        for fname in files:
            if os.path.splitext(fname)[1].lower() in SUPPORTED_EXTS:
                abs_paths.add(os.path.abspath(os.path.join(root, fname)))

    path_to_id = {
        os.path.abspath(doc.get("path", "")): doc_id
        for doc_id, doc in client.documents.items()
        if doc.get("path")
    }

    for file_path in sorted(abs_paths):
        if file_path in path_to_id:
            indexed_ids.append(path_to_id[file_path])
            continue
        try:
            print(f"DEBUG:    [PageIndex] 正在索引: {os.path.basename(file_path)}")
            doc_id = client.index(file_path)
            indexed_ids.append(doc_id)
        except Exception as e:
            print(f"WARNING:  [PageIndex] 索引失败 {os.path.basename(file_path)}: {e}")

    return indexed_ids


def _dispatch_tool(name: str, arguments: dict) -> str:
    if name == "list_documents":
        return list_documents()
    if name == "get_document":
        return get_document(arguments["doc_id"])
    if name == "get_document_structure":
        return get_document_structure(arguments["doc_id"])
    if name == "get_page_content":
        return get_page_content(arguments["doc_id"], arguments["pages"])
    return json.dumps({"error": f"未知工具: {name}"})


def page_index_search(query: str, max_iterations: int = 10) -> str:
    """
    PageIndex 层级结构检索：Agent 自动调用 get_document / get_document_structure / get_page_content。
    检索结果会标注来源文档名称。
    """
    print(f"DEBUG:    [PageIndex] 开始 agentic 检索 query='{query}'")
    ensure_documents_indexed()
    client = get_pageindex_client()

    if not client.documents:
        return (
            "【PageIndex 检索结果】\n"
            "暂无已索引的结构化文档。请将 PDF 或 Markdown 文件放入 data/raw_docs/，"
            "并运行 scripts/build_pageindex.py 构建索引。\n"
        )

    catalog = list_documents()
    # 构建文档 ID 到名称的映射，用于后续标注来源（使用带扩展名的文件名）
    doc_id_to_name = {}
    for doc_id, doc in client.documents.items():
        doc_path = doc.get("path", "")
        doc_name_with_ext = os.path.basename(doc_path)
        doc_id_to_name[doc_id] = doc_name_with_ext

    # 在 system prompt 中增加来源标注要求
    prompt_with_citation = (
        f"{PAGEINDEX_AGENT_PROMPT}\n\n"
        "重要要求：在回答的最后，必须明确标注参考来源的文档名称。"
        "格式：在回答结束后另起一行，输出 '---' 分割线，然后写 '参考来源：<文档名称>'。\n\n"
        f"可用文档列表：\n{catalog}"
    )
    messages = [
        {"role": "system", "content": prompt_with_citation},
        {"role": "user", "content": query},
    ]
    # 记录检索过程中引用的文档 ID
    cited_doc_ids = set()

    llm = _get_llm_client()
    for i in range(max_iterations):
        response = llm.chat.completions.create(
            model=MAIN_MODEL,
            messages=messages,
            tools=PAGEINDEX_TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.2,
        )
        message = response.choices[0].message

        if message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )
            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments or "{}")
                print(f"DEBUG:    [PageIndex] tool_call={fn_name} args={fn_args}")
                # 记录引用的文档 ID
                if "doc_id" in fn_args:
                    cited_doc_ids.add(fn_args["doc_id"])
                result = _dispatch_tool(fn_name, fn_args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )
            continue

        answer = message.content or ""
        # 如果模型没有标注来源，自动补充
        if cited_doc_ids and "---" not in answer:
            source_names = [doc_id_to_name.get(doc_id, "未知文档") for doc_id in cited_doc_ids]
            source_str = ", ".join(source_names)
            answer += f"\n\n---\n参考来源：{source_str}"
        print(f"DEBUG:    [PageIndex] 检索完成，迭代={i + 1}，结果长度={len(answer)}")
        return answer

    return "【PageIndex 检索结果】\n检索迭代次数过多，请简化问题后重试。\n"
