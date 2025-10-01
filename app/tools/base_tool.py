from typing import Dict, Any
from langchain_core.tools import BaseTool as LangChainBaseTool
from app.utils import setup_logging
from .tool_registry import tool_registry

# 初始化日志配置
logger = setup_logging()


def run_tool(tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行指定工具的统一入口

    Args:
        tool_name: 工具名称
        input_data: 工具输入参数

    Returns:
        工具执行结果
    """
    try:
        logger.info(f"执行工具: {tool_name}, 参数: {input_data}")

        # 获取工具实例
        tool = tool_registry.get(tool_name)
        if not tool:
            raise ValueError(f"未找到工具: {tool_name}")

        # 执行工具
        result = tool.run(input_data)

        # 统一结果格式
        if "success" not in result:
            result = {"success": True, "result": result}

        logger.info(f"工具执行成功: {tool_name}, 结果: {result}")
        return result

    except Exception as e:
        logger.error(f"工具执行失败: {tool_name}, 错误: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


class BaseTool(LangChainBaseTool):
    """工具基类（可选，用于需要自定义行为的工具）"""
    pass