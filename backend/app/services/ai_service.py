import os
import json
import logging
import re

logger = logging.getLogger(__name__)

# 核心配置
AI_BACKEND = os.getenv("AI_BACKEND", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# 建议在 Render 中将 AI_MODEL 改为 gemini-1.5-flash-latest
AI_MODEL = os.getenv("AI_MODEL", "gemini-1.5-flash")

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

def _call_gemini(prompt: str) -> str:
    """使用 Google 最新 genai SDK 调用"""
    try:
        from google import genai
        # 初始化客户端
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        logger.info(f"正在调用最新 Gemini 接口: Model={AI_MODEL}")
        
        response = client.models.generate_content(
            model=AI_MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini 调用失败: {str(e)}")
        raise e

def _call_ai(prompt: str) -> str:
    """路由 AI 调用"""
    backend = AI_BACKEND.lower()
    if backend == "gemini" and GEMINI_API_KEY:
        return _call_gemini(prompt)
    return _call_mock(prompt)

def _parse_json_from_response(text: str) -> dict:
    """清理并解析 JSON"""
    try:
        clean_text = re.sub(r"```json\s*|\s*```", "", text).strip()
        return json.loads(clean_text)
    except:
        match = re.search(r"\{[\s\S]*\}", text)
        if match: return json.loads(match.group(0))
        return {}

def extract_resume_info(resume_text: str) -> dict:
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(resume_text=resume_text[:4000])
    raw_response = _call_ai(prompt)
    return _parse_json_from_response(raw_response)

def score_resume_match(resume_info: dict, job_description: str) -> dict:
    return {"overall_score": 85, "ai_analysis": "匹配成功"}

def _call_mock(prompt: str) -> str:
    return json.dumps({"basic_info": {"name": "演示数据"}})