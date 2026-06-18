import os
import sys
import json
from typing import AsyncGenerator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

from backend.models.schemas import ChatRequest
from backend.agents.main_agent import MainAgent
from backend.tools.doc_parser import parse_document

app = FastAPI(title="AI Chat Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

main_agent = MainAgent()

@app.on_event("startup")
async def startup_event():
    from backend.tools.rag_tool import _init_chroma
    try:
        _init_chroma()
        print("INFO:     向量数据库已加载")
    except Exception as e:
        print(f"WARNING:  向量数据库加载失败: {e}")

# 普通一次性接口（无改动，底层逻辑已统一）
@app.post("/chat")
async def chat(req: ChatRequest):
    msgs = [{"role": m.role, "content": m.content} for m in req.messages]
    image_url = req.image_url
    upload_files = req.upload_files

    doc_context = ""
    for file_item in upload_files:
        text = parse_document(file_item.name, file_item.base64)
        doc_context += text + "\n\n"

    answer = main_agent.run(
        messages=msgs,
        image_url=image_url,
        upload_doc_content=doc_context
    )
    return {"content": answer}

# 流式生成器：仅封装SSE协议，无任何业务逻辑
async def stream_chat(req: ChatRequest) -> AsyncGenerator[str, None]:
    msgs = [{"role": m.role, "content": m.content} for m in req.messages]
    image_url = req.image_url
    upload_files = req.upload_files

    # 解析上传文档（仅入参处理）
    doc_context = ""
    for file_item in upload_files:
        text = parse_document(file_item.name, file_item.base64)
        doc_context += text + "\n\n"

    # 封装SSE日志生成函数，传给agent作为回调
    def create_sse_log_yielder(log_text: str):
        log_data = json.dumps({"type": "log", "content": log_text}, ensure_ascii=False)
        return f"data: {log_data}\n\n"

    # 调用统一流式agent，传入日志回调
    agent_stream = main_agent.stream_run(
        messages=msgs,
        image_url=image_url,
        upload_doc_content=doc_context,
        log_callback=create_sse_log_yielder
    )

    # 遍历agent产出的每一段（日志行 / 回答文本 / 结束标记）
    async for chunk in agent_stream:
        if chunk is None:
            # 模型输出完成，推送结束事件
            finish_data = json.dumps({"type": "finish", "msg": "全部流程执行结束，回答生成完成"}, ensure_ascii=False)
            yield f"data: {finish_data}\n\n"
            break
        # chunk分两种：SSE日志字符串 / 回答文本增量
        if chunk.startswith("data: "):
            # 是日志，直接下发
            yield chunk
        else:
            # 是回答文本，包装answer类型下发
            ans_data = json.dumps({"type": "answer", "content": chunk}, ensure_ascii=False)
            yield f"data: {ans_data}\n\n"

# 流式SSE接口
@app.post("/chat-stream", response_class=StreamingResponse)
async def chat_stream(req: ChatRequest):
    generator = stream_chat(req)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff"
        }
    )

# 静态页面路由
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# 背景食物图片静态资源
data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
flow_images_dir = os.path.join(data_dir, "flow_images")
app.mount("/data/flow_images", StaticFiles(directory=flow_images_dir), name="flow_images")

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/flow-images")
async def list_flow_images():
    if not os.path.exists(flow_images_dir):
        return {"images": []}
    files = [
        f for f in os.listdir(flow_images_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"))
    ]
    return {"images": sorted(files)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)