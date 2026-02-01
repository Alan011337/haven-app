import os
from dotenv import load_dotenv  

def get_openai_key():
    load_dotenv()
    if os.getenv("OPENAI_API_KEY") is None:
        print("OPENAI_API_KEY is not set")
        return None
    else:
        return os.getenv("OPENAI_API_KEY")
