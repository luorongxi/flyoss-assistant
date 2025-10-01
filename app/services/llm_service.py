import os
import httpx
from openai import AsyncOpenAI
from typing import List, AsyncGenerator
from app.utils import config, setup_logging

# 初始化日志配置
logger = setup_logging()

class LLMService:
    """大语言模型服务"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_API_BASE,
            http_client=httpx.AsyncClient(
                proxies={
                    "http://": config.HTTP_PROXY,
                    "https://": config.HTTPS_PROXY
                } if config.HTTP_PROXY or config.HTTPS_PROXY else None
            )
        )
        self.model = config.CHAT_MODEL
        self.embedding_model = config.EMBEDDING_MODEL

    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本响应"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.TEMPERATURE,
                max_tokens=config.MAX_TOKENS,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("模型生成失败", error=str(e))
            raise RuntimeError(f"模型调用失败: {str(e)}")

    async def stream_generate(self, prompt: str) -> AsyncGenerator[str, None]:
        """流式生成文本响应"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.TEMPERATURE,
                max_tokens=config.MAX_TOKENS,
                stream=True
            )

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error("流式生成失败", error=str(e))
            yield "抱歉，生成响应时出现问题。"

    async def get_embeddings(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("获取嵌入失败", error=str(e))
            raise RuntimeError(f"嵌入生成失败: {str(e)}")


# 全局LLM服务实例
llm_service = LLMService()