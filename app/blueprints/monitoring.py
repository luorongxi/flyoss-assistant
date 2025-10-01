import os
import sys
import redis
import requests

from flask_restx import Namespace, Resource, fields
from app.utils import config, setup_logging
from app.core import memory_system, knowledge_base

# 初始化日志配置
logger = setup_logging()

# 创建命名空间
monitoring_ns = Namespace('monitoring', description='系统监控操作')

# 定义数据模型
health_status_model = monitoring_ns.model('HealthStatus', {
    'status': fields.String(description='整体状态'),
    'version': fields.String(description='版本号'),
    'dependencies': fields.Raw(description='依赖服务状态')
})

metrics_model = monitoring_ns.model('Metrics', {
    'requests': fields.Integer(description='请求数量'),
    'errors': fields.Integer(description='错误数量'),
    'response_time': fields.Float(description='平均响应时间')
})

logs_model = monitoring_ns.model('Logs', {
    'logs': fields.List(fields.String, description='日志内容'),
    'error': fields.String(description='错误信息', default=None)
})

@monitoring_ns.route('/health')
class HealthCheck(Resource):
    @monitoring_ns.doc('health_check')
    @monitoring_ns.response(200, '健康检查成功', health_status_model)
    def get(self):
        """健康检查端点"""
        status = {
            "status": "ok",
            "version": "0.1.0",
            "dependencies": {}
        }

        # 检查Redis连接
        try:
            memory_system.client.ping()
            status["dependencies"]["redis"] = "connected"
        except redis.RedisError as e:
            status["dependencies"]["redis"] = f"error: {str(e)}"
            status["status"] = "degraded"

        # 检查Qdrant连接
        try:
            knowledge_base.client.get_collection(knowledge_base.collection_name)
            status["dependencies"]["qdrant"] = "connected"
        except Exception as e:
            status["dependencies"]["qdrant"] = f"error: {str(e)}"
            status["status"] = "degraded"

        # 检查LLM服务
        try:
            test_prompt = "健康检查"
            response = requests.post(
                f"{config.LLM_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
                json={
                    "model": config.CHAT_MODEL,
                    "messages": [{"role": "user", "content": test_prompt}],
                    "max_tokens": 10
                },
                timeout=5
            )
            response.raise_for_status()
            status["dependencies"]["llm"] = "connected"
        except Exception as e:
            status["dependencies"]["llm"] = f"error: {str(e)}"
            status["status"] = "degraded"

        return status

@monitoring_ns.route('/logs')
class Logs(Resource):
    @monitoring_ns.doc('logs')
    @monitoring_ns.response(200, '成功获取日志', logs_model)
    @monitoring_ns.response(500, '服务器内部错误', logs_model)
    def get(self):
        """获取最近日志"""
        try:
            # 获取项目根目录的绝对路径
            if getattr(sys, 'frozen', False):  # 如果是打包后的可执行文件
                project_root = os.path.dirname(sys.executable)
            else:
                current_file = os.path.abspath(__file__)
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

            # 在项目根目录下创建 logs 文件夹
            log_dir = os.path.join(project_root, "logs")
            log_file = os.path.join(log_dir, config.LOG_FILE_NAME)
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()[-100:]  # 获取最后100行
            return {"logs": lines}
        except Exception as e:
            return {"logs": [], "error": str(e)}, 500