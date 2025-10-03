from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from typing import List
from app.schemas import SearchResult
from app.utils import config, setup_logging

# 初始化日志配置
logger = setup_logging()


class SearchService:
    """搜索服务 - 使用 TavilySearchAPIWrapper"""

    def __init__(self):
        self.api_key = config.TAVILY_API_KEY
        self.search_depth = config.SEARCH_DEPTH or "basic"  # "basic" 或 "advanced"
        self.max_results = config.MAX_RESULTS or 5
        self.tavily_wrapper = None
        self._initialize_wrapper()

    def _initialize_wrapper(self):
        """初始化 TavilySearchAPIWrapper"""
        try:
            if not self.api_key:
                logger.error("Tavily API 密钥未配置")
                return

            # 创建 TavilySearchAPIWrapper 实例
            self.tavily_wrapper = TavilySearchAPIWrapper(
                tavily_api_key=self.api_key,
            )
            logger.info("TavilySearchAPIWrapper 初始化成功")
        except Exception as e:
            logger.error(f"TavilySearchAPIWrapper 初始化失败: {str(e)}", exc_info=True)

    def web_search(self, query: str) -> List[SearchResult]:
        """执行网络搜索"""
        try:
            if not self.tavily_wrapper:
                logger.error("TavilySearchAPIWrapper 未初始化，无法执行搜索")
                return []

            # 执行搜索
            logger.info(f"执行搜索: {query} | 数量: {self.max_results} | 深度: {self.search_depth}")

            # 获取搜索结果
            results = self.tavily_wrapper.results(
                query=query,
                max_results=self.max_results,
                search_depth=self.search_depth
            )

            # 提取结构化结果
            search_results = []
            for item in results:
                search_results.append(SearchResult(
                    title=item.get("title", ""),
                    link=item.get("url", ""),
                    snippet=item.get("content", "")  # Tavily 使用 "content" 作为摘要
                ))

            # 日志记录第一个结果摘要
            if search_results:
                logger.info(f"网络搜索结构化结果: {search_results[0].snippet[:50]}...")

            return search_results
        except Exception as e:
            logger.error(f"搜索处理失败: {str(e)}", exc_info=True)
            return []

# 全局搜索服务实例
search_service = SearchService()