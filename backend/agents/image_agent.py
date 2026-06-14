from backend.tools.image_tool import read_image


class ImageAgent:
    def __init__(self):
        self.name = "ImageAgent"

    def run(self, image_url: str, query: str = "") -> str:
        """
        识别图像内容并返回描述。
        """
        prompt = query if query else "请详细描述这张图片的内容。"
        result = read_image(image_url, prompt)
        return f"【图像识别结果】\n{result}\n"
