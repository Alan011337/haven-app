import streamlit as st
from src.sentiment import analyze_journal

st.set_page_config(page_title="Haven", page_icon="❤️")
st.title("Haven ❤️ 棲")
st.write("寫下今天的日記，讓 AI 成為你們的情感翻譯機。")

# 1. 日記輸入區
diary_content = st.text_area("親愛的日記", height=150, placeholder ="今天發生了什麼事？你的心情如何？")


# 2. 按鈕觸發區
if st.button("✨提交並分析", type="primary"):
    if not diary_content:
        st.warning("請先寫點東西再提交喔")
    else:
        # 顯示載入中的動畫
        with st.spinner(" AI 正在用心閱讀並整理思緒中"):
            # 呼叫我們寫好的 AI 分析函數
            result = analyze_journal(diary_content)

        # 3. 顯示結果
        if result:
            st.divider() # 分隔線

            # 顯示情緒標籤
            st.subheader(f"當下情緒：{result['mood_label']}")

            # 顯示深層需求（用漂亮的標籤呈現）
            st.write("💡**你內心的深層渴望：**")
            # 把清單變成一顆一顆的標籤
            st.markdown(" ".join([f"`{need}`" for need in result['emotional_needs']]))

            st.divider()

            # 左右兩欄顯示建議
            col1, col2 = st.columns(2)

            with col1:
                st.info("🧘 **給你的自我反思**")
                for advice in result['advice_for_user']:
                    st.write(f"-{advice}")
            
            with col2:
                st.info("🤝 **給伴侶的行動建議**")
                for action in result['action_for_partner']:
                    st.write(f"-{action}")

            st.divider()

            # 推薦卡牌
            st.write("🃏 **推薦你們現在玩這組卡牌：**")
            st.metric(label="Card Recommendation", value=result['card_type_recommendation'])

        else:
            st.error("分析失敗，請檢查 API KEY 或網路連線")