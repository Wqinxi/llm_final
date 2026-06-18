"""ImageAgent：图像识别 Agent。"""
import asyncio
from backend.tools.image_tool import read_image


class ImageAgent:
    def __init__(self):
        self.name = "ImageAgent"

    async def run(self, image_url: str, query: str = "", log_callback=None):
        """识别图像内容，返回精简的识别结果。
        以 async generator 形式产出日志和结果，工具调用放入线程池避免阻塞事件循环
        """
        display_url = image_url[:60] + "..." if len(image_url) > 60 else image_url
        print(f"DEBUG:    [ImageAgent] 开始识别 image_url={display_url}")

        if log_callback:
            yield ("log", log_callback("    调用read_image tool"))

        # 构建识别提示，要求结果精简
        if query:
            prompt = f"{query}请用一句话简洁回答，只输出关键信息（如菜品名称、主要食材），不要详细步骤。"
        else:
            prompt = "请描述这张图片的内容，用一句话简洁回答。"

        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None, read_image, image_url, prompt
            )
            print(f"DEBUG:    [ImageAgent] 识别完成，结果={result}")
            yield ("result", f"【图像识别结果】\n{result}")
        except Exception as e:
            print(f"ERROR:    [ImageAgent] 识别失败: {e}")
            yield ("result", f"【图像识别结果】\n识别失败: {str(e)}")
