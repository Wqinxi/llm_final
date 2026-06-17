import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.models.schemas import ChatRequest, ChatResponse
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

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msgs = [{"role": m.role, "content": m.content} for m in req.messages]
    image_url = req.image_url
    upload_files = req.upload_files

    # 解析所有上传文档，拼接完整文档文本
    doc_context = ""
    for file_item in upload_files:
        text = parse_document(file_item.name, file_item.base64)
        doc_context += text + "\n\n"

    answer = main_agent.run(
        messages=msgs,
        image_url=image_url,
        upload_doc_content=doc_context  # 新增参数传递文档解析内容
    )
    return ChatResponse(content=answer)

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)