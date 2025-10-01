import json
import time

from flask import request, Response
from flask_restx import Namespace, Resource, fields
from app.agents import main_agent
from app.utils import setup_logging, UserContext

# 初始化日志配置
logger = setup_logging()

# 创建命名空间
agent_ns = Namespace('agent', description='钉钉集成操作')

# 定义数据模型
message_model = agent_ns.model('Message', {
    'content': fields.String(required=True, description='消息内容'),
    'senderStaffId': fields.String(description='发送者员工ID'),
    'senderId': fields.String(description='发送者ID'),
    'conversationId': fields.String(required=True, description='会话ID')
})

response_model = agent_ns.model('Response', {
    'msgtype': fields.String(description='消息类型'),
    'text': fields.Nested(agent_ns.model('TextContent', {
        'content': fields.String(description='响应内容')
    }))
})

stream_chunk_model = agent_ns.model('StreamChunk', {
    'text': fields.String(description='流式输出片段')
})


@agent_ns.route('/send_message')
class MessageSend(Resource):
    @agent_ns.doc('send_message')
    @agent_ns.expect(message_model)
    @agent_ns.response(200, '消息发送成功', response_model)
    @agent_ns.response(400, '无效请求')
    @agent_ns.response(500, '服务器内部错误')
    def post(self):
        """发送消息给主Agent并获取响应"""

        try:
            data = request.json
            logger.info("收到钉钉回调", data=data)

            # 提取消息内容
            text_content = data.get('text')
            sender_id = data.get('sender_id')
            conversation_id = data.get('conversation_id')

            # 设置用户上下文
            UserContext.set_user(sender_id)

            # 处理消息
            response = main_agent.process(
                message=text_content,
                sender_id=sender_id,
                conversation_id=conversation_id
            )

            # 返回响应
            return {
                "msgtype": "text",
                "text": {
                    "content": response.text
                }
            }
        except Exception as e:
            logger.error("钉钉回调处理失败", error=str(e))
            return {
                "msgtype": "text",
                "text": {
                    "content": "处理消息时出错，请稍后再试。"
                }
            }, 500


@agent_ns.route('/stream_test')
class StreamTest(Resource):
    @agent_ns.doc('stream_test')
    @agent_ns.expect(agent_ns.model('StreamTestRequest', {
        'text': fields.String(required=True, description='测试文本'),
        'user_id': fields.String(description='用户ID', default='test_user'),
        'conversation_id': fields.String(description='会话ID', default='test_user')
    }))
    @agent_ns.response(200, '流式输出成功', stream_chunk_model)
    @agent_ns.response(500, '服务器内部错误')
    def post(self):
        """流式输出测试接口"""
        try:
            data = request.json
            text = data.get('text', '')
            sender_id = data.get('user_id', 'test_user')
            conversation_id = data.get('conversation_id', 'test_user')

            def generate():
                """生成流式响应"""
                for chunk in main_agent.stream_process(text, sender_id):
                    yield json.dumps({"text": chunk}) + "\n"
                    time.sleep(0.1)

            return Response(generate(), mimetype='application/json-stream')
        except Exception as e:
            logger.error("流式测试失败", error=str(e))
            return {"error": str(e)}, 500


