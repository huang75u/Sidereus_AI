from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BasicInfo(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class JobIntent(BaseModel):
    position: Optional[str] = None
    expected_salary: Optional[str] = None


class BackgroundInfo(BaseModel):
    years_of_experience: Optional[str] = None
    education: Optional[str] = None
    projects: Optional[List[str]] = Field(default_factory=list)
    skills: Optional[List[str]] = Field(default_factory=list)


class ResumeData(BaseModel):
    resume_id: str
    basic_info: BasicInfo
    job_intent: Optional[JobIntent] = None
    background: Optional[BackgroundInfo] = None
    raw_text: Optional[str] = None
    created_at: Optional[str] = None


class MatchRequest(BaseModel):
    resume_id: str
    job_description: str


class SkillMatchDetail(BaseModel):
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    match_rate: float = 0.0


class MatchResult(BaseModel):
    resume_id: str
    job_description: str
    skill_match: SkillMatchDetail
    experience_relevance: float = 0.0
    overall_score: float = 0.0
    ai_analysis: Optional[str] = None
    recommendation: Optional[str] = None
    created_at: Optional[str] = None


class UploadResponse(BaseModel):
    success: bool
    resume_id: str
    message: str
    data: Optional[ResumeData] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None
