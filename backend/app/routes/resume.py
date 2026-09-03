"""AI Coach resume tailoring endpoints."""

import io
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from app.auth import require_current_user
from app.models.resume_models import ResumeTextRequest, ResumeTailorResponse
from app.services.resume_service import get_resume_service

router = APIRouter(prefix="/api/coach/resume", tags=["ai-coach"])


def _extract_upload(upload: UploadFile, content: bytes) -> str:
    name = (upload.filename or "").lower()
    if name.endswith(".docx"):
        from docx import Document
        return "\n".join(paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs if paragraph.text.strip())
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
        except ImportError as exc:
            raise HTTPException(503, "PDF extraction is unavailable. Paste the resume text or install the PDF extractor.") from exc
    raise HTTPException(400, "Resume must be a PDF or DOCX file.")


@router.post("/tailor", response_model=ResumeTailorResponse)
async def tailor_resume(resume: UploadFile = File(...), job_description: str = Form(...), current_user=Depends(require_current_user)):
    if not job_description.strip():
        raise HTTPException(400, "Job description cannot be empty.")
    text = _extract_upload(resume, await resume.read())
    if len(text.strip()) < 40:
        raise HTTPException(400, "The resume does not contain enough readable text.")
    return get_resume_service().tailor(text, job_description)


@router.post("/tailor-text", response_model=ResumeTailorResponse)
def tailor_resume_text(request: ResumeTextRequest, current_user=Depends(require_current_user)):
    return get_resume_service().tailor(request.resume_text, request.job_description)


@router.get("/{tailoring_id}/pdf")
def download_tailored_resume(tailoring_id: str, current_user=Depends(require_current_user)):
    document = get_resume_service().documents.get(tailoring_id)
    if not document:
        raise HTTPException(404, "Tailored resume not found.")
    return StreamingResponse(io.BytesIO(get_resume_service().generate_pdf(document["tailored_resume"])), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="InterviewIQ_Tailored_Resume_{tailoring_id}.pdf"'})