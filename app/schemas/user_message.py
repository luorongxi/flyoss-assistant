from pydantic import BaseModel, Field

class UserMessage(BaseModel):
    """用户消息输入模型"""
    text: str = Field(..., description="用户输入的文本消息")
    sender_id: str = Field(..., description="用户唯一标识")
    conversation_id: str = Field(..., description="会话唯一标识")
    timestamp: int = Field(..., description="消息时间戳")