import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import MatchRequest, MatchResult, SkillMatchDetail
from app.services.ai_service import score_resume_match
from app.services.cache_service import get_cached_resume, cache_match_result, get_cached_match

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=MatchResult,
    summary="简历与岗位匹配评分",
    description="将已解析的简历与岗位需求进行 AI 匹配分析，返回详细评分",
)
async def match_resume(request: MatchRequest):
    if not request.job_description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="岗位需求描述不能为空",
        )

    # Check if resume exists
    resume_data = get_cached_resume(request.resume_id)
    if not resume_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"简历 {request.resume_id} 不存在或已过期，请重新上传",
        )

    # Check cached match result to avoid duplicate AI calls
    cached_match = get_cached_match(request.resume_id, request.job_description)
    if cached_match:
        logger.info(f"Returning cached match for resume {request.resume_id}")
        return MatchResult(**cached_match)

    # Prepare resume info for AI scoring
    resume_info = {
        "basic_info": resume_data.get("basic_info", {}),
        "job_intent": resume_data.get("job_intent", {}),
        "background": resume_data.get("background", {}),
        "raw_text_excerpt": (resume_data.get("raw_text") or "")[:1000],
    }

    # AI-powered matching
    try:
        match_raw = score_resume_match(resume_info, request.job_description)
    except Exception as e:
        logger.error(f"AI matching failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 评分服务暂时不可用: {str(e)}",
        )

    # Build structured result
    skill_raw = match_raw.get("skill_match", {})
    now = datetime.now(timezone.utc).isoformat()

    match_result = MatchResult(
        resume_id=request.resume_id,
        job_description=request.job_description[:500],
        skill_match=SkillMatchDetail(
            matched=skill_raw.get("matched", []),
            missing=skill_raw.get("missing", []),
            match_rate=float(skill_raw.get("match_rate", 0.0)),
        ),
        experience_relevance=float(match_raw.get("experience_relevance", 0.0)),
        overall_score=float(match_raw.get("overall_score", 0.0)),
        ai_analysis=match_raw.get("ai_analysis"),
        recommendation=match_raw.get("recommendation"),
        created_at=now,
    )

    # Cache the match result
    cache_match_result(request.resume_id, request.job_description, match_result.model_dump())

    logger.info(f"Match completed for resume {request.resume_id}, score={match_result.overall_score}")
    return match_result
