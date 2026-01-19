# 🧹 SweepMonk 掃地僧

> 深藏不露的 Telegram 群組守護者 - 防廣告/詐騙 Bot

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-v20+-blue.svg)](https://core.telegram.org/bots/api)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

![SweepMonk Demo](https://img.shields.io/badge/Status-Active-success)

## ✨ 功能特色

### 🔍 智能關鍵字過濾
- 自動偵測並刪除包含敏感關鍵字的訊息
- 支援**正則表達式**匹配（如：`賺\d+萬`）
- 支援**繁簡體自動轉換**
- 內建 100+ 中英文廣告/詐騙關鍵字

### 👤 新成員驗證機制
- 新成員加入時自動限制發言權限
- 點擊按鈕驗證後恢復權限
- 超時未驗證自動踢出（預設 5 分鐘）

### ⚡ 違規自動處理
- 偵測違規 → 立即刪除訊息
- 自動禁言用戶（預設 24 小時）
- 通知管理員並記錄日誌

### 🛠 管理員指令

| 指令 | 功能 |
|------|------|
| `/ping` | 測試 Bot 是否正常運作 |
| `/help` | 顯示幫助訊息 |
| `/stats` | 查看統計資料 |
| `/addkeyword <詞>` | 新增敏感關鍵字 |
| `/delkeyword <詞>` | 刪除敏感關鍵字 |
| `/listkeywords` | 列出所有關鍵字 |
| `/reload` | 重新載入關鍵字列表 |
| `/unmute <用戶ID>` | 解除禁言（或回覆訊息） |
| `/setmutetime <秒>` | 設定禁言時長 |

## 🚀 快速開始

### 方法一：本地運行

```bash
# 1. Clone 專案
git clone https://github.com/zohan724/SweepMonk.git
cd SweepMonk

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設定環境變數
export BOT_TOKEN="你的Bot Token"

# 4. 啟動 Bot
python bot.py
```

### 方法二：部署到 Fly.io（推薦）

```bash
# 1. 安裝 Fly CLI
brew install flyctl  # macOS
# 或 curl -L https://fly.io/install.sh | sh  # Linux

# 2. 登入 Fly.io
fly auth login

# 3. 建立並部署
fly launch --no-deploy
fly secrets set BOT_TOKEN="你的Bot Token"
fly deploy
```

## ⚙️ 設定說明

### 取得 Bot Token

1. 在 Telegram 找到 [@BotFather](https://t.me/BotFather)
2. 發送 `/newbot` 並按照指示創建
3. 複製取得的 Token

### 設定 Bot 權限

在 @BotFather 中設定：
```
/mybots → 選擇你的 Bot → Bot Settings → Group Privacy → Turn off
```

### 加入群組

1. 將 Bot 加入群組
2. **設為管理員**，並授予以下權限：
   - ✅ 刪除訊息
   - ✅ 封禁用戶
   - ✅ 限制成員

## 📝 自訂關鍵字

### 編輯 keywords.txt

```txt
# 一般關鍵字（每行一個）
投資
賺錢
passive income

# 正則表達式（以 regex: 開頭）
regex:賺\d+萬
regex:earn.{0,10}\$\d+
```

修改後使用 `/reload` 重新載入。

### 使用指令新增

```
/addkeyword 新關鍵字
/delkeyword 舊關鍵字
```

## 📁 專案結構

```
SweepMonk/
├── bot.py              # 主程式入口
├── config.py           # 配置檔
├── handlers/
│   ├── admin.py        # 管理員指令
│   ├── member.py       # 新成員驗證
│   └── message.py      # 訊息過濾
├── filters/
│   └── spam_filter.py  # 關鍵字過濾邏輯
├── database/
│   └── db.py           # SQLite 資料庫
├── keywords.txt        # 敏感關鍵字列表
├── Dockerfile          # Docker 配置
├── fly.toml            # Fly.io 配置
└── requirements.txt    # 依賴套件
```

## 🔧 環境變數

| 變數 | 說明 | 必填 |
|------|------|------|
| `BOT_TOKEN` | Telegram Bot Token | ✅ |
| `LOG_LEVEL` | 日誌等級 (DEBUG/INFO/WARNING/ERROR) | ❌ |

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

MIT License - 自由使用、修改、分發

## 💡 靈感來源

名稱「掃地僧」來自金庸小說《天龍八部》中的神秘高手，外表低調做著清掃工作，實則武功蓋世。就像這個 Bot，默默守護群組，清除廣告垃圾。

---

**Made with ❤️ for Telegram communities**
