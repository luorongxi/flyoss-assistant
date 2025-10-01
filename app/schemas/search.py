from pydantic import BaseModel

class SearchResult(BaseModel):
    """网络搜索结果模型"""
    title: str
    link: str
    snippet: str