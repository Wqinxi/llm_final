from openai import OpenAI
from backend.config import ZHIPU_API_KEY, ZHIPU_BASE_URL, VISION_MODEL

client = OpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)


def read_image(image_url: str, prompt: str = "请描述这张图片的内容。") -> str:
    """
    调用智谱视觉模型识别图像。
    image_url 支持网络图片 URL 或 base64 编码（data:image/jpeg;base64,...）。
    """
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"图像识别失败: {str(e)}"
