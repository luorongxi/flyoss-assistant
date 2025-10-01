import asyncio
import threading
import traceback

from dingtalk_stream import AckMessage, ChatbotMessage, DingTalkStreamClient, Credential, ChatbotHandler, CallbackMessage
from app.utils import config, setup_logging, UserContextManager
from app.agents import main_agent

# 初始化日志配置
logger = setup_logging()

class ChatbotMessageHandler(ChatbotHandler):
    """钉钉机器人消息处理器"""

    def __init__(self, service_instance):
        super().__init__()
        self.service = service_instance

    async def process(self, callback: CallbackMessage) -> tuple:
        try:
            # 从回调数据中提取聊天消息
            # logger.info(f"回调数据：{callback.data}")
            incoming_message = ChatbotMessage.from_dict(callback.data)
            logger.info(f"聊天消息：{incoming_message}")

            # 获取会话ID
            conversation_id = callback.data['conversationId']
            # 获取发送者的用户ID
            user_id = callback.data['senderStaffId']
            # 提取消息文本内容并去除前后空白
            message = incoming_message.text.content.strip()

            logger.info(f"处理来自用户 {user_id} 的消息: {message}")

            # 异步处理消息
            asyncio.create_task(self.process_message_async(incoming_message, conversation_id, user_id, message))

            return AckMessage.STATUS_OK, 'OK'
        except Exception as e:
            logger.error(f"消息处理失败: {str(e)}\n{traceback.format_exc()}", exc_info=True)
            return AckMessage.STATUS_SYSTEM_EXCEPTION, str(e)

    async def process_message_async(self, incoming_message: ChatbotMessage, conversation_id: str, user_id: str, message: str):
        """异步处理消息的核心逻辑"""
        try:
            response = await main_agent.process(conversation_id, user_id, message)

            if response:
                logger.info(f"准备回复消息: {response.text[:50]}...")

                # 使用父类的reply方法回复消息
                self.reply_text(response.text, incoming_message)
                logger.info(f"已回复消息: {response.text[:50]}...")
            else:
                logger.warning("生成了空回复")
        except Exception as e:
            logger.error(f"异步消息处理失败: {str(e)}\n{traceback.format_exc()}", exc_info=True)
            try:
                # 错误回复 - 使用父类的reply方法
                self.reply_text("处理您的消息时出现问题，请稍后再试", incoming_message)
            except Exception as fallback_error:
                logger.error(f"发送错误回退消息失败: {str(fallback_error)}\n{traceback.format_exc()}")


class DingTalkService:
    def __init__(self):
        # logger.info(f"钉钉配置验证 - AppKey: {config.DINGTALK_APP_KEY}, AppSecret: {config.DINGTALK_APP_SECRET}")

        self.credential = Credential(
            client_id=config.DINGTALK_APP_KEY,
            client_secret=config.DINGTALK_APP_SECRET
        )

        self.client = DingTalkStreamClient(
            credential=self.credential,
            logger=logger
        )

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.chatbot_handler = ChatbotMessageHandler(self)
        self.client.register_callback_handler(ChatbotMessage.TOPIC, self.chatbot_handler)
        logger.info(f"已注册消息处理器")

        self.service_thread = None
        self.running = False

    def start(self):
        if self.running:
            logger.warning("钉钉服务已在运行中")
            return

        logger.info("启动钉钉机器人服务...")
        self.service_thread = threading.Thread(target=self.run_service, daemon=True)
        self.service_thread.start()
        logger.info(f"钉钉服务已在后台线程启动")
        self.running = True

    def run_service(self):
        try:
            self.loop.run_until_complete(self.client.start_forever())
            logger.info("钉钉服务线程开始运行")
        except Exception as e:
            logger.error(f"钉钉服务运行失败: {str(e)}\n{traceback.format_exc()}", exc_info=True)
        finally:
            self.running = False
            logger.info("钉钉服务已停止")

    def is_running(self):
        return self.running

# 全局钉钉服务实例
dingtalk_service = DingTalkService()