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
    PageIndex RAG Tool (预留)
```

- **Main Agent**：意图识别与结果汇总，调用智谱大模型（`glm-4-flash`）。
- **Doc Agent**：提供文档增强能力，内置两个 Tool：
  - `rag_search`：普通 RAG 检索（当前为 Mock 实现，可接入真实向量库）。
  - `page_index_search`：结构文档 PageIndex 检索（预留接口）。
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
│       ├── rag_tool.py      # RAG 相关工具
│       └── image_tool.py    # 图像识别工具
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

## 启动服务

在项目根目录执行：

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后：
- 前端页面：http://localhost:8000/
- API 文档：http://localhost:8000/docs

## 使用说明

1. 打开浏览器访问 `http://localhost:8000/`。
2. 在底部输入框中输入问题，按 **Enter** 发送（Shift+Enter 换行）。
3. 前端会根据文本内容自动调整输入框高度。
4. 后端 Main Agent 会自动判断：
   - 若问题涉及文档知识，自动调用 **Doc Agent** 进行 RAG 增强。
   - 若问题涉及图像，自动调用 **Image Agent** 进行识别（当前版本需通过 API 传入 `image_url`）。
   - 否则直接由大模型回答。

## 后续扩展

- **RAG 接入真实向量库**：修改 `backend/tools/rag_tool.py` 中的 `rag_search` 函数，接入 Chroma / Milvus 等向量数据库。
- **PageIndex RAG**：实现 `page_index_search` 函数，支持按页码索引的结构化文档检索。
- **图片上传**：前端增加图片上传组件，将图片转为 Base64 后通过 `image_url` 字段传给后端。
- **数据持久化**：接入数据库，保存对话历史、文档原始内容与向量嵌入。
