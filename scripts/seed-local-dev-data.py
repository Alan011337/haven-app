#!/usr/bin/env python3
# ruff: noqa: E402
"""Seed local-dev Postgres with representative data for localhost development.

Usage:
    # Via local-dev-db.sh (recommended — inherits correct DATABASE_URL):
    bash scripts/local-dev-db.sh seed

    # Standalone (requires DATABASE_URL pointing at local Postgres):
    cd backend && PYTHONUTF8=1 PYTHONPATH=. python ../scripts/seed-local-dev-data.py

    # Reset first, then seed:
    bash scripts/local-dev-db.sh seed --reset

Safety:
    - Idempotent: skips if seed users already exist.
    - Refuses to run against Supabase pooler URLs (production safety).
    - All data is synthetic / lorem-style. No real PII.
"""

from __future__ import annotations

import sys
import os
import uuid
from datetime import date, datetime, timedelta, timezone

# Ensure backend package is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

from sqlmodel import Session, select, create_engine
from app.core.config import settings
from app.core.security import get_password_hash

# ---------------------------------------------------------------------------
# Safety: refuse to run against remote Supabase
# ---------------------------------------------------------------------------
_db_url = settings.DATABASE_URL or ""
if "pooler.supabase.com" in _db_url.lower():
    print("[seed] ABORT: DATABASE_URL points at Supabase pooler.")
    print("[seed] This script is for local-dev Postgres only.")
    print("[seed] Start via: bash scripts/local-dev-db.sh seed")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Deterministic UUIDs (stable across re-runs for idempotency)
# ---------------------------------------------------------------------------
ALICE_ID = uuid.UUID("a0000000-0000-4000-8000-000000000001")
BOB_ID   = uuid.UUID("b0000000-0000-4000-8000-000000000002")

ALICE_EMAIL = "alice@example.com"
BOB_EMAIL   = "bob@example.com"
DEV_PASSWORD = "havendev1"  # Shared dev password — localhost only

# ---------------------------------------------------------------------------
# Import models (side-effect: registers SQLModel tables)
# ---------------------------------------------------------------------------
from app.models.user import User
from app.models.card import Card, CardCategory
from app.models.journal import Journal
from app.models.card_response import CardResponse, ResponseStatus
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus
from app.models.daily_sync import DailySync
from app.models.appreciation import Appreciation
from app.models.user_streak_summary import UserStreakSummary
from app.models.billing import BillingEntitlementState
from app.models.user_onboarding_consent import UserOnboardingConsent
from app.models.consent_receipt import ConsentReceipt
from app.models.journal_attachment import JournalAttachment
from app.models.relationship_baseline import RelationshipBaseline
from app.models.couple_goal import CoupleGoal
from app.models.love_map_note import LoveMapNote
from app.models.wishlist_item import WishlistItem

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_engine(settings.DATABASE_URL)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _days_ago(n: int) -> datetime:
    return _utcnow() - timedelta(days=n)


# =========================================================================
# 1. Seed Users
# =========================================================================
def seed_users(session: Session) -> tuple[User, User]:
    alice = session.get(User, ALICE_ID)
    bob = session.get(User, BOB_ID)

    if alice and bob:
        print("[seed] users: Alice and Bob already exist — skipping")
        return alice, bob

    now = _utcnow()
    hashed = get_password_hash(DEV_PASSWORD)

    if not alice:
        alice = User(
            id=ALICE_ID,
            email=ALICE_EMAIL,
            hashed_password=hashed,
            full_name="Alice Chen",
            is_active=True,
            partner_id=BOB_ID,
            savings_score=42,
            terms_accepted_at=now,
            birth_year=1995,
        )
        session.add(alice)

    if not bob:
        bob = User(
            id=BOB_ID,
            email=BOB_EMAIL,
            hashed_password=hashed,
            full_name="Bob Lin",
            is_active=True,
            partner_id=ALICE_ID,
            savings_score=38,
            terms_accepted_at=now,
            birth_year=1994,
        )
        session.add(bob)

    session.commit()
    session.refresh(alice)
    session.refresh(bob)
    print(f"[seed] users: created Alice ({ALICE_EMAIL}) and Bob ({BOB_EMAIL})")
    print(f"[seed] users: password for both = '{DEV_PASSWORD}'")
    return alice, bob


# =========================================================================
# 2. Seed Cards (30 golden test cards from backend/seed.py pattern)
# =========================================================================
SEED_CARDS = [
    # DAILY_VIBE (7) — depth: 3×d1, 2×d2, 2×d3
    {"category": CardCategory.DAILY_VIBE, "title": "今日能量", "description": "用一個比喻來形容今天的狀態。", "question": "如果把你今天的狀態形容成一種天氣，那是晴天、陰天還是暴風雨？為什麼？", "difficulty_level": 1, "depth_level": 1},
    {"category": CardCategory.DAILY_VIBE, "title": "微小的快樂", "description": "生活中的小確幸往往最能治癒人心。", "question": "今天發生了哪件小事讓你稍微嘴角上揚了一下？", "difficulty_level": 1, "depth_level": 1},
    {"category": CardCategory.DAILY_VIBE, "title": "壓力釋放", "description": "說出來，肩膀會輕一點。", "question": "此時此刻，你腦中佔用最多記憶體的一件事是什麼？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.DAILY_VIBE, "title": "餐桌話題", "description": "關於味覺的記憶。", "question": "如果今晚我們可以瞬間移動去吃任何餐廳，你想吃什麼？", "difficulty_level": 1, "depth_level": 1},
    {"category": CardCategory.DAILY_VIBE, "title": "睡前感恩", "description": "帶著正念結束這一天。", "question": "請說出一個你今天想感謝對方的地方。", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.DAILY_VIBE, "title": "收心儀式", "description": "在一天結束前，留下更靠近彼此的時刻。", "question": "今晚睡前，你想跟我一起做的「收心儀式」是什麼？（例：擁抱、分享三件事、一起規劃明天）", "difficulty_level": 3, "depth_level": 3},
    {"category": CardCategory.DAILY_VIBE, "title": "如果今天可以重來", "description": "回頭看看今天，也讓彼此更理解當下的需要。", "question": "如果今天可以重來一次，你最想改變的 1 件事是什麼？我能怎麼協助？", "difficulty_level": 3, "depth_level": 3},
    # SOUL_DIVE (5) — depth: 3×d2, 2×d3
    {"category": CardCategory.SOUL_DIVE, "title": "核心恐懼", "description": "面對脆弱，才能連結彼此。", "question": "在我們這段關係中，你內心深處最害怕發生的一件事是什麼？", "difficulty_level": 3, "depth_level": 3},
    {"category": CardCategory.SOUL_DIVE, "title": "被愛的感覺", "description": "每個人接收愛的方式都不同。", "question": "上一次你強烈感覺到「我被深深愛著」，是什麼時候？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.SOUL_DIVE, "title": "未來的我", "description": "關於個人成長的想像。", "question": "如果不考慮金錢和現實，三年後的你理想中的生活狀態是什麼樣子？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.SOUL_DIVE, "title": "遺憾清單", "description": "有些話沒說出口，就變成了石頭。", "question": "有沒有哪一次吵架或事件，你其實心裡很抱歉，但一直沒有機會好好說出口？", "difficulty_level": 3, "depth_level": 3},
    {"category": CardCategory.SOUL_DIVE, "title": "價值觀排序", "description": "理解對方的優先級。", "question": "事業、家庭、健康、夢想。請將這四項依照你目前的真實心境排序。", "difficulty_level": 2, "depth_level": 2},
    # SAFE_ZONE (5) — depth: 1×d1, 3×d2, 1×d3
    {"category": CardCategory.SAFE_ZONE, "title": "爭吵模式", "description": "覺察我們的互動慣性。", "question": "當我們意見不合時，你希望我如何回應？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.SAFE_ZONE, "title": "情緒按鈕", "description": "避開彼此的地雷區。", "question": "我有沒有哪個無心的口頭禪或小動作，其實每次都會讓你感到不舒服？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.SAFE_ZONE, "title": "修復時刻", "description": "和好的藝術。", "question": "當你在生氣時，我做什麼事情最能讓你瞬間軟化？", "difficulty_level": 2, "depth_level": 1},
    {"category": CardCategory.SAFE_ZONE, "title": "安全感來源", "description": "建立信任的基石。", "question": "我可以多做哪一件具體的小事，會讓你覺得更有安全感？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.SAFE_ZONE, "title": "傾聽練習", "description": "不帶評判的接納。", "question": "最近有沒有什麼話是你一直想跟我發牢騷，但怕我覺得你煩而不敢說的？", "difficulty_level": 2, "depth_level": 3},
    # MEMORY_LANE (5) — depth: 4×d1, 1×d2
    {"category": CardCategory.MEMORY_LANE, "title": "初次心動", "description": "回到最初的起點。", "question": "你還記得第一次對我產生心動的那個瞬間嗎？當時發生了什麼？", "difficulty_level": 1, "depth_level": 1},
    {"category": CardCategory.MEMORY_LANE, "title": "最棒的旅行", "description": "共同創造的巔峰體驗。", "question": "在我們去過的所有地方裡，你覺得最快樂的一次回憶是哪裡？", "difficulty_level": 1, "depth_level": 1},
    {"category": CardCategory.MEMORY_LANE, "title": "艱難時刻", "description": "患難見真情。", "question": "回顧過去，你覺得我們一起度過最艱難的挑戰是什麼？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.MEMORY_LANE, "title": "第一印象", "description": "打破濾鏡。", "question": "剛認識時，你對我的第一印象跟現在最大的反差是什麼？", "difficulty_level": 1, "depth_level": 1},
    {"category": CardCategory.MEMORY_LANE, "title": "傻瓜時刻", "description": "一起犯傻也是浪漫。", "question": "我們一起做過最愚蠢、最荒謬，但想起來會大笑的事情是什麼？", "difficulty_level": 1, "depth_level": 1},
    # GROWTH_QUEST (5) — depth: 2×d1, 3×d2
    {"category": CardCategory.GROWTH_QUEST, "title": "彼此的教練", "description": "互相激勵。", "question": "你覺得我身上最大的優點或潛力是什麼？你希望我如何發揮它？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.GROWTH_QUEST, "title": "新技能解鎖", "description": "一起學習新事物。", "question": "如果我們今年要一起學習一項新技能，你想學什麼？", "difficulty_level": 1, "depth_level": 1},
    {"category": CardCategory.GROWTH_QUEST, "title": "財務目標", "description": "務實的未來規劃。", "question": "對於我們共同的財務狀況，你目前最想達成的一個具體目標是什麼？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.GROWTH_QUEST, "title": "生活習慣", "description": "微小的改變。", "question": "為了健康，你希望我們兩個可以一起培養哪一個習慣？", "difficulty_level": 1, "depth_level": 1},
    {"category": CardCategory.GROWTH_QUEST, "title": "夢想支持者", "description": "成為彼此的後盾。", "question": "最近你在追求的目標中，哪裡最需要我的支持或協助？", "difficulty_level": 2, "depth_level": 2},
    # AFTER_DARK (5) — depth: 1×d1, 1×d2, 3×d3
    {"category": CardCategory.AFTER_DARK, "title": "神秘幻想", "description": "探索未知的領域。", "question": "有沒有哪個場景或情境，是你曾經幻想過但還沒嘗試過的？", "difficulty_level": 3, "depth_level": 3},
    {"category": CardCategory.AFTER_DARK, "title": "敏感地帶", "description": "身體的地圖。", "question": "我不經意的哪個觸摸動作，最容易讓你有感覺？", "difficulty_level": 3, "depth_level": 3},
    {"category": CardCategory.AFTER_DARK, "title": "完美夜晚", "description": "定義浪漫。", "question": "描述一下你心中完美的親密夜晚包含哪些元素？", "difficulty_level": 2, "depth_level": 2},
    {"category": CardCategory.AFTER_DARK, "title": "吸引力法則", "description": "找回火花。", "question": "你覺得我什麼時候看起來最性感？", "difficulty_level": 2, "depth_level": 1},
    {"category": CardCategory.AFTER_DARK, "title": "禁忌邊緣", "description": "說出真心話。", "question": "在親密關係中，有什麼是你一直想嘗試，但怕我無法接受的？", "difficulty_level": 3, "depth_level": 3},
]

# Deterministic card UUIDs based on index
def _card_uuid(i: int) -> uuid.UUID:
    return uuid.UUID(f"c0000000-0000-4000-8000-{i:012d}")


def seed_cards(session: Session) -> list[Card]:
    existing = session.exec(select(Card).limit(1)).first()
    if existing:
        print("[seed] cards: cards already exist — skipping")
        cards = list(session.exec(select(Card)).all())
        return cards

    cards = []
    for i, data in enumerate(SEED_CARDS):
        card = Card(id=_card_uuid(i), **data)
        session.add(card)
        cards.append(card)
    session.commit()
    print(f"[seed] cards: seeded {len(cards)} golden test cards")
    return cards


# =========================================================================
# 3. Seed Journals
# =========================================================================
JOURNAL_ENTRIES = [
    # Alice's journals
    {"user_id": ALICE_ID, "days_ago": 7, "content": "今天跟 Bob 去了那家新開的拉麵店。湯頭很濃郁，他點了辣味的，我點了原味。吃完之後我們在河邊散步，聊了很多最近工作上的壓力。覺得能有一個人願意聽我抱怨，真的很幸福。", "mood": "grateful"},
    {"user_id": ALICE_ID, "days_ago": 5, "content": "工作上遇到一個很棘手的 bug，debug 了一整天都沒有頭緒。回到家之後 Bob 幫我泡了一杯熱可可，雖然問題還沒解決，但心情好多了。明天再戰！", "mood": "tired"},
    {"user_id": ALICE_ID, "days_ago": 3, "content": "今天是我們在一起的第 500 天紀念日！Bob 偷偷準備了一束花和一張手寫卡片。卡片上寫著「謝謝你願意陪我一起長大」，看到的瞬間眼眶就紅了。我們約好以後每個一百天都要慶祝一下。", "mood": "happy"},
    {"user_id": ALICE_ID, "days_ago": 1, "content": "跟 Bob 因為家事分工的問題小吵了一架。冷靜下來之後，我覺得自己太急了，應該好好溝通而不是指責。晚上主動跟他道歉，他也說了他的想法。吵架不可怕，可怕的是不願意面對。", "mood": "reflective"},
    # Bob's journals
    {"user_id": BOB_ID, "days_ago": 6, "content": "Alice 最近工作壓力很大，我能感覺到她回家的時候整個人都很緊繃。今天特意早下班去買了她最喜歡的草莓蛋糕，看到她吃的時候露出的笑容，覺得一切都值得了。", "mood": "caring"},
    {"user_id": BOB_ID, "days_ago": 4, "content": "今天在公司的專案獲得了主管的讚賞，第一個想分享的人就是 Alice。打電話跟她說的時候，她比我還開心，一直說「我就知道你可以的！」。有人無條件相信你的感覺真好。", "mood": "proud"},
    {"user_id": BOB_ID, "days_ago": 2, "content": "週末兩個人窩在家裡看了一整天的電影。從早到晚吃了三包爆米花，看了四部片。雖然什麼特別的事都沒做，但這種平凡的幸福才是最珍貴的吧。", "mood": "content"},
    {"user_id": BOB_ID, "days_ago": 0, "content": "今天跟 Alice 討論了明年的旅行計畫。她想去日本看櫻花，我想去冰島看極光。最後決定兩個都去！開始存旅費的動力瞬間就來了。有共同目標的感覺真的很棒。", "mood": "excited"},
]

def _journal_uuid(i: int) -> uuid.UUID:
    return uuid.UUID(f"d0000000-0000-4000-8000-{i:012d}")


def seed_journals(session: Session) -> list[Journal]:
    existing = session.exec(select(Journal).limit(1)).first()
    if existing:
        print("[seed] journals: journals already exist — skipping")
        return list(session.exec(select(Journal)).all())

    journals = []
    for i, entry in enumerate(JOURNAL_ENTRIES):
        j = Journal(
            id=_journal_uuid(i),
            user_id=entry["user_id"],
            content=entry["content"],
            mood=entry["mood"],
            visibility="PARTNER_TRANSLATED_ONLY",
            content_format="markdown",
            partner_translation_status="NOT_REQUESTED",
            is_draft=False,
            created_at=_days_ago(entry["days_ago"]),
            updated_at=_days_ago(entry["days_ago"]),
        )
        session.add(j)
        journals.append(j)
    session.commit()
    print(f"[seed] journals: seeded {len(journals)} journal entries (4 Alice, 4 Bob)")
    return journals


# =========================================================================
# 4. Seed Card Sessions + Responses
# =========================================================================
def _session_uuid(i: int) -> uuid.UUID:
    return uuid.UUID(f"e0000000-0000-4000-8000-{i:012d}")


def _response_uuid(i: int) -> uuid.UUID:
    return uuid.UUID(f"f0000000-0000-4000-8000-{i:012d}")


CARD_RESPONSE_TEXTS = [
    ("今天是暴風雨，工作太忙了。但跟你在一起就像雨後的彩虹。", "我覺得是陰天轉晴，早上有點低落，但下午收到你的訊息就好多了。"),
    ("想去京都吃那家百年蕎麥麵！你上次說想再去的那家。", "我想吃泰式料理！曼谷那種路邊攤的 pad thai。"),
    ("謝謝你昨天幫我整理書桌，雖然你嘴上說很煩，但我知道你是心甘情願的。", "謝謝你每天早上幫我準備咖啡，雖然有時候太淡了，但心意我都收到了。"),
]


def seed_card_sessions(session: Session, cards: list[Card]) -> None:
    existing = session.exec(select(CardSession).limit(1)).first()
    if existing:
        print("[seed] card_sessions: already exist — skipping")
        return

    if len(cards) < 3:
        print("[seed] card_sessions: not enough cards — skipping")
        return

    # Insert sessions first, then commit, then responses (FK constraint)
    session_objs = []
    # 3 DAILY_RITUAL sessions (days 7, 6, 5 ago)
    for i, (alice_text, bob_text) in enumerate(CARD_RESPONSE_TEXTS):
        card = cards[i]
        cs = CardSession(
            id=_session_uuid(i),
            creator_id=ALICE_ID,
            partner_id=BOB_ID,
            card_id=card.id,
            category=card.category.value if hasattr(card.category, 'value') else str(card.category),
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.COMPLETED,
            created_at=_days_ago(7 - i),
        )
        session.add(cs)
        session_objs.append((i, cs, alice_text, bob_text))

    # 2 DECK mode sessions (days 4, 3 ago) — ensures Memory shows both modes
    deck_responses = [
        ("如果可以有一個超能力，我想要讀心術，這樣就能知道你在想什麼。", "我想要時間暫停，這樣我們在一起的時光就能更長。"),
        ("最讓我感動的是你記得我隨口說過想吃的東西，然後默默買回來。", "你生病的時候堅持要幫我煮飯那次，雖然味道普通但我哭了。"),
    ]
    deck_offset = len(CARD_RESPONSE_TEXTS)
    for j, (alice_text, bob_text) in enumerate(deck_responses):
        card = cards[(deck_offset + j) % len(cards)]
        cs = CardSession(
            id=_session_uuid(deck_offset + j),
            creator_id=ALICE_ID,
            partner_id=BOB_ID,
            card_id=card.id,
            category=card.category.value if hasattr(card.category, 'value') else str(card.category),
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.COMPLETED,
            created_at=_days_ago(4 - j),
        )
        session.add(cs)
        session_objs.append((deck_offset + j, cs, alice_text, bob_text))

    session.commit()

    for i, cs, alice_text, bob_text in session_objs:
        card = cards[i]
        r1 = CardResponse(
            id=_response_uuid(i * 2),
            card_id=card.id,
            user_id=ALICE_ID,
            session_id=cs.id,
            content=alice_text,
            status=ResponseStatus.REVEALED,
            is_initiator=True,
            created_at=_days_ago(7 - i),
        )
        session.add(r1)

        r2 = CardResponse(
            id=_response_uuid(i * 2 + 1),
            card_id=card.id,
            user_id=BOB_ID,
            session_id=cs.id,
            content=bob_text,
            status=ResponseStatus.REVEALED,
            is_initiator=False,
            created_at=_days_ago(7 - i),
        )
        session.add(r2)

    session.commit()
    print(f"[seed] card_sessions: seeded {len(CARD_RESPONSE_TEXTS)} sessions with responses")


# =========================================================================
# 5. Seed Daily Syncs
# =========================================================================
def seed_daily_syncs(session: Session) -> None:
    existing = session.exec(select(DailySync).limit(1)).first()
    if existing:
        print("[seed] daily_sync: already exist — skipping")
        return

    syncs = [
        DailySync(user_id=ALICE_ID, sync_date=date.today() - timedelta(days=2), mood_score=4, question_id="q_energy", answer_text="今天狀態不錯，有好好吃飯和運動。", created_at=_days_ago(2)),
        DailySync(user_id=BOB_ID,   sync_date=date.today() - timedelta(days=2), mood_score=3, question_id="q_energy", answer_text="有點累，但還好。晚上想早點休息。", created_at=_days_ago(2)),
        DailySync(user_id=ALICE_ID, sync_date=date.today() - timedelta(days=1), mood_score=5, question_id="q_grateful", answer_text="感謝 Bob 今天幫我修電腦！", created_at=_days_ago(1)),
        DailySync(user_id=BOB_ID,   sync_date=date.today() - timedelta(days=1), mood_score=4, question_id="q_grateful", answer_text="感謝 Alice 煮了好吃的晚餐。", created_at=_days_ago(1)),
    ]
    for s in syncs:
        session.add(s)
    session.commit()
    print(f"[seed] daily_sync: seeded {len(syncs)} sync entries")


# =========================================================================
# 6. Seed Appreciations
# =========================================================================
def seed_appreciations(session: Session) -> None:
    existing = session.exec(select(Appreciation).limit(1)).first()
    if existing:
        print("[seed] appreciation: already exist — skipping")
        return

    items = [
        Appreciation(user_id=ALICE_ID, partner_id=BOB_ID, body_text="謝謝你每天早上幫我準備咖啡，這個小習慣讓我每天都很期待起床。", created_at=_days_ago(3)),
        Appreciation(user_id=BOB_ID, partner_id=ALICE_ID, body_text="謝謝你願意聽我講工作上的煩惱，你的建議總是很有用。", created_at=_days_ago(2)),
        Appreciation(user_id=ALICE_ID, partner_id=BOB_ID, body_text="你昨天主動洗碗讓我很感動，我知道你也很累了。", created_at=_days_ago(1)),
    ]
    for a in items:
        session.add(a)
    session.commit()
    print(f"[seed] appreciation: seeded {len(items)} entries")


# =========================================================================
# 6.5 Seed Relationship System data
# =========================================================================
def seed_relationship_system(session: Session) -> None:
    baseline_exists = session.exec(select(RelationshipBaseline).limit(1)).first()
    goal_exists = session.exec(select(CoupleGoal).limit(1)).first()
    note_exists = session.exec(select(LoveMapNote).limit(1)).first()
    wishlist_exists = session.exec(select(WishlistItem).limit(1)).first()

    if baseline_exists and goal_exists and note_exists and wishlist_exists:
        print("[seed] relationship_system: already exist — skipping")
        return

    if not baseline_exists:
        baselines = [
            RelationshipBaseline(
                user_id=ALICE_ID,
                partner_id=BOB_ID,
                filled_at=_days_ago(2),
                scores={
                    "intimacy": 4,
                    "conflict": 3,
                    "trust": 5,
                    "communication": 4,
                    "commitment": 5,
                },
            ),
            RelationshipBaseline(
                user_id=BOB_ID,
                partner_id=ALICE_ID,
                filled_at=_days_ago(1),
                scores={
                    "intimacy": 4,
                    "conflict": 3,
                    "trust": 4,
                    "communication": 4,
                    "commitment": 5,
                },
            ),
        ]
        for baseline in baselines:
            session.add(baseline)
        session.commit()
        print("[seed] relationship_system: seeded 2 relationship baselines")

    if not goal_exists:
        session.add(
            CoupleGoal(
                user_id=min(ALICE_ID, BOB_ID),
                partner_id=max(ALICE_ID, BOB_ID),
                goal_slug="better_communication",
                chosen_at=_days_ago(1),
            )
        )
        session.commit()
        print("[seed] relationship_system: seeded couple goal")

    if not note_exists:
        notes = [
            LoveMapNote(
                user_id=ALICE_ID,
                partner_id=BOB_ID,
                layer="safe",
                content="我已經知道你在工作很累的晚上，最需要的不是解法，而是一點安靜、一點被理解，還有先被抱一下。",
                created_at=_days_ago(3),
                updated_at=_days_ago(1),
            ),
            LoveMapNote(
                user_id=ALICE_ID,
                partner_id=BOB_ID,
                layer="medium",
                content="最近我更清楚地感覺到，當我們忙起來時，不是感情變淡，而是需要一個更穩定的方式提醒彼此回來對話。",
                created_at=_days_ago(2),
                updated_at=_days_ago(1),
            ),
            LoveMapNote(
                user_id=ALICE_ID,
                partner_id=BOB_ID,
                layer="deep",
                content="我真正想被你理解的，是我不是在要求完美回應，而是在害怕那些重要的感受如果沒有被接住，會慢慢變得不敢再說。",
                created_at=_days_ago(1),
                updated_at=_days_ago(0),
            ),
        ]
        for note in notes:
            session.add(note)
        session.commit()
        print("[seed] relationship_system: seeded 3 love map reflections")

    if not wishlist_exists:
        wishlist_items = [
            WishlistItem(
                user_id=ALICE_ID,
                partner_id=BOB_ID,
                title="每個月留一晚只屬於我們",
                notes="不安排社交，不追進度，只把那晚留給我們兩個人的晚餐和散步。",
                created_at=_days_ago(5),
            ),
            WishlistItem(
                user_id=BOB_ID,
                partner_id=ALICE_ID,
                title="一起去京都看秋天",
                notes="想在有涼意的季節，一起住安靜的小旅館，慢慢走神社和巷子。",
                created_at=_days_ago(4),
            ),
            WishlistItem(
                user_id=ALICE_ID,
                partner_id=BOB_ID,
                title="建立我們的衝突後修復儀式",
                notes="吵完架之後，不急著分輸贏，而是固定留二十分鐘說彼此真正卡住的是什麼。",
                created_at=_days_ago(2),
            ),
        ]
        for item in wishlist_items:
            session.add(item)
        session.commit()
        print("[seed] relationship_system: seeded 3 shared future items")


# =========================================================================
# 7. Seed Streak Summaries
# =========================================================================
def seed_streak_summaries(session: Session) -> None:
    existing = session.exec(select(UserStreakSummary).limit(1)).first()
    if existing:
        print("[seed] streak_summary: already exist — skipping")
        return

    now = _utcnow()
    for uid, partner, streak, level in [
        (ALICE_ID, BOB_ID, 5, 2),
        (BOB_ID, ALICE_ID, 5, 2),
    ]:
        ss = UserStreakSummary(
            user_id=uid,
            partner_id=partner,
            has_partner_context=True,
            streak_days=streak,
            best_streak_days=streak + 3,
            streak_eligible_today=True,
            level=level,
            level_points_total=250,
            level_points_current=50,
            level_points_target=200,
            love_bar_percent=0.65,
            level_title="Growing Together",
            updated_at=now,
        )
        session.add(ss)
    session.commit()
    print("[seed] streak_summary: seeded for Alice and Bob")


# =========================================================================
# 8. Seed Billing Entitlement (TRIAL)
# =========================================================================
def seed_billing_entitlements(session: Session) -> None:
    existing = session.exec(select(BillingEntitlementState).limit(1)).first()
    if existing:
        print("[seed] billing: already exist — skipping")
        return

    now = _utcnow()
    for uid in [ALICE_ID, BOB_ID]:
        ent = BillingEntitlementState(
            id=uuid.uuid4(),
            user_id=uid,
            lifecycle_state="TRIAL",
            current_plan=None,
            revision=1,
            updated_at=now,
        )
        session.add(ent)
    session.commit()
    print("[seed] billing: seeded TRIAL entitlements for Alice and Bob")


# =========================================================================
# 9. Seed Onboarding Consent
# =========================================================================
def seed_onboarding_consent(session: Session) -> None:
    existing = session.exec(select(UserOnboardingConsent).limit(1)).first()
    if existing:
        print("[seed] onboarding_consent: already exist — skipping")
        return

    now = _utcnow()
    for uid in [ALICE_ID, BOB_ID]:
        consent = UserOnboardingConsent(
            user_id=uid,
            privacy_scope_accepted=True,
            notification_frequency="normal",
            ai_intensity="gentle",
            updated_at=now,
        )
        session.add(consent)
    session.commit()
    print("[seed] onboarding_consent: seeded for Alice and Bob")


# =========================================================================
# 10. Seed Consent Receipts
# =========================================================================
def seed_consent_receipts(session: Session) -> None:
    existing = session.exec(select(ConsentReceipt).limit(1)).first()
    if existing:
        print("[seed] consent_receipts: already exist — skipping")
        return

    now = _utcnow()
    for uid in [ALICE_ID, BOB_ID]:
        for consent_type, version in [("terms_of_service", "1.0"), ("privacy_policy", "1.0")]:
            receipt = ConsentReceipt(
                user_id=uid,
                consent_type=consent_type,
                policy_version=version,
                granted_at=now,
                ip_address="127.0.0.1",
            )
            session.add(receipt)
    session.commit()
    print("[seed] consent_receipts: seeded for Alice and Bob")


# =========================================================================
# Main
# =========================================================================
def _attachment_uuid(i: int) -> uuid.UUID:
    return uuid.UUID(f"a1000000-0000-4000-8000-{i:012d}")


def seed_journal_attachments(session: Session) -> None:
    existing = session.exec(select(JournalAttachment).limit(1)).first()
    if existing:
        print("[seed] journal_attachments: already exist — skipping")
        return

    # Attach photos to Alice's journal #0 (days_ago=7, ramen shop) and #2 (days_ago=3, anniversary)
    attachments = [
        JournalAttachment(
            id=_attachment_uuid(0),
            journal_id=_journal_uuid(0),
            user_id=ALICE_ID,
            file_name="ramen-shop.jpg",
            mime_type="image/jpeg",
            size_bytes=245_000,
            storage_path="journals/alice/ramen-shop.jpg",
            caption="那天的拉麵店",
            created_at=_days_ago(7),
        ),
        JournalAttachment(
            id=_attachment_uuid(1),
            journal_id=_journal_uuid(0),
            user_id=ALICE_ID,
            file_name="riverside-walk.jpg",
            mime_type="image/jpeg",
            size_bytes=312_000,
            storage_path="journals/alice/riverside-walk.jpg",
            caption="河邊散步",
            created_at=_days_ago(7),
        ),
        JournalAttachment(
            id=_attachment_uuid(2),
            journal_id=_journal_uuid(2),
            user_id=ALICE_ID,
            file_name="anniversary-flowers.jpg",
            mime_type="image/jpeg",
            size_bytes=189_000,
            storage_path="journals/alice/anniversary-flowers.jpg",
            caption="500 天紀念日的花束",
            created_at=_days_ago(3),
        ),
    ]
    for att in attachments:
        session.add(att)
    session.commit()
    print(f"[seed] journal_attachments: seeded {len(attachments)} attachments (2 on ramen journal, 1 on anniversary)")


# =========================================================================
# 11. Seed Time Capsule data (365 days ago)
# =========================================================================
TC_JOURNAL_ID = uuid.UUID("d1000000-0000-4000-8000-000000000365")
TC_SESSION_ID = uuid.UUID("e1000000-0000-4000-8000-000000000365")
TC_RESPONSE_ALICE_ID = uuid.UUID("f1000000-0000-4000-8000-000000000365")
TC_RESPONSE_BOB_ID = uuid.UUID("f1000000-0000-4000-8000-000000000366")


def seed_time_capsule_data(session: Session, cards: list[Card]) -> None:
    """Seed data from 365 days ago so the Time Capsule activates in local dev."""
    existing = session.get(Journal, TC_JOURNAL_ID)
    if existing:
        print("[seed] time_capsule: already exist — skipping")
        return

    ts = _days_ago(365)

    # 1 Journal — Alice's memory from one year ago
    j = Journal(
        id=TC_JOURNAL_ID,
        user_id=ALICE_ID,
        content="一年前的今天，我們第一次一起去了那間隱藏在巷子裡的咖啡廳。你點了拿鐵，我點了手沖，我們坐在窗邊聊了一整個下午。那天陽光很好，你笑的時候眼睛會瞇起來，我到現在都還記得。",
        is_draft=False,
        mood="happy",
        mood_label="☕ 溫暖",
        visibility="PARTNER_TRANSLATED_ONLY",
        content_format="markdown",
        created_at=ts,
    )
    session.add(j)

    # 1 CardSession (completed) with responses
    if cards:
        card = cards[0]
        cs = CardSession(
            id=TC_SESSION_ID,
            creator_id=ALICE_ID,
            partner_id=BOB_ID,
            card_id=card.id,
            category=card.category.value if hasattr(card.category, "value") else str(card.category),
            mode=CardSessionMode.DAILY_RITUAL,
            status=CardSessionStatus.COMPLETED,
            created_at=ts,
        )
        session.add(cs)
        session.commit()  # FK constraint: session must exist before responses

        r1 = CardResponse(
            id=TC_RESPONSE_ALICE_ID,
            card_id=card.id,
            user_id=ALICE_ID,
            session_id=TC_SESSION_ID,
            content="我覺得最幸福的事就是每天回家都有人在等我。",
            status=ResponseStatus.REVEALED,
            is_initiator=True,
            created_at=ts,
        )
        r2 = CardResponse(
            id=TC_RESPONSE_BOB_ID,
            card_id=card.id,
            user_id=BOB_ID,
            session_id=TC_SESSION_ID,
            content="能和你一起做很平凡的事，就是最大的幸福。",
            status=ResponseStatus.REVEALED,
            is_initiator=False,
            created_at=ts,
        )
        session.add(r1)
        session.add(r2)
    else:
        session.commit()

    # 1 Appreciation — Alice to Bob
    appr = Appreciation(
        user_id=ALICE_ID,
        partner_id=BOB_ID,
        body_text="謝謝你那天下午陪我去咖啡廳，你總是知道什麼時候我需要放鬆一下。",
        created_at=ts,
    )
    session.add(appr)
    session.commit()
    print("[seed] time_capsule: seeded 1 journal + 1 card session + 1 appreciation (365 days ago)")


def seed_all() -> None:
    print("=" * 60)
    print("[seed] Haven local-dev data seed")
    print(f"[seed] target: {settings.DATABASE_URL[:40]}...")
    print("=" * 60)

    with Session(engine) as session:
        alice, bob = seed_users(session)
        cards = seed_cards(session)
        seed_journals(session)
        seed_journal_attachments(session)
        seed_card_sessions(session, cards)
        seed_daily_syncs(session)
        seed_appreciations(session)
        seed_relationship_system(session)
        seed_time_capsule_data(session, cards)
        seed_streak_summaries(session)
        seed_billing_entitlements(session)
        seed_onboarding_consent(session)
        seed_consent_receipts(session)

    print("=" * 60)
    print("[seed] DONE. Local dev data is ready.")
    print(f"[seed] Login:  {ALICE_EMAIL} / {DEV_PASSWORD}")
    print(f"[seed]         {BOB_EMAIL} / {DEV_PASSWORD}")
    print("=" * 60)


if __name__ == "__main__":
    seed_all()
