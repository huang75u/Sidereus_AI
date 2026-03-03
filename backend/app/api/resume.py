import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, File, UploadFile, HTTPException, status

from app.models.schemas import UploadResponse, ResumeData, BasicInfo, JobIntent, BackgroundInfo, ErrorResponse
from app.services.pdf_parser import extract_text_from_pdf, clean_and_structure_text
from app.services.ai_service import extract_resume_info
from app.services.cache_service import cache_resume, get_cached_resume

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE_MB = 10
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="上传简历 PDF",
    description="上传单个 PDF 格式简历，自动解析并提取关键信息",
)
async def upload_resume(file: UploadFile = File(..., description="PDF 格式简历文件")):
    # Validate file type
    content_type = file.content_type or ""
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf") and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 PDF 格式文件",
        )

    # Read file bytes
    file_bytes = await file.read()

    # Validate file size
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE_MB}MB）",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传的文件为空",
        )

    # Step 1: Extract text from PDF
    try:
        raw_text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="无法从 PDF 中提取文本，请确认文件非扫描版",
        )

    # Step 2: Clean and structure text
    cleaned_text = clean_and_structure_text(raw_text)

    # Step 3: AI extraction
    try:
        extracted = extract_resume_info(cleaned_text)
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        # Return partial result without AI extraction
        extracted = {
            "basic_info": {},
            "job_intent": {},
            "background": {"projects": [], "skills": []},
        }

    # Step 4: Build structured response
    resume_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    basic_raw = extracted.get("basic_info", {})
    job_raw = extracted.get("job_intent", {})
    bg_raw = extracted.get("background", {})

    resume_data = ResumeData(
        resume_id=resume_id,
        basic_info=BasicInfo(
            name=basic_raw.get("name"),
            phone=basic_raw.get("phone"),
            email=basic_raw.get("email"),
            address=basic_raw.get("address"),
        ),
        job_intent=JobIntent(
            position=job_raw.get("position"),
            expected_salary=job_raw.get("expected_salary"),
        ),
        background=BackgroundInfo(
            years_of_experience=bg_raw.get("years_of_experience"),
            education=bg_raw.get("education"),
            projects=bg_raw.get("projects", []),
            skills=bg_raw.get("skills", []),
        ),
        raw_text=cleaned_text[:2000],  # Store first 2000 chars for matching
        created_at=now,
    )

    # Step 5: Cache the result
    cache_resume(resume_id, resume_data.model_dump())

    logger.info(f"Resume processed successfully: {resume_id}")
    return UploadResponse(
        success=True,
        resume_id=resume_id,
        message="简历解析成功",
        data=resume_data,
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeData,
    summary="获取已解析简历",
    description="根据 resume_id 获取已解析的简历数据",
)
async def get_resume(resume_id: str):
    cached = get_cached_resume(resume_id)
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"简历 {resume_id} 不存在或已过期",
        )
    return ResumeData(**cached)
