import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 1. 核心配置：从环境变量读取
AI_BACKEND = os.getenv("AI_BACKEND", "gemini") # 默认改为 gemini
AI_MODEL = os.getenv("AI_MODEL", "gemini-1.5-flash") # 默认使用 flash

# 密钥配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
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

def _call_gemini(prompt: str) -> str:
    """原生调用 Google Gemini API"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(AI_MODEL)
        
        logger.info(f"正在调用 Gemini 接口: Model={AI_MODEL}")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini 调用失败: {str(e)}")
        raise e

def _call_openai(prompt: str) -> str:
    """调用 OpenAI 兼容接口"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        logger.info(f"正在调用 OpenAI API: {OPENAI_BASE_URL} 模型: {AI_MODEL}")
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI 调用失败: {str(e)}")
        raise e

def _call_ai(prompt: str) -> str:
    """路由 AI 调用 - 修正逻辑"""
    backend = AI_BACKEND.lower()
    
    # 增加 Gemini 分支
    if backend == "gemini" and GEMINI_API_KEY:
        return _call_gemini(prompt)
    elif backend == "openai" and OPENAI_API_KEY:
        return _call_openai(prompt)
    elif backend == "dashscope" and DASHSCOPE_API_KEY:
        from dashscope import Generation
        import dashscope
        dashscope.api_key = DASHSCOPE_API_KEY
        resp = Generation.call(model=AI_MODEL, messages=[{"role":"user","content":prompt}], result_format="message")
        return resp.output.choices[0].message.content
    
    # 如果没匹配到后端，或者缺少 Key，才返回 Mock
    logger.warning(f"未匹配到有效的 AI 后端或缺少 Key (Current Backend: {backend})，使用 mock 响应")
    return _call_mock(prompt)

def _parse_json_from_response(text: str) -> dict:
    """解析 JSON，增加对 Markdown 代码块的清洗"""
    try:
        # 去除 Gemini 经常返回的 ```json ... ``` 标记
        clean_text = re.sub(r"```json\s*|\s*```", "", text).strip()
        return json.loads(clean_text)
    except:
        match = re.search(r"\{[\s\S]*\}", text)
        if match: return json.loads(match.group(0))
        raise ValueError(f"AI 返回了无效的 JSON: {text[:100]}")

def extract_resume_info(resume_text: str) -> dict:
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(resume_text=resume_text[:4000])
    raw_response = _call_ai(prompt)
    return _parse_json_from_response(raw_response)

def score_resume_match(resume_info: dict, job_description: str) -> dict:
    return {"overall_score": 85, "ai_analysis": "匹配成功"}

def _call_mock(prompt: str) -> str:
    return json.dumps({"basic_info": {"name": "演示数据"}})