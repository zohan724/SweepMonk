"""
資料庫操作模組
使用 SQLite + aiosqlite 進行異步操作
"""

import aiosqlite
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    """異步資料庫操作類別"""

    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = Path(db_path)
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """建立資料庫連接"""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info(f"Database connected: {self.db_path}")

    async def close(self) -> None:
        """關閉資料庫連接"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    async def _create_tables(self) -> None:
        """建立資料表"""
        async with self._connection.cursor() as cursor:
            # 用戶記錄表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    violation_count INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 違規記錄表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_text TEXT,
                    matched_keyword TEXT,
                    action_taken TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # 群組設定表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_settings (
                    chat_id INTEGER PRIMARY KEY,
                    chat_title TEXT,
                    mute_duration INTEGER DEFAULT 86400,
                    verification_timeout INTEGER DEFAULT 300,
                    notify_admins INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 待驗證成員表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    UNIQUE(user_id, chat_id)
                )
            """)

            await self._connection.commit()
            logger.info("Database tables created/verified")

    # === 用戶相關操作 ===

    async def get_or_create_user(
        self, user_id: int, username: str = None, first_name: str = None, last_name: str = None
    ) -> dict:
        """取得或建立用戶記錄"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()

            if row:
                return dict(row)

            await cursor.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, username, first_name, last_name),
            )
            await self._connection.commit()

            return {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "violation_count": 0,
                "is_banned": 0,
            }

    async def increment_violation_count(self, user_id: int) -> int:
        """增加用戶違規次數"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE users
                SET violation_count = violation_count + 1, updated_at = ?
                WHERE user_id = ?
                """,
                (datetime.now(), user_id),
            )
            await self._connection.commit()

            await cursor.execute("SELECT violation_count FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row["violation_count"] if row else 0

    # === 違規記錄相關操作 ===

    async def add_violation(
        self,
        user_id: int,
        chat_id: int,
        message_text: str,
        matched_keyword: str,
        action_taken: str,
    ) -> int:
        """新增違規記錄"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO violations (user_id, chat_id, message_text, matched_keyword, action_taken)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, chat_id, message_text, matched_keyword, action_taken),
            )
            await self._connection.commit()
            return cursor.lastrowid

    async def get_violations_count(self, user_id: int = None, chat_id: int = None) -> int:
        """取得違規記錄數量"""
        query = "SELECT COUNT(*) as count FROM violations WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if chat_id:
            query += " AND chat_id = ?"
            params.append(chat_id)

        async with self._connection.cursor() as cursor:
            await cursor.execute(query, params)
            row = await cursor.fetchone()
            return row["count"]

    async def get_recent_violations(self, chat_id: int, limit: int = 10) -> list[dict]:
        """取得最近的違規記錄"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT v.*, u.username, u.first_name
                FROM violations v
                LEFT JOIN users u ON v.user_id = u.user_id
                WHERE v.chat_id = ?
                ORDER BY v.created_at DESC
                LIMIT ?
                """,
                (chat_id, limit),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # === 群組設定相關操作 ===

    async def get_chat_settings(self, chat_id: int) -> dict:
        """取得群組設定"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
            row = await cursor.fetchone()

            if row:
                return dict(row)

            # 使用預設值建立記錄
            await cursor.execute(
                """
                INSERT INTO chat_settings (chat_id)
                VALUES (?)
                """,
                (chat_id,),
            )
            await self._connection.commit()

            return {
                "chat_id": chat_id,
                "mute_duration": 86400,
                "verification_timeout": 300,
                "notify_admins": 1,
            }

    async def update_chat_settings(self, chat_id: int, **kwargs) -> None:
        """更新群組設定"""
        if not kwargs:
            return

        set_clause = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values()) + [datetime.now(), chat_id]

        async with self._connection.cursor() as cursor:
            await cursor.execute(
                f"""
                UPDATE chat_settings
                SET {set_clause}, updated_at = ?
                WHERE chat_id = ?
                """,
                values,
            )
            await self._connection.commit()

    # === 待驗證成員相關操作 ===

    async def add_pending_verification(
        self, user_id: int, chat_id: int, message_id: int, expires_at: datetime
    ) -> None:
        """新增待驗證成員"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT OR REPLACE INTO pending_verifications (user_id, chat_id, message_id, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, chat_id, message_id, expires_at),
            )
            await self._connection.commit()

    async def get_pending_verification(self, user_id: int, chat_id: int) -> Optional[dict]:
        """取得待驗證記錄"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT * FROM pending_verifications
                WHERE user_id = ? AND chat_id = ?
                """,
                (user_id, chat_id),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def remove_pending_verification(self, user_id: int, chat_id: int) -> bool:
        """移除待驗證記錄"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                DELETE FROM pending_verifications
                WHERE user_id = ? AND chat_id = ?
                """,
                (user_id, chat_id),
            )
            await self._connection.commit()
            return cursor.rowcount > 0

    async def get_expired_verifications(self) -> list[dict]:
        """取得所有過期的驗證"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT * FROM pending_verifications
                WHERE expires_at < ?
                """,
                (datetime.now(),),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def clear_expired_verifications(self) -> int:
        """清除過期的驗證記錄"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                DELETE FROM pending_verifications
                WHERE expires_at < ?
                """,
                (datetime.now(),),
            )
            await self._connection.commit()
            return cursor.rowcount

    # === 統計相關操作 ===

    async def get_stats(self, chat_id: int = None) -> dict:
        """取得統計資料"""
        stats = {}

        async with self._connection.cursor() as cursor:
            # 總違規次數
            if chat_id:
                await cursor.execute(
                    "SELECT COUNT(*) as count FROM violations WHERE chat_id = ?", (chat_id,)
                )
            else:
                await cursor.execute("SELECT COUNT(*) as count FROM violations")
            row = await cursor.fetchone()
            stats["total_violations"] = row["count"]

            # 今日違規次數
            today = datetime.now().strftime("%Y-%m-%d")
            if chat_id:
                await cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM violations
                    WHERE chat_id = ? AND DATE(created_at) = ?
                    """,
                    (chat_id, today),
                )
            else:
                await cursor.execute(
                    "SELECT COUNT(*) as count FROM violations WHERE DATE(created_at) = ?",
                    (today,),
                )
            row = await cursor.fetchone()
            stats["today_violations"] = row["count"]

            # 總用戶數
            await cursor.execute("SELECT COUNT(*) as count FROM users")
            row = await cursor.fetchone()
            stats["total_users"] = row["count"]

            # 待驗證人數
            if chat_id:
                await cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM pending_verifications
                    WHERE chat_id = ? AND expires_at > ?
                    """,
                    (chat_id, datetime.now()),
                )
            else:
                await cursor.execute(
                    "SELECT COUNT(*) as count FROM pending_verifications WHERE expires_at > ?",
                    (datetime.now(),),
                )
            row = await cursor.fetchone()
            stats["pending_verifications"] = row["count"]

        return stats
