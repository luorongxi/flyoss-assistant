from pydantic import BaseModel, Field, validator
from app.tools.base_tool import BaseTool
import requests
from app.utils import config, setup_logging
from typing import Dict, Any, Type

# 初始化日志配置
logger = setup_logging()


class WebSearchInput(BaseModel):
    """搜索工具输入模型"""
    query: str = Field(..., description="搜索查询内容")
    num_results: int = Field(5, description="返回结果数量", ge=1, le=10)
    region: str = Field("cn", description="搜索区域，如 'cn' 或 'us'")


class WebSearchTool(BaseTool):
    """当需要获取最新信息或未知领域知识时使用此工具进行网络搜索

    功能说明:
    - 使用搜索引擎获取实时信息
    - 返回包含标题、链接和摘要的搜索结果
    - 支持自定义结果数量和搜索区域
    """
    name: str = "web_search"
    description: str = "执行网络搜索获取最新信息"
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str, num_results: int = 5, region: str = "cn") -> Dict[str, Any]:
        logger.info(f"执行搜索: {query} | 数量: {num_results} | 区域: {region}")

        headers = {
            "Authorization": f"Bearer {config.SEARCHAPI_KEY}",
            "Content-Type": "application/json"
        }

        params = {
            "q": query,
            "num": num_results,
            "region": region,
            "engine": "google"  # 可配置为百度、必应等
        }

        try:
            response = requests.get(
                f"{config.SEARCHAPI_BASE}/search",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            results = response.json().get("organic_results", [])
            logger.info(f"搜索成功: 找到{len(results)}条结果")

            # 提取关键信息
            search_results = []
            for result in results[:num_results]:
                search_results.append({
                    "title": result.get("title"),
                    "link": result.get("link"),
                    "snippet": result.get("snippet")
                })

            return {
                "success": True,
                "query": query,
                "num_results": len(search_results),
                "results": search_results
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"搜索API请求失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"搜索失败: {str(e)}"
            }