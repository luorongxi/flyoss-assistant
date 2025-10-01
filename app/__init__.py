from flask import Flask, request, jsonify
from flask_restx import Api, Resource
from app.utils import config, setup_logging
from app.services import dingtalk_service
from app.blueprints import agent_ns, knowledge_ns, monitoring_ns

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)

    # 初始化日志配置
    logger = setup_logging()

    # 配置应用
    app.config.update(
        DEBUG=config.DEBUG,
        SECRET_KEY=config.SECRET_KEY if hasattr(config, 'SECRET_KEY') else 'dev',
        PROPAGATE_EXCEPTIONS=True,
        RESTX_MASK_SWAGGER=False  # 禁用敏感数据屏蔽
    )

    # 创建 RESTX API 实例
    api = Api(
        app,
        version='1.0',
        title='FlyOSS Assistant API',
        description='FlyOSS Assistant API 文档',
        doc='/docs',  # 文档访问路径
        default='API',
        default_label='主要 API 操作',
        contact='flyoss.ai@flyoss.com',
        contact_url='https://www.flyoss.com',
        license='Apache 2.0',
        license_url='https://opensource.org/license/apache-2-0'
    )

    # 关键修复：确保根路由正确注册，并指定唯一的端点名称
    @app.route('/', endpoint='homepage')
    def home():
        """应用首页"""
        return {
            "name": "FlyOSS Assistant",
            "version": "0.1.0",
            "status": "running",
            "services": {
                "llm": config.CHAT_MODEL,
                "memory": "Redis",
                "knowledge": "Qdrant"
            }
        }

    # 使用装饰器注册API根路由
    @api.route('/api', endpoint='api_root')
    class ApiRootResource(Resource):
        @api.doc('api_root')
        @api.response(200, 'API状态信息')
        def get(self):
            """API根端点"""
            return {
                "api_version": "1.0",
                "endpoints": {
                    "agent": "/agent",
                    "knowledge": "/knowledge",
                    "monitoring": "/monitoring",
                    "documentation": "/docs"
                }
            }

    # 注册命名空间
    api.add_namespace(agent_ns, path='/agent')
    api.add_namespace(knowledge_ns, path='/knowledge')
    api.add_namespace(monitoring_ns, path='/monitoring')

    # 初始化钉钉服务
    if config.DINGTALK_ENABLED:
        dingtalk_service.start()
        logger.info("钉钉服务已启动")

    @app.before_request
    def before_request():
        """请求前处理"""
        logger.info(f"收到请求: {request.method} {request.path}")

    @app.after_request
    def after_request(response):
        """请求后处理"""
        logger.info(f"请求完成: {request.method} {request.path} - 状态码: {response.status_code}")
        return response

    # 全局错误处理
    @app.errorhandler(404)
    def handle_404(error):
        """处理404错误"""
        return jsonify({
            "error": "资源未找到",
            "message": f"请求的路径 {request.path} 不存在",
            "available_endpoints": {
                "homepage": "/",
                "api_root": "/api",
                "documentation": "/docs",
                "agent": "/agent",
                "knowledge": "/knowledge",
                "monitoring": "/monitoring"
            }
        }), 404

    @app.errorhandler(500)
    def handle_500(error):
        """处理500错误"""
        logger.error(f"服务器内部错误: {str(error)}")
        return jsonify({
            "error": "服务器内部错误",
            "message": "请稍后再试或联系管理员"
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """全局异常处理"""
        logger.error(f"未处理的异常: {str(error)}")
        return jsonify({
            "error": "服务器内部错误",
            "message": str(error)
        }), 500

    # 打印所有注册的路由用于调试
    logger.info("应用已注册的路由:")
    for rule in app.url_map.iter_rules():
        logger.info(f"  {rule} - 端点: {rule.endpoint}")

    return app