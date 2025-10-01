# app/core/memory.py
import redis
import json
from typing import List, Dict, Any
from app.services import llm_service
from app.schemas import AgentState
from app.prompts import get_template
from app.utils import config, setup_logging

# 初始化日志配置
logger = setup_logging()


class RedisMemory:
    """基于Redis的记忆系统"""

    def __init__(self):
        self.client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD or None,
            decode_responses=True
        )
        # 验证配置值
        if config.MEMORY_MAX_LENGTH < -1:
            raise ValueError("MEMORY_MAX_LENGTH 不能小于 -1")
        if config.MEMORY_QUERY_LENGTH <= 0:
            raise ValueError("MEMORY_QUERY_LENGTH 必须大于 0")

        # 新增验证：配置值必须为大于0的偶数（MEMORY_MAX_LENGTH 可以为-1）
        if config.MEMORY_MAX_LENGTH != -1:
            if config.MEMORY_MAX_LENGTH <= 0:
                raise ValueError("MEMORY_MAX_LENGTH 必须为-1或大于0的偶数")
            if config.MEMORY_MAX_LENGTH % 2 != 0:
                raise ValueError("MEMORY_MAX_LENGTH 必须是偶数（除-1外）")

        if config.MEMORY_QUERY_LENGTH <= 0:
            raise ValueError("MEMORY_QUERY_LENGTH 必须大于0")
        if config.MEMORY_QUERY_LENGTH % 2 != 0:
            raise ValueError("MEMORY_QUERY_LENGTH 必须是偶数")
        self.memory_key = config.MEMORY_KEY
        self.max_length = config.MEMORY_MAX_LENGTH
        self.query_length = config.MEMORY_QUERY_LENGTH
        self.template = get_template("history_summary")

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的对话历史，使用MEMORY_QUERY_LENGTH限制查询条数"""
        key = f"{self.memory_key}:{user_id}"
        try:
            # 获取列表总长度
            total_len = self.client.llen(key)
            if total_len == 0:
                return []

            # 获取最新的历史记录（从头开始取 query_length 条），因为 lpush + lrange(0, n) 已经是最新的记录
            history_json = self.client.lrange(key, 0, self.query_length - 1)

            # 反转列表使记录按时间顺序排列（从旧到新）
            return [json.loads(item) for item in reversed(history_json)]

        except redis.RedisError as e:
            logger.error(f"获取记忆失败：{str(e)}", exc_info=True)
            return []
        except json.JSONDecodeError as e:
            logger.error(f"记忆数据解析失败：{str(e)}", exc_info=True)
            return []

    async def get_history_summary(self, state: AgentState) -> dict:
        """获取用户的对话历史摘要"""
        user_id = state.input.sender_id
        history = self.get_history(user_id)
        logger.info(f"用户：{user_id}，检索到：{len(history)} 条历史记录")

        # 新增摘要生成功能
        history_summary = ""
        if history:
            try:
                # 构建摘要生成提示
                conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                # 准备提示词
                prompt = self.template.render(
                    message=state.input.text,
                    history=conversation,
                )

                # 异步调用LLM生成摘要
                history_summary = await llm_service.generate(prompt)
                logger.info(f"生成对话摘要成功：{history_summary}")

            except Exception as e:
                logger.error(f"对话摘要生成失败: {str(e)}")
                history_summary = "（摘要生成失败）"
        else:
            history_summary = "（无历史对话）"

        return {
            "history": history,
            "history_summary": history_summary
        }

    def add_record(self, user_id: str, record: Dict[str, Any]):
        """添加新的对话记录"""
        key = f"{self.memory_key}:{user_id}"
        try:
            # 添加新记录
            self.client.lpush(key, json.dumps(record, ensure_ascii=False))

            # 当max_length不为-1时进行修剪
            if self.max_length != -1:
                # 修剪列表，保留最近的记录
                self.client.ltrim(key, 0, self.max_length - 1)
        except redis.RedisError as e:
            logger.error(f"保存记忆失败: {str(e)}", user_id=user_id)
        except TypeError as e:
            logger.error(f"记忆数据序列化失败: {str(e)}", user_id=user_id)

    def clear_memory(self, user_id: str):
        """清除用户的所有记忆"""
        key = f"{self.memory_key}:{user_id}"
        try:
            self.client.delete(key)
            logger.info(f"用户记忆已清除: {user_id}")
        except redis.RedisError as e:
            logger.error(f"清除记忆失败: {str(e)}", user_id=user_id)


# 全局记忆系统实例
memory_system = RedisMemory()