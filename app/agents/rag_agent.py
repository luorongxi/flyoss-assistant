from app.schemas import AgentState
from app.utils import setup_logging
from app.core import knowledge_base

# 初始化日志配置
logger = setup_logging()

class RAGAgent:
    """知识库检索Agent"""

    def __init__(self):
        pass

    async def retrieve_knowledge(self, state: AgentState):
        """从知识库检索相关信息"""
        try:
            query = state.input.text
            emotion = state.emotion_result.emotion

            # 情感增强查询（如果需要）
            enhanced_query = self._enhance_query_with_emotion(query, emotion)

            # 检索知识
            state.knowledge_result = await knowledge_base.retrieve(
                query=enhanced_query,
                top_k=3,
                score_threshold=0.7
            )

            # 记录结果
            if state.knowledge_result:
                logger.info(f"知识库检索完成：{state.knowledge_result[0].content[:50]}...")

            return state
        except Exception as e:
            logger.error(f"知识检索失败：{str(e)}", exc_info=True)
            return {"knowledge_result": []}

    def _enhance_query_with_emotion(self, query: str, emotion: str) -> str:
        """根据情感增强查询"""
        if emotion == "sad":
            return f"{query} [寻求安慰]"
        elif emotion == "angry":
            return f"{query} [冷静解决方案]"
        elif emotion == "confused":
            return f"{query} [详细解释]"
        return query


# 全局RAG Agent实例
rag_agent = RAGAgent()

# 添加模块级别的retrieve_knowledge属性，直接指向实例方法
retrieve_knowledge = rag_agent.retrieve_knowledge
