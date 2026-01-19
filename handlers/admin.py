"""
管理員指令處理模組
"""

import logging
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError

from filters.spam_filter import SpamFilter
from database.db import Database
import config

logger = logging.getLogger(__name__)


async def is_admin(update: Update) -> bool:
    """檢查用戶是否為管理員"""
    if update.effective_chat.type == "private":
        return True

    # 檢查是否以頻道身分發送（頻道連結的討論群）
    if update.message and update.message.sender_chat:
        sender_chat = update.message.sender_chat
        # 如果是以頻道身分發送，且頻道是群組的連結頻道，視為管理員
        if sender_chat.type == "channel":
            return True
        # 如果是以群組匿名管理員身分發送
        if sender_chat.id == update.effective_chat.id:
            return True

    # 一般用戶檢查
    if update.effective_user:
        try:
            member = await update.effective_chat.get_member(update.effective_user.id)
            return member.status in ("administrator", "creator")
        except TelegramError:
            return False

    return False


async def admin_required(update: Update) -> bool:
    """管理員權限檢查裝飾器輔助函數"""
    if not await is_admin(update):
        await update.message.reply_text("⛔ 此指令僅限管理員使用\nThis command is for admins only")
        return False
    return True


async def cmd_addkeyword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """新增敏感關鍵字"""
    if not await admin_required(update):
        return

    if not context.args:
        await update.message.reply_text("用法 Usage: /addkeyword <關鍵字 keyword>")
        return

    keyword = " ".join(context.args)
    spam_filter: SpamFilter = context.bot_data.get("spam_filter")

    if not spam_filter:
        await update.message.reply_text("❌ 系統錯誤 / System error")
        return

    if spam_filter.add_keyword(keyword):
        await update.message.reply_text(f"✅ 已新增關鍵字 / Keyword added: {keyword}")
        logger.info(f"Admin {update.effective_user.id} added keyword: {keyword}")
    else:
        await update.message.reply_text(f"⚠️ 關鍵字已存在 / Keyword already exists: {keyword}")


async def cmd_delkeyword(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """刪除敏感關鍵字"""
    if not await admin_required(update):
        return

    if not context.args:
        await update.message.reply_text("用法 Usage: /delkeyword <關鍵字 keyword>")
        return

    keyword = " ".join(context.args)
    spam_filter: SpamFilter = context.bot_data.get("spam_filter")

    if not spam_filter:
        await update.message.reply_text("❌ 系統錯誤 / System error")
        return

    if spam_filter.remove_keyword(keyword):
        await update.message.reply_text(f"✅ 已刪除關鍵字 / Keyword deleted: {keyword}")
        logger.info(f"Admin {update.effective_user.id} removed keyword: {keyword}")
    else:
        await update.message.reply_text(f"⚠️ 關鍵字不存在 / Keyword not found: {keyword}")


async def cmd_listkeywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """列出所有關鍵字"""
    if not await admin_required(update):
        return

    spam_filter: SpamFilter = context.bot_data.get("spam_filter")

    if not spam_filter:
        await update.message.reply_text("❌ 系統錯誤 / System error")
        return

    keywords = spam_filter.get_keywords()

    if not keywords:
        await update.message.reply_text("📝 目前沒有設定任何關鍵字\nNo keywords configured")
        return

    # 分頁顯示（每頁 50 個）
    page_size = 50
    total_pages = (len(keywords) + page_size - 1) // page_size

    # 取得頁碼參數
    page = 1
    if context.args:
        try:
            page = max(1, min(int(context.args[0]), total_pages))
        except ValueError:
            pass

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_keywords = keywords[start_idx:end_idx]

    message = f"📝 關鍵字列表 / Keyword List (第 {page}/{total_pages} 頁，共 {len(keywords)} 個)\n\n"
    message += "\n".join(f"• {kw}" for kw in page_keywords)

    if total_pages > 1:
        message += f"\n\n使用 /listkeywords <頁碼> 查看其他頁\nUse /listkeywords <page> to view other pages"

    await update.message.reply_text(message)


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """解除用戶禁言"""
    if not await admin_required(update):
        return

    # 支援回覆訊息或指定用戶 ID
    target_user_id = None

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("用法 Usage: /unmute <用戶ID user_id> 或回覆該用戶的訊息\nor reply to user's message")
            return
    else:
        await update.message.reply_text("用法: /unmute <用戶ID> 或回覆該用戶的訊息")
        return

    try:
        await update.effective_chat.restrict_member(
            user_id=target_user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_invite_users=True,
            ),
        )
        await update.message.reply_text(f"✅ 已解除用戶 {target_user_id} 的禁言\nUser {target_user_id} unmuted")
        logger.info(f"Admin {update.effective_user.id} unmuted user {target_user_id}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ 解除禁言失敗 / Unmute failed: {e}")
        logger.error(f"Failed to unmute user {target_user_id}: {e}")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """查看統計資料"""
    if not await admin_required(update):
        return

    db: Database = context.bot_data.get("database")

    if not db:
        await update.message.reply_text("❌ 系統錯誤 / System error")
        return

    chat_id = update.effective_chat.id if update.effective_chat.type != "private" else None
    stats = await db.get_stats(chat_id)

    message = "📊 統計資料 / Statistics\n\n"

    if chat_id:
        message += f"📍 本群組統計 / This Group:\n"
    else:
        message += f"🌐 全域統計 / Global:\n"

    message += f"• 總違規次數 Total violations: {stats['total_violations']}\n"
    message += f"• 今日違規 Today: {stats['today_violations']}\n"
    message += f"• 記錄用戶數 Users: {stats['total_users']}\n"
    message += f"• 待驗證成員 Pending: {stats['pending_verifications']}\n"

    # 取得最近違規記錄
    if chat_id:
        recent = await db.get_recent_violations(chat_id, limit=5)
        if recent:
            message += f"\n📋 最近違規記錄 / Recent Violations:\n"
            for v in recent:
                username = v.get("username") or v.get("first_name") or str(v["user_id"])
                keyword = v["matched_keyword"][:20]
                message += f"• {username}: {keyword}\n"

    await update.message.reply_text(message)


async def cmd_setmutetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """設定禁言時長"""
    if not await admin_required(update):
        return

    if not context.args:
        await update.message.reply_text(
            "用法 Usage: /setmutetime <秒數 seconds>\n"
            "例如 Example: /setmutetime 3600 (1小時 1hr)\n"
            "             /setmutetime 86400 (24小時 24hr)"
        )
        return

    try:
        seconds = int(context.args[0])
        if seconds < 60:
            await update.message.reply_text("⚠️ 禁言時長至少為 60 秒\nMute duration must be at least 60 seconds")
            return
        if seconds > 31536000:  # 1 年
            await update.message.reply_text("⚠️ 禁言時長不能超過 1 年\nMute duration cannot exceed 1 year")
            return
    except ValueError:
        await update.message.reply_text("❌ 請輸入有效的秒數\nPlease enter a valid number")
        return

    db: Database = context.bot_data.get("database")
    if not db:
        await update.message.reply_text("❌ 系統錯誤 / System error")
        return

    chat_id = update.effective_chat.id
    await db.update_chat_settings(chat_id, mute_duration=seconds)

    hours = seconds / 3600
    await update.message.reply_text(f"✅ 禁言時長已設定為 {seconds} 秒 ({hours:.1f} 小時)\nMute duration set to {seconds}s ({hours:.1f}h)")
    logger.info(f"Admin {update.effective_user.id} set mute time to {seconds}s in chat {chat_id}")


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """重新載入關鍵字列表"""
    if not await admin_required(update):
        return

    spam_filter: SpamFilter = context.bot_data.get("spam_filter")

    if not spam_filter:
        await update.message.reply_text("❌ 系統錯誤 / System error")
        return

    spam_filter.load_keywords()
    keywords = spam_filter.get_keywords()
    regex_count = len(spam_filter.regex_patterns)

    await update.message.reply_text(
        f"✅ 關鍵字列表已重新載入 / Keywords reloaded\n"
        f"• 一般關鍵字 Keywords: {len(keywords)}\n"
        f"• 正則表達式 Regex: {regex_count}"
    )
    logger.info(f"Admin {update.effective_user.id} reloaded keywords")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """顯示幫助訊息"""
    help_text = """
🧹 SweepMonk 掃地僧 - Group Guardian

📝 關鍵字管理 Keyword Management:
• /addkeyword <詞> - 新增關鍵字 Add keyword
• /delkeyword <詞> - 刪除關鍵字 Delete keyword
• /listkeywords - 列出關鍵字 List keywords
• /reload - 重新載入 Reload keywords

👤 用戶管理 User Management:
• /unmute <ID> - 解除禁言 Unmute user

⚙️ 設定 Settings:
• /setmutetime <秒> - 設定禁言時長 Set mute duration

📊 其他 Other:
• /stats - 查看統計 View statistics
• /help - 顯示幫助 Show help

💡 提示 Tips:
• 僅限管理員 Admin only
• Bot 需要管理員權限 Bot needs admin rights
"""
    await update.message.reply_text(help_text)


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """測試指令"""
    print(f"[DEBUG] ping received from {update.effective_user.id}", flush=True)
    await update.message.reply_text("🏓 Pong! Bot 運作正常 / Bot is running")


def setup_admin_handlers(application) -> None:
    """設定管理員指令處理器"""
    handlers = [
        CommandHandler("ping", cmd_ping),
        CommandHandler("addkeyword", cmd_addkeyword),
        CommandHandler("delkeyword", cmd_delkeyword),
        CommandHandler("listkeywords", cmd_listkeywords),
        CommandHandler("unmute", cmd_unmute),
        CommandHandler("stats", cmd_stats),
        CommandHandler("setmutetime", cmd_setmutetime),
        CommandHandler("reload", cmd_reload),
        CommandHandler("help", cmd_help),
        CommandHandler("start", cmd_help),
    ]

    for handler in handlers:
        application.add_handler(handler)

    logger.info("Admin handlers registered")
