from enum import Enum
from pydantic import BaseModel, Field

class EmotionType(str, Enum):
    """情绪类型枚举"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    NEUTRAL = "neutral"
    CONFUSED = "confused"

class EmotionResult(BaseModel):
    emotion: EmotionType
    reason: str
    score: float = Field(..., description="情绪得分")