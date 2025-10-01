from app.schemas import AgentState, IntentType
from app.utils import setup_logging
from app.services import search_service

# 初始化日志配置
logger = setup_logging()

class SearchAgent:
    """网络搜索Agent"""

    def __init__(self):
        pass

    async def web_search(self, state: AgentState):
        """执行网络搜索"""
        try:
            query = state.input.text
            intent = state.intent_result.intent

            # 增强查询（如果需要）
            enhanced_query = self._enhance_query_with_intent(query, intent)

            # 执行搜索
            state.search_result = search_service.web_search(
                query=enhanced_query,
                num_results=5
            )

            if state.search_result:
                # 记录转换后的结果
                logger.info(f"网络搜索结果: {state.search_result[0].snippet[:50]}...")
            return state
        except Exception as e:
            logger.error(f"网络搜索失败：{str(e)}", exc_info=True)
            return {"search_result": []}

    def _enhance_query_with_intent(self, query: str, intent: str) -> str:
        """根据意图增强查询"""
        if intent == IntentType.COMMAND:
            return f"{query} 步骤指南"
        elif intent == IntentType.QUESTION:
            return f"{query} 最新信息"
        return query


# 全局搜索Agent实例
search_agent = SearchAgent()

# 添加模块级别的web_search属性，直接指向实例方法
web_search = search_agent.web_search