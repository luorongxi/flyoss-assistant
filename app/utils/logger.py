# app/utils/log_config.py
import os
import logging
import sys

from app.utils import get_config

def setup_logging():
    """设置日志配置"""
    logger = logging.getLogger("flyoss-assistant")

    # 移除所有现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 在函数内部获取配置
    config = get_config()  # 使用 get_config() 获取配置实例

    logging.getLogger().setLevel(logging.DEBUG if config.LOG_LEVEL else logging.INFO)

    # 配置其他日志器
    for log_name in ["uvicorn", "uvicorn.error", "fastapi", "dingtalk_stream"]:
        logging.getLogger(log_name).setLevel(
            logging.DEBUG if config.LOG_LEVEL else logging.WARNING
        )

    # 创建控制台处理器
    console_handler = logging.StreamHandler()

    # 确保日志目录存在
    # 获取项目根目录的绝对路径（根据当前文件位置计算）
    if getattr(sys, 'frozen', False):  # 如果是打包后的可执行文件
        project_root = os.path.dirname(sys.executable)
    else:
        # 假设这个文件在项目的 src/utils 目录下（根据实际结构调整）
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

    # 在项目根目录下创建 logs 文件夹
    log_dir = os.path.join(project_root, "logs")
    log_file = os.path.join(log_dir, config.LOG_FILE_NAME)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)  # 如果目录不存在，则创建它

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")  # 日志输出到文件

    # 创建格式化器并将其添加到处理器
    formatter = logging.Formatter(
        '%(asctime)s - %(thread)d- [%(name)s - %(levelname)s - %(filename)s - %(funcName)s:%(lineno)d] - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 将处理器添加到logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# 初始化日志配置
setup_logging()

