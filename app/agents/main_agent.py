import time
from typing import AsyncGenerator
from app.schemas import UserMessage, AgentResponse
from app.agents import agent_workflow
from app.utils import setup_logging, UserContextManager

# 初始化日志配置
logger = setup_logging()

class MainAgent:
    """主控Agent，协调整个决策流程"""

    def __init__(self):
        pass

    async def process(self, conversation_id: str, sender_id: str, message: str) -> AgentResponse:
        """处理用户消息并返回响应"""
        with UserContextManager(sender_id):
            # 创建输入消息
            input_data = UserMessage(
                text=message,
                sender_id=sender_id,
                conversation_id=conversation_id,
                timestamp=int(time.time() * 1000)
            )

            # 运行Agent工作流
            state = await agent_workflow.run({"input": input_data})

            # 返回最终响应
            return state["response"]

    async def stream_process(self, conversation_id: str, sender_id: str, message: str) -> AsyncGenerator[str, None]:
        """流式处理用户消息"""
        with UserContextManager(sender_id):
            # 创建输入消息
            input_data = UserMessage(
                text=message,
                sender_id=sender_id,
                conversation_id=conversation_id,
                timestamp=int(time.time() * 1000)
            )

            # 运行Agent工作流
            state = await agent_workflow.run({"input": input_data})

            # 流式输出响应
            response_text = state["response"].text
            for chunk in self._split_into_chunks(response_text):
                yield chunk
                time.sleep(0.05)  # 模拟流式延迟

    def _split_into_chunks(self, text: str, chunk_size: int = 20) -> list:
        """将文本分割成适合流式输出的块"""
        words = text.split()
        chunks = []
        current_chunk = []
        char_count = 0

        for word in words:
            if char_count + len(word) + 1 > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                char_count = len(word)
            else:
                current_chunk.append(word)
                char_count += len(word) + 1

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks


# 全局主控Agent实例
main_agent = MainAgent()