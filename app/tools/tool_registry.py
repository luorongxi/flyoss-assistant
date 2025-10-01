import json
from typing import Dict, Any, Type, Optional, Union
from pydantic import BaseModel
from langchain_core.tools import BaseTool as LangChainBaseTool
from app.utils import setup_logging

# 初始化日志配置
logger = setup_logging()


class ToolRegistry:
    """集中化的工具注册和管理系统"""

    def __init__(self):
        self._tools: Dict[str, LangChainBaseTool] = {}

    def register(self, tool: Union[LangChainBaseTool, Type[LangChainBaseTool]]) -> None:
        """注册工具类或实例到注册表"""
        # 如果是工具类则实例化
        if isinstance(tool, type) and issubclass(tool, LangChainBaseTool):
            tool_instance = tool()
        else:
            tool_instance = tool

        if not getattr(tool_instance, 'name', None):
            raise ValueError("工具必须具有 'name' 属性")

        name = tool_instance.name
        if name in self._tools:
            raise ValueError(f"工具 '{name}' 已注册")

        self._tools[name] = tool_instance
        logger.info(f"注册工具成功: {name} - {tool_instance.description[:50]}...")

    def get(self, tool_name: str) -> Optional[LangChainBaseTool]:
        """按名称获取工具实例"""
        return self._tools.get(tool_name)

    def list_tools(self) -> Dict[str, str]:
        """获取所有工具名称和描述的映射"""
        return {name: tool.description for name, tool in self._tools.items()}

    def get_tool_schemas(self) -> Dict[str, dict]:
        """获取所有工具的JSON Schema定义"""
        schemas = {}
        for name, tool in self._tools.items():
            if hasattr(tool, 'args_schema') and tool.args_schema:
                schemas[name] = tool.args_schema.schema()
        return schemas

    def get_tool_metadata(self) -> Dict[str, dict]:
        """生成符合OpenAI格式的工具元数据集"""
        metadata = {}
        for name, tool in self._tools.items():
            schema = {}
            if hasattr(tool, 'args_schema') and tool.args_schema:
                # 解决中文乱码问题
                schema = json.loads(json.dumps(
                    tool.args_schema.schema(),
                    ensure_ascii=False  # 关键参数，保留中文字符
                ))
            metadata[name] = {
                "description": tool.description,
                "category": getattr(tool, "category", "general"),
                "schema": schema
            }
        return metadata

    def _filter_tools_by_prefix(self, prefix: str) -> Dict[str, dict]:
        """按前缀过滤工具的内部方法"""
        return {
            name: meta
            for name, meta in self.get_tool_metadata().items()
            if name.startswith(prefix)
        }

    def get_dingtalk_tools(self) -> Dict[str, dict]:
        """获取所有钉钉相关工具元数据"""
        return self._filter_tools_by_prefix("dingtalk_")

    def get_general_tools(self) -> Dict[str, dict]:
        """获取非钉钉类通用工具元数据"""
        return {
            name: meta
            for name, meta in self.get_tool_metadata().items()
            if not name.startswith("dingtalk_")
        }


# 全局工具注册表单例
tool_registry = ToolRegistry()