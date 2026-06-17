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

    def _plan_tasks(self, user_message: str, has_image: bool, has_upload_files: bool) -> dict:
        """
        任务规划：根据用户输入和图片情况，规划需要执行的任务链。
        返回格式示例：
        {
            "steps": [
                {"agent": "image", "query": "识别图片中的内容", "reason": "需要了解图片信息"},
                {"agent": "doc", "query": "搜索识别出的内容", "reason": "需要查询文档"}
            ],
            "final_intent": "用户想要做什么"
        }
        """
        image_hint = "用户上传了图片。" if has_image else "用户没有上传图片。"
        upload_files_hint = "用户上传了文档。" if has_upload_files else "用户没有上传文档。"
        prompt = f"""
你是任务规划专家。请分析用户需求，规划调用 ImageAgent（图像识别）和 DocAgent（文档检索）的任务链。

{image_hint}
{upload_files_hint}
用户输入: "{user_message}"
【重要前置条件】本次对话用户已上传本地文档，文档内容会直接作为上下文提供，无需调用DocAgent检索知识库。

可用Agent：
- ImageAgent: 分析图片内容，提取关键信息（如识别菜品、文字、物体等）
- DocAgent: 根据查询词检索知识库文档，返回相关内容和来源

强制规划规则（优先级最高，必须严格遵守）
1. 若用户**已经上传本地文档**：用户提问仅针对这份上传文档概括、解读、总结、梳理内容时，禁止生成doc步骤，不需要调用DocAgent；
   只有用户额外需要知识库外部资料、其他菜谱/专业知识时，才必须添加doc步骤。
2. 无本地上传文档时：只要用户问题属于**需要资料、教程、做法、食材、步骤、专业知识、物品介绍、菜谱、制作流程**类提问，无论是否上传图片，**必须生成doc步骤调用DocAgent**，禁止返回空steps。
3. 仅以下场景允许不调用任何Agent（steps为空）：纯闲聊、主观情绪抒发、无实际查询诉求、单纯打招呼、主观评价类无资料需求问题；以及仅基于已上传文档作答的提问。
4. 如果有图片且需要了解图片内容 → 先调用 ImageAgent；再追加doc步骤（仅当需要外部知识库资料时），DocAgent 的query只写用户意图，例如"如何制作这道菜品"，识别结果会在运行时自动拼接进去
5. 如果用户纯文字询问教程、菜谱、知识、制作方法等，且无上传本地文档 → 只生成一条doc步骤，禁止空steps
6. 如果只上传图片，无文字提问（仅识图）→ 只调用 ImageAgent

请按以下JSON格式输出任务计划：
{{
    "steps": [
        {{"agent": "image", "query": "给ImageAgent的具体识别指令（如：这是什么汤？列出食材）", "reason": "为什么需要这个步骤"}},
        {{"agent": "doc", "query": "用户意图短句，例如：如何制作这道菜品", "reason": "需要根据图片识别内容查询对应做法"}}
    ],
    "final_intent": "用户的最终意图描述"
}}

重要规则：
- ImageAgent的query必须是具体的识别指令，不要写笼统的"分析图片内容"
- DocAgent 的 query 只写纯意图，禁止使用任何占位符、图片描述文本，运行时会自动拼接图片识别结果
- steps数组可以为空（表示不需要调用任何Agent）
- 如果不需要调用Agent，直接返回 {{"steps": [], "final_intent": "直接回答"}}
- 确保JSON格式正确
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
                plan = json.loads(json_match.group())
                # 验证格式
                if "steps" in plan and isinstance(plan["steps"], list):
                    return plan
        except Exception as e:
            print(f"ERROR:    [MainAgent] 任务规划失败: {e}")
        
        # 默认：直接回答
        return {"steps": [], "final_intent": "直接回答"}

    def run(self, messages: list, image_url: str = None, upload_doc_content: str = "") -> str:
        """
        主 Agent 运行逻辑：
        1. 任务规划：决定调用哪些Agent及调用顺序
        2. 按顺序执行Agent，收集上下文
        3. 汇总上传文档、检索文档信息，生成最终回答
        """
        user_message = messages[-1]["content"] if messages else ""

        # 任务规划
        plan = self._plan_tasks(user_message, has_image=bool(image_url), has_upload_files=bool(upload_doc_content))
        print(f"DEBUG:    [MainAgent] 任务规划: {json.dumps(plan, ensure_ascii=False)}")

        context_parts = []
        # 先放入用户上传本地解析的文档内容
        if upload_doc_content.strip():
            context_parts.append(f"【用户上传本地文档内容】\n{upload_doc_content}")
        previous_results = {}  # 存储各步骤的结果，供后续步骤引用

        # 按顺序执行规划的任务
        for i, step in enumerate(plan.get("steps", [])):
            agent_type = step.get("agent")
            query = step.get("query", "")
            reason = step.get("reason", "")
            
            print(f"DEBUG:    [MainAgent] 执行步骤 {i+1}: {agent_type} - {reason}")
            
            if agent_type == "image" and image_url:
                # 调用 ImageAgent
                result = self.image_agent.run(image_url, query=query)
                context_parts.append(result)
                previous_results[f"step_{i+1}_image"] = result
                
            elif agent_type == "doc":
                # 拿到规划时生成的纯意图短句（无占位符）
                intent_query = step.get("query", "")
                prev_step_key = f"step_{i}_image"
                if prev_step_key in previous_results:
                    # 获取真实图片识别输出
                    image_result = previous_results[prev_step_key]
                    # 提取核心实体，精简图片内容，避免超长文本
                    core_entity = self._extract_key_info(image_result)
                    formatted_query = f"{intent_query}：{core_entity}"
                    # 清洗换行、多余空格
                    formatted_query = re.sub(r"\s+", " ", formatted_query).strip()
                    print(f"DEBUG:    [MainAgent] 意图:{intent_query}，提取实体:{core_entity}，最终检索query:{formatted_query}")
                else:
                    # 无前置图片步骤，直接使用规划的意图作为检索词
                    formatted_query = intent_query

                result = self.doc_agent.run(formatted_query)
                context_parts.append(result)
                previous_results[f"step_{i+1}_doc"] = result
                
            else:
                print(f"DEBUG:    [MainAgent] 跳过步骤 {i+1}: 条件不满足")

        if not context_parts:
            print("DEBUG:    [MainAgent] 无需调用子Agent，直接由大模型回答")

        print(f"DEBUG:    [MainAgent] 收集到的参考信息片段数: {len(context_parts)}")

        # 构建最终 prompt
        system_prompt = "你是一个智能助手。请根据用户问题"
        if context_parts:
            system_prompt += """
            【有参考文档时必须严格遵守的硬性规则】
            1. 参考信息分为两类：用户本地上传文档、知识库检索文档，全部结合起来完整回答，禁止删减、简化、合并原文内容，步骤、食材、参数必须完整保留。
            2. 优先级：优先使用【用户本地上传本地文档】内容作答，本地文档存在对应内容时，**禁止输出「未找到相关文档」**；仅本地文档完全无相关信息时，再使用知识库补充。
            3. 只有当本地文档 + 知识库文档两类资料全都没有对应内容，才允许回复：未找到相关文档。
            4. 输出禁止一切Markdown符号：#、**、-/*列表、---、反引号`全部不能出现。
            5. 分点只用数字1、2、3换行展示，纯自然文字。
            6. 回答末尾如需标注来源，单独一行写「参考来源：xxx」，不要分割线。
            """
        else:
            system_prompt += "，给出准确、简洁的回答。"

        full_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            if m["role"] != "system":
                full_messages.append(m)

        if context_parts:
            context_str = "\n\n===== 分割线 =====\n\n".join(context_parts)
            last_user = full_messages[-1]
            if last_user["role"] == "user":
                last_user["content"] += (
                    f"\n\n--- 全部参考信息（本地上传文档+知识库检索） ---\n"
                    f"{context_str}"
                )

        try:
            response = client.chat.completions.create(
                model=MAIN_MODEL,
                messages=full_messages,
                temperature=0.1,
            )
            raw_ans = response.choices[0].message.content.strip()
            # 后置清洗markdown
            import re
            res = re.sub(r"#+\s*", "", raw_ans)
            res = re.sub(r"\*\*(.+?)\*\*", r"\1", res)
            res = re.sub(r"^[-*]\s+", "", res, flags=re.MULTILINE)
            res = re.sub(r"[-]{3,}", "", res)
            res = re.sub(r"`+", "", res)
            res = re.sub(r"\n{2,}", "\n\n", res).strip()
            return res
        except Exception as e:
            return f"请求失败: {str(e)}"

    def _extract_key_info(self, text: str) -> str:
        """
        从文本中提取关键信息作为查询词。
        """
        # 移除前缀，获取实际内容
        clean_text = text.replace("【图像识别结果】\n", "").replace("【文档检索结果】\n", "").strip()
        
        # 如果内容很短，直接返回
        if len(clean_text) <= 20:
            return clean_text
        
        prompt = f"""请从以下文本中提取最核心的实体名称（如菜品名、产品名、物品名等），用于文档检索。
只需要输出名称，不要其他解释。如果无法确定，输出"提取失败"。

文本：
{clean_text[:500]}

核心名称："""
        try:
            response = client.chat.completions.create(
                model=MAIN_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            key_info = response.choices[0].message.content.strip()
            # 清理
            key_info = key_info.replace("核心名称：", "").replace("\"", "").strip()
            
            # 检查提取结果是否有效
            if key_info and key_info not in ["", "未知", "提取失败", "无"]:
                print(f"DEBUG:    [MainAgent] 提取到关键词: {key_info}")
                return key_info
        except Exception as e:
            print(f"ERROR:    [MainAgent] 提取关键信息失败: {e}")
        
        # 如果提取失败，返回清理后的文本前30字符
        fallback = clean_text[:30].replace("\n", " ").strip()
        print(f"DEBUG:    [MainAgent] 使用fallback关键词: {fallback}")
        return fallback if fallback else "图片内容"
