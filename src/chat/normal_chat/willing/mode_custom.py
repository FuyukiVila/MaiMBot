from .mode_dynamic import DynamicWillingManager


class CustomWillingManager(DynamicWillingManager):
    async def get_reply_probability(self, message_id):
        willing_info = self.ongoing_messages[message_id]
        group_info = willing_info.message.message_info.group_info
        if not group_info:
            if willing_info.is_mentioned_bot:
                return 1.0
            elif not willing_info.is_emoji:
                return 0.75
            else:
                return 0.1
        return await super().get_reply_probability(message_id)
