from contextvars import ContextVar
from typing import Optional
from app.utils import setup_logging

# 初始化日志配置
logger = setup_logging()

# 使用ContextVar实现线程安全的用户上下文
current_user: ContextVar[Optional[str]] = ContextVar("current_user", default=None)


class UserContext:
    """用户上下文管理类（不再依赖Flask g对象）"""

    @staticmethod
    def set_user(user_id: str):
        """设置当前用户ID"""
        current_user.set(user_id)
        logger.info(f"设置用户上下文: {user_id}")

    @staticmethod
    def get_user() -> Optional[str]:
        """获取当前用户ID"""
        return current_user.get()

    @staticmethod
    def clear_user():
        """清除当前用户上下文"""
        current_user.set(None)


# 上下文管理器，用于确保用户上下文被正确设置和清理
class UserContextManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.token = None  # 用于保存ContextVar的状态

    def __enter__(self):
        """进入上下文时设置用户ID"""
        self.token = current_user.set(self.user_id)
        logger.info(f"设置用户上下文: {self.user_id}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """退出上下文时恢复之前的状态"""
        current_user.reset(self.token)
        logger.info(f"清除用户上下文: {self.user_id}")


def with_user(user_id: str):
    """装饰器，为函数设置用户上下文"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            with UserContextManager(user_id):
                return func(*args, **kwargs)

        return wrapper

    return decorator