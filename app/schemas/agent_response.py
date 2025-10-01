from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.schemas import EmotionType, ToolSelection

class AgentResponse(BaseModel):
    """Agent响应输出模型"""
    text: str = Field(..., description="响应文本")
    emotion: EmotionType = Field(EmotionType.NEUTRAL, description="响应情绪")
    suggestions: List[str] = Field(default_factory=list, description="后续建议")
    references: List[Dict] = Field(default_factory=list, description="参考来源")
    tool_selection: ToolSelection
    tool_result: Dict[str, Any] = Field(default_factory=dict, description="工具执行结果")
    is_final: bool = Field(True, description="是否为最终响应")