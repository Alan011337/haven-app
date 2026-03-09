# backend/fix_db.py
from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_database():
    print("🔧 正在連線至資料庫...")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("🚑 正在修復 'card_responses' 表格...")
        
        # 1. 補上 is_initiator 欄位
        try:
            conn.execute(text("ALTER TABLE card_responses ADD COLUMN IF NOT EXISTS is_initiator BOOLEAN DEFAULT FALSE;"))
            print("✅ 已新增 is_initiator 欄位")
        except Exception as e:
            print(f"⚠️ is_initiator 新增失敗 (可能已存在): {e}")

        # 2. 為了保險，順便檢查 session_id 是否存在 (如果這也是新加的)
        try:
            conn.execute(text("ALTER TABLE card_responses ADD COLUMN IF NOT EXISTS session_id UUID;"))
            print("✅ 已新增 session_id 欄位")
        except Exception as e:
            print(f"⚠️ session_id 新增失敗: {e}")

        conn.commit()
        print("🎉 資料庫修復完成！")

if __name__ == "__main__":
    fix_database()