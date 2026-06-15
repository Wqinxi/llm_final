import json
import re

from openai import OpenAI

from backend.config import ZHIPU_API_KEY, ZHIPU_BASE_URL, MAIN_MODEL
from backend.agents.doc_agent import DocAgent
from backend.agents.image_agent import ImageAgent

client = OpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)


class MainAgent:
    def __init__(self):
        self.doc_agent = DocAgent()
        self.image_agent = ImageAgent()

    def _classify_intent(self, user_message: str) -> dict:
        """
        使用 LLM 判断用户意图，决定是否需要调用 DocAgent 或 ImageAgent。
        返回格式示例：
        {"needs_doc": true, "needs_image": false, "reason": "..."}
        """
        prompt = f"""请分析以下用户输入，判断是否需要调用文档检索助手(DocAgent)或图像识别助手(ImageAgent)。
用户输入: "{user_message}"

请仅按以下 JSON 格式输出，不要输出其他内容:
{{"needs_doc": true/false, "needs_image": true/false, "reason": "简短原因"}}
"""
        try:
            response = client.chat.completions.create(
                model=MAIN_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = response.choices[0].message.content.strip()
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return {"needs_doc": False, "needs_image": False, "reason": "直接回答"}

    def run(self, messages: list, image_url: str = None) -> str:
        """
        主 Agent 运行逻辑：
        1. 获取最新用户消息
        2. 判断意图
        3. 如需，调用子 Agent 收集信息
        4. 汇总所有信息，调用 LLM 生成最终回答
        """
        user_message = messages[-1]["content"] if messages else ""

        # 意图判断
        intent = self._classify_intent(user_message)
        print(f"DEBUG:    [MainAgent] 意图判断结果: {intent}")

        context_parts = []

        # 图像处理
        if image_url or intent.get("needs_image"):
            print("DEBUG:    [MainAgent] 决定调用 ImageAgent...")
            if image_url:
                img_result = self.image_agent.run(image_url, query=user_message)
                context_parts.append(img_result)
            else:
                context_parts.append("【图像识别结果】\n用户未提供图片URL，但意图涉及图像。\n")
        else:
            print("DEBUG:    [MainAgent] 无需调用 ImageAgent")

        # 文档处理
        if intent.get("needs_doc"):
            print("DEBUG:    [MainAgent] 决定调用 DocAgent...")
            doc_result = self.doc_agent.run(user_message)
            context_parts.append(doc_result)
        else:
            print("DEBUG:    [MainAgent] 无需调用 DocAgent")

        if not context_parts:
            print("DEBUG:    [MainAgent] 无需调用子Agent，直接由大模型回答")

        print(f"DEBUG:    [MainAgent] 收集到的参考信息片段数: {len(context_parts)}")

        # 构建最终 prompt
        system_prompt = "你是一个智能助手。请根据用户问题"
        if context_parts:
            system_prompt += (
                "及以下参考信息，给出准确、完整的回答。"
                "如果参考信息涉及多个文档，请分别整理每个文档的内容，确保不遗漏任何一份文档的信息。"
                "如果参考信息不足，请基于你的知识回答，不要编造。"
                "重要要求：不要在正文中逐条标注来源。如果回答参考了文档，请在回答最后另起一行输出 '---' 分割线，然后列出参考来源的文档名称。"
            )
        else:
            system_prompt += "，给出准确、简洁的回答。"

        full_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m["role"] != "system":
                full_messages.append(m)

        if context_parts:
            context_str = "\n".join(context_parts)
            last_user = full_messages[-1]
            if last_user["role"] == "user":
                last_user["content"] += (
                    f"\n\n--- 参考信息 ---\n"
                    f"以下是从文档中检索到的参考片段，请在回答最后通过分割线列出参考来源文档名称，不要在正文中逐条标注。\n"
                    f"{context_str}"
                )

        try:
            response = client.chat.completions.create(
                model=MAIN_MODEL,
                messages=full_messages,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"请求失败: {str(e)}"
