"""
构建 PageIndex 层级结构索引。

将 data/raw_docs/ 下的 PDF / Markdown 文件索引到 data/pageindex_workspace/。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tools.pageindex_tool import ensure_documents_indexed, get_pageindex_client, list_documents


def main():
    print("=" * 60)
    print("PageIndex 索引构建")
    print("=" * 60)

    doc_ids = ensure_documents_indexed()
    client = get_pageindex_client()

    print(f"\n索引完成，共 {len(client.documents)} 份文档：")
    for item in __import__("json").loads(list_documents()):
        print(f"  - [{item['doc_id'][:8]}...] {item['doc_name']} ({item['type']})")

    if not doc_ids and not client.documents:
        print("\n提示：请将 PDF 或 Markdown 文件放入 data/raw_docs/ 后重试。")


if __name__ == "__main__":
    main()
