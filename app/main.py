import logging
import uvicorn
from asgiref.wsgi import WsgiToAsgi
from app import create_app
from app.utils import config, setup_logging

# 初始化日志配置
logger = setup_logging()

def create_app_instance():
    """创建应用实例"""
    return create_app()

# 创建Flask应用实例并转换为ASGI应用
flask_app = create_app_instance()
app = WsgiToAsgi(flask_app)

def run_server():
    """运行应用服务器"""
    logger.info(f"启动服务器: {config.SERVER_HOST}:{config.SERVER_PORT}")

    # 根据环境选择应用加载方式
    if config.DEBUG:
        # DEBUG模式使用字符串加载支持热重载
        app_to_run = "app.main:app"
    else:
        # 生产模式使用ASGI包装后的应用
        app_to_run = app

    uvicorn.run(
        app=app_to_run,
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=config.DEBUG,
        log_level=logging.DEBUG if config.LOG_LEVEL else logging.WARNING,
        workers=1 if config.DEBUG else 4
    )

if __name__ == "__main__":
    run_server()