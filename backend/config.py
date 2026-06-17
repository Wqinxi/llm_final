import os

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "d753350d7c9c4023936e961c22d344cc.UF8QZwxg1V1899JT")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
MAIN_MODEL = "glm-4-flash"
VISION_MODEL = "glm-4v"

# PageIndex 配置
PAGEINDEX_PATH = os.getenv("PAGEINDEX_PATH", "")
PAGEINDEX_WORKSPACE = os.path.join(os.path.dirname(__file__), "..", "data", "pageindex_workspace")
PAGEINDEX_MODEL = "zai/glm-4.5-flash"
