#!/usr/bin/env python3
"""
SweepMonk 掃地僧 - Telegram 防廣告/詐騙 Bot
主程式入口
"""

import logging
import asyncio
import sys
from pathlib import Path

from telegram.ext import Application

import config
from filters.spam_filter import SpamFilter
from database.db import Database
from handlers import setup_message_handlers, setup_member_handlers, setup_admin_handlers

# 設定日誌
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL),
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Bot 初始化後的設定"""
    # 初始化資料庫
    db = Database(config.DATABASE_PATH)
    await db.connect()
    application.bot_data["database"] = db

    # 初始化垃圾訊息過濾器
    keywords_path = Path(__file__).parent / config.KEYWORDS_FILE
    spam_filter = SpamFilter(str(keywords_path))
    application.bot_data["spam_filter"] = spam_filter

    logger.info("Bot initialized successfully")


async def post_shutdown(application: Application) -> None:
    """Bot 關閉時的清理"""
    db: Database = application.bot_data.get("database")
    if db:
        await db.close()
    logger.info("Bot shutdown complete")


def main() -> None:
    """主程式"""
    # 檢查 Token
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("請在 config.py 中設定您的 Bot Token!")
        logger.error("您可以從 @BotFather 取得 Token")
        sys.exit(1)

    # 建立 Application
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # 註冊 handlers
    setup_message_handlers(application)
    setup_member_handlers(application)
    setup_admin_handlers(application)

    # 啟動 Bot
    logger.info(f"Starting {config.BOT_NAME} (掃地僧)...")
    application.run_polling(
        allowed_updates=[
            "message",
            "callback_query",
            "chat_member",
        ],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
