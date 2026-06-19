# AI Chat Agent

基于手绘架构图实现的前后端分离式 AI 对话应用。主 Agent 根据用户输入自动判断是否需要调用文档检索 Agent（Doc Agent）或图像识别 Agent（Image Agent），最终汇总生成回答。前端支持**知识问答**与**构建知识库**两种模式，可在对话界面一键切换。

## 架构概览

```
用户 -> 前端 -> /chat-stream -> Main Agent
                                  |
                  ----------------- -----------------
                  |                                 |
              Doc Agent                       Image Agent
                  |                                 |
               RAG Tool                      read_image Tool
            PageIndex Tool
```

- **Main Agent**：意图识别与结果汇总，调用智谱大模型（`glm-4-flash`）。
- **Doc Agent**：提供文档增强能力，内置两个检索工具并合并返回结果：
  - `rag_search`：普通 RAG 检索，基于 ChromaDB 向量数据库实现，适用于 `.txt`、`.doc`、`.docx`、`.pdf` 文档。
  - `page_index_search`：结构化 PageIndex 检索，基于文档层级结构索引，适用于 `.md`、`.markdown` 文档，检索结果会标注来源文档。
- **Image Agent**：提供图像识别能力，内置 `read_image` Tool，调用智谱视觉模型（`glm-4.6v-flash`）。
- **Knowledge Builder**：支持通过前端上传文档并实时构建索引，自动根据文件类型选择向量索引或 PageIndex。

## 目录结构

```
llm_final/
├── backend/
│   ├── main.py              # FastAPI 入口，提供 /chat 与 /build-knowledge 接口并挂载前端
│   ├── config.py            # 智谱 API 配置
│   ├── models/
│   │   └── schemas.py       # Pydantic 请求/响应模型
│   ├── agents/
│   │   ├── main_agent.py    # 主 Agent（意图判断 + 汇总回答）
│   │   ├── doc_agent.py     # 文档 Agent（RAG 工具调用）
│   │   └── image_agent.py   # 图像 Agent（视觉识别）
│   ├── tools/
│   │   ├── rag_tool.py      # RAG 相关工具（基于 ChromaDB）
│   │   ├── pageindex_tool.py# PageIndex 工具封装
│   │   └── image_tool.py    # 图像识别工具
│   └── services/
│       └── knowledge_builder.py  # 知识库构建服务（文件保存 + 索引构建 + 进度推送）
├── scripts/
│   ├── build_index.py       # RAG 向量索引构建脚本（支持增量更新）
│   └── build_pageindex.py   # PageIndex 结构索引构建脚本
├── data/
│   ├── raw_docs/            # 存放原始文档
│   │                         #   - RAG: .txt / .doc / .docx / .pdf
│   │                         #   - PageIndex: .md / .markdown
│   │                         #   - 前端上传: user_custom/（自动创建）
│   ├── chroma_db/           # 向量数据库持久化目录（RAG）
│   ├── index_state.json     # 索引状态（记录文件 MD5）
│   └── pageindex_workspace/ # PageIndex 索引工作目录
├── frontend/
│   └── index.html           # 单页面聊天界面（支持模式切换、文件拖拽上传）
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
- `chromadb`（向量数据库）
- `python-docx`（Word 读取）
- `pdfplumber`（PDF 读取增强）
- `PyPDF2`（PDF 读取回退方案）
- `pywin32`（Windows 下读取 `.doc`）
- `litellm` / `pageindex`（PageIndex 检索支持）

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

## 启动服务

在项目根目录执行：

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后：
- 前端页面：http://localhost:8000/
- API 文档：http://localhost:8000/docs

## 使用说明

### 1. 知识问答（默认模式）

1. 打开浏览器访问 `http://localhost:8000/`。
2. 在底部输入框中输入问题，按 **Enter** 发送（Shift+Enter 换行）。
3. 支持拖拽上传图片或文档（`.txt`、`.md`、`.pdf`、`.doc`、`.docx`），已选文件在输入框上方水平排列。
4. 后端 Main Agent 会自动判断：
   - 若问题涉及文档知识，自动调用 **Doc Agent** 进行检索增强：
     - 对 `.md` 文件：使用 **PageIndex** 结构化检索
     - 对 `.txt/.doc/.docx/.pdf` 文件：使用 **RAG** 向量检索
   - 若问题涉及图像，自动调用 **Image Agent** 进行识别。
   - 否则直接由大模型回答。

### 2. 构建知识库

1. 点击发送按钮左侧的**箭头按钮**，在下拉菜单中选择**构建知识库**。
2. 底部输入区域变为上传按钮，支持：
   - **点击上传**：唤起文件选择器，可多选。
   - **拖拽上传**：将文件直接拖入页面任意位置。
   - 支持格式：`.pdf`、`.txt`、`.md`、`.doc`、`.docx`。
3. 已选文件在输入框上方水平排列，可点击"删除"移除单个文件。
4. 点击**上传并构建**，前端通过 SSE 流式接收构建进度：
   - 文件保存状态
   - 各文件的索引构建状态（构建中 / 已完成 / 失败）
   - 整体完成提示
5. 构建完成后，文档即可被问答模式检索使用。

> **注意**：切换模式时会自动清空当前已选文件。

## 构建文档索引（命令行方式）

除前端一键构建外，也可通过命令行脚本手动构建索引，适合批量处理或 CI 场景。

### 构建 RAG 向量索引

```bash
py scripts/build_index.py
```

脚本会读取 `data/raw_docs/` 下的 `.txt`、`.doc`、`.docx`、`.pdf` 文件，分块后调用智谱 `embedding-3` 模型生成向量，保存到 `data/chroma_db/`。

支持**增量构建**：
- 首次运行时索引所有文档。
- 再次运行时比对 `data/index_state.json` 中的 MD5：
  - **新增文件**：加入索引。
  - **内容变更**：删除旧索引，重新生成向量。
  - **未变更文件**：跳过。
  - **已删除文件**：从向量库移除旧索引。

> 如需强制重建全部索引，可手动删除 `data/index_state.json` 和 `data/chroma_db/` 目录后重新运行脚本。

### 构建 PageIndex 结构索引

```bash
py scripts/build_pageindex.py
```

脚本会递归读取 `data/raw_docs/` 下的所有 Markdown 文件（仅 `.md` / `.markdown`），调用智谱大模型分析文档结构，生成层级索引，保存到 `data/pageindex_workspace/`。

- 支持子目录，不限层级。
- 已索引的文件会跳过，避免重复处理。
- 检索结果自动标注来源文档名称。

> **注意**：PageIndex 依赖 `pageindex` 库，需确保已安装并在 `backend/config.py` 中配置 `PAGEINDEX_PATH`。

## 后端接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 普通对话接口，返回 JSON 格式回答 `{"content": ...}` |
| `/chat-stream` | POST | 流式对话接口，返回 SSE 格式的思考日志与回答内容 |
| `/build-knowledge` | POST | 构建知识库接口，接收多文件 Base64，返回 SSE 格式的构建进度 |

## 后续扩展

- **数据持久化**：接入数据库，保存对话历史、文档原始内容与向量嵌入。
- **更多文档格式**：扩展 PageIndex 支持 PDF 结构解析，或增加更多文件类型的支持。
