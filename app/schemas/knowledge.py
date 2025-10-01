from pydantic import BaseModel, Field
from typing import Dict, Any

class KnowledgeQuery(BaseModel):
    """知识库查询模型"""
    query: str = Field(..., description="查询内容")
    top_k: int = Field(3, description="返回结果数量")
    score_threshold: float = Field(0.7, description="相似度阈值")

class KnowledgeResult(BaseModel):
    """知识库检索结果模型"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float