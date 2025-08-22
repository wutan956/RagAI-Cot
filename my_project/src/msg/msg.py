from pydantic import BaseModel

class Message(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]  # 聊天历史（类似 OpenAI API）


class QueryResponse(BaseModel):
    answer: str  # LLM 生成的回答
    sources: List[str] = []  # 来源 PDF 文件名
