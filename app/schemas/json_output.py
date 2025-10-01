import json
import re

from pydantic import BaseModel
from typing import Type
from app.utils import setup_logging

# 初始化日志配置
logger = setup_logging()

class JsonOutputParser:
    """JSON输出解析器"""

    @staticmethod
    def parse(output: str, model: Type[BaseModel]) -> BaseModel:
        """
        解析模型输出为指定的Pydantic模型
        自动处理Markdown代码块标记

        参数:
            output: 模型输出的字符串
            model: 目标Pydantic模型类

        返回:
            模型实例

        异常:
            ValueError: 如果输出无法解析为有效JSON
        """
        try:
            # 清理输出中的非JSON内容
            cleaned_output = JsonOutputParser._clean_json_output(output)

            # 解析JSON
            data = json.loads(cleaned_output)
            return model(**data)
        except (json.JSONDecodeError, TypeError) as e:
            # 记录原始输出以便调试
            logger.error(f"JSON解析失败: {str(e)}\n原始输出: {output}", exc_info=True)
            raise ValueError(f"无效的JSON输出: {str(e)}")
        except Exception as e:
            logger.error(f"解析过程中发生意外错误: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _clean_json_output(output: str) -> str:
        """
        清理模型输出中的Markdown代码块标记

        支持格式:
        ```json
        { ... }
        ```

        或
        ```
        { ... }
        ```

        参数:
            output: 原始输出字符串

        返回:
            清理后的JSON字符串
        """
        # 如果输出为空，直接返回
        if not output:
            return output

        # 尝试匹配带语言标记的代码块
        json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', output)
        if json_block_match:
            return json_block_match.group(1).strip()

        # 尝试匹配普通代码块
        generic_block_match = re.search(r'```\s*([\s\S]*?)\s*```', output)
        if generic_block_match:
            return generic_block_match.group(1).strip()

        # 尝试匹配只有大括号的内容（有时模型会忘记代码块标记）
        brace_match = re.search(r'\{[\s\S]*\}', output)
        if brace_match:
            return brace_match.group(0).strip()

        # 没有匹配到任何模式，返回原始输出
        return output.strip()

    @staticmethod
    def get_format_instructions(model: Type[BaseModel]) -> str:
        """获取模型的格式化指令"""
        schema = model.model_json_schema()
        return (
            "请严格按以下JSON格式输出，不要包含任何其他内容：\n"
            f"```json\n{schema}\n```"
        )