from app.schemas import AgentState, IntentType, IntentResult, JsonOutputParser
from app.utils import setup_logging
from app.services import llm_service
from app.prompts import get_template
from app.tools import tool_registry

# 初始化日志配置
logger = setup_logging()

class IntentAgent:
    """意图识别Agent"""

    def __init__(self):
        self.parser = JsonOutputParser()
        self.template = get_template("intent")
        self.tools = tool_registry.list_tools()

    async def detect_intent(self, state: AgentState) -> AgentState:
        """识别用户消息的意图"""
        try:
            # 准备提示词
            prompt = self.template.render(
                message=state.input.text,
                emotion_result=state.emotion_result,
                history_summary=state.history_summary,
                tools=self.tools
            )

            # logger.info(f"意图识别提示词：{prompt}")

            # 调用模型
            response = await llm_service.generate(prompt)

            # 解析输出
            result = self.parser.parse(response, IntentResult)

            # 记录结果
            logger.info(f"意图识别完成：{result}")

            if result:
                state.intent_result = IntentResult(
                    intent=result.intent,
                    reason=result.reason,
                    requires_tool=result.requires_tool,
                    tool_suggestion=result.tool_suggestion
                )

            return state
        except Exception as e:
            logger.error("意图识别失败", error=str(e))
            state.intent_result = IntentResult(
                intent=IntentType.CHAT,
                reason="意图识别失败",
                requires_tool=False,
                tool_suggestion=""
            )
            return state


# 全局意图Agent实例
intent_agent = IntentAgent()

# 添加模块级别的intent_agent属性，直接指向实例方法
detect_intent = intent_agent.detect_intent