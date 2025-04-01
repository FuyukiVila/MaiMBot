
from ..moods.moods import MoodManager  # 导入情绪管理器
from ..config.config import global_config
from ..chat_module.reasoning_chat.reasoning_generator import ResponseGenerator


from ..storage.storage import MessageStorage  # 修改导入路径

from src.common.logger import get_module_logger, CHAT_STYLE_CONFIG, LogConfig
from ..chat_module.think_flow_chat.think_flow_chat import ThinkFlowChat
from ..chat_module.reasoning_chat.reasoning_chat import ReasoningChat

# 定义日志配置
chat_config = LogConfig(
    # 使用消息发送专用样式
    console_format=CHAT_STYLE_CONFIG["console_format"],
    file_format=CHAT_STYLE_CONFIG["file_format"],
)

# 配置主程序日志格式
logger = get_module_logger("chat_bot", config=chat_config)


class ChatBot:
    def __init__(self):
        self.storage = MessageStorage()
        self.gpt = ResponseGenerator()
        self.bot = None  # bot 实例引用
        self._started = False
        self.mood_manager = MoodManager.get_instance()  # 获取情绪管理器单例
        self.mood_manager.start_mood_update()  # 启动情绪更新
        self.think_flow_chat = ThinkFlowChat()
        self.reasoning_chat = ReasoningChat()

    async def _ensure_started(self):
        """确保所有任务已启动"""
        if not self._started:
            self._started = True

    async def message_process(self, message_data: str) -> None:
        """处理转化后的统一格式消息
        1. 过滤消息
        2. 记忆激活
        3. 意愿激活
        4. 生成回复并发送
        5. 更新关系
        6. 更新情绪
        """
        
        timing_results = {}  # 用于收集所有计时结果
        response_set = None  # 初始化response_set变量

        message = MessageRecv(message_data)
        groupinfo = message.message_info.group_info
        userinfo = message.message_info.user_info
        messageinfo = message.message_info

        if groupinfo.group_id not in global_config.talk_allowed_groups:
            return
        
        
        # 消息过滤，涉及到config有待更新

        # 创建聊天流
        chat = await chat_manager.get_or_create_stream(
            platform=messageinfo.platform,
            user_info=userinfo,
            group_info=groupinfo,
        )
        message.update_chat_stream(chat)

        # 创建 心流与chat的观察
        heartflow.create_subheartflow(chat.stream_id)

        await message.process()

        # 过滤词/正则表达式过滤
        if self._check_ban_words(message.processed_plain_text, chat, userinfo) or self._check_ban_regex(
            message.raw_message, chat, userinfo
        ):
            return

        await self.storage.store_message(message, chat)

        timer1 = time.time()
        interested_rate = 0
        interested_rate = await HippocampusManager.get_instance().get_activate_from_text(
            message.processed_plain_text, fast_retrieval=True
        )
        timer2 = time.time()
        timing_results["记忆激活"] = timer2 - timer1

        is_mentioned = is_mentioned_bot_in_message(message)

        if global_config.enable_think_flow:
            current_willing_old = willing_manager.get_willing(chat_stream=chat)
            current_willing_new = (heartflow.get_subheartflow(chat.stream_id).current_state.willing - 5) / 4
            print(f"旧回复意愿：{current_willing_old}，新回复意愿：{current_willing_new}")
            current_willing = (current_willing_old + current_willing_new) / 2
        else:
            logger.error(f"未知的回复模式，请检查配置文件！！: {global_config.response_mode}")


# 创建全局ChatBot实例
chat_bot = ChatBot()
