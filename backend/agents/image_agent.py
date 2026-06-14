from backend.tools.image_tool import read_image


class ImageAgent:
    def __init__(self):
        self.name = "ImageAgent"

    def run(self, image_url: str, query: str = "") -> str:
        """
        识别图像内容并返回描述。
        """
        display_url = image_url if len(image_url) <= 60 else image_url[:60] + "..."
        print(f"DEBUG:    [ImageAgent] 开始识别 image_url={display_url}")
        prompt = query if query else "请详细描述这张图片的内容。"
        result = read_image(image_url, prompt)
        print(f"DEBUG:    [ImageAgent] 识别完成，结果长度={len(result)}")
        return f"【图像识别结果】\n{result}\n"
