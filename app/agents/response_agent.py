from app.schemas import AgentState, AgentResponse, EmotionType, IntentType
from app.utils import setup_logging
from app.services import llm_service
from app.prompts import get_template

# 初始化日志配置
logger = setup_logging()

class ResponseAgent:
    """响应生成Agent"""

    def __init__(self):
        self.template = get_template("response")

    async def generate_response(self, state: AgentState) -> dict:
        """生成最终响应"""
        try:
            # 准备提示词
            prompt = self.template.render(
                message=state.input.text,
                emotion_result=state.emotion_result,
                history_summary=state.history_summary,
                tool_result=state.tool_result,
                knowledge_result=state.knowledge_result,
                search_result=state.search_result
            )

            # logger.info(f"生成响应提示词：{prompt}")

            # 生成响应文本
            response_text = await llm_service.generate(prompt)

            # 记录结果
            logger.info(f"响应生成完成，长度：{len(response_text)}，内容：{response_text}")

            # 创建响应对象
            response = AgentResponse(
                text=response_text,
                emotion=self._determine_response_emotion(state),
                suggestions=self._generate_suggestions(state),
                references=self._extract_references(state),
                tool_selection=state.tool_selection,
                tool_result=state.tool_result,
                is_final=True
            )

            return {"response": response}
        except Exception as e:
            logger.error("响应生成失败", error=str(e))
            return {
                "response": AgentResponse(
                    text="抱歉，我遇到了一个问题，暂时无法回答。",
                    emotion=EmotionType.NEUTRAL,
                    is_final=True
                )
            }

    def _determine_response_emotion(self, state: AgentState) -> EmotionType:
        """确定响应情绪"""
        user_emotion = state.emotion_result.emotion

        # 根据用户情绪调整响应情绪
        if user_emotion == EmotionType.SAD:
            return EmotionType.HAPPY  # 尝试提升用户情绪
        elif user_emotion == EmotionType.ANGRY:
            return EmotionType.NEUTRAL  # 保持中立冷静
        return EmotionType.NEUTRAL

    def _generate_suggestions(self, state: AgentState) -> list:
        """生成后续建议"""
        suggestions = []

        # 如果有工具结果，建议进一步操作
        if state.tool_result:
            suggestions.append("需要我执行其他操作吗？")

        # 如果是问题，建议深入探讨
        if state.intent_result.intent == IntentType.QUESTION:
            suggestions.append("需要更详细的解释吗？")

        return suggestions

    def _extract_references(self, state: AgentState) -> list:
        """提取参考来源"""
        references = []

        # 添加知识库来源
        if state.knowledge_result:
            for item in state.knowledge_result:
                if item.metadata.get("source"):
                    references.append({
                        "type": "knowledge",
                        "title": item.metadata.get("title", "知识库条目"),
                        "source": item.metadata["source"]
                    })

        # 添加搜索来源
        if state.search_result:
            for item in state.search_result:
                references.append({
                    "type": "web",
                    "title": item.title,
                    "source": item.link
                })

        return references


# 全局响应Agent实例
response_agent = ResponseAgent()

# 添加模块级别的generate_response属性，直接指向实例方法
generate_response = response_agent.generate_response