from pydantic import BaseModel, Field
from typing import Dict, Any

class ToolSelection(BaseModel):
    """工具选择输出模型"""
    tool_name: str = Field(..., description="选择的工具名称")
    reason: str = Field(..., description="选择该工具的原因")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")

class ToolCallRequest(BaseModel):
    """工具调用请求模型"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(..., description="工具参数")
