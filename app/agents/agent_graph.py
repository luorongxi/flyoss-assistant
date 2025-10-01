import time
from typing import Any, Coroutine

from langgraph.graph import StateGraph, END
from app.schemas import AgentState, AgentResponse, EmotionType, IntentResult, IntentType, \
    EmotionResult, ToolSelection
from app.agents import emotion_agent, intent_agent, tool_agent, rag_agent, search_agent, response_agent
from app.utils import setup_logging
from app.core.memory import RedisMemory

# 初始化日志配置
logger = setup_logging()

class AgentWorkflow:
    """Agent决策流程管理器"""
    def __init__(self):
        self.workflow = StateGraph(AgentState)
        self._build_workflow()
        self.app = self._compile_workflow()
        self.memory = RedisMemory()

    def _build_workflow(self):
        """构建Agent决策流程"""
        self.workflow.add_node("retrieve_memory", self.retrieve_memory_node)
        self.workflow.add_node("detect_emotion", emotion_agent.detect_emotion)
        self.workflow.add_node("detect_intent", intent_agent.detect_intent)
        self.workflow.add_node("select_tool", tool_agent.select_tool)
        self.workflow.add_node("execute_tool", tool_agent.execute_tool)
        self.workflow.add_node("retrieve_knowledge", rag_agent.retrieve_knowledge)
        self.workflow.add_node("knowledge_decision", self.knowledge_decision_node)
        self.workflow.add_node("web_search", search_agent.web_search)
        self.workflow.add_node("generate_response", response_agent.generate_response)
        self.workflow.add_node("save_memory", self.save_memory_node)

        # 设置入口点
        self.workflow.set_entry_point("retrieve_memory")

        # 添加边
        self.workflow.add_edge("retrieve_memory", "detect_emotion")
        self.workflow.add_edge("detect_emotion", "detect_intent")

        # 意图路由
        self.workflow.add_conditional_edges(
            "detect_intent",
            self.route_by_intent,
            {
                IntentType.TOOL: "select_tool",
                IntentType.QUESTION: "retrieve_knowledge",
                IntentType.COMMAND: "web_search",
                IntentType.CHAT: "generate_response"
            }
        )

        # 工具执行路径
        self.workflow.add_edge("select_tool", "execute_tool")
        self.workflow.add_edge("execute_tool", "generate_response")

        # 知识库处理路径
        self.workflow.add_edge("retrieve_knowledge", "knowledge_decision")
        self.workflow.add_conditional_edges(
            "knowledge_decision",
            self.route_after_knowledge,
            {
                "has_knowledge": "generate_response",
                "need_search": "web_search"
            }
        )

        # 搜索路径
        self.workflow.add_edge("web_search", "generate_response")

        # 响应和记忆保存
        self.workflow.add_edge("generate_response", "save_memory")
        self.workflow.add_edge("save_memory", END)

    def _compile_workflow(self):
        """编译工作流"""
        return self.workflow.compile()

    def knowledge_decision_node(self, state: AgentState) -> dict:
        """知识决策节点 - 传递状态"""
        # 这个节点不做任何修改，只是传递状态
        # 实际的决策在条件边函数中
        return state.model_dump()

    def route_after_knowledge(self, state: AgentState) -> str:
        """根据知识库结果决定下一步"""
        knowledge_results = state.knowledge_result

        if knowledge_results and any(res.content for res in knowledge_results):
            return "has_knowledge"
        return "need_search"

    def route_by_intent(self, state: AgentState) -> str:
        """根据意图路由决策路径"""
        intent = state.intent_result.intent
        if not intent:
            logger.error("意图识别失败，使用默认路径: chat")
            return IntentType.CHAT
        logger.info(f"意图路由决策路径：{intent.value}")
        return intent

    async def retrieve_memory_node(self, state: AgentState) -> dict:
        """从记忆系统检索对话历史"""
        history_summary = await self.memory.get_history_summary(state)
        return history_summary

    def save_memory_node(self, state: AgentState) -> dict:
        """保存对话到记忆系统"""
        user_id = state.input.sender_id
        user_message = state.input.text
        assistant_response = state.response

        # 保存用户消息
        self.memory.add_record(user_id, {
            "role": "user",
            "content": user_message,
            "timestamp": state.input.timestamp
        })

        # 保存助手响应
        self.memory.add_record(user_id, {
            "role": "assistant",
            "content": str(assistant_response),
            "timestamp": int(time.time() * 1000)
        })

        logger.info(f"用户：{user_id} 的对话已保存到记忆系统")
        return {}

    async def run(self, input_data: dict) -> AgentState:
        """运行Agent决策流程"""
        try:
            # 初始化Agent状态
            initial_state = AgentState(
                input=input_data["input"],
                history=[],
                history_summary="",
                emotion_result=EmotionResult(emotion=EmotionType.NEUTRAL, reason="", score=1.00),
                intent_result=IntentResult(intent=IntentType.CHAT, reason="", requires_tool=False),
                tool_selection=ToolSelection(tool_name="", parameters={}, reason=""),
                route=None,
                knowledge_result=[],
                tool_result={},
                search_result=[],
                response=AgentResponse(text="", emotion=EmotionType.NEUTRAL, references=[], suggestions=[], tool_selection=ToolSelection(tool_name="", parameters={}, reason=""), tool_result={}, is_final=True)
            )

            # 执行工作流
            result = await self.app.ainvoke(initial_state)
            return result
        except Exception as e:
            logger.error(f"Agent工作流执行失败：{str(e)}", exc_info=True)
            raise RuntimeError(f"Agent决策失败: {str(e)}")


# 全局Agent工作流实例
agent_workflow = AgentWorkflow()