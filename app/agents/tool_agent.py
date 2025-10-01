import json
from datetime import datetime
from app.schemas import AgentState, JsonOutputParser, ToolSelection
from app.tools import tool_registry
from app.tools.base_tool import run_tool
from app.utils import setup_logging
from app.services import llm_service
from app.prompts import get_template

logger = setup_logging()


class ToolAgent:
    """工具调用Agent - 适配重构后的工具系统"""

    def __init__(self):
        self.parser = JsonOutputParser()
        self.selection_template = get_template("tool_selection")

        # 获取工具元数据
        self.dingtalk_tools = tool_registry.get_dingtalk_tools()
        self.general_tools = tool_registry.get_general_tools()

        logger.info(f"已加载工具: {len(tool_registry.list_tools())}个 (钉钉工具: {len(self.dingtalk_tools)}个)")

    async def select_tool(self, state: AgentState) -> AgentState:
        """选择要调用的工具"""
        try:
            # 准备提示词
            prompt = self.selection_template.render(
                message=state.input.text,
                emotion_result=state.emotion_result,
                intent_result=state.intent_result,
                history=state.history,
                dingtalk_tools=self.dingtalk_tools,
                general_tools=self.general_tools,
                current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            # logger.debug(f"工具选择提示词: {prompt}")

            # 调用模型
            response = await llm_service.generate(prompt)
            logger.debug(f"模型原始响应: {response}")

            # 解析输出
            result = self.parser.parse(response, ToolSelection)
            logger.info(f"工具选择完成: {result}")

            state.tool_selection = ToolSelection(
                tool_name=result.tool_name,
                parameters=result.parameters,
                reason=result.reason
            )

            return state
        except Exception as e:
            logger.error(f"工具选择失败: {str(e)}", exc_info=True)
            state.tool_selection = ToolSelection(
                tool_name="",
                parameters={},
                reason=f"选择过程中出错: {str(e)}"
            )
            return state

    async def execute_tool(self, state: AgentState) -> dict:
        """执行选定的工具"""
        if not state.tool_selection or not state.tool_selection.tool_name:
            logger.warning("未选择工具，跳过执行")
            return {"tool_result": None}

        tool_name = state.tool_selection.tool_name
        params = state.tool_selection.parameters

        try:
            logger.info(f"执行工具: {tool_name}, 参数: {json.dumps(params, ensure_ascii=False)}")

            # 使用统一的工具执行方法
            result = run_tool(tool_name, params)

            return {"tool_result": result}
        except Exception as e:
            logger.exception(f"工具执行异常: {tool_name}", exc_info=True)
            return {
                "tool_result": {
                    "success": False,
                    "error": str(e)
                }
            }


# 全局工具Agent实例
tool_agent = ToolAgent()

# 模块级函数别名
select_tool = tool_agent.select_tool
execute_tool = tool_agent.execute_tool