import os

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    """应用配置类"""

    # 基础配置
    DEBUG: bool = Field(False, env="DEBUG")
    SERVER_HOST: str = Field("0.0.0.0", env="SERVER_HOST")
    SERVER_PORT: int = Field(8000, env="SERVER_PORT")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FILE_NAME: str = Field("flyoss-assistant.log", env="LOG_FILE_NAME")

    # 钉钉配置
    DINGTALK_ENABLED: bool = Field(True, env="DINGTALK_ENABLED")
    DINGTALK_APP_KEY: str = Field("", env="DINGTALK_APP_KEY")
    DINGTALK_APP_SECRET: str = Field("", env="DINGTALK_APP_SECRET")
    DINGTALK_ROBOT_CODE: str = Field("", env="DINGTALK_ROBOT_CODE")

    # 模型服务配置
    LLM_API_BASE: str = Field("https://api.siliconflow.cn/v1", env="LLM_API_BASE")
    LLM_API_KEY: str = Field("", env="LLM_API_KEY")
    CHAT_MODEL: str = Field("DeepSeek-V3-671B", env="CHAT_MODEL")
    TEMPERATURE: float = Field(0.7, env="TEMPERATURE")
    MAX_TOKENS: int = Field(2048, env="MAX_TOKENS")
    EMBEDDING_MODEL: str = Field("BAAI/bge-m3", env="EMBEDDING_MODEL")
    DIMENSION_SIZE: int = Field(1024, env="DIMENSION_SIZE")

    # 存储服务配置
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_PASSWORD: str = Field("", env="REDIS_PASSWORD")
    MEMORY_KEY: str = Field("flyoss_memory", env="MEMORY_KEY")
    MEMORY_MAX_LENGTH: int = Field(-1, env="MEMORY_MAX_LENGTH")
    MEMORY_QUERY_LENGTH: int = Field(5, env="MEMORY_QUERY_LENGTH")

    QDRANT_HOST: str = Field("localhost", env="QDRANT_HOST")
    QDRANT_PORT: int = Field(6333, env="QDRANT_PORT")
    QDRANT_API_KEY: str = Field("", env="QDRANT_API_KEY")
    KNOWLEDGE_COLLECTION: str = Field("flyoss_knowledge", env="KNOWLEDGE_COLLECTION")

    # URL 加载配置
    URL_MAX_RETRIES: int = Field(3, env="URL_MAX_RETRIES")
    URL_RETRY_DELAY: float = Field(2.0, env="URL_RETRY_DELAY")
    URL_CHUNK_SIZE: int = Field(1000, env="URL_CHUNK_SIZE")
    URL_CHUNK_OVERLAP: int = Field(200, env="URL_CHUNK_OVERLAP")
    URL_MAX_CONCURRENT: int = Field(10, env="URL_MAX_CONCURRENT")
    URL_TIMEOUT: float = Field(15.0, env="URL_TIMEOUT")

    # 搜索引擎配置
    SERPAPI_KEY: str = Field("", env="SERPAPI_KEY")
    SEARCH_REGION: str = Field("cn", env="SEARCH_REGION")
    MAX_RESULTS: int = Field(5, env="MAX_RESULTS")

    # 监控配置
    LANGCHAIN_ENDPOINT: str = Field("https://api.smith.langchain.com", env="LANGSMITH_ENDPOINT")
    LANGCHAIN_API_KEY: str = Field("", env="LANGSMITH_API_KEY")
    LANGCHAIN_PROJECT: str = Field("flyoss-assistant", env="LANGSMITH_PROJECT")
    LANGCHAIN_TRACING_V2: bool = Field(False, env="LANGSMITH_TRACING")

    # 代理配置
    HTTP_PROXY: str = Field("", env="HTTP_PROXY")
    HTTPS_PROXY: str = Field("", env="HTTPS_PROXY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"无效的日志级别: {v}，有效值: {', '.join(valid_levels)}")
        return v.upper()

    def setup_langchain_environment(self):
        """根据当前配置设置 LangChain 环境变量以启用 LangSmith 跟踪"""
        if self.LANGCHAIN_TRACING_V2 and self.LANGCHAIN_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = str(self.LANGCHAIN_TRACING_V2).lower()
            os.environ["LANGCHAIN_API_KEY"] = self.LANGCHAIN_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = self.LANGCHAIN_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = self.LANGCHAIN_ENDPOINT
            print(f"LangChain 跟踪已启用：项目 '{self.LANGCHAIN_PROJECT}'")
        else:
            print("LangChain 跟踪未启用（缺少 LANGCHAIN_TRACING_V2 或 LANGCHAIN_API_KEY）")


# 加载环境变量
load_dotenv()

# 全局配置实例
config = Config()

# 应用 LangChain 环境变量
config.setup_langchain_environment()

def get_config():
    """获取配置实例"""
    return config