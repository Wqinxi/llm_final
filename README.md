# AI Chat Agent

基于手绘架构图实现的前后端分离式 AI 对话应用。主 Agent 根据用户输入自动判断是否需要调用文档检索 Agent（Doc Agent）或图像识别 Agent（Image Agent），最终汇总生成回答。

## 架构概览

```
用户 -> 前端 -> /chat -> Main Agent
                          |
          ----------------- -----------------
          |                                 |
      Doc Agent                       Image Agent
          |                                 |
    普通 RAG Tool                    read_image Tool
    PageIndex RAG Tool
```

- **Main Agent**：意图识别与结果汇总，调用智谱大模型（`glm-4-flash`）。
- **Doc Agent**：提供文档增强能力，内置两个 Tool：
  - `rag_search`：普通 RAG 检索，基于 ChromaDB 向量数据库实现，支持 `.txt`、`.doc`、`.docx`、`.pdf` 格式。
  - `page_index_search`：结构化文档 PageIndex 检索，基于文档层级结构索引，支持 `.md`、`.markdown` 格式，检索结果会标注来源文档。
- **Image Agent**：提供图像识别能力，内置 `read_image` Tool，调用智谱视觉模型（`glm-4v`）。

## 目录结构

```
llm_final/
├── backend/
│   ├── main.py              # FastAPI 入口，提供 /chat 接口并挂载前端
│   ├── config.py            # 智谱 API 配置
│   ├── models/
│   │   └── schemas.py       # Pydantic 请求/响应模型
│   ├── agents/
│   │   ├── main_agent.py    # 主 Agent（意图判断 + 汇总回答）
│   │   ├── doc_agent.py     # 文档 Agent（RAG 工具调用）
│   │   └── image_agent.py   # 图像 Agent（视觉识别）
│   └── tools/
│       ├── rag_tool.py      # RAG 相关工具（基于 ChromaDB）
│       └── image_tool.py    # 图像识别工具
├── scripts/
│   ├── build_index.py       # RAG 向量索引构建脚本（支持增量更新）
│   └── build_pageindex.py   # PageIndex 结构索引构建脚本
├── data/
│   ├── raw_docs/            # 存放原始文档
│   │                         #   - RAG: .txt / .doc / .docx / .pdf
│   │                         #   - PageIndex: .md / .markdown
│   ├── chroma_db/           # 向量数据库持久化目录（RAG）
│   ├── index_state.json     # 索引状态（记录文件 MD5）
│   └── pageindex_workspace/ # PageIndex 索引工作目录
├── frontend/
│   └── index.html           # 单页面聊天界面（自适应输入框）
├── requirements.txt         # Python 依赖
└── README.md                # 本文件
```

## 环境准备

1. 安装 Python 3.10+。
2. 获取智谱 AI API Key（[开放平台](https://open.bigmodel.cn/)）。

## 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

> **Windows 提示**：若遇到权限拒绝错误，可添加 `--user` 参数，或在虚拟环境中安装。

依赖列表：
- `fastapi`
- `uvicorn`
- `openai`（用于调用智谱兼容接口）
- `python-multipart`
- `pydantic`

## 配置 API Key

打开 `backend/config.py`，将 `your-zhipu-api-key` 替换为你的真实 Key：

```python
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "your-zhipu-api-key")
```

或者通过环境变量设置（推荐）：

```bash
# Windows PowerShell
$env:ZHIPU_API_KEY="your-zhipu-api-key"

# Linux / macOS
export ZHIPU_API_KEY=your-zhipu-api-key
```

## 构建文档索引（RAG）

后端 RAG 检索依赖向量数据库，需要先将原始文档构建为向量索引。

### 1. 准备文档

将需要检索的文档放入 `data/raw_docs/` 目录下。目前支持以下格式：

| 格式 | 说明 |
|------|------|
| `.txt` / `.md` | 纯文本 / Markdown，直接读取 |
| `.docx` | Word 文档（需安装 `python-docx`） |
| `.pdf` | PDF 文档（需安装 `PyPDF2`） |
| `.doc` | 旧版 Word 文档（Windows 下需安装 `pywin32`，且系统中需有 Microsoft Word） |

> **提示**：如果 `.doc` 读取失败，建议将其另存为 `.docx` 后再放入目录。

### 2. 执行索引脚本

在项目根目录执行：

```bash
py scripts/build_index.py
```

脚本会：
- 读取 `data/raw_docs/` 下的所有支持格式文件。
- 将文本分块后，调用智谱 `embedding-3` 模型生成向量。
- 将向量索引保存到 `data/chroma_db/`。

### 3. 增量更新机制

脚本支持**增量构建**，不会每次都全量重建索引：

- 首次运行时，会索引所有文档。
- 再次运行时，脚本会比对 `data/index_state.json` 中记录的各文件 MD5：
  - **新增文件**：直接加入索引。
  - **内容变更**：删除旧索引，重新生成向量。
  - **未变更文件**：跳过，避免重复调用 Embedding API 浪费 token。
  - **已删除文件**：从向量库中移除对应的旧索引。

> 如需强制重建全部索引，可手动删除 `data/index_state.json` 和 `data/chroma_db/` 目录后重新运行脚本。

## 启动服务

在项目根目录执行：

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后：
- 前端页面：http://localhost:8000/
- API 文档：http://localhost:8000/docs

## 构建 PageIndex 索引（结构化文档检索）

PageIndex 适用于 Markdown 文档的结构化检索，基于文档层级结构（标题、段落）进行索引和查询，检索结果会明确标注来源文档。

### 1. 准备 Markdown 文档

将 `.md` 或 `.markdown` 文件放入 `data/raw_docs/` 目录或其子目录中。

### 2. 执行 PageIndex 索引脚本

在项目根目录执行：

```bash
py scripts/build_pageindex.py
```

脚本会：
- 递归读取 `data/raw_docs/` 下的所有 Markdown 文件。
- 调用智谱大模型分析文档结构，生成层级索引。
- 将索引保存到 `data/pageindex_workspace/`。

### 3. 索引特点

- **递归遍历**：支持子目录，不限层级。
- **增量索引**：已索引的文件会跳过，避免重复处理。
- **来源标注**：检索结果会自动标注参考的文档名称（含扩展名）。

> **注意**：PageIndex 依赖 `pageindex` 库，需确保已安装并在 `backend/config.py` 中配置 `PAGEINDEX_PATH`。

## 使用说明

1. 打开浏览器访问 `http://localhost:8000/`。
2. 在底部输入框中输入问题，按 **Enter** 发送（Shift+Enter 换行）。
3. 前端会根据文本内容自动调整输入框高度。
4. 后端 Main Agent 会自动判断：
   - 若问题涉及文档知识，自动调用 **Doc Agent** 进行检索增强：
     - 对 `.md` 文件：使用 **PageIndex** 结构化检索
     - 对 `.txt/.doc/.docx/.pdf` 文件：使用 **RAG** 向量检索
   - 若问题涉及图像，自动调用 **Image Agent** 进行识别。
   - 否则直接由大模型回答。

## 后续扩展

- **图片上传**：前端增加图片上传组件，将图片转为 Base64 后通过 `image_url` 字段传给后端。
- **数据持久化**：接入数据库，保存对话历史、文档原始内容与向量嵌入。
- **更多文档格式**：扩展 PageIndex 支持 PDF 结构解析，或增加更多文件类型的支持。
