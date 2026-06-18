from pydantic import BaseModel, Field
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str
    content: str

class UploadFileItem(BaseModel):
    name: str
    base64: str
    type: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    image_url: Optional[str] = None
    upload_files: Optional[List[UploadFileItem]] = Field(default_factory=list)


class BuildKnowledgeRequest(BaseModel):
    files: List[UploadFileItem]

class ChatResponse(BaseModel):
    content: str
