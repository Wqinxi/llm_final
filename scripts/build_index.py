"""
索引构建脚本（支持增量更新）
用法：
    py scripts/build_index.py
说明：
    读取 data/raw_docs/ 下的 .txt 文件，分块后调用智谱 Embedding API 构建向量索引，
    保存到 data/chroma_db/ 目录下。
    通过维护 data/index_state.json 中的文件 MD5，只对新文件或内容变更的文件重新索引。
"""
import hashlib
import json
import os
import sys
import argparse

# 将项目根目录加入 sys.path，以便导入 backend 包
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

import chromadb
from openai import OpenAI
from backend.config import ZHIPU_API_KEY, ZHIPU_BASE_URL

EMBEDDING_MODEL = "embedding-3"
RAW_DOCS_PATH = os.path.join(PROJECT_ROOT, "data", "raw_docs")
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")
INDEX_STATE_PATH = os.path.join(PROJECT_ROOT, "data", "index_state.json")


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


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list:
    """简单文本分块"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def compute_md5(filepath: str) -> str:
    """计算文件 MD5"""
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="构建文档向量索引")
    parser.add_argument("--input-dir", default=RAW_DOCS_PATH, help="原始文档目录")
    parser.add_argument("--db-path", default=CHROMA_DB_PATH, help="向量数据库保存路径")
    args = parser.parse_args()

    if not os.path.exists(args.input_dir):
        print(f"原始文档目录不存在: {args.input_dir}")
        print("请先将 .txt 文档放入该目录后再运行此脚本。")
        return

    # 加载历史索引状态
    index_state = {}
    if os.path.exists(INDEX_STATE_PATH):
        with open(INDEX_STATE_PATH, "r", encoding="utf-8") as f:
            index_state = json.load(f)

    client = chromadb.PersistentClient(path=args.db_path)
    collection = client.get_or_create_collection(
        name="docs",
        embedding_function=ZhipuEmbeddingFunction(),
    )

    # 计算当前所有 .txt 文件的 MD5
    current_files = {}
    for filename in os.listdir(args.input_dir):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(args.input_dir, filename)
        current_files[filename] = compute_md5(filepath)

    # 判断哪些文件需要重新索引，哪些旧文件已被删除
    files_to_index = []
    files_to_delete = []

    for filename, md5 in current_files.items():
        if filename not in index_state or index_state[filename] != md5:
            files_to_index.append(filename)

    for filename in list(index_state.keys()):
        if filename not in current_files:
            files_to_delete.append(filename)

    # 删除已从目录中移除的文件对应的旧索引
    for filename in files_to_delete:
        collection.delete(where={"source": filename})
        del index_state[filename]
        print(f"已删除旧索引: {filename}")

    # 对新文件或内容变更的文件进行索引（先删旧再添加）
    for filename in files_to_index:
        filepath = os.path.join(args.input_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text)

        # 如果是变更文件，先删除旧 chunks
        if filename in index_state:
            collection.delete(where={"source": filename})
            print(f"已更新旧索引: {filename}")

        docs = []
        ids = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            docs.append(chunk)
            ids.append(f"{filename}_{i}")
            metadatas.append({"source": filename, "chunk_index": i})

        collection.add(documents=docs, ids=ids, metadatas=metadatas)
        index_state[filename] = current_files[filename]
        print(f"已索引 {filename}，分块数: {len(chunks)}")

    # 保存索引状态
    os.makedirs(os.path.dirname(INDEX_STATE_PATH), exist_ok=True)
    with open(INDEX_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(index_state, f, ensure_ascii=False, indent=2)

    if not files_to_index and not files_to_delete:
        print("所有文档均未变更，无需更新索引。")
    else:
        print("索引更新完成！向量数据库已保存到 data/chroma_db/")


if __name__ == "__main__":
    main()
