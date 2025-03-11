from dotenv import load_dotenv
import os

load_dotenv()

# 飞书配置
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
LOCAL_MARKDOWN_DIR = os.getenv('LOCAL_MARKDOWN_DIR')