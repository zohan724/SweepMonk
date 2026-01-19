"""
Telegram Bot 配置檔
"""
import os

# Bot 名稱
BOT_NAME = "SweepMonk"

# Telegram Bot Token (優先從環境變數讀取，部署用)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# 資料庫檔案路徑
DATABASE_PATH = "bot_data.db"

# 關鍵字檔案路徑
KEYWORDS_FILE = "keywords.txt"

# 預設設定
DEFAULT_MUTE_DURATION = 24 * 60 * 60  # 禁言時長：24 小時（秒）
VERIFICATION_TIMEOUT = 5 * 60  # 驗證超時：5 分鐘（秒）

# 是否通知管理員違規訊息
NOTIFY_ADMINS = True

# 日誌設定
LOG_LEVEL = "INFO"
