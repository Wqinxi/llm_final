"""
知识库构建服务
接收文件列表，保存到 data/raw_docs/user_custom/，
根据文件类型异步构建索引并通过 SSE 推送进度。
"""
import os
import json
import hashlib
import base64
import asyncio
from typing import AsyncGenerator

import chromadb
from openai import OpenAI

from backend.config import ZHIPU_API_KEY, ZHIPU_BASE_URL
from backend.tools.pageindex_tool import get_pageindex_client

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
USER_CUSTOM_DIR = os.path.join(PROJECT_ROOT, "data", "raw_docs", "user_custom")
RAW_DOCS_DIR = os.path.join(PROJECT_ROOT, "data", "raw_docs")
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")
INDEX_STATE_PATH = os.path.join(PROJECT_ROOT, "data", "index_state.json")

EMBEDDING_MODEL = "embedding-3"
VECTOR_SUPPORTED_EXTS = {".txt", ".doc", ".docx", ".pdf"}
PAGEINDEX_SUPPORTED_EXTS = {".md", ".markdown"}


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class ZhipuEmbeddingFunction:
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
        return response.data[0].embedding

    def name(self):
        return "zhipu_embedding"


def _decode_base64_file(base64_str: str) -> bytes:
    if base64_str.startswith("data:"):
        base64_str = base64_str.split(",")[-1]
    return base64.b64decode(base64_str)


def _read_file(filepath: str) -> str:
    """根据文件扩展名读取文本内容（从 build_index.py 复刻）"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in {".txt", ".md"}:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    if ext == ".docx":
        try:
            import docx
            document = docx.Document(filepath)
            return "\n".join([p.text for p in document.paragraphs])
        except Exception as e:
            print(f"读取 {filepath} 失败: {e}")
            return ""

    if ext == ".pdf":
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except ImportError:
            pass
        except Exception as e:
            print(f"DEBUG: pdfplumber 读取 {filepath} 失败: {e}")

        try:
            import PyPDF2
            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            print(f"读取 {filepath} 失败: {e}")
            return ""

    if ext == ".doc":
        try:
            import win32com.client as wc
            word = wc.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(os.path.abspath(filepath))
            text = doc.Content.Text
            doc.Close(False)
            word.Quit()
            return text
        except ImportError:
            print(f"跳过 {filepath}：读取 .doc 需要安装 pywin32")
            return ""
        except Exception as e:
            print(f"读取 {filepath} 失败: {e}")
            return ""

    return ""


def _chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _compute_md5(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


async def build_knowledge_stream(files: list) -> AsyncGenerator[str, None]:
    """
    files: list of dict with keys name, base64, type
    """
    os.makedirs(USER_CUSTOM_DIR, exist_ok=True)

    # 1. 保存文件
    yield _sse({"type": "log", "content": "正在保存文件..."})
    saved_paths = []
    for f in files:
        fname = f["name"]
        filepath = os.path.join(USER_CUSTOM_DIR, fname)
        try:
            data = _decode_base64_file(f["base64"])
            with open(filepath, "wb") as fh:
                fh.write(data)
            saved_paths.append(filepath)
            yield _sse({"type": "progress", "file": fname, "status": "saved"})
        except Exception as e:
            yield _sse({"type": "progress", "file": fname, "status": "error", "msg": str(e)})

    if not saved_paths:
        yield _sse({"type": "finish", "msg": "没有成功保存的文件"})
        return
    yield _sse({"type": "log", "content": "文件保存完成"})

    md_files = [p for p in saved_paths if os.path.splitext(p)[1].lower() in PAGEINDEX_SUPPORTED_EXTS]
    other_files = [p for p in saved_paths if os.path.splitext(p)[1].lower() in VECTOR_SUPPORTED_EXTS]

    # 2. 构建 PageIndex（仅限 md）
    if md_files:
        yield _sse({"type": "log", "content": "开始构建 PageIndex 索引..."})
        client = get_pageindex_client()
        for fp in md_files:
            fname = os.path.basename(fp)
            yield _sse({"type": "progress", "file": fname, "status": "building"})
            try:
                await asyncio.get_running_loop().run_in_executor(None, client.index, fp)
                yield _sse({"type": "progress", "file": fname, "status": "done"})
            except Exception as e:
                yield _sse({"type": "progress", "file": fname, "status": "error", "msg": str(e)})

    # 3. 构建向量索引（txt/doc/docx/pdf）
    if other_files:
        yield _sse({"type": "log", "content": "开始构建向量索引..."})
        embedding_fn = ZhipuEmbeddingFunction()
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_or_create_collection(
            name="docs", embedding_function=embedding_fn
        )

        index_state = {}
        if os.path.exists(INDEX_STATE_PATH):
            with open(INDEX_STATE_PATH, "r", encoding="utf-8") as f:
                index_state = json.load(f)

        for fp in other_files:
            fname = os.path.basename(fp)
            rel_path = os.path.relpath(fp, RAW_DOCS_DIR)
            yield _sse({"type": "progress", "file": fname, "status": "building"})

            text = await asyncio.get_running_loop().run_in_executor(None, _read_file, fp)
            if not text.strip():
                yield _sse({"type": "progress", "file": fname, "status": "error", "msg": "未能读取到有效文本"})
                continue

            chunks = _chunk_text(text)

            # 删除旧 chunks（如果存在）
            if rel_path in index_state:
                await asyncio.get_running_loop().run_in_executor(
                    None, lambda rp=rel_path: collection.delete(where={"source": rp})
                )

            docs = []
            ids = []
            metadatas = []
            for i, chunk in enumerate(chunks):
                docs.append(chunk)
                ids.append(f"{rel_path}_{i}")
                metadatas.append({"source": rel_path, "chunk_index": i})

            await asyncio.get_running_loop().run_in_executor(
                None, lambda: collection.add(documents=docs, ids=ids, metadatas=metadatas)
            )
            index_state[rel_path] = _compute_md5(fp)
            yield _sse({"type": "progress", "file": fname, "status": "done"})

        os.makedirs(os.path.dirname(INDEX_STATE_PATH), exist_ok=True)
        with open(INDEX_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(index_state, f, ensure_ascii=False, indent=2)

    yield _sse({"type": "finish", "msg": "全部构建完成"})
