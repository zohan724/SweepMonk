# SweepMonk 掃地僧

> 🧹 深藏不露的群組守護者 - Telegram 防廣告/詐騙 Bot

保護您的 Telegram 群組免受廣告和詐騙訊息的騷擾。

## 功能特色

### 1. 關鍵字過濾系統
- 自動偵測並刪除包含敏感關鍵字的訊息
- 支援正則表達式匹配（如：`賺\d+萬`）
- 支援繁簡體轉換
- 預設包含常見廣告/詐騙關鍵字

### 2. 新成員驗證機制
- 新成員加入時自動限制發言權限
- 發送驗證按鈕，點擊後恢復權限
- 超時未驗證自動踢出（預設 5 分鐘）

### 3. 違規處理
- 偵測到違規訊息立即刪除
- 自動禁言用戶（預設 24 小時）
- 通知群組管理員
- 記錄違規日誌

### 4. 管理員指令
| 指令 | 功能 |
|------|------|
| `/addkeyword <詞>` | 新增敏感關鍵字 |
| `/delkeyword <詞>` | 刪除敏感關鍵字 |
| `/listkeywords` | 列出所有關鍵字 |
| `/unmute <用戶ID>` | 解除禁言（或回覆訊息） |
| `/stats` | 查看統計資料 |
| `/setmutetime <秒>` | 設定禁言時長 |
| `/reload` | 重新載入關鍵字列表 |
| `/help` | 顯示幫助訊息 |

## 安裝步驟

### 1. 環境需求
- Python 3.11 或更高版本

### 2. 安裝依賴
```bash
cd /Users/zohan/Desktop/TGbot
pip install -r requirements.txt
```

### 3. 設定 Bot Token
1. 在 Telegram 中找到 [@BotFather](https://t.me/BotFather)
2. 發送 `/newbot` 創建新 Bot
3. 複製取得的 Token
4. 編輯 `config.py`，將 `BOT_TOKEN` 設定為您的 Token：
```python
BOT_TOKEN = "your_bot_token_here"
```

### 4. 啟動 Bot
```bash
python bot.py
```

## 群組設定

### 將 Bot 加入群組
1. 在 Telegram 中搜尋您的 Bot
2. 點擊「Add to Group」將 Bot 加入群組
3. **重要**: 將 Bot 設為群組管理員，並授予以下權限：
   - 刪除訊息
   - 封禁用戶
   - 限制成員

### 啟用成員加入通知
為了讓新成員驗證功能正常運作，需要在群組設定中：
1. 進入群組設定
2. 啟用「Chat History for New Members」

## 自訂關鍵字

### 方法一：編輯 keywords.txt
直接編輯 `keywords.txt` 檔案，每行一個關鍵字：
```
# 這是註解
投資
賺錢
regex:賺\d+萬
```

編輯後使用 `/reload` 指令重新載入。

### 方法二：使用指令
在群組中使用管理員指令：
```
/addkeyword 新關鍵字
/delkeyword 舊關鍵字
```

## 正則表達式

關鍵字支援正則表達式，以 `regex:` 開頭：
```
regex:賺\d+萬      # 匹配「賺1萬」「賺100萬」等
regex:加.{0,2}LINE  # 匹配「加LINE」「加我LINE」等
```

## 設定說明

在 `config.py` 中可以調整以下設定：

| 設定項 | 說明 | 預設值 |
|--------|------|--------|
| `DEFAULT_MUTE_DURATION` | 禁言時長（秒） | 86400 (24小時) |
| `VERIFICATION_TIMEOUT` | 驗證超時（秒） | 300 (5分鐘) |
| `NOTIFY_ADMINS` | 是否通知管理員 | True |
| `LOG_LEVEL` | 日誌等級 | INFO |

## 專案結構
```
TGbot/
├── bot.py              # 主程式入口
├── config.py           # 配置檔
├── handlers/
│   ├── __init__.py
│   ├── message.py      # 訊息處理
│   ├── member.py       # 新成員驗證
│   └── admin.py        # 管理員指令
├── filters/
│   ├── __init__.py
│   └── spam_filter.py  # 關鍵字過濾
├── database/
│   ├── __init__.py
│   └── db.py           # 資料庫操作
├── keywords.txt        # 敏感關鍵字列表
├── requirements.txt    # 依賴套件
└── README.md           # 使用說明
```

## 常見問題

### Bot 無法刪除訊息？
確認 Bot 已被設為群組管理員，並有「刪除訊息」權限。

### 新成員驗證不起作用？
1. 確認 Bot 有「限制成員」權限
2. 確認群組已啟用「Chat History for New Members」

### 關鍵字沒有生效？
使用 `/reload` 重新載入關鍵字列表。

## 授權條款
MIT License
