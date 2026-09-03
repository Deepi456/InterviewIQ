"""
Interview Report API Endpoints for Phase 5 and Phase 6.
Provides report generation, retrieval, export, and email delivery automation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import logging
import re
import io

from app.models.interview_models import (
    InterviewReport,
    SendReportRequest
)
from app.services.report_service import get_report_service
from app.services.report_export_service import get_export_service
from app.services.question_repository import get_question_repository
from app.services.automation_service import get_automation_service
from app.database import DB_PATH, get_connection
from app.config import settings
from app.auth import assert_session_owner, require_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/interview",
    tags=["interview-reports"]
)


@router.get(
    "/{session_id}/report",
    response_model=InterviewReport
)
async def get_report(
    session_id: str,
    preparation_days: int = Query(
        5,
        ge=1,
        le=14,
        description="Number of days in preparation plan"
    ),
    current_user=Depends(require_current_user),
):
    """
    Get or generate interview performance report.

    If report exists, returns cached report.
    If not, generates new report with AI analysis.
    """

    try:
        assert_session_owner(session_id, current_user)
        question_repo = get_question_repository()

        report_service = get_report_service(
            str(DB_PATH),
            question_repo
        )

        report = report_service.generate_report(
            session_id,
            preparation_days
        )

        return report

    except ValueError as e:
        logger.error(
            f"Report retrieval error: {e}"
        )

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating report: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to generate report"
        )


@router.post(
    "/{session_id}/report/regenerate",
    response_model=InterviewReport
)
async def regenerate_report(
    session_id: str,
    preparation_days: int = Query(
        5,
        ge=1,
        le=14,
        description="Number of days in preparation plan"
    ),
    current_user=Depends(require_current_user),
):
    """
    Force regenerate report, bypassing cache.
    """

    try:
        assert_session_owner(session_id, current_user)
        question_repo = get_question_repository()

        report_service = get_report_service(
            str(DB_PATH),
            question_repo
        )

        report = report_service.regenerate_report(
            session_id,
            preparation_days
        )

        return report

    except ValueError as e:
        logger.error(
            f"Report regeneration error: {e}"
        )

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error regenerating report: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to regenerate report"
        )


@router.get(
    "/{session_id}/report/download/pdf"
)
async def download_pdf_report(
    session_id: str,
    preparation_days: int = Query(
        5,
        ge=1,
        le=14,
        description="Number of days in preparation plan"
    ),
    current_user=Depends(require_current_user),
):
    """
    Download interview report as PDF.
    """

    try:
        assert_session_owner(session_id, current_user)
        question_repo = get_question_repository()

        report_service = get_report_service(
            str(DB_PATH),
            question_repo
        )

        report = report_service.generate_report(
            session_id,
            preparation_days
        )

        export_service = get_export_service()

        pdf_bytes = export_service.generate_pdf(
            report
        )

        if not pdf_bytes:
            raise ValueError(
                "PDF report could not be generated"
            )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f"filename=InterviewIQ_Report_"
                    f"{session_id}.pdf"
                )
            }
        )

    except ValueError as e:
        logger.error(
            f"PDF download error: {e}"
        )

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating PDF: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to generate PDF report"
        )


@router.get(
    "/{session_id}/report/download/docx"
)
async def download_docx_report(
    session_id: str,
    preparation_days: int = Query(
        5,
        ge=1,
        le=14,
        description="Number of days in preparation plan"
    ),
    current_user=Depends(require_current_user),
):
    """
    Download interview report as DOCX.
    """

    try:
        assert_session_owner(session_id, current_user)
        question_repo = get_question_repository()

        report_service = get_report_service(
            str(DB_PATH),
            question_repo
        )

        report = report_service.generate_report(
            session_id,
            preparation_days
        )

        export_service = get_export_service()

        docx_bytes = export_service.generate_docx(
            report
        )

        if not docx_bytes:
            raise ValueError(
                "DOCX report could not be generated"
            )

        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type=(
                "application/vnd.openxmlformats-"
                "officedocument.wordprocessingml.document"
            ),
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f"filename=InterviewIQ_Report_"
                    f"{session_id}.docx"
                )
            }
        )

    except ValueError as e:
        logger.error(
            f"DOCX download error: {e}"
        )

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating DOCX: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to generate DOCX report"
        )


@router.get(
    "/{session_id}/report/pdf"
)
async def get_report_pdf_only(
    session_id: str,
    current_user=Depends(require_current_user),
):
    """
    Return only the generated PDF for a specific session.
    """

    try:
        assert_session_owner(session_id, current_user)
        question_repo = get_question_repository()

        report_service = get_report_service(
            str(DB_PATH),
            question_repo
        )

        report = report_service.generate_report(
            session_id
        )

        export_service = get_export_service()

        pdf_bytes = export_service.generate_pdf(
            report
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f"filename=InterviewIQ_Report_"
                    f"{session_id}.pdf"
                )
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"PDF retrieval error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve PDF report"
        )


@router.post(
    "/{session_id}/send-report"
)
async def send_report_by_email(
    session_id: str,
    payload: SendReportRequest,
    current_user=Depends(require_current_user),
):
    """
    Send interview report to configured n8n webhook.
    """

    try:
        assert_session_owner(session_id, current_user)
        question_repo = get_question_repository()

        report_service = get_report_service(
            str(DB_PATH),
            question_repo
        )

        automation_service = get_automation_service()

        # ----------------------------------------------------------
        # Validate interview session
        # ----------------------------------------------------------

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM interview_sessions
            WHERE session_id = ?
            """,
            (session_id,)
        )
        session = cursor.fetchone()

        if not session:
            conn.close()

            raise ValueError(
                f"Session not found: {session_id}"
            )

        if session["status"] != "completed":
            conn.close()
            conn.close()

            raise ValueError(
                f"Interview not completed: {session_id}"
            )

        conn.close()

        # ----------------------------------------------------------
        # Generate report
        # ----------------------------------------------------------

        report = report_service.generate_report(
            session_id
        )

        # The first delivery request may also create the cached report.
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM interview_reports
            WHERE session_id = ?
            """,
            (session_id,)
        )
        report_row = cursor.fetchone()
        conn.close()

        if not report_row:
            raise ValueError(
                f"Report not found for session: {session_id}"
            )

        report_dict = report.dict()

        # ----------------------------------------------------------
        # Validate candidate email
        # ----------------------------------------------------------

        candidate_email = (
            payload.candidate_email.strip()
        )

        if not re.match(
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            candidate_email
        ):
            raise ValueError(
                "Invalid email address"
            )

        # ----------------------------------------------------------
        # Prevent accidental duplicate delivery
        # ----------------------------------------------------------

        if (
            report_row["automation_status"] == "SENT"
            and not payload.resend
        ):
            raise ValueError(
                "Report has already been sent to this candidate"
            )

        # ----------------------------------------------------------
        # Generate PDF
        # ----------------------------------------------------------

        export_service = get_export_service()

        pdf_bytes = export_service.generate_pdf(
            report
        )

        if len(pdf_bytes) <= 0:
            raise ValueError(
                "PDF report not available for delivery"
            )

        # ----------------------------------------------------------
        # PUBLIC PDF URL
        #
        # IMPORTANT:
        # n8n is running in the cloud, so localhost will NOT work.
        # ----------------------------------------------------------

        public_api_base_url = settings.public_api_base_url.rstrip("/")

        pdf_url = (
            f"{public_api_base_url}"
            f"/api/interview/"
            f"{session_id}"
            f"/report/pdf"
        )

        logger.info(
            f"Using public PDF URL: {pdf_url}"
        )

        # ----------------------------------------------------------
        # Send report to n8n
        # ----------------------------------------------------------

        result = (
            automation_service.send_report_to_n8n(
                session_id=session_id,
                job_role=report.job_role,
                candidate_email=candidate_email,
                report=report_dict,
                pdf_download_url=pdf_url,
            )
        )

        return {
            "success": result["success"],
            "message": result["message"],
            "automation_status": result[
                "automation_status"
            ],
        }

    except ValueError as e:
        logger.error(
            f"Automation error: {e}"
        )

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except TimeoutError as e:
        logger.error(
            f"n8n timeout: {e}"
        )

        raise HTTPException(
            status_code=504,
            detail="n8n delivery timed out"
        )

    except RuntimeError as e:
        logger.error(
            f"n8n delivery error: {e}"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Report could not be delivered right now"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected automation error: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to send report"
        )