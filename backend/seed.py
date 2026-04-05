# backend/seed.py
# ruff: noqa: E402

import sys
import os
from sqlmodel import Session, select, create_engine
from app.models.card import Card, CardCategory
from app.core.config import settings

# 讓這個 script 找得到 app 模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 建立資料庫連線
engine = create_engine(settings.DATABASE_URL)

# 30 張黃金測試卡片 (由 Gemini AI 生成)
INITIAL_CARDS = [
    # 1. Daily Vibe (日常共感)
    {
        "category": CardCategory.DAILY_VIBE,
        "title": "今日能量",
        "description": "用一個比喻來形容今天的狀態。",
        "question": "如果把你今天的狀態形容成一種天氣，那是晴天、陰天還是暴風雨？為什麼？",
        "difficulty_level": 1,
        "depth_level": 1,
    },
    {
        "category": CardCategory.DAILY_VIBE,
        "title": "微小的快樂",
        "description": "生活中的小確幸往往最能治癒人心。",
        "question": "今天發生了哪件小事（無論多小），讓你稍微嘴角上揚了一下？",
        "difficulty_level": 1,
        "depth_level": 1,
    },
    {
        "category": CardCategory.DAILY_VIBE,
        "title": "壓力釋放",
        "description": "說出來，肩膀會輕一點。",
        "question": "此時此刻，你腦中佔用最多記憶體（最煩心）的一件事是什麼？",
        "difficulty_level": 2,
        "depth_level": 2,
    },
    {
        "category": CardCategory.DAILY_VIBE,
        "title": "餐桌話題",
        "description": "關於味覺的記憶。",
        "question": "如果今晚我們可以瞬間移動去吃任何餐廳，你想吃什麼？",
        "difficulty_level": 1,
        "depth_level": 1,
    },
    {
        "category": CardCategory.DAILY_VIBE,
        "title": "睡前感恩",
        "description": "帶著正念結束這一天。",
        "question": "請說出一個你今天想感謝對方的地方（即使是幫忙倒杯水）。",
        "difficulty_level": 2,
        "depth_level": 2
    },
    {
        "category": CardCategory.DAILY_VIBE,
        "title": "收心儀式",
        "description": "在一天結束前，留下更靠近彼此的時刻。",
        "question": "今晚睡前，你想跟我一起做的「收心儀式」是什麼？（例：擁抱、分享三件事、一起規劃明天）",
        "difficulty_level": 3,
        "depth_level": 3
    },
    {
        "category": CardCategory.DAILY_VIBE,
        "title": "如果今天可以重來",
        "description": "回頭看看今天，也讓彼此更理解當下的需要。",
        "question": "如果今天可以重來一次，你最想改變的 1 件事是什麼？我能怎麼協助？",
        "difficulty_level": 3,
        "depth_level": 3
    },

    # 2. Soul Dive (靈魂深潛)
    {
        "category": CardCategory.SOUL_DIVE,
        "title": "核心恐懼",
        "description": "面對脆弱，才能連結彼此。",
        "question": "在我們這段關係中，你內心深處最害怕發生的一件事是什麼？",
        "difficulty_level": 3
    },
    {
        "category": CardCategory.SOUL_DIVE,
        "title": "被愛的感覺",
        "description": "每個人接收愛的方式都不同。",
        "question": "回想一下，上一次你強烈感覺到「我被深深愛著」，是什麼時候？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.SOUL_DIVE,
        "title": "未來的我",
        "description": "關於個人成長的想像。",
        "question": "如果不考慮金錢和現實，三年後的你，理想中的生活狀態是什麼樣子？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.SOUL_DIVE,
        "title": "遺憾清單",
        "description": "有些話沒說出口，就變成了石頭。",
        "question": "有沒有哪一次吵架或事件，你其實心裡很抱歉，但一直沒有機會好好說出口？",
        "difficulty_level": 3
    },
    {
        "category": CardCategory.SOUL_DIVE,
        "title": "價值觀排序",
        "description": "理解對方的優先級。",
        "question": "事業、家庭、健康、夢想。請將這四項依照你目前的真實心境排序，並告訴我為什麼。",
        "difficulty_level": 2
    },

    # 3. Safe Zone (安全屋)
    {
        "category": CardCategory.SAFE_ZONE,
        "title": "爭吵模式",
        "description": "覺察我們的互動慣性。",
        "question": "當我們意見不合時，你希望我如何回應？（例如：先安靜聽、給擁抱、還是理性分析？）",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.SAFE_ZONE,
        "title": "情緒按鈕",
        "description": "避開彼此的地雷區。",
        "question": "我有沒有哪個無心的口頭禪或小動作，其實每次都會讓你感到不舒服？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.SAFE_ZONE,
        "title": "修復時刻",
        "description": "和好的藝術。",
        "question": "當你在生氣時，我做什麼事情最能讓你「瞬間軟化」？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.SAFE_ZONE,
        "title": "安全感來源",
        "description": "建立信任的基石。",
        "question": "我可以多做哪一件具體的小事，會讓你覺得更有安全感？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.SAFE_ZONE,
        "title": "傾聽練習",
        "description": "不帶評判的接納。",
        "question": "最近有沒有什麼話是你一直想跟我發牢騷，但怕我覺得你煩而不敢說的？",
        "difficulty_level": 2
    },

    # 4. Memory Lane (時光機)
    {
        "category": CardCategory.MEMORY_LANE,
        "title": "初次心動",
        "description": "回到最初的起點。",
        "question": "你還記得第一次對我產生「好感」或「心動」的那個瞬間嗎？當時發生了什麼？",
        "difficulty_level": 1
    },
    {
        "category": CardCategory.MEMORY_LANE,
        "title": "最棒的旅行",
        "description": "共同創造的巔峰體驗。",
        "question": "在我們去過的所有地方裡，你覺得最快樂、最無憂無慮的一次回憶是哪裡？",
        "difficulty_level": 1
    },
    {
        "category": CardCategory.MEMORY_LANE,
        "title": "艱難時刻",
        "description": "患難見真情。",
        "question": "回顧過去，你覺得我們一起度過最艱難的挑戰是什麼？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.MEMORY_LANE,
        "title": "第一印象",
        "description": "打破濾鏡。",
        "question": "剛認識時，你對我的第一印象跟現在最大的反差是什麼？",
        "difficulty_level": 1
    },
    {
        "category": CardCategory.MEMORY_LANE,
        "title": "傻瓜時刻",
        "description": "一起犯傻也是浪漫。",
        "question": "我們一起做過最愚蠢、最荒謬，但想起來會大笑的事情是什麼？",
        "difficulty_level": 1
    },

    # 5. Growth Quest (共同成長)
    {
        "category": CardCategory.GROWTH_QUEST,
        "title": "彼此的教練",
        "description": "互相激勵。",
        "question": "你覺得我身上最大的優點或潛力是什麼？你希望我如何發揮它？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.GROWTH_QUEST,
        "title": "新技能解鎖",
        "description": "一起學習新事物。",
        "question": "如果我們今年要一起學習一項新技能（例如：衝浪、法文、陶藝），你想學什麼？",
        "difficulty_level": 1
    },
    {
        "category": CardCategory.GROWTH_QUEST,
        "title": "財務目標",
        "description": "務實的未來規劃。",
        "question": "對於我們共同的財務狀況，你目前最想達成的一個具體目標是什麼？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.GROWTH_QUEST,
        "title": "生活習慣",
        "description": "微小的改變。",
        "question": "為了健康，你希望我們兩個可以一起戒掉或是培養哪一個習慣？",
        "difficulty_level": 1
    },
    {
        "category": CardCategory.GROWTH_QUEST,
        "title": "夢想支持者",
        "description": "成為彼此的後盾。",
        "question": "最近你在追求的目標中，哪裡最需要我的支持或協助？",
        "difficulty_level": 2
    },

    # 6. After Dark (深夜話題 - P2, 但先放著)
    {
        "category": CardCategory.AFTER_DARK,
        "title": "神秘幻想",
        "description": "探索未知的領域。",
        "question": "有沒有哪個場景或情境，是你曾經幻想過但還沒嘗試過的？",
        "difficulty_level": 3
    },
    {
        "category": CardCategory.AFTER_DARK,
        "title": "敏感地帶",
        "description": "身體的地圖。",
        "question": "我不經意的哪個觸摸動作，最容易讓你「有感覺」？",
        "difficulty_level": 3
    },
    {
        "category": CardCategory.AFTER_DARK,
        "title": "完美夜晚",
        "description": "定義浪漫。",
        "question": "描述一下你心中「完美的親密夜晚」包含哪些元素？（音樂？燈光？流程？）",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.AFTER_DARK,
        "title": "吸引力法則",
        "description": "找回火花。",
        "question": "你覺得我什麼時候（穿什麼、做什麼動作）看起來最性感？",
        "difficulty_level": 2
    },
    {
        "category": CardCategory.AFTER_DARK,
        "title": "禁忌邊緣",
        "description": "說出真心話。",
        "question": "在親密關係中，有什麼是你一直想嘗試，但怕我無法接受的？",
        "difficulty_level": 3
    },
]

def seed_data():
    with Session(engine) as session:
        # 1. 檢查是否已經有資料，避免重複寫入
        existing_cards = session.exec(select(Card)).first()
        if existing_cards:
            print("⚠️  資料庫中已有卡片資料，跳過初始化 (Skipped)。")
            print("💡  提示：若想重置，請先清空 cards 表格。")
            return

        print(f"🌱 開始寫入 {len(INITIAL_CARDS)} 張種子卡片...")
        
        for card_data in INITIAL_CARDS:
            card = Card(**card_data)
            session.add(card)
        
        session.commit()
        print("✅ 成功！30 張卡片已植入資料庫！ (Seed Complete)")

if __name__ == "__main__":
    seed_data()
