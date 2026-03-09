# backend/app/schemas/ai.py

from pydantic import BaseModel, Field
from enum import Enum

# 定義八大卡牌類別
class CardRecommendation(str, Enum):
    DAILY_VIBE = "Daily Vibe (日常共感)"
    SOUL_DIVE = "Soul Dive (靈魂深潛)"
    SAFE_ZONE = "Safe Zone (安全氣囊)"
    AFTER_DARK = "After Dark (深夜模式)"
    CO_PILOT = "Co-Pilot (最佳副駕)"
    LOVE_BLUEPRINT = "Love Blueprint (愛情藍圖)"
    MEMORY_LANE = "Memory Lane (時光機)"
    GROWTH_QUEST = "Growth Quest (共同成長)"

# 定義我們期望 AI 回傳的 JSON 結構
class JournalAnalysis(BaseModel):
    # --- 情緒概況 ---
    mood_label: str = Field(
        ..., 
        description="數個可以完整形容日記內容的情緒標籤，必須精準且包含 Emoji (e.g., 🌧️ 失落, 😤 憤怒, 🎉 開心, 🌿 平靜)."
    )
    
    # --- 核心心理分析 (EFT) ---
    emotional_needs: str = Field(
        ..., 
        description=(
            "無論情緒好壞，請分析背後的依附需求。嚴禁留白。"
            "負面時：翻譯表層憤怒為『渴望被重視、害怕失去連結』。"
            "正面時：翻譯快樂為『渴望分享、希望被見證、期待與你同步這份喜悅』。"
        )
    )

    # --- 給使用者的建議 (NVC & CBT) ---
    advice_for_user: str = Field(
        ..., 
        description="給使用者的心理調節建議。若心情好，建議如何保存這份快樂；若心情不好，建議如何自我安撫。"
    )
    action_for_user: str = Field(
        ..., 
        description="給使用者一個具體、微小且立即能做的行動 (Micro-action)。"
    )

    # --- 給伴侶的建議 (Systemic Therapy) ---
    advice_for_partner: str = Field(
        ...,
        description=(
            "這段話會『直接顯示在伴侶的手機上』。嚴禁留白。"
            "若使用者心情好：請教導伴侶如何『積極回應 (Active Constructive Responding)』，放大對方的快樂。"
            "若使用者心情差：請教導伴侶如何『同理與安撫』。"
            "若 safety_tier >= 2：建議給予空間並尋求專業協助。"
        )
    )
    action_for_partner: str = Field(
        ..., 
        description="給伴侶的具體行動指令。請具體、友善且具操作性 (e.g., 給予擁抱、問他電影哪裡好看、說一句肯定他的話)。"
    )

    # --- 互動推薦 ---
    card_recommendation: CardRecommendation = Field(
        ...,
        description="根據當下情緒與關係狀態，推薦最適合現在兩人進行的一種卡牌互動模式。"
    )

    # --- 安全機制 (0-3) ---
    safety_tier: int = Field(
        ...,
        ge=0,
        le=3,
        description=(
            "安全分級判定："
            "0=Normal (一般情緒抒發/快樂分享), "
            "1=Elevated (高壓力/情緒激動), "
            "2=Self-harm/Crisis (自傷意念/重度憂鬱 -> 需顯示求助資訊), "
            "3=Violence/Abuse (家暴/肢體威脅 -> 需啟動緊急保護流程)."
        )
    )