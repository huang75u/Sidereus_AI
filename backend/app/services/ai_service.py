import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 核心配置：从环境变量读取
AI_BACKEND = os.getenv("AI_BACKEND", "openai")
# 适配 Mammouth/OpenAI 的密钥和地址
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
# 动态读取模型名称，默认为 deepseek-v3
AI_MODEL = os.getenv("AI_MODEL", "deepseek-v3")

# 阿里云配置（保留作为备份）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

EXTRACTION_PROMPT_TEMPLATE = """
你是一位专业的HR助手。请从以下简历文本中提取关键信息，并以JSON格式返回。
简历文本：{resume_text}
请提取信息并返回严格的JSON格式（不要包含任何解释）：
{{
  "basic_info": {{ "name": "null", "phone": "null", "email": "null", "address": "null" }},
  "job_intent": {{ "position": "null", "expected_salary": "null" }},
  "background": {{ "years_of_experience": "null", "education": "null", "projects": [], "skills": [] }}
}}
"""

def _call_openai(prompt: str) -> str:
    """调用 OpenAI 兼容接口（适配 Mammouth AI）"""
    try:
        from openai import OpenAI
        # 强制使用环境变量中的配置
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        
        logger.info(f"正在调用 API: {OPENAI_BASE_URL} 模型: {AI_MODEL}")
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI/Mammouth 调用失败: {str(e)}")
        raise e

def _call_ai(prompt: str) -> str:
    """路由 AI 调用"""
    backend = AI_BACKEND.lower()
    if backend == "openai":
        return _call_openai(prompt)
    # 如果配置为 dashscope 则调用阿里云
    elif backend == "dashscope" and DASHSCOPE_API_KEY:
        from dashscope import Generation
        import dashscope
        dashscope.api_key = DASHSCOPE_API_KEY
        resp = Generation.call(model=AI_MODEL, messages=[{"role":"user","content":prompt}], result_format="message")
        return resp.output.choices[0].message.content
    return _call_mock(prompt)

def _parse_json_from_response(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except:
        match = re.search(r"\{[\s\S]*\}", text)
        if match: return json.loads(match.group(0))
        raise ValueError("AI 返回了无效的 JSON")

def extract_resume_info(resume_text: str) -> dict:
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(resume_text=resume_text[:4000])
    raw_response = _call_ai(prompt)
    return _parse_json_from_response(raw_response)

def score_resume_match(resume_info: dict, job_description: str) -> dict:
    # 简化逻辑，实际项目中可按需扩充
    return {"overall_score": 80, "ai_analysis": "匹配成功"}

def _call_mock(prompt: str) -> str:
    return json.dumps({"basic_info": {"name": "演示数据"}})