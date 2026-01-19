"""
訊息處理模組
監聽所有訊息並進行關鍵字過濾
"""

import logging
from datetime import datetime, timedelta

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.error import TelegramError

from filters.spam_filter import SpamFilter
from database.db import Database
import config

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理所有文字訊息"""
    message = update.message
    if not message or not message.text:
        return

    # 忽略私聊訊息
    if message.chat.type == "private":
        return

    # 忽略管理員訊息
    user = message.from_user
    try:
        member = await message.chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            return
    except TelegramError as e:
        logger.error(f"Failed to get member status: {e}")
        # 無法確認身份時，為安全起見不處理該訊息
        return

    # 取得過濾器和資料庫
    spam_filter: SpamFilter = context.bot_data.get("spam_filter")
    db: Database = context.bot_data.get("database")

    if not spam_filter or not db:
        logger.error("Spam filter or database not initialized")
        return

    # 檢查訊息是否為垃圾訊息
    matched_keyword = spam_filter.check_message(message.text)

    if matched_keyword:
        logger.info(
            f"Spam detected from user {user.id} ({user.username}): keyword='{matched_keyword}'"
        )

        # 取得群組設定
        chat_settings = await db.get_chat_settings(message.chat_id)
        mute_duration = chat_settings.get("mute_duration", config.DEFAULT_MUTE_DURATION)

        # 1. 刪除訊息
        try:
            await message.delete()
            logger.info(f"Deleted spam message from user {user.id}")
        except TelegramError as e:
            logger.error(f"Failed to delete message: {e}")

        # 2. 禁言用戶
        try:
            until_date = datetime.now() + timedelta(seconds=mute_duration)
            await message.chat.restrict_member(
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
            logger.info(f"Muted user {user.id} for {mute_duration} seconds")
        except TelegramError as e:
            logger.error(f"Failed to mute user: {e}")

        # 3. 記錄到資料庫
        await db.get_or_create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        await db.increment_violation_count(user.id)
        await db.add_violation(
            user_id=user.id,
            chat_id=message.chat_id,
            message_text=message.text[:500],  # 只保存前 500 字
            matched_keyword=matched_keyword,
            action_taken=f"deleted, muted for {mute_duration}s",
        )

        # 4. 通知管理員（可選）
        if chat_settings.get("notify_admins", config.NOTIFY_ADMINS):
            try:
                user_mention = f"@{user.username}" if user.username else user.first_name
                hours = mute_duration // 3600
                notification = (
                    f"⚠️ 偵測到違規訊息 / Violation Detected\n\n"
                    f"用戶 User: {user_mention} (ID: {user.id})\n"
                    f"關鍵字 Keyword: {matched_keyword}\n"
                    f"處理 Action: 刪除訊息，禁言 {hours} 小時 / Deleted, muted {hours}h"
                )
                await message.chat.send_message(notification)
            except TelegramError as e:
                logger.error(f"Failed to send admin notification: {e}")


def setup_message_handlers(application) -> None:
    """設定訊息處理器"""
    # 監聽所有文字訊息（群組和超級群組），排除指令
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            handle_message,
        )
    )
    logger.info("Message handlers registered")
