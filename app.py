import streamlit as st
import json
from dotenv import load_dotenv
from supabase import create_client, Client
from src.sentiment import analyze_journal

# 1. 載入環境變數與設定
load_dotenv()
st.set_page_config(page_title="Haven", page_icon="❤️", layout="centered")

# === 🔐 P0-4: 安全防護 (Simple Auth) ===
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 不要在 session 留存密碼
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 第一次進入，初始化狀態
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        # 已經登入過，放行
        return True

    # 還沒登入，顯示輸入框
    st.title("🔒 Haven 安全通道")
    st.text_input(
        "請輸入通關密語", type="password", on_change=password_entered, key="password"
    )
    st.caption("提示：你們紀念日的四位數字")
    return False

if not check_password():
    st.stop()  # ⛔️ 密碼不對就停在這裡，不執行下面的程式

# === 🔐 安全防護結束，下面才是原本的主程式 ===

# 2. 初始化 Supabase 連線
# ... (後略)

# 2. 初始化 Supabase 連線
# (請確認 .streamlit/secrets.toml 裡面已經設定好 [supabase] 的 url 和 key)
try:
    supabase_url = st.secrets["supabase"]["url"]
    supabase_key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(supabase_url, supabase_key)
    # 靜默測試連線 (不顯示成功訊息，除非報錯)
except Exception as e:
    st.error(f"❌ 資料庫連線失敗: {e}")
    st.stop()

# --- UI 標題區 ---
st.title("Haven ❤️ 棲")
st.caption("你的 AI 關係教練 & 情感翻譯機")

# --- Sidebar: 使用者設定 ---
with st.sidebar:
    st.header("👤 使用者設定")
    current_user = st.selectbox("我是誰？", ["Alan", "Vicky", "Guest"])
    current_partner = st.text_input("我的伴侶是？", value="Vicky" if current_user == "Alan" else "Alan")
    
    # 未來可以這裡加 Feature C 的積分條
    st.divider()
    st.write("❤️ 關係存款: $0 (建置中...)")

# --- 主介面: 分頁設計 ---
tab1, tab2 = st.tabs(["📝 寫日記 (翻譯情緒)", "🃏 抽張卡 (增進連結)"])

# ==========================================
# TAB 1: 日記與 AI 分析 (The Heart)
# ==========================================
with tab1:
    st.write("寫下今天的感受，讓 Haven 幫你翻譯內心的聲音。")
    diary_content = st.text_area("親愛的日記...", height=150, placeholder="今天發生了什麼事？你的感覺如何？")

    if st.button("✨ 提交並分析", type="primary"):
        if not diary_content:
            st.warning("請先寫點東西再提交喔！")
        else:
            with st.spinner("🤖 Haven 正在用心閱讀並整理思緒中..."):
                # 1. 呼叫 AI 分析 (src/sentiment.py)
                result = analyze_journal(diary_content)

            if result:
                # 2. 顯示 AI 分析結果 (配合 v3.1 Prompt 格式)
                st.divider()
                
                # 情緒標籤
                st.subheader(f"當下情緒：{result.get('mood_label', '分析中...')}")
                
                # 深層需求
                st.success(f"💡 **內心深層渴望**：\n{result.get('emotional_needs', '')}")
                
                # 左右兩欄建議
                col1, col2 = st.columns(2)
                with col1:
                    st.info("🧘 **給你的自我反思**")
                    st.write(result.get('advice_for_user', ''))
                
                with col2:
                    st.info("🤝 **給伴侶的使用說明書**")
                    # 原本是 st.write，改成下面這樣：
                    partner_action = result.get('action_for_partner', '無建議')
                    
                    # 使用 st.code 呈現，雖然它是純文字，但這樣右上角會有「複製」按鈕
                    st.code(partner_action, language="text") 
                    st.caption("👆 點擊右上角複製，直接 Line 給對方")

                st.divider()
                st.write(f"🃏 **推薦卡牌**：{result.get('card_type_recommendation', '一般卡牌')}")

                # 3. 存入 Supabase (logs 表)
                try:
                    data = {
                        "user_name": current_user,
                        "partner_name": current_partner,
                        "journal_text": diary_content,
                        "ai_analysis": result  # 🔥 直接存 JSON！
                    }
                    supabase.table("logs").insert(data).execute()
                    st.toast("✅ 日記已安全存入雲端大腦！", icon="💾")
                except Exception as e:
                    st.error(f"儲存失敗: {e}")
            else:
                st.error("分析失敗，AI 好像在發呆，請再試一次。")

# ==========================================
# TAB 2: 抽卡系統 (The Game)
# ==========================================
with tab2:
    st.subheader("🔮 關係卡牌")
    st.write("不知道聊什麼？抽一張卡來開啟話題吧！")
    
    card_dictionary = {
        "Daily Vibe (日常共感)": "Daily Vibe (日常共感)",
        "Soul Dive (靈魂深潛)": "Soul Dive (靈魂深潛)",
        "Safe Zone (安全氣囊)": "Safe Zone (安全氣囊)",
        "After Dark (深夜模式)": "After Dark (深夜模式)",
        "Co-Pilot (最佳副駕)": "Co-Pilot (最佳副駕)",
        "Love Blueprint (愛情藍圖)": "Love Blueprint (愛情藍圖)"
    }

    # 讓選項直接從字典產生，保證一致
    selected_label = st.selectbox("選擇卡牌種類", options=card_dictionary.keys())

    # --- 按鈕 A: 負責「抽」卡片，並存入「短期記憶」 ---
    if st.button("🎲 隨機抽一張卡"):
        try:
            # 1. 去資料庫撈資料
            response = supabase.table("cards").select("*").eq("category", card_dictionary[selected_label]).execute()
            cards_data = response.data
            
            if cards_data:
                import random
                # 2. 隨機選一張，並存入 session_state (這是關鍵！讓卡片不會消失)
                st.session_state['current_card'] = random.choice(cards_data)
                
                # 3. 順便清空上一張卡的回答紀錄，避免殘留
                if 'card_response' in st.session_state:
                    del st.session_state['card_response']
            else:
                st.warning("這個分類目前牌庫是空的，請先去資料庫新增卡牌！")
                
        except Exception as e:
            st.error(f"抽卡失敗: {e}")

    # --- 顯示區域: 只要記憶裡有卡片，就顯示出來 (不管畫面有沒有重整) ---
    if 'current_card' in st.session_state:
        card = st.session_state['current_card']
        
        st.divider()
        st.markdown(f"### {card['category']}")
        st.markdown(f"## {card['content']}")
        st.divider()
        
        st.write("💬 **你的想法**")
        
        # 輸入框綁定 key，這樣 Streamlit 會自動幫你管理它的內容狀態
        response_text = st.text_area(
            label="輸入你的回答...", 
            height=100, 
            placeholder="這張卡讓你想到什麼？寫下來紀錄這刻的連結...",
            label_visibility="collapsed",
            key="card_response" 
        )

        # --- 按鈕 B: 負責「存」回答 ---
        if st.button("💌 記錄回答"):
            if not response_text:
                st.warning("請先寫點東西再儲存喔！")
            else:
                try:
                    data = {
                        "user_name": current_user,
                        "partner_name": current_partner,
                        "card_id": card['id'],
                        "response_text": response_text
                    }
                    # 這裡存入正確的 cards_logs 表
                    supabase.table("card_logs").insert(data).execute()
                    st.toast("✅ 你們的對話已安全保存！", icon="💾")
                    st.balloons() # 給你一點獎勵動畫！
                    
                except Exception as e:
                    st.error(f"儲存失敗: {e}")