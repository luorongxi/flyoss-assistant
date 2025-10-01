from enum import Enum
from pydantic import BaseModel

class IntentType(str, Enum):
    """意图类型枚举"""
    QUESTION = "question"
    COMMAND = "command"
    CHAT = "chat"
    TOOL = "tool"

class IntentResult(BaseModel):
    """意图识别结果模型"""
    intent: IntentType
    reason: str
    requires_tool: bool
    tool_suggestion: str = ""