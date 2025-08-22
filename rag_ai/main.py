import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir,'src')
sys.path.append(src_path)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import time
import os
from process import process_user_question
app = FastAPI()


# 定义请求模型
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = "deepseek-r1-distill-qwen-1.5b"


@app.post("/generate/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    # 提取当前用户问题
    # 准备历史的对话数据
    messages = [msg.dict() for msg in request.messages]
    if len(messages) > 1:
        history = messages[:-1]
    else:
        history = []

    print("___________________________________________")
    print(history)
    print("_________________________________________")
    # 提取当前用户问题
    last_user_msg = next((msg.content for msg in reversed(request.messages) if msg.role == "user"), None)
    if not last_user_msg:
        raise HTTPException(400, detail="No user message found")

    print("=" * 50)
    print(f"接收到用户问题: {last_user_msg}")
    print("=" * 50)

    try:
        # 调用你的处理逻辑
        answer = process_user_question(last_user_msg)

        print("=" * 50)
        print("处理完成，返回答案")
        print("=" * 50)

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model or "deepseek-r1-distill-qwen-1.5b",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer,
                    "sources": [],  # 可以根据需要添加来源
                    "tool_calls": None
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }

    except Exception as e:
        print(f"处理过程中出错: {e}")
        raise HTTPException(500, detail=f"处理失败: {str(e)}")


# 健康检查端点
@app.get("/health")
async def health_check():
    print("health被调用")
    return {"status": "healthy", "message": "Service is running"}


# 测试端点
@app.post("/test")
async def test_endpoint(question: str):
    """测试端点，直接处理问题"""
    try:
        result = process_user_question(question)
        return {"question": question, "answer": result}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)