import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template

# 获取提示词目录
PROMPTS_DIR = Path(os.path.dirname(__file__))

# 创建Jinja2环境
env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True
)

# 加载所有提示词模板
templates = {
    "history_summary": env.get_template("history_summary.jinja2"),
    "emotion": env.get_template("emotion.jinja2"),
    "intent": env.get_template("intent.jinja2"),
    "tool_selection": env.get_template("tool_selection.jinja2"),
    "response": env.get_template("response.jinja2")
}

def get_template(name: str) -> Template:
    """获取指定名称的模板"""
    if name not in templates:
        raise ValueError(f"未知的模板名称: {name}")
    return templates[name]

__all__ = ["get_template", "templates"]