from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from app.schemas import UserMessage, EmotionResult, IntentResult, ToolSelection, SearchResult, KnowledgeResult
from app.schemas.agent_response import AgentResponse


class AgentState(BaseModel):
    """Agent决策状态模型"""
    input: UserMessage
    history: List[Dict] = Field(default_factory=list, description="对话历史")
    history_summary: str = Field("", description="对话历史摘要")
    emotion_result: EmotionResult
    intent_result: IntentResult
    tool_selection: ToolSelection
    route: Optional[str] = Field(None, description="路由结果")
    knowledge_result: List[KnowledgeResult]
    tool_result: Dict[str, Any] = Field(default_factory=dict, description="工具执行结果")
    search_result: List[SearchResult]
    response: AgentResponse

