import asyncio
import math
from typing import Tuple

from src.chat.memory_system.Hippocampus import hippocampus_manager
from src.chat.message_receive.message import MessageRecv, MessageRecvS4U
from maim_message.message_base import GroupInfo
from src.chat.message_receive.storage import MessageStorage
from src.chat.message_receive.chat_stream import get_chat_manager
from src.chat.utils.timer_calculator import Timer
from src.chat.utils.utils import is_mentioned_bot_in_message
from src.common.logger import get_logger
from src.config.config import global_config
from src.mais4u.mais4u_chat.body_emotion_action_manager import action_manager
from src.mais4u.mais4u_chat.s4u_mood_manager import mood_manager
from src.mais4u.mais4u_chat.s4u_watching_manager import watching_manager
from src.mais4u.mais4u_chat.context_web_manager import get_context_web_manager
from src.mais4u.mais4u_chat.gift_manager import gift_manager
from src.mais4u.mais4u_chat.screen_manager import screen_manager

from .s4u_chat import get_s4u_chat_manager


# from ..message_receive.message_buffer import message_buffer

logger = get_logger("chat")


async def _calculate_interest(message: MessageRecv) -> Tuple[float, bool]:
    """计算消息的兴趣度

    Args:
        message: 待处理的消息对象

    Returns:
        Tuple[float, bool]: (兴趣度, 是否被提及)
    """
    is_mentioned, _ = is_mentioned_bot_in_message(message)
    interested_rate = 0.0

    if global_config.memory.enable_memory:
        with Timer("记忆激活"):
            interested_rate = await hippocampus_manager.get_activate_from_text(
                message.processed_plain_text,
                fast_retrieval=True,
            )
            logger.debug(f"记忆激活率: {interested_rate:.2f}")

    text_len = len(message.processed_plain_text)
    # 根据文本长度调整兴趣度，长度越大兴趣度越高，但增长率递减，最低0.01，最高0.05
    # 采用对数函数实现递减增长

    base_interest = 0.01 + (0.05 - 0.01) * (math.log10(text_len + 1) / math.log10(1000 + 1))
    base_interest = min(max(base_interest, 0.01), 0.05)

    interested_rate += base_interest

    if is_mentioned:
        interest_increase_on_mention = 1
        interested_rate += interest_increase_on_mention

    return interested_rate, is_mentioned


class S4UMessageProcessor:
    """心流处理器，负责处理接收到的消息并计算兴趣度"""

    def __init__(self):
        """初始化心流处理器，创建消息存储实例"""
        self.storage = MessageStorage()

    async def process_message(self, message: MessageRecvS4U, skip_gift_debounce: bool = False) -> None:
        """处理接收到的原始消息数据

        主要流程:
        1. 消息解析与初始化
        2. 消息缓冲处理
        3. 过滤检查
        4. 兴趣度计算
        5. 关系处理

        Args:
            message_data: 原始消息字符串
        """

        # 1. 消息解析与初始化
        groupinfo = message.message_info.group_info
        userinfo = message.message_info.user_info
        message_info = message.message_info

        chat = await get_chat_manager().get_or_create_stream(
            platform=message_info.platform,
            user_info=userinfo,
            group_info=groupinfo,
        )

        if await self.handle_internal_message(message):
            return

        if await self.hadle_if_voice_done(message):
            return

        # 处理礼物消息，如果消息被暂存则停止当前处理流程
        if not skip_gift_debounce and not await self.handle_if_gift(message):
            return
        await self.check_if_fake_gift(message)

        # 处理屏幕消息
        if await self.handle_screen_message(message):
            return

        await self.storage.store_message(message, chat)

        s4u_chat = get_s4u_chat_manager().get_or_create_chat(chat)

        await s4u_chat.add_message(message)

        _interested_rate, _ = await _calculate_interest(message)

        await mood_manager.start()

        # 一系列llm驱动的前处理
        chat_mood = mood_manager.get_mood_by_chat_id(chat.stream_id)
        asyncio.create_task(chat_mood.update_mood_by_message(message))
        chat_action = action_manager.get_action_state_by_chat_id(chat.stream_id)
        asyncio.create_task(chat_action.update_action_by_message(message))
        # 视线管理：收到消息时切换视线状态
        chat_watching = watching_manager.get_watching_by_chat_id(chat.stream_id)
        await chat_watching.on_message_received()

        # 上下文网页管理：启动独立task处理消息上下文
        asyncio.create_task(self._handle_context_web_update(chat.stream_id, message))

        # 日志记录
        if message.is_gift:
            logger.info(f"[S4U-礼物] {userinfo.user_nickname} 送出了 {message.gift_name} x{message.gift_count}")
        else:
            logger.info(f"[S4U]{userinfo.user_nickname}:{message.processed_plain_text}")

    async def handle_internal_message(self, message: MessageRecvS4U):
        if message.is_internal:
            
            group_info = GroupInfo(platform = "amaidesu_default",group_id = 660154,group_name = "内心")
            
            chat =  await get_chat_manager().get_or_create_stream(
                platform = "amaidesu_default",
                user_info = message.message_info.user_info,
                group_info = group_info
            )
            s4u_chat = get_s4u_chat_manager().get_or_create_chat(chat)
            message.message_info.group_info = s4u_chat.chat_stream.group_info
            message.message_info.platform = s4u_chat.chat_stream.platform

            s4u_chat.internal_message.append(message)
            s4u_chat._new_message_event.set()

            logger.info(
                f"[{s4u_chat.stream_name}] 添加内部消息-------------------------------------------------------: {message.processed_plain_text}"
            )

            return True
        return False

    async def handle_screen_message(self, message: MessageRecvS4U):
        if message.is_screen:
            screen_manager.set_screen(message.screen_info)
            return True
        return False

    async def hadle_if_voice_done(self, message: MessageRecvS4U):
        if message.voice_done:
            s4u_chat = get_s4u_chat_manager().get_or_create_chat(message.chat_stream)
            s4u_chat.voice_done = message.voice_done
            return True
        return False

    async def check_if_fake_gift(self, message: MessageRecvS4U) -> bool:
        """检查消息是否为假礼物"""
        if message.is_gift:
            return False

        gift_keywords = ["送出了礼物", "礼物", "送出了", "投喂"]
        if any(keyword in message.processed_plain_text for keyword in gift_keywords):
            message.is_fake_gift = True
            return True

        return False

    async def handle_if_gift(self, message: MessageRecvS4U) -> bool:
        """处理礼物消息

        Returns:
            bool: True表示应该继续处理消息，False表示消息已被暂存不需要继续处理
        """
        if message.is_gift:
            # 定义防抖完成后的回调函数
            def gift_callback(merged_message: MessageRecvS4U):
                """礼物防抖完成后的回调"""
                # 创建异步任务来处理合并后的礼物消息，跳过防抖处理
                asyncio.create_task(self.process_message(merged_message, skip_gift_debounce=True))

            # 交给礼物管理器处理，并传入回调函数
            # 对于礼物消息，handle_gift 总是返回 False（消息被暂存）
            await gift_manager.handle_gift(message, gift_callback)
            return False  # 消息被暂存，不继续处理

        return True  # 非礼物消息，继续正常处理

    async def _handle_context_web_update(self, chat_id: str, message: MessageRecv):
        """处理上下文网页更新的独立task

        Args:
            chat_id: 聊天ID
            message: 消息对象
        """
        try:
            logger.debug(f"🔄 开始处理上下文网页更新: {message.message_info.user_info.user_nickname}")

            context_manager = get_context_web_manager()

            # 只在服务器未启动时启动（避免重复启动）
            if context_manager.site is None:
                logger.info("🚀 首次启动上下文网页服务器...")
                await context_manager.start_server()

            # 添加消息到上下文并更新网页
            await asyncio.sleep(1.5)

            await context_manager.add_message(chat_id, message)

            logger.debug(f"✅ 上下文网页更新完成: {message.message_info.user_info.user_nickname}")

        except Exception as e:
            logger.error(f"❌ 处理上下文网页更新失败: {e}", exc_info=True)
