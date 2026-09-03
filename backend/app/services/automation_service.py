"""Automation service for n8n report delivery."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional

import requests

from app.config import settings
from app.database import get_connection

logger = logging.getLogger(__name__)


class AutomationService:
    """Sends interview report delivery payloads to an n8n webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = (webhook_url or settings.n8n_webhook_url or "").strip()

    def _is_valid_email(self, email: str) -> bool:
        if not email or not isinstance(email, str):
            return False
        value = email.strip()
        # Basic email validation: must have form "something@domain.tld"
        # No spaces allowed in the entire email
        if ' ' in value:
            return False
        if '@' not in value:
            return False
        local, domain = value.rsplit('@', 1)
        # Local part must not be empty, not start/end with dot
        if not local or local[0] == '.' or local[-1] == '.':
            return False
        # Domain must have at least one dot, not be empty, not start/end with dot
        if not domain or '.' not in domain or domain[0] == '.' or domain[-1] == '.':
            return False
        # Domain parts must not be empty
        domain_parts = domain.split('.')
        if any(not part for part in domain_parts):
            return False
        return True

    def get_report_payload(
        self,
        session_id: str,
        job_role: str,
        candidate_email: str,
        report: Dict,
        pdf_download_url: str,
    ) -> Dict:
        """Build the minimal user-facing payload sent to n8n."""
        return {
            "session_id": session_id,
            "job_role": job_role,
            "candidate_email": candidate_email,
            "overall_score": int(round(float(report.get('overall_score', 0)))),
            "performance_level": report.get('performance_level', 'Developing'),
            "summary": report.get('summary', ''),
            "strengths": [
                {"skill": s.get('skill', ''), "reason": s.get('reason', '')}
                for s in report.get('strengths', [])
            ],
            "weak_areas": [
                {"skill": w.get('skill', ''), "reason": w.get('reason', ''), "priority": w.get('priority', 'Medium')}
                for w in report.get('weak_areas', [])
            ],
            "recommendations": [
                {
                    "skill": r.get('skill', ''),
                    "topic": r.get('topic', ''),
                    "action": r.get('action', ''),
                    "priority": r.get('priority', 'Medium')
                }
                for r in report.get('recommendations', [])
            ],
            "report_download_url": pdf_download_url,
        }

    def update_automation_status(self, session_id: str, status: str, email: Optional[str] = None):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE interview_reports
            SET automation_status = ?, delivery_email = ?, last_sent_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (status, email, datetime.utcnow().isoformat() if status in {'QUEUED', 'SENT'} else None, session_id),
        )
        conn.commit()
        conn.close()

    def send_report_to_n8n(
        self,
        session_id: str,
        job_role: str,
        candidate_email: str,
        report: Dict,
        pdf_download_url: str,
    ) -> Dict:
        """Send a POST request to configured n8n webhook and return status."""
        if not self.webhook_url:
            raise ValueError("n8n webhook URL is not configured")

        if not self._is_valid_email(candidate_email):
            raise ValueError("Invalid email address")

        payload = self.get_report_payload(session_id, job_role, candidate_email, report, pdf_download_url)

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=20,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json() if response.content else {}
            automation_status = str(result.get("automation_status", "queued")).upper() if isinstance(result, dict) else "QUEUED"
            self.update_automation_status(session_id, automation_status, candidate_email)
            return {
                "success": True,
                "message": "Report sent for delivery",
                "automation_status": automation_status.lower() if automation_status.lower() in {'queued', 'sent', 'failed'} else 'queued',
            }
        except requests.exceptions.Timeout:
            self.update_automation_status(session_id, 'FAILED', candidate_email)
            raise TimeoutError("n8n delivery timed out")
        except requests.exceptions.RequestException as exc:
            self.update_automation_status(session_id, 'FAILED', candidate_email)
            raise RuntimeError(f"n8n delivery failed: {exc}")


def get_automation_service() -> AutomationService:
    return AutomationService()
