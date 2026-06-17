"""ImageAgent：图像识别 Agent。"""
from backend.tools.image_tool import read_image


class ImageAgent:
    def __init__(self):
        self.name = "ImageAgent"

    def run(self, image_url: str, query: str = "") -> str:
        """识别图像内容，返回精简的识别结果。"""
        display_url = image_url[:60] + "..." if len(image_url) > 60 else image_url
        print(f"DEBUG:    [ImageAgent] 开始识别 image_url={display_url}")

        # 构建识别提示，要求结果精简
        if query:
            prompt = f"{query}请用一句话简洁回答，只输出关键信息（如菜品名称、主要食材），不要详细步骤。"
        else:
            prompt = "请描述这张图片的内容，用一句话简洁回答。"

        try:
            result = read_image(image_url, prompt)
            print(f"DEBUG:    [ImageAgent] 识别完成，结果={result}")
            return f"【图像识别结果】\n{result}"
        except Exception as e:
            print(f"ERROR:    [ImageAgent] 识别失败: {e}")
            return f"【图像识别结果】\n识别失败: {str(e)}"
