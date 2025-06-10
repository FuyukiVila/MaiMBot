import asyncio
import time
from maim_message import MessageServer
from .common.remote import TelemetryHeartBeatTask
from .manager.async_task_manager import async_task_manager
from .chat.utils.statistic import OnlineTimeRecordTask, StatisticOutputTask
from .manager.mood_manager import MoodPrintTask, MoodUpdateTask
from .chat.emoji_system.emoji_manager import emoji_manager
from .chat.normal_chat.willing.willing_manager import willing_manager
from .chat.message_receive.chat_stream import chat_manager
from src.chat.heart_flow.heartflow import heartflow
from .chat.message_receive.message_sender import message_manager
from .chat.message_receive.storage import MessageStorage
from .config.config import global_config
from .chat.message_receive.bot import chat_bot
from .common.logger_manager import get_logger
from .individuality.individuality import individuality, Individuality
from .common.server import global_server, Server
from rich.traceback import install
from .chat.focus_chat.expressors.exprssion_learner import expression_learner
from .api.main import start_api_server
# 导入actions模块，确保装饰器被执行
import src.chat.actions.default_actions  # noqa

# 条件导入记忆系统
if global_config.memory.enable_memory:
    from .chat.memory_system.Hippocampus import hippocampus_manager

# 插件系统现在使用统一的插件加载器

install(extra_lines=3)

logger = get_logger("main")


class MainSystem:
    def __init__(self):
        # 根据配置条件性地初始化记忆系统
        if global_config.memory.enable_memory:
            self.hippocampus_manager = hippocampus_manager
        else:
            self.hippocampus_manager = None
            
        self.individuality: Individuality = individuality

        # 使用消息API替代直接的FastAPI实例
        from src.common.message import global_api

        self.app: MessageServer = global_api
        self.server: Server = global_server

    async def initialize(self):
        """初始化系统组件"""
        logger.debug(f"正在唤醒{global_config.bot.nickname}......")

        # 其他初始化任务
        await asyncio.gather(self._init_components())

        logger.debug("系统初始化完成")

    async def _init_components(self):
        """初始化其他组件"""
        init_start_time = time.time()

        # 添加在线时间统计任务
        await async_task_manager.add_task(OnlineTimeRecordTask())

        # 添加统计信息输出任务
        await async_task_manager.add_task(StatisticOutputTask())

        # 添加遥测心跳任务
        await async_task_manager.add_task(TelemetryHeartBeatTask())

        # 启动API服务器
        start_api_server()
        logger.success("API服务器启动成功")
        
        # 加载所有actions，包括默认的和插件的
        self._load_all_actions()
        logger.success("动作系统加载成功")
        
        # 初始化表情管理器
        emoji_manager.initialize()
        logger.success("表情包管理器初始化成功")

        # 添加情绪衰减任务
        await async_task_manager.add_task(MoodUpdateTask())
        # 添加情绪打印任务
        await async_task_manager.add_task(MoodPrintTask())

        # 启动愿望管理器
        await willing_manager.async_task_starter()

        # 初始化聊天管理器
        await chat_manager._initialize()
        asyncio.create_task(chat_manager._auto_save_task())

        # 根据配置条件性地初始化记忆系统
        if global_config.memory.enable_memory:
            if self.hippocampus_manager:
                self.hippocampus_manager.initialize()
                logger.success("记忆系统初始化成功")
        else:
            logger.info("记忆系统已禁用，跳过初始化")

        # await asyncio.sleep(0.5) #防止logger输出飞了

        # 将bot.py中的chat_bot.message_process消息处理函数注册到api.py的消息处理基类中
        self.app.register_message_handler(chat_bot.message_process)

        # 初始化个体特征
        await self.individuality.initialize(
            bot_nickname=global_config.bot.nickname,
            personality_core=global_config.personality.personality_core,
            personality_sides=global_config.personality.personality_sides,
            identity_detail=global_config.identity.identity_detail,
        )
        logger.success("个体特征初始化成功")

        try:
            # 启动全局消息管理器 (负责消息发送/排队)
            await message_manager.start()
            logger.success("全局消息管理器启动成功")

            # 启动心流系统主循环
            asyncio.create_task(heartflow.heartflow_start_working())
            logger.success("心流系统启动成功")

            init_time = int(1000 * (time.time() - init_start_time))
            logger.success(f"初始化完成，神经元放电{init_time}次")
        except Exception as e:
            logger.error(f"启动大脑和外部世界失败: {e}")
            raise

    def _load_all_actions(self):
        """加载所有actions和commands，使用统一的插件加载器"""
        try:
            # 导入统一的插件加载器
            from src.plugins.plugin_loader import plugin_loader
            
            # 使用统一的插件加载器加载所有插件组件
            loaded_actions, loaded_commands = plugin_loader.load_all_plugins()
            
            # 加载命令处理系统
            try:
                # 导入命令处理系统
                from src.chat.command.command_handler import command_manager
                logger.success("命令处理系统加载成功")
            except Exception as e:
                logger.error(f"加载命令处理系统失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                    
        except Exception as e:
            logger.error(f"加载插件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def schedule_tasks(self):
        """调度定时任务"""
        while True:
            tasks = [
                emoji_manager.start_periodic_check_register(),
                self.remove_recalled_message_task(),
                self.app.run(),
                self.server.run(),
            ]
            
            # 根据配置条件性地添加记忆系统相关任务
            if global_config.memory.enable_memory and self.hippocampus_manager:
                tasks.extend([
                    self.build_memory_task(),
                    self.forget_memory_task(),
                    self.consolidate_memory_task(),
                ])
            
            tasks.append(self.learn_and_store_expression_task())
            
            await asyncio.gather(*tasks)

    async def build_memory_task(self):
        """记忆构建任务"""
        while True:
            await asyncio.sleep(global_config.memory.memory_build_interval)
            logger.info("正在进行记忆构建")
            await self.hippocampus_manager.build_memory()

    async def forget_memory_task(self):
        """记忆遗忘任务"""
        while True:
            await asyncio.sleep(global_config.memory.forget_memory_interval)
            logger.info("[记忆遗忘] 开始遗忘记忆...")
            await self.hippocampus_manager.forget_memory(
                percentage=global_config.memory.memory_forget_percentage
            )
            logger.info("[记忆遗忘] 记忆遗忘完成")

    async def consolidate_memory_task(self):
        """记忆整合任务"""
        while True:
            await asyncio.sleep(global_config.memory.consolidate_memory_interval)
            logger.info("[记忆整合] 开始整合记忆...")
            await self.hippocampus_manager.consolidate_memory()
            logger.info("[记忆整合] 记忆整合完成")

    @staticmethod
    async def learn_and_store_expression_task():
        """学习并存储表达方式任务"""
        while True:
            await asyncio.sleep(global_config.expression.learning_interval)
            if global_config.expression.enable_expression_learning:
                logger.info("[表达方式学习] 开始学习表达方式...")
                await expression_learner.learn_and_store_expression()
                logger.info("[表达方式学习] 表达方式学习完成")

    # async def print_mood_task(self):
    #     """打印情绪状态"""
    #     while True:
    #         self.mood_manager.print_mood_status()
    #         await asyncio.sleep(60)

    @staticmethod
    async def remove_recalled_message_task():
        """删除撤回消息任务"""
        while True:
            try:
                storage = MessageStorage()
                await storage.remove_recalled_message(time.time())
            except Exception:
                logger.exception("删除撤回消息失败")
            await asyncio.sleep(3600)


async def main():
    """主函数"""
    system = MainSystem()
    await asyncio.gather(
        system.initialize(),
        system.schedule_tasks(),
    )


if __name__ == "__main__":
    asyncio.run(main())
