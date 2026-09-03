"""Grounded resume extraction, matching, tailoring, and PDF export."""

import io
import re
import uuid
from typing import Dict

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


COMMON_TERMS = {
    "python", "java", "javascript", "typescript", "react", "node.js", "sql", "excel", "pandas", "numpy",
    "statistics", "machine learning", "deep learning", "docker", "aws", "azure", "gcp", "fastapi", "spring",
    "express", "rest", "api", "git", "tableau", "power bi", "tensorflow", "pytorch", "kubernetes", "nlp",
}


class ResumeService:
    def __init__(self):
        self.documents: Dict[str, Dict] = {}

    @staticmethod
    def extract_keywords(text: str):
        normalized = text.lower()
        found = [term for term in sorted(COMMON_TERMS, key=len, reverse=True) if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized)]
        return found

    def tailor(self, resume_text: str, job_description: str) -> Dict:
        resume_terms = self.extract_keywords(resume_text)
        job_terms = self.extract_keywords(job_description)
        strong = [term for term in job_terms if term in resume_terms]
        gaps = [term for term in job_terms if term not in resume_terms]
        score = round(len(strong) / len(job_terms) * 100) if job_terms else 0
        sections = re.split(r"\n\s*(?=[A-Z][A-Z &/]{2,}\s*$)", resume_text.strip(), flags=re.MULTILINE)
        summary = "Professional summary tailored to the target role, based only on the experience and skills documented below."
        tailored = f"PROFESSIONAL SUMMARY\n{summary}\n\nRELEVANT SKILLS\n{', '.join(strong) if strong else 'See original resume'}\n\nORIGINAL EXPERIENCE AND PROJECTS\n{resume_text.strip()}"
        recommendations = ([f"Emphasize documented experience with {term}." for term in strong[:4]] or ["Add specific evidence from the original resume to strengthen the match."])
        result = {"tailoring_id": str(uuid.uuid4()), "job_match_score": score, "strong_matches": strong, "skill_gaps": gaps, "recommendations": recommendations, "tailored_resume": tailored}
        self.documents[result["tailoring_id"]] = result
        return result

    @staticmethod
    def generate_pdf(text: str) -> bytes:
        output = io.BytesIO()
        document = SimpleDocTemplate(output, pagesize=LETTER, rightMargin=.7 * inch, leftMargin=.7 * inch, topMargin=.65 * inch, bottomMargin=.65 * inch)
        styles = getSampleStyleSheet()
        story = []
        for index, block in enumerate(text.split("\n")):
            if not block.strip():
                story.append(Spacer(1, 7))
            else:
                style = styles["Heading2"] if index == 0 or block.isupper() and len(block) < 45 else styles["BodyText"]
                story.append(Paragraph(block.replace("&", "&amp;"), style))
                story.append(Spacer(1, 3))
        document.build(story)
        return output.getvalue()


_service = ResumeService()


def get_resume_service():
    return _service