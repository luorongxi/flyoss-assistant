from langchain_community.utilities import SerpAPIWrapper
from typing import List
from app.schemas import SearchResult
from app.utils import config, setup_logging

# 初始化日志配置
logger = setup_logging()


class SearchService:
    """搜索服务 - 使用 SerpAPIWrapper"""

    def __init__(self):
        self.api_key = config.SERPAPI_KEY
        self.region = config.SEARCH_REGION or "cn"
        self.serpapi_wrapper = None
        self._initialize_wrapper()

    def _initialize_wrapper(self):
        """初始化 SerpAPIWrapper"""
        try:
            if not self.api_key:
                logger.error("SerpAPI 密钥未配置")
                return

            # 创建 SerpAPIWrapper 实例
            self.serpapi_wrapper = SerpAPIWrapper(
                serpapi_api_key=self.api_key,
                params={
                    "engine": "google",
                    "google_domain": "google.com",
                    "gl": self.region,
                    "hl": "zh-cn" if self.region == "cn" else "en"
                }
            )
            logger.info("SerpAPIWrapper 初始化成功")
        except Exception as e:
            logger.error(f"SerpAPIWrapper 初始化失败: {str(e)}", exc_info=True)

    def web_search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """执行网络搜索"""
        try:
            if not self.serpapi_wrapper:
                logger.error("SerpAPIWrapper 未初始化，无法执行搜索")
                return []

            # 执行搜索
            logger.info(f"执行搜索: {query}")
            # 修改调用方式
            results = self.serpapi_wrapper.results(query)  # 返回原始JSON结构

            # 提取结构化结果
            search_results = []
            for item in results["organic_results"]:  # 关键：解析organic_results
                search_results.append(SearchResult(
                    title=item["title"],
                    link=item["link"],
                    snippet=item.get("snippet", "")
                ))

            if search_results:
               logger.info(f"网络搜索结构化结果: {search_results[0].snippet[:50]}...")

            # 解析结果
            return search_results
        except Exception as e:
            logger.error(f"搜索处理失败: {str(e)}", exc_info=True)
            return []

# 全局搜索服务实例
search_service = SearchService()