from src.chat.heart_flow.observation.chatting_observation import ChattingObservation
from src.chat.heart_flow.observation.observation import Observation
from src.llm_models.utils_model import LLMRequest
from src.config.config import global_config
import time
import traceback
from src.common.logger import get_logger
from src.chat.utils.prompt_builder import Prompt, global_prompt_manager
from src.chat.message_receive.chat_stream import get_chat_manager
from src.person_info.relationship_manager import get_relationship_manager
from .base_processor import BaseProcessor
from typing import List
from typing import Dict
from src.chat.focus_chat.info.info_base import InfoBase
from src.chat.focus_chat.info.relation_info import RelationInfo
from json_repair import repair_json
from src.person_info.person_info import get_person_info_manager
import json
import asyncio
from src.chat.utils.chat_message_builder import (
    get_raw_msg_by_timestamp_with_chat,
    get_raw_msg_by_timestamp_with_chat_inclusive,
    get_raw_msg_before_timestamp_with_chat,
    num_new_messages_since,
)
import os
import pickle


# 消息段清理配置
SEGMENT_CLEANUP_CONFIG = {
    "enable_cleanup": True,  # 是否启用清理
    "max_segment_age_days": 7,  # 消息段最大保存天数
    "max_segments_per_user": 10,  # 每用户最大消息段数
    "cleanup_interval_hours": 1,  # 清理间隔（小时）
}


logger = get_logger("processor")


def init_prompt():
    relationship_prompt = """
<聊天记录>
{chat_observe_info}
</聊天记录>

{name_block}
现在，你想要回复{person_name}的消息，消息内容是：{target_message}。请根据聊天记录和你要回复的消息，从你对{person_name}的了解中提取有关的信息：
1.你需要提供你想要提取的信息具体是哪方面的信息，例如：年龄，性别，对ta的印象，最近发生的事等等。
2.请注意，请不要重复调取相同的信息，已经调取的信息如下：
{info_cache_block}
3.如果当前聊天记录中没有需要查询的信息，或者现有信息已经足够回复，请返回{{"none": "不需要查询"}}

请以json格式输出，例如：

{{
    "info_type": "信息类型",
}}

请严格按照json输出格式，不要输出多余内容：
"""
    Prompt(relationship_prompt, "relationship_prompt")

    fetch_info_prompt = """
    
{name_block}
以下是你在之前与{person_name}的交流中，产生的对{person_name}的了解：
{person_impression_block}
{points_text_block}

请从中提取用户"{person_name}"的有关"{info_type}"信息
请以json格式输出，例如：

{{
    {info_json_str}
}}

请严格按照json输出格式，不要输出多余内容：
"""
    Prompt(fetch_info_prompt, "fetch_person_info_prompt")


class PersonImpressionpProcessor(BaseProcessor):
    log_prefix = "关系"

    def __init__(self, subheartflow_id: str):
        super().__init__()

        self.subheartflow_id = subheartflow_id
        self.info_fetching_cache: List[Dict[str, any]] = []
        self.info_fetched_cache: Dict[
            str, Dict[str, any]
        ] = {}  # {person_id: {"info": str, "ttl": int, "start_time": float}}

        # 新的消息段缓存结构：
        # {person_id: [{"start_time": float, "end_time": float, "last_msg_time": float, "message_count": int}, ...]}
        self.person_engaged_cache: Dict[str, List[Dict[str, any]]] = {}

        # 持久化存储文件路径
        self.cache_file_path = os.path.join("data", "relationship", f"relationship_cache_{self.subheartflow_id}.pkl")

        # 最后处理的消息时间，避免重复处理相同消息
        current_time = time.time()
        self.last_processed_message_time = current_time

        # 最后清理时间，用于定期清理老消息段
        self.last_cleanup_time = 0.0

        self.llm_model = LLMRequest(
            model=global_config.model.relation,
            request_type="focus.relationship",
        )

        # 小模型用于即时信息提取
        self.instant_llm_model = LLMRequest(
            model=global_config.model.utils_small,
            request_type="focus.relationship.instant",
        )

        name = get_chat_manager().get_stream_name(self.subheartflow_id)
        self.log_prefix = f"[{name}] "

        # 加载持久化的缓存
        self._load_cache()

    # ================================
    # 缓存管理模块
    # 负责持久化存储、状态管理、缓存读写
    # ================================

    def _load_cache(self):
        """从文件加载持久化的缓存"""
        if os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, "rb") as f:
                    cache_data = pickle.load(f)
                    # 新格式：包含额外信息的缓存
                    self.person_engaged_cache = cache_data.get("person_engaged_cache", {})
                    self.last_processed_message_time = cache_data.get("last_processed_message_time", 0.0)
                    self.last_cleanup_time = cache_data.get("last_cleanup_time", 0.0)

                logger.info(
                    f"{self.log_prefix} 成功加载关系缓存，包含 {len(self.person_engaged_cache)} 个用户，最后处理时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_processed_message_time)) if self.last_processed_message_time > 0 else '未设置'}"
                )
            except Exception as e:
                logger.error(f"{self.log_prefix} 加载关系缓存失败: {e}")
                self.person_engaged_cache = {}
                self.last_processed_message_time = 0.0
        else:
            logger.info(f"{self.log_prefix} 关系缓存文件不存在，使用空缓存")

    def _save_cache(self):
        """保存缓存到文件"""
        try:
            os.makedirs(os.path.dirname(self.cache_file_path), exist_ok=True)
            cache_data = {
                "person_engaged_cache": self.person_engaged_cache,
                "last_processed_message_time": self.last_processed_message_time,
                "last_cleanup_time": self.last_cleanup_time,
            }
            with open(self.cache_file_path, "wb") as f:
                pickle.dump(cache_data, f)
            logger.debug(f"{self.log_prefix} 成功保存关系缓存")
        except Exception as e:
            logger.error(f"{self.log_prefix} 保存关系缓存失败: {e}")

    # ================================
    # 消息段管理模块
    # 负责跟踪用户消息活动、管理消息段、清理过期数据
    # ================================

    def _update_message_segments(self, person_id: str, message_time: float):
        """更新用户的消息段

        Args:
            person_id: 用户ID
            message_time: 消息时间戳
        """
        if person_id not in self.person_engaged_cache:
            self.person_engaged_cache[person_id] = []

        segments = self.person_engaged_cache[person_id]
        current_time = time.time()

        # 获取该消息前5条消息的时间作为潜在的开始时间
        before_messages = get_raw_msg_before_timestamp_with_chat(self.subheartflow_id, message_time, limit=5)
        if before_messages:
            # 由于get_raw_msg_before_timestamp_with_chat返回按时间升序排序的消息，最后一个是最接近message_time的
            # 我们需要第一个消息作为开始时间，但应该确保至少包含5条消息或该用户之前的消息
            potential_start_time = before_messages[0]["time"]
        else:
            # 如果没有前面的消息，就从当前消息开始
            potential_start_time = message_time

        # 如果没有现有消息段，创建新的
        if not segments:
            new_segment = {
                "start_time": potential_start_time,
                "end_time": message_time,
                "last_msg_time": message_time,
                "message_count": self._count_messages_in_timerange(potential_start_time, message_time),
            }
            segments.append(new_segment)

            person_name = get_person_info_manager().get_value_sync(person_id, "person_name") or person_id
            logger.info(
                f"{self.log_prefix} 眼熟用户 {person_name} 在 {time.strftime('%H:%M:%S', time.localtime(potential_start_time))} - {time.strftime('%H:%M:%S', time.localtime(message_time))} 之间有 {new_segment['message_count']} 条消息"
            )
            self._save_cache()
            return

        # 获取最后一个消息段
        last_segment = segments[-1]

        # 计算从最后一条消息到当前消息之间的消息数量（不包含边界）
        messages_between = self._count_messages_between(last_segment["last_msg_time"], message_time)

        if messages_between <= 10:
            # 在10条消息内，延伸当前消息段
            last_segment["end_time"] = message_time
            last_segment["last_msg_time"] = message_time
            # 重新计算整个消息段的消息数量
            last_segment["message_count"] = self._count_messages_in_timerange(
                last_segment["start_time"], last_segment["end_time"]
            )
            logger.debug(f"{self.log_prefix} 延伸用户 {person_id} 的消息段: {last_segment}")
        else:
            # 超过10条消息，结束当前消息段并创建新的
            # 结束当前消息段：延伸到原消息段最后一条消息后5条消息的时间
            after_messages = get_raw_msg_by_timestamp_with_chat(
                self.subheartflow_id, last_segment["last_msg_time"], current_time, limit=5, limit_mode="earliest"
            )
            if after_messages and len(after_messages) >= 5:
                # 如果有足够的后续消息，使用第5条消息的时间作为结束时间
                last_segment["end_time"] = after_messages[4]["time"]
            else:
                # 如果没有足够的后续消息，保持原有的结束时间
                pass

            # 重新计算当前消息段的消息数量
            last_segment["message_count"] = self._count_messages_in_timerange(
                last_segment["start_time"], last_segment["end_time"]
            )

            # 创建新的消息段
            new_segment = {
                "start_time": potential_start_time,
                "end_time": message_time,
                "last_msg_time": message_time,
                "message_count": self._count_messages_in_timerange(potential_start_time, message_time),
            }
            segments.append(new_segment)
            person_info_manager = get_person_info_manager()
            person_name = person_info_manager.get_value_sync(person_id, "person_name") or person_id
            logger.info(f"{self.log_prefix} 重新眼熟用户 {person_name} 创建新消息段（超过10条消息间隔）: {new_segment}")

        self._save_cache()

    def _count_messages_in_timerange(self, start_time: float, end_time: float) -> int:
        """计算指定时间范围内的消息数量（包含边界）"""
        messages = get_raw_msg_by_timestamp_with_chat_inclusive(self.subheartflow_id, start_time, end_time)
        return len(messages)

    def _count_messages_between(self, start_time: float, end_time: float) -> int:
        """计算两个时间点之间的消息数量（不包含边界），用于间隔检查"""
        return num_new_messages_since(self.subheartflow_id, start_time, end_time)

    def _get_total_message_count(self, person_id: str) -> int:
        """获取用户所有消息段的总消息数量"""
        if person_id not in self.person_engaged_cache:
            return 0

        total_count = 0
        for segment in self.person_engaged_cache[person_id]:
            total_count += segment["message_count"]

        return total_count

    def _cleanup_old_segments(self) -> bool:
        """清理老旧的消息段

        Returns:
            bool: 是否执行了清理操作
        """
        if not SEGMENT_CLEANUP_CONFIG["enable_cleanup"]:
            return False

        current_time = time.time()

        # 检查是否需要执行清理（基于时间间隔）
        cleanup_interval_seconds = SEGMENT_CLEANUP_CONFIG["cleanup_interval_hours"] * 3600
        if current_time - self.last_cleanup_time < cleanup_interval_seconds:
            return False

        logger.info(f"{self.log_prefix} 开始执行老消息段清理...")

        cleanup_stats = {
            "users_cleaned": 0,
            "segments_removed": 0,
            "total_segments_before": 0,
            "total_segments_after": 0,
        }

        max_age_seconds = SEGMENT_CLEANUP_CONFIG["max_segment_age_days"] * 24 * 3600
        max_segments_per_user = SEGMENT_CLEANUP_CONFIG["max_segments_per_user"]

        users_to_remove = []

        for person_id, segments in self.person_engaged_cache.items():
            cleanup_stats["total_segments_before"] += len(segments)
            original_segment_count = len(segments)

            # 1. 按时间清理：移除过期的消息段
            segments_after_age_cleanup = []
            for segment in segments:
                segment_age = current_time - segment["end_time"]
                if segment_age <= max_age_seconds:
                    segments_after_age_cleanup.append(segment)
                else:
                    cleanup_stats["segments_removed"] += 1
                    logger.debug(
                        f"{self.log_prefix} 移除用户 {person_id} 的过期消息段: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(segment['start_time']))} - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(segment['end_time']))}"
                    )

            # 2. 按数量清理：如果消息段数量仍然过多，保留最新的
            if len(segments_after_age_cleanup) > max_segments_per_user:
                # 按end_time排序，保留最新的
                segments_after_age_cleanup.sort(key=lambda x: x["end_time"], reverse=True)
                segments_removed_count = len(segments_after_age_cleanup) - max_segments_per_user
                cleanup_stats["segments_removed"] += segments_removed_count
                segments_after_age_cleanup = segments_after_age_cleanup[:max_segments_per_user]
                logger.debug(
                    f"{self.log_prefix} 用户 {person_id} 消息段数量过多，移除 {segments_removed_count} 个最老的消息段"
                )

            # 使用清理后的消息段

            # 更新缓存
            if len(segments_after_age_cleanup) == 0:
                # 如果没有剩余消息段，标记用户为待移除
                users_to_remove.append(person_id)
            else:
                self.person_engaged_cache[person_id] = segments_after_age_cleanup
                cleanup_stats["total_segments_after"] += len(segments_after_age_cleanup)

            if original_segment_count != len(segments_after_age_cleanup):
                cleanup_stats["users_cleaned"] += 1

        # 移除没有消息段的用户
        for person_id in users_to_remove:
            del self.person_engaged_cache[person_id]
            logger.debug(f"{self.log_prefix} 移除用户 {person_id}：没有剩余消息段")

        # 更新最后清理时间
        self.last_cleanup_time = current_time

        # 保存缓存
        if cleanup_stats["segments_removed"] > 0 or len(users_to_remove) > 0:
            self._save_cache()
            logger.info(
                f"{self.log_prefix} 清理完成 - 影响用户: {cleanup_stats['users_cleaned']}, 移除消息段: {cleanup_stats['segments_removed']}, 移除用户: {len(users_to_remove)}"
            )
            logger.info(
                f"{self.log_prefix} 消息段统计 - 清理前: {cleanup_stats['total_segments_before']}, 清理后: {cleanup_stats['total_segments_after']}"
            )
        else:
            logger.debug(f"{self.log_prefix} 清理完成 - 无需清理任何内容")

        return cleanup_stats["segments_removed"] > 0 or len(users_to_remove) > 0

    def force_cleanup_user_segments(self, person_id: str) -> bool:
        """强制清理指定用户的所有消息段

        Args:
            person_id: 用户ID

        Returns:
            bool: 是否成功清理
        """
        if person_id in self.person_engaged_cache:
            segments_count = len(self.person_engaged_cache[person_id])
            del self.person_engaged_cache[person_id]
            self._save_cache()
            logger.info(f"{self.log_prefix} 强制清理用户 {person_id} 的 {segments_count} 个消息段")
            return True
        return False

    def get_cache_status(self) -> str:
        """获取缓存状态信息，用于调试和监控"""
        if not self.person_engaged_cache:
            return f"{self.log_prefix} 关系缓存为空"

        status_lines = [f"{self.log_prefix} 关系缓存状态："]
        status_lines.append(
            f"最后处理消息时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_processed_message_time)) if self.last_processed_message_time > 0 else '未设置'}"
        )
        status_lines.append(
            f"最后清理时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_cleanup_time)) if self.last_cleanup_time > 0 else '未执行'}"
        )
        status_lines.append(f"总用户数：{len(self.person_engaged_cache)}")
        status_lines.append(
            f"清理配置：{'启用' if SEGMENT_CLEANUP_CONFIG['enable_cleanup'] else '禁用'} (最大保存{SEGMENT_CLEANUP_CONFIG['max_segment_age_days']}天, 每用户最多{SEGMENT_CLEANUP_CONFIG['max_segments_per_user']}段)"
        )
        status_lines.append("")

        for person_id, segments in self.person_engaged_cache.items():
            total_count = self._get_total_message_count(person_id)
            status_lines.append(f"用户 {person_id}:")
            status_lines.append(f"  总消息数：{total_count} ({total_count}/45)")
            status_lines.append(f"  消息段数：{len(segments)}")

            for i, segment in enumerate(segments):
                start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(segment["start_time"]))
                end_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(segment["end_time"]))
                last_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(segment["last_msg_time"]))
                status_lines.append(
                    f"    段{i + 1}: {start_str} -> {end_str} (最后消息: {last_str}, 消息数: {segment['message_count']})"
                )
            status_lines.append("")

        return "\n".join(status_lines)

    # ================================
    # 主要处理流程
    # 统筹各模块协作、对外提供服务接口
    # ================================

    async def process_info(
        self,
        observations: List[Observation] = None,
        action_type: str = None,
        action_data: dict = None,
        **kwargs,
    ) -> List[InfoBase]:
        """处理信息对象

        Args:
            observations: 观察对象列表
            action_type: 动作类型
            action_data: 动作数据

        Returns:
            List[InfoBase]: 处理后的结构化信息列表
        """
        await self.build_relation(observations)

        relation_info_str = await self.relation_identify(observations, action_type, action_data)

        if relation_info_str:
            relation_info = RelationInfo()
            relation_info.set_relation_info(relation_info_str)
        else:
            relation_info = None
            return None

        return [relation_info]

    async def build_relation(self, observations: List[Observation] = None):
        """构建关系"""
        self._cleanup_old_segments()
        current_time = time.time()

        if observations:
            for observation in observations:
                if isinstance(observation, ChattingObservation):
                    latest_messages = get_raw_msg_by_timestamp_with_chat(
                        self.subheartflow_id,
                        self.last_processed_message_time,
                        current_time,
                        limit=50,  # 获取自上次处理后的消息
                    )
                    if latest_messages:
                        # 处理所有新的非bot消息
                        for latest_msg in latest_messages:
                            user_id = latest_msg.get("user_id")
                            platform = latest_msg.get("user_platform") or latest_msg.get("chat_info_platform")
                            msg_time = latest_msg.get("time", 0)

                            if (
                                user_id
                                and platform
                                and user_id != global_config.bot.qq_account
                                and msg_time > self.last_processed_message_time
                            ):
                                from src.person_info.person_info import PersonInfoManager

                                person_id = PersonInfoManager.get_person_id(platform, user_id)
                                self._update_message_segments(person_id, msg_time)
                                logger.debug(
                                    f"{self.log_prefix} 更新用户 {person_id} 的消息段，消息时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg_time))}"
                                )
                                self.last_processed_message_time = max(self.last_processed_message_time, msg_time)
                    break

        # 1. 检查是否有用户达到关系构建条件（总消息数达到45条）
        users_to_build_relationship = []
        for person_id, segments in self.person_engaged_cache.items():
            total_message_count = self._get_total_message_count(person_id)
            if total_message_count >= 45:
                users_to_build_relationship.append(person_id)
                logger.info(
                    f"{self.log_prefix} 用户 {person_id} 满足关系构建条件，总消息数：{total_message_count}，消息段数：{len(segments)}"
                )
            elif total_message_count > 0:
                # 记录进度信息
                logger.debug(
                    f"{self.log_prefix} 用户 {person_id} 进度：{total_message_count}/45 条消息，{len(segments)} 个消息段"
                )

        # 2. 为满足条件的用户构建关系
        for person_id in users_to_build_relationship:
            segments = self.person_engaged_cache[person_id]
            # 异步执行关系构建
            asyncio.create_task(self.update_impression_on_segments(person_id, self.subheartflow_id, segments))
            # 移除已处理的用户缓存
            del self.person_engaged_cache[person_id]
            self._save_cache()

    async def relation_identify(
        self,
        observations: List[Observation] = None,
        action_type: str = None,
        action_data: dict = None,
    ):
        """
        从人物获取信息
        """

        chat_observe_info = ""
        current_time = time.time()
        if observations:
            for observation in observations:
                if isinstance(observation, ChattingObservation):
                    chat_observe_info = observation.get_observe_info()
                    # latest_message_time = observation.last_observe_time
                    # 从聊天观察中提取用户信息并更新消息段
                    # 获取最新的非bot消息来更新消息段
                    latest_messages = get_raw_msg_by_timestamp_with_chat(
                        self.subheartflow_id,
                        self.last_processed_message_time,
                        current_time,
                        limit=50,  # 获取自上次处理后的消息
                    )
                    if latest_messages:
                        # 处理所有新的非bot消息
                        for latest_msg in latest_messages:
                            user_id = latest_msg.get("user_id")
                            platform = latest_msg.get("user_platform") or latest_msg.get("chat_info_platform")
                            msg_time = latest_msg.get("time", 0)

                            if (
                                user_id
                                and platform
                                and user_id != global_config.bot.qq_account
                                and msg_time > self.last_processed_message_time
                            ):
                                from src.person_info.person_info import PersonInfoManager

                                person_id = PersonInfoManager.get_person_id(platform, user_id)
                                self._update_message_segments(person_id, msg_time)
                                logger.debug(
                                    f"{self.log_prefix} 更新用户 {person_id} 的消息段，消息时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg_time))}"
                                )
                                self.last_processed_message_time = max(self.last_processed_message_time, msg_time)
                    break

        for person_id in list(self.info_fetched_cache.keys()):
            for info_type in list(self.info_fetched_cache[person_id].keys()):
                self.info_fetched_cache[person_id][info_type]["ttl"] -= 1
                if self.info_fetched_cache[person_id][info_type]["ttl"] <= 0:
                    del self.info_fetched_cache[person_id][info_type]
            if not self.info_fetched_cache[person_id]:
                del self.info_fetched_cache[person_id]

        if action_type != "reply":
            return None

        target_message = action_data.get("reply_to", "")

        if ":" in target_message:
            parts = target_message.split(":", 1)
        elif "：" in target_message:
            parts = target_message.split("：", 1)
        else:
            logger.warning(f"reply_to格式不正确: {target_message}，跳过关系识别")
            return None

        if len(parts) != 2:
            logger.warning(f"reply_to格式不正确: {target_message}，跳过关系识别")
            return None

        sender = parts[0].strip()
        text = parts[1].strip()

        person_info_manager = get_person_info_manager()
        person_id = person_info_manager.get_person_id_by_person_name(sender)

        if not person_id:
            logger.warning(f"未找到用户 {sender} 的ID，跳过关系识别")
            return None

        nickname_str = ",".join(global_config.bot.alias_names)
        name_block = f"你的名字是{global_config.bot.nickname},你的昵称有{nickname_str}，有人也会用这些昵称称呼你。"

        info_cache_block = ""
        if self.info_fetching_cache:
            # 对于每个(person_id, info_type)组合，只保留最新的记录
            latest_records = {}
            for info_fetching in self.info_fetching_cache:
                key = (info_fetching["person_id"], info_fetching["info_type"])
                if key not in latest_records or info_fetching["start_time"] > latest_records[key]["start_time"]:
                    latest_records[key] = info_fetching

            # 按时间排序并生成显示文本
            sorted_records = sorted(latest_records.values(), key=lambda x: x["start_time"])
            for info_fetching in sorted_records:
                info_cache_block += (
                    f"你已经调取了[{info_fetching['person_name']}]的[{info_fetching['info_type']}]信息\n"
                )

        prompt = (await global_prompt_manager.get_prompt_async("relationship_prompt")).format(
            chat_observe_info=chat_observe_info,
            name_block=name_block,
            info_cache_block=info_cache_block,
            person_name=sender,
            target_message=text,
        )

        try:
            logger.info(f"{self.log_prefix} 人物信息prompt: \n{prompt}\n")
            content, _ = await self.llm_model.generate_response_async(prompt=prompt)
            if content:
                # print(f"content: {content}")
                content_json = json.loads(repair_json(content))

                # 检查是否返回了不需要查询的标志
                if "none" in content_json:
                    logger.info(f"{self.log_prefix} LLM判断当前不需要查询任何信息：{content_json.get('none', '')}")
                    # 跳过新的信息提取，但仍会处理已有缓存
                else:
                    info_type = content_json.get("info_type")
                    if info_type:
                        self.info_fetching_cache.append(
                            {
                                "person_id": person_id,
                                "person_name": sender,
                                "info_type": info_type,
                                "start_time": time.time(),
                                "forget": False,
                            }
                        )
                        if len(self.info_fetching_cache) > 20:
                            self.info_fetching_cache.pop(0)

                        logger.info(f"{self.log_prefix} 调取用户 {sender} 的[{info_type}]信息。")

                        # 执行信息提取
                        await self._fetch_single_info_instant(person_id, info_type, time.time())
                    else:
                        logger.warning(f"{self.log_prefix} LLM did not return a valid info_type. Response: {content}")

        except Exception as e:
            logger.error(f"{self.log_prefix} 执行LLM请求或处理响应时出错: {e}")
            logger.error(traceback.format_exc())

        # 7. 合并缓存和新处理的信息
        persons_infos_str = ""
        # 处理已获取到的信息
        if self.info_fetched_cache:
            persons_with_known_info = []  # 有已知信息的人员
            persons_with_unknown_info = []  # 有未知信息的人员

            for person_id in self.info_fetched_cache:
                person_known_infos = []
                person_unknown_infos = []
                person_name = ""

                for info_type in self.info_fetched_cache[person_id]:
                    person_name = self.info_fetched_cache[person_id][info_type]["person_name"]
                    if not self.info_fetched_cache[person_id][info_type]["unknow"]:
                        info_content = self.info_fetched_cache[person_id][info_type]["info"]
                        person_known_infos.append(f"[{info_type}]：{info_content}")
                    else:
                        person_unknown_infos.append(info_type)

                # 如果有已知信息，添加到已知信息列表
                if person_known_infos:
                    known_info_str = "；".join(person_known_infos) + "；"
                    persons_with_known_info.append((person_name, known_info_str))

                # 如果有未知信息，添加到未知信息列表
                if person_unknown_infos:
                    persons_with_unknown_info.append((person_name, person_unknown_infos))

            # 先输出有已知信息的人员
            for person_name, known_info_str in persons_with_known_info:
                persons_infos_str += f"你对 {person_name} 的了解：{known_info_str}\n"

            # 统一处理未知信息，避免重复的警告文本
            if persons_with_unknown_info:
                unknown_persons_details = []
                for person_name, unknown_types in persons_with_unknown_info:
                    unknown_types_str = "、".join(unknown_types)
                    unknown_persons_details.append(f"{person_name}的[{unknown_types_str}]")

                if len(unknown_persons_details) == 1:
                    persons_infos_str += (
                        f"你不了解{unknown_persons_details[0]}信息，不要胡乱回答，可以直接说不知道或忘记了；\n"
                    )
                else:
                    unknown_all_str = "、".join(unknown_persons_details)
                    persons_infos_str += f"你不了解{unknown_all_str}等信息，不要胡乱回答，可以直接说不知道或忘记了；\n"

        return persons_infos_str

    # ================================
    # 关系构建模块
    # 负责触发关系构建、整合消息段、更新用户印象
    # ================================

    async def update_impression_on_segments(self, person_id: str, chat_id: str, segments: List[Dict[str, any]]):
        """
        基于消息段更新用户印象

        Args:
            person_id: 用户ID
            chat_id: 聊天ID
            segments: 消息段列表
        """
        logger.debug(f"开始为 {person_id} 基于 {len(segments)} 个消息段更新印象")
        try:
            processed_messages = []

            for i, segment in enumerate(segments):
                start_time = segment["start_time"]
                end_time = segment["end_time"]
                segment["message_count"]
                start_date = time.strftime("%Y-%m-%d %H:%M", time.localtime(start_time))

                # 获取该段的消息（包含边界）
                segment_messages = get_raw_msg_by_timestamp_with_chat_inclusive(
                    self.subheartflow_id, start_time, end_time
                )
                logger.info(
                    f"消息段 {i + 1}: {start_date} - {time.strftime('%Y-%m-%d %H:%M', time.localtime(end_time))}, 消息数: {len(segment_messages)}"
                )

                if segment_messages:
                    # 如果不是第一个消息段，在消息列表前添加间隔标识
                    if i > 0:
                        # 创建一个特殊的间隔消息
                        gap_message = {
                            "time": start_time - 0.1,  # 稍微早于段开始时间
                            "user_id": "system",
                            "user_platform": "system",
                            "user_nickname": "系统",
                            "user_cardname": "",
                            "display_message": f"...（中间省略一些消息）{start_date} 之后的消息如下...",
                            "is_action_record": True,
                            "chat_info_platform": segment_messages[0].get("chat_info_platform", ""),
                            "chat_id": chat_id,
                        }
                        processed_messages.append(gap_message)

                    # 添加该段的所有消息
                    processed_messages.extend(segment_messages)

            if processed_messages:
                # 按时间排序所有消息（包括间隔标识）
                processed_messages.sort(key=lambda x: x["time"])

                logger.info(f"为 {person_id} 获取到总共 {len(processed_messages)} 条消息（包含间隔标识）用于印象更新")
                relationship_manager = get_relationship_manager()

                # 调用原有的更新方法
                await relationship_manager.update_person_impression(
                    person_id=person_id, timestamp=time.time(), bot_engaged_messages=processed_messages
                )
            else:
                logger.info(f"没有找到 {person_id} 的消息段对应的消息，不更新印象")

        except Exception as e:
            logger.error(f"为 {person_id} 更新印象时发生错误: {e}")
            logger.error(traceback.format_exc())

    # ================================
    # 信息调取模块
    # 负责实时分析对话需求、提取用户信息、管理信息缓存
    # ================================

    async def _fetch_single_info_instant(self, person_id: str, info_type: str, start_time: float):
        """
        使用小模型提取单个信息类型
        """
        person_info_manager = get_person_info_manager()

        # 首先检查 info_list 缓存
        info_list = await person_info_manager.get_value(person_id, "info_list") or []
        cached_info = None
        person_name = await person_info_manager.get_value(person_id, "person_name")

        # print(f"info_list: {info_list}")

        # 查找对应的 info_type
        for info_item in info_list:
            if info_item.get("info_type") == info_type:
                cached_info = info_item.get("info_content")
                logger.debug(f"{self.log_prefix} 在info_list中找到 {person_name} 的 {info_type} 信息: {cached_info}")
                break

        # 如果缓存中有信息，直接使用
        if cached_info:
            if person_id not in self.info_fetched_cache:
                self.info_fetched_cache[person_id] = {}

            self.info_fetched_cache[person_id][info_type] = {
                "info": cached_info,
                "ttl": 2,
                "start_time": start_time,
                "person_name": person_name,
                "unknow": cached_info == "none",
            }
            logger.info(f"{self.log_prefix} 记得 {person_name} 的 {info_type}: {cached_info}")
            return

        try:
            person_name = await person_info_manager.get_value(person_id, "person_name")
            person_impression = await person_info_manager.get_value(person_id, "impression")
            if person_impression:
                person_impression_block = (
                    f"<对{person_name}的总体了解>\n{person_impression}\n</对{person_name}的总体了解>"
                )
            else:
                person_impression_block = ""

            points = await person_info_manager.get_value(person_id, "points")
            if points:
                points_text = "\n".join([f"{point[2]}:{point[0]}" for point in points])
                points_text_block = f"<对{person_name}的近期了解>\n{points_text}\n</对{person_name}的近期了解>"
            else:
                points_text_block = ""

            if not points_text_block and not person_impression_block:
                if person_id not in self.info_fetched_cache:
                    self.info_fetched_cache[person_id] = {}
                self.info_fetched_cache[person_id][info_type] = {
                    "info": "none",
                    "ttl": 2,
                    "start_time": start_time,
                    "person_name": person_name,
                    "unknow": True,
                }
                logger.info(f"{self.log_prefix} 完全不认识 {person_name}")
                await self._save_info_to_cache(person_id, info_type, "none")
                return

            nickname_str = ",".join(global_config.bot.alias_names)
            name_block = f"你的名字是{global_config.bot.nickname},你的昵称有{nickname_str}，有人也会用这些昵称称呼你。"
            prompt = (await global_prompt_manager.get_prompt_async("fetch_person_info_prompt")).format(
                name_block=name_block,
                info_type=info_type,
                person_impression_block=person_impression_block,
                person_name=person_name,
                info_json_str=f'"{info_type}": "有关{info_type}的信息内容"',
                points_text_block=points_text_block,
            )
        except Exception:
            logger.error(traceback.format_exc())
            return

        try:
            # 使用小模型进行即时提取
            content, _ = await self.instant_llm_model.generate_response_async(prompt=prompt)

            if content:
                content_json = json.loads(repair_json(content))
                if info_type in content_json:
                    info_content = content_json[info_type]
                    is_unknown = info_content == "none" or not info_content

                    # 保存到运行时缓存
                    if person_id not in self.info_fetched_cache:
                        self.info_fetched_cache[person_id] = {}
                    self.info_fetched_cache[person_id][info_type] = {
                        "info": "unknow" if is_unknown else info_content,
                        "ttl": 3,
                        "start_time": start_time,
                        "person_name": person_name,
                        "unknow": is_unknown,
                    }

                    # 保存到持久化缓存 (info_list)
                    await self._save_info_to_cache(person_id, info_type, info_content if not is_unknown else "none")

                    if not is_unknown:
                        logger.info(f"{self.log_prefix} 思考得到，{person_name} 的 {info_type}: {content}")
                    else:
                        logger.info(f"{self.log_prefix} 思考了也不知道{person_name} 的 {info_type} 信息")
            else:
                logger.warning(f"{self.log_prefix} 小模型返回空结果，获取 {person_name} 的 {info_type} 信息失败。")
        except Exception as e:
            logger.error(f"{self.log_prefix} 执行小模型请求获取用户信息时出错: {e}")
            logger.error(traceback.format_exc())

    async def _save_info_to_cache(self, person_id: str, info_type: str, info_content: str):
        """
        将提取到的信息保存到 person_info 的 info_list 字段中

        Args:
            person_id: 用户ID
            info_type: 信息类型
            info_content: 信息内容
        """
        try:
            person_info_manager = get_person_info_manager()

            # 获取现有的 info_list
            info_list = await person_info_manager.get_value(person_id, "info_list") or []

            # 查找是否已存在相同 info_type 的记录
            found_index = -1
            for i, info_item in enumerate(info_list):
                if isinstance(info_item, dict) and info_item.get("info_type") == info_type:
                    found_index = i
                    break

            # 创建新的信息记录
            new_info_item = {
                "info_type": info_type,
                "info_content": info_content,
            }

            if found_index >= 0:
                # 更新现有记录
                info_list[found_index] = new_info_item
                logger.info(f"{self.log_prefix} [缓存更新] 更新 {person_id} 的 {info_type} 信息缓存")
            else:
                # 添加新记录
                info_list.append(new_info_item)
                logger.info(f"{self.log_prefix} [缓存保存] 新增 {person_id} 的 {info_type} 信息缓存")

            # 保存更新后的 info_list
            await person_info_manager.update_one_field(person_id, "info_list", info_list)

        except Exception as e:
            logger.error(f"{self.log_prefix} [缓存保存] 保存信息到缓存失败: {e}")
            logger.error(traceback.format_exc())


init_prompt()
