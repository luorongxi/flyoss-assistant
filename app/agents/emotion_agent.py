from app.schemas import AgentState, EmotionType, EmotionResult
from app.utils import setup_logging
from app.services import llm_service
from app.prompts import get_template
from app.schemas import JsonOutputParser

# 初始化日志配置
logger = setup_logging()

class EmotionAgent:
    """情感识别Agent"""

    def __init__(self):
        self.parser = JsonOutputParser()
        self.template = get_template("emotion")

    async def detect_emotion(self, state: AgentState) -> AgentState:
        """检测用户消息中的情感"""
        try:
            # 准备提示词
            prompt = self.template.render(
                message=state.input.text,
                history_summary=state.history_summary,
            )

            # logger.info(f"情感检测提示词：{prompt}")

            # 调用模型
            response = await llm_service.generate(prompt)
            logger.info(f"情感检测模型输出：{response}")

            # 解析输出
            result = self.parser.parse(response, EmotionResult)

            # 记录结果
            logger.info(f"情感检测完成：{result}")

            if result:
                state.emotion_result = EmotionResult(
                    emotion=result.emotion,
                    reason=result.reason,
                    score=result.score
                )

            return state
        except Exception as e:
            logger.error("情感检测失败", error=str(e))
            state.emotion = EmotionResult(
                emotion=EmotionType.NEUTRAL,
                reason="模型调用失败",
                score=1.00
            )
            return state


# 全局情感Agent实例
emotion_agent = EmotionAgent()

# 添加模块级别的detect_emotion属性，直接指向实例方法
detect_emotion = emotion_agent.detect_emotion