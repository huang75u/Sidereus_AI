import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Supported AI backends: "dashscope" (Qwen), "openai", "mock"
AI_BACKEND = os.getenv("AI_BACKEND", "dashscope")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "qwen-plus")


EXTRACTION_PROMPT_TEMPLATE = """
你是一位专业的HR助手。请从以下简历文本中提取关键信息，并以JSON格式返回。

简历文本：
{resume_text}

请提取以下信息并返回严格的JSON格式（不要包含任何解释或多余文字）：
{{
  "basic_info": {{
    "name": "姓名（字符串或null）",
    "phone": "电话号码（字符串或null）",
    "email": "邮箱地址（字符串或null）",
    "address": "地址（字符串或null）"
  }},
  "job_intent": {{
    "position": "求职意向（字符串或null）",
    "expected_salary": "期望薪资（字符串或null）"
  }},
  "background": {{
    "years_of_experience": "工作年限（字符串或null）",
    "education": "最高学历（字符串或null）",
    "projects": ["项目1", "项目2"],
    "skills": ["技能1", "技能2", "技能3"]
  }}
}}
"""

MATCHING_PROMPT_TEMPLATE = """
你是一位专业的招聘顾问。请评估以下候选人简历与职位需求的匹配程度。

岗位需求描述：
{job_description}

候选人简历信息：
{resume_info}

请从以下维度进行分析并返回严格的JSON格式（不要包含任何解释或多余文字）：
{{
  "overall_score": 综合评分(0-100的数字),
  "skill_match": {{
    "matched": ["已匹配的技能列表"],
    "missing": ["缺失的关键技能列表"],
    "match_rate": 技能匹配率(0-1的小数)
  }},
  "experience_relevance": 工作经验相关性评分(0-1的小数),
  "ai_analysis": "详细分析说明（2-3句话）",
  "recommendation": "录用建议（推荐/考虑/不推荐）"
}}
"""


def _call_dashscope(prompt: str, model: str = None) -> str:
    """Call Alibaba Cloud DashScope (Qwen) API."""
    try:
        import dashscope
        from dashscope import Generation

        dashscope.api_key = DASHSCOPE_API_KEY
        response = Generation.call(
            model=model or AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            result_format="message",
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            raise RuntimeError(f"DashScope error {response.status_code}: {response.message}")
    except ImportError:
        raise RuntimeError("dashscope package not installed. Run: pip install dashscope")


ddef _call_openai(prompt: str, model: str = None) -> str:
    """调用 OpenAI 兼容接口，适配 Mammouth AI 等第三方聚合商"""
    try:
        from openai import OpenAI
        import os

        # 读取环境变量
        api_key = os.getenv("OPENAI_API_KEY", "")
        # 如果环境变量里没填地址，默认回退到官方地址
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        # 优先使用传参的模型名，其次选环境变量里的，最后默认用 gpt-3.5-turbo
        model_name = model or os.getenv("AI_MODEL", "gpt-3.5-turbo")

        # 初始化客户端时注入 base_url
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI 调用失败: {e}")
        raise RuntimeError(f"API 调用错误: {str(e)}")


def _call_mock(prompt: str) -> str:
    """Mock AI response for development/testing without API keys."""
    if "提取关键信息" in prompt or "extract" in prompt.lower():
        return json.dumps(
            {
                "basic_info": {
                    "name": "张三",
                    "phone": "13800138000",
                    "email": "zhangsan@example.com",
                    "address": "北京市朝阳区",
                },
                "job_intent": {"position": "后端开发工程师", "expected_salary": "25-35K"},
                "background": {
                    "years_of_experience": "3年",
                    "education": "本科",
                    "projects": ["电商平台后端系统", "微服务架构改造"],
                    "skills": ["Python", "FastAPI", "MySQL", "Redis", "Docker"],
                },
            },
            ensure_ascii=False,
        )
    else:
        return json.dumps(
            {
                "overall_score": 78,
                "skill_match": {
                    "matched": ["Python", "FastAPI", "MySQL"],
                    "missing": ["Kubernetes", "Go"],
                    "match_rate": 0.75,
                },
                "experience_relevance": 0.8,
                "ai_analysis": "候选人具备扎实的Python后端开发经验，技能与岗位需求高度匹配。有3年相关工作经验，参与过多个实际项目。",
                "recommendation": "推荐",
            },
            ensure_ascii=False,
        )


def _call_ai(prompt: str) -> str:
    """Route AI call to the configured backend."""
    backend = AI_BACKEND.lower()

    if backend == "dashscope" and DASHSCOPE_API_KEY:
        return _call_dashscope(prompt)
    elif backend == "openai" and OPENAI_API_KEY:
        return _call_openai(prompt)
    else:
        logger.warning("No AI API key configured, using mock responses")
        return _call_mock(prompt)


def _parse_json_from_response(text: str) -> dict:
    """Robustly extract JSON from AI response text."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting JSON block from markdown code fence
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding the first { ... } block
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.error(f"Failed to parse JSON from AI response: {text[:200]}")
    raise ValueError("AI returned invalid JSON response")


def extract_resume_info(resume_text: str) -> dict:
    """
    Use AI to extract structured information from resume text.
    Returns a dict conforming to ResumeData schema fields.
    """
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(resume_text=resume_text[:4000])
    raw_response = _call_ai(prompt)
    logger.debug(f"AI extraction response: {raw_response[:300]}")
    return _parse_json_from_response(raw_response)


def score_resume_match(resume_info: dict, job_description: str) -> dict:
    """
    Use AI to compute a matching score between resume and job description.
    Returns a dict conforming to MatchResult schema fields.
    """
    resume_info_str = json.dumps(resume_info, ensure_ascii=False, indent=2)
    prompt = MATCHING_PROMPT_TEMPLATE.format(
        job_description=job_description[:2000],
        resume_info=resume_info_str[:2000],
    )
    raw_response = _call_ai(prompt)
    logger.debug(f"AI scoring response: {raw_response[:300]}")
    result = _parse_json_from_response(raw_response)

    # Normalize score to 0-100 range
    score = result.get("overall_score", 0)
    if isinstance(score, float) and score <= 1.0:
        result["overall_score"] = round(score * 100, 1)

    return result
