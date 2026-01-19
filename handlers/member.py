"""
新成員驗證處理模組
- 限制新成員發言權限
- 發送驗證按鈕
- 驗證成功恢復權限
- 超時未驗證自動踢出
"""

import logging
from datetime import datetime, timedelta

from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ChatMemberHandler,
    CallbackQueryHandler,
)
from telegram.error import TelegramError

from database.db import Database
import config

logger = logging.getLogger(__name__)

# 驗證按鈕回調數據前綴
VERIFY_CALLBACK_PREFIX = "verify_"


async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理新成員加入事件"""
    chat_member = update.chat_member
    if not chat_member:
        return

    # 檢查是否為新成員加入
    old_status = chat_member.old_chat_member.status
    new_status = chat_member.new_chat_member.status

    if old_status in ("left", "kicked") and new_status == "member":
        user = chat_member.new_chat_member.user
        chat = chat_member.chat

        # 忽略 Bot 自己
        if user.is_bot:
            return

        logger.info(f"New member joined: {user.id} ({user.username}) in chat {chat.id}")

        db: Database = context.bot_data.get("database")
        if not db:
            logger.error("Database not initialized")
            return

        # 取得群組設定
        chat_settings = await db.get_chat_settings(chat.id)
        verification_timeout = chat_settings.get(
            "verification_timeout", config.VERIFICATION_TIMEOUT
        )

        # 1. 限制新成員發言權限
        try:
            await chat.restrict_member(
                user_id=user.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                ),
            )
            logger.info(f"Restricted new member {user.id}")
        except TelegramError as e:
            logger.error(f"Failed to restrict member: {e}")
            return

        # 2. 發送驗證訊息
        user_mention = f"@{user.username}" if user.username else user.first_name
        timeout_minutes = verification_timeout // 60

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ 我不是機器人",
                    callback_data=f"{VERIFY_CALLBACK_PREFIX}{user.id}_{chat.id}",
                )
            ]
        ])

        try:
            verify_message = await chat.send_message(
                f"👋 歡迎 {user_mention} 加入！\n\n"
                f"請在 {timeout_minutes} 分鐘內點擊下方按鈕完成驗證，否則將被自動移出群組。",
                reply_markup=keyboard,
            )
            logger.info(f"Sent verification message for user {user.id}")
        except TelegramError as e:
            logger.error(f"Failed to send verification message: {e}")
            return

        # 3. 記錄待驗證狀態
        expires_at = datetime.now() + timedelta(seconds=verification_timeout)
        await db.add_pending_verification(
            user_id=user.id,
            chat_id=chat.id,
            message_id=verify_message.message_id,
            expires_at=expires_at,
        )

        # 4. 設定超時任務
        context.job_queue.run_once(
            verification_timeout_callback,
            when=verification_timeout,
            data={
                "user_id": user.id,
                "chat_id": chat.id,
                "message_id": verify_message.message_id,
            },
            name=f"verify_timeout_{user.id}_{chat.id}",
        )


async def handle_verification_button(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """處理驗證按鈕點擊"""
    query = update.callback_query

    if not query.data.startswith(VERIFY_CALLBACK_PREFIX):
        return

    # 解析回調數據
    try:
        data = query.data[len(VERIFY_CALLBACK_PREFIX):]
        user_id, chat_id = map(int, data.split("_"))
    except ValueError:
        await query.answer("驗證資料錯誤")
        return

    # 檢查是否為本人點擊
    if query.from_user.id != user_id:
        await query.answer("這不是你的驗證按鈕！", show_alert=True)
        return

    db: Database = context.bot_data.get("database")
    if not db:
        await query.answer("系統錯誤，請稍後再試")
        return

    # 檢查是否還在待驗證狀態
    pending = await db.get_pending_verification(user_id, chat_id)
    if not pending:
        await query.answer("驗證已過期或已完成")
        try:
            await query.message.delete()
        except TelegramError:
            pass
        return

    # 1. 恢復發言權限
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_invite_users=True,
                can_pin_messages=False,
                can_change_info=False,
            ),
        )
        logger.info(f"Restored permissions for user {user_id}")
    except TelegramError as e:
        logger.error(f"Failed to restore permissions: {e}")
        await query.answer("驗證失敗，請聯繫管理員")
        return

    # 2. 移除待驗證記錄
    await db.remove_pending_verification(user_id, chat_id)

    # 3. 取消超時任務
    job_name = f"verify_timeout_{user_id}_{chat_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    # 4. 更新驗證訊息
    await query.answer("驗證成功！歡迎加入！")
    try:
        user_mention = (
            f"@{query.from_user.username}"
            if query.from_user.username
            else query.from_user.first_name
        )
        await query.message.edit_text(f"✅ {user_mention} 驗證成功！歡迎加入群組！")
    except TelegramError as e:
        logger.error(f"Failed to edit verification message: {e}")

    logger.info(f"User {user_id} verified successfully in chat {chat_id}")


async def verification_timeout_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """驗證超時回調"""
    job = context.job
    data = job.data
    user_id = data["user_id"]
    chat_id = data["chat_id"]
    message_id = data["message_id"]

    db: Database = context.bot_data.get("database")
    if not db:
        return

    # 檢查是否還在待驗證狀態
    pending = await db.get_pending_verification(user_id, chat_id)
    if not pending:
        return

    logger.info(f"Verification timeout for user {user_id} in chat {chat_id}")

    # 1. 踢出用戶
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        # 立即解除封禁，允許重新加入
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
        logger.info(f"Kicked user {user_id} for verification timeout")
    except TelegramError as e:
        logger.error(f"Failed to kick user: {e}")

    # 2. 移除待驗證記錄
    await db.remove_pending_verification(user_id, chat_id)

    # 3. 更新驗證訊息
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="⏰ 驗證超時，用戶已被移出群組。",
        )
    except TelegramError as e:
        logger.error(f"Failed to edit timeout message: {e}")


async def check_expired_verifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    """定期檢查過期的驗證（備用機制）"""
    db: Database = context.bot_data.get("database")
    if not db:
        return

    expired = await db.get_expired_verifications()
    for record in expired:
        user_id = record["user_id"]
        chat_id = record["chat_id"]
        message_id = record.get("message_id")

        logger.info(f"Found expired verification for user {user_id} in chat {chat_id}")

        # 踢出用戶
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
        except TelegramError as e:
            logger.error(f"Failed to kick user {user_id}: {e}")

        # 更新訊息
        if message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="⏰ 驗證超時，用戶已被移出群組。",
                )
            except TelegramError:
                pass

    # 清除過期記錄
    await db.clear_expired_verifications()


def setup_member_handlers(application) -> None:
    """設定成員處理器"""
    # 監聽成員狀態變化
    application.add_handler(
        ChatMemberHandler(handle_new_member, ChatMemberHandler.CHAT_MEMBER)
    )

    # 監聽驗證按鈕點擊
    application.add_handler(
        CallbackQueryHandler(
            handle_verification_button,
            pattern=f"^{VERIFY_CALLBACK_PREFIX}",
        )
    )

    # 定期檢查過期驗證（每分鐘）
    application.job_queue.run_repeating(
        check_expired_verifications,
        interval=60,
        first=10,
        name="check_expired_verifications",
    )

    logger.info("Member handlers registered")
