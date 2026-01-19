"""
關鍵字過濾邏輯
支援：
- 精確匹配
- 正則表達式匹配
- 繁簡體轉換
"""

import re
import logging
from pathlib import Path
from typing import Optional

try:
    from opencc import OpenCC
    HAS_OPENCC = True
except ImportError:
    HAS_OPENCC = False

logger = logging.getLogger(__name__)


class SpamFilter:
    """垃圾訊息過濾器"""

    def __init__(self, keywords_file: str = "keywords.txt"):
        self.keywords_file = Path(keywords_file)
        self.keywords: set[str] = set()
        self.regex_patterns: list[re.Pattern] = []

        # 繁簡轉換器
        if HAS_OPENCC:
            self.t2s = OpenCC('t2s')  # 繁體轉簡體
            self.s2t = OpenCC('s2t')  # 簡體轉繁體
        else:
            self.t2s = None
            self.s2t = None
            logger.warning("OpenCC not installed, traditional/simplified conversion disabled")

        self.load_keywords()

    def load_keywords(self) -> None:
        """從檔案載入關鍵字"""
        self.keywords.clear()
        self.regex_patterns.clear()

        if not self.keywords_file.exists():
            logger.warning(f"Keywords file not found: {self.keywords_file}")
            return

        with open(self.keywords_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # 檢查是否為正則表達式（以 regex: 開頭）
                if line.startswith("regex:"):
                    pattern = line[6:].strip()
                    try:
                        self.regex_patterns.append(re.compile(pattern, re.IGNORECASE))
                        logger.debug(f"Added regex pattern: {pattern}")
                    except re.error as e:
                        logger.error(f"Invalid regex pattern '{pattern}': {e}")
                else:
                    # 一般關鍵字
                    self.keywords.add(line.lower())
                    logger.debug(f"Added keyword: {line}")

        logger.info(f"Loaded {len(self.keywords)} keywords and {len(self.regex_patterns)} regex patterns")

    def add_keyword(self, keyword: str) -> bool:
        """新增關鍵字"""
        keyword_lower = keyword.lower().strip()
        if keyword_lower in self.keywords:
            return False

        self.keywords.add(keyword_lower)

        # 寫入檔案
        with open(self.keywords_file, "a", encoding="utf-8") as f:
            f.write(f"\n{keyword}")

        logger.info(f"Added keyword: {keyword}")
        return True

    def remove_keyword(self, keyword: str) -> bool:
        """刪除關鍵字"""
        keyword_lower = keyword.lower().strip()
        if keyword_lower not in self.keywords:
            return False

        self.keywords.discard(keyword_lower)

        # 重寫檔案
        self._save_keywords()

        logger.info(f"Removed keyword: {keyword}")
        return True

    def _save_keywords(self) -> None:
        """將關鍵字寫入檔案"""
        with open(self.keywords_file, "w", encoding="utf-8") as f:
            f.write("# 敏感關鍵字列表\n")
            f.write("# 每行一個關鍵字，以 # 開頭的行為註解\n")
            f.write("# 正則表達式以 regex: 開頭\n\n")

            # 先寫入正則表達式
            for pattern in self.regex_patterns:
                f.write(f"regex:{pattern.pattern}\n")

            # 再寫入一般關鍵字
            for keyword in sorted(self.keywords):
                f.write(f"{keyword}\n")

    def get_keywords(self) -> list[str]:
        """取得所有關鍵字"""
        return sorted(list(self.keywords))

    def _normalize_text(self, text: str) -> list[str]:
        """
        正規化文字，回傳多個變體以供比對
        包含：原始文字、簡體、繁體
        """
        variants = [text.lower()]

        if self.t2s and self.s2t:
            # 轉換為簡體
            simplified = self.t2s.convert(text).lower()
            if simplified not in variants:
                variants.append(simplified)

            # 轉換為繁體
            traditional = self.s2t.convert(text).lower()
            if traditional not in variants:
                variants.append(traditional)

        return variants

    def check_message(self, text: str) -> Optional[str]:
        """
        檢查訊息是否包含敏感關鍵字

        Args:
            text: 要檢查的訊息文字

        Returns:
            如果找到敏感關鍵字，回傳該關鍵字；否則回傳 None
        """
        if not text:
            return None

        # 取得文字變體
        text_variants = self._normalize_text(text)

        # 檢查一般關鍵字
        for variant in text_variants:
            for keyword in self.keywords:
                if keyword in variant:
                    return keyword

        # 檢查正則表達式
        for pattern in self.regex_patterns:
            for variant in text_variants:
                if pattern.search(variant):
                    return f"regex:{pattern.pattern}"

        return None

    def is_spam(self, text: str) -> bool:
        """檢查訊息是否為垃圾訊息"""
        return self.check_message(text) is not None
