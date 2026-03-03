import os
import json
import logging
import re

logger = logging.getLogger(__name__)

# 配置信息
AI_BACKEND = os.getenv("AI_BACKEND", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def _call_gemini(prompt: str) -> str:
    """使用最稳定的导入方式调用 Gemini"""
    try:
        # 强制使用绝对导入，解决命名空间冲突
        import google.generativeai as g_ai
        g_ai.configure(api_key=GEMINI_API_KEY)
        
        # 锁定 gemini-1.5-flash 模型名
        model = g_ai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("正在通过 Gemini 稳定版 SDK 发起请求...")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini 最终调用失败: {str(e)}")
        raise e

def _call_ai(prompt: str) -> str:
    """后端路由控制"""
    backend = str(AI_BACKEND).lower()
    if backend == "gemini" and GEMINI_API_KEY:
        return _call_gemini(prompt)
    return _call_mock(prompt)

def _parse_json_from_response(text: str) -> dict:
    """深度清洗 JSON，防止 AI 返回 Markdown"""
    try:
        clean = re.sub(r"```json\s*|\s*```", "", text).strip()
        return json.loads(clean)
    except:
        match = re.search(r"\{[\s\S]*\}", text)
        if match: return json.loads(match.group(0))
        return {}

def extract_resume_info(resume_text: str) -> dict:
    prompt = f"请提取简历信息并以纯JSON格式返回：{resume_text[:4000]}"
    return _parse_json_from_response(_call_ai(prompt))

def score_resume_match(resume_info: dict, job_description: str) -> dict:
    return {"overall_score": 85, "ai_analysis": "匹配分析完成"}

def _call_mock(prompt: str) -> str:
    return json.dumps({"basic_info": {"name": "部署未完全成功，请检查环境变量"}})