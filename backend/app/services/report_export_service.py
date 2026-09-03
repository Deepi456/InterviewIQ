"""
Report Export Service for Phase 5
Generates downloadable PDF and DOCX reports from InterviewReport data.
"""

import io
import json
from typing import Optional
import logging

from app.models.interview_models import InterviewReport

logger = logging.getLogger(__name__)


class ReportExportService:
    """Exports interview reports to PDF and DOCX formats."""

    @staticmethod
    def generate_pdf(report: InterviewReport) -> bytes:
        """
        Generate a valid multi-page PDF report containing question-by-question
        analysis and performance metrics without external binary dependencies.
        """
        try:
            def pdf_escape(value: str) -> str:
                return str(value or '').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

            def wrap_text(text: str, max_chars: int = 76) -> list:
                if not text:
                    return [""]
                out = []
                for p in str(text).split("\n"):
                    p = p.strip()
                    if not p:
                        out.append("")
                        continue
                    while len(p) > max_chars:
                        idx = p.rfind(" ", 0, max_chars)
                        if idx <= 0:
                            idx = max_chars
                        out.append(p[:idx].strip())
                        p = p[idx:].strip()
                    if p:
                        out.append(p)
                return out

            # [(font_id, font_size, text)]
            lines = []

            # Document Title
            lines.append(("/F2", 18, "InterviewIQ"))
            lines.append(("/F2", 14, "Interview Performance Report"))
            lines.append(("/F1", 10, ""))

            # Candidate & Role Metadata
            lines.append(("/F1", 10, f"Target Role: {report.job_role}"))
            lines.append(("/F1", 10, f"Interview Date: {report.interview_date}"))
            lines.append(("/F1", 10, f"Status: {report.completion_status.upper()} ({report.questions_answered} of {report.total_questions} questions answered)"))
            lines.append(("/F1", 10, "-" * 75))
            lines.append(("/F1", 10, ""))

            # Result Summary
            lines.append(("/F2", 13, "RESULT SUMMARY"))
            lines.append(("/F2", 10, f"Correct: {report.correct_count} / {report.total_questions}"))
            lines.append(("/F2", 10, f"Wrong: {report.wrong_count} / {report.total_questions}"))
            lines.append(("/F1", 10, f"Total Questions: {report.total_questions}"))
            lines.append(("/F1", 10, f"Accuracy: {report.accuracy:.1f}%"))
            lines.append(("/F1", 10, f"Overall Score: {report.overall_score:.0f}%"))
            lines.append(("/F1", 10, f"Performance Level: {report.performance_level}"))
            lines.append(("/F1", 10, "-" * 75))
            lines.append(("/F1", 10, ""))

            # Question-by-Question Review
            if report.questions:
                lines.append(("/F2", 13, "QUESTION-BY-QUESTION REVIEW"))
                lines.append(("/F1", 10, ""))
                for q in report.questions:
                    res_mark = "Correct" if q.result == "Correct" else ("Wrong" if q.result == "Wrong" else q.result)
                    score_str = f"{q.score:.1f}" if q.score is not None else "N/A"
                    lines.append(("/F2", 11, f"Question {q.question_number} [{q.skill} - {q.difficulty}] - {res_mark} (Score: {score_str}/10)"))

                    lines.append(("/F2", 10, "QUESTION:"))
                    for wl in wrap_text(q.question, 76):
                        lines.append(("/F1", 9, f"  {wl}"))

                    lines.append(("/F2", 10, "YOUR ANSWER:"))
                    for wl in wrap_text(q.candidate_answer or "(No answer provided)", 76):
                        lines.append(("/F1", 9, f"  {wl}"))

                    lines.append(("/F2", 10, "EXPECTED / CORRECT ANSWER:"))
                    for wl in wrap_text(q.expected_answer or "Evaluation unavailable — this answer has not been successfully evaluated yet.", 76):
                        lines.append(("/F1", 9, f"  {wl}"))

                    lines.append(("/F2", 10, f"RESULT: {res_mark}"))
                    lines.append(("/F2", 10, f"SCORE: {score_str}/10" if q.score is not None else "SCORE: N/A"))

                    lines.append(("/F2", 10, "EVALUATION:"))
                    for wl in wrap_text(q.evaluation or "Evaluation unavailable — this answer has not been successfully evaluated yet.", 76):
                        lines.append(("/F1", 9, f"  {wl}"))

                    if q.strengths:
                        lines.append(("/F2", 10, "WHAT YOU DID WELL:"))
                        for s in q.strengths:
                            for wl in wrap_text(f"- {s}", 74):
                                lines.append(("/F1", 9, f"  {wl}"))

                    if q.weaknesses:
                        lines.append(("/F2", 10, "WHAT TO IMPROVE:"))
                        for w in q.weaknesses:
                            for wl in wrap_text(f"- {w}", 74):
                                lines.append(("/F1", 9, f"  {wl}"))

                    if q.improvement:
                        lines.append(("/F2", 10, "HOW TO ANSWER BETTER:"))
                        for wl in wrap_text(q.improvement, 76):
                            lines.append(("/F1", 9, f"  {wl}"))

                    lines.append(("/F1", 10, "." * 75))
                    lines.append(("/F1", 10, ""))

            # Overall Performance & Guidance
            lines.append(("/F2", 13, "OVERALL PERFORMANCE & GUIDANCE"))
            if report.summary:
                lines.append(("/F2", 10, "Summary:"))
                for wl in wrap_text(report.summary, 76):
                    lines.append(("/F1", 9, f"  {wl}"))
                lines.append(("/F1", 10, ""))

            if report.skill_scores:
                lines.append(("/F2", 10, "Skill Breakdown:"))
                for skill in report.skill_scores:
                    lines.append(("/F1", 9, f"- {skill.skill}: {skill.avg_score:.1f}/10 ({skill.performance_level}) across {skill.question_count} question(s)"))
                lines.append(("/F1", 10, ""))

            if report.strengths:
                lines.append(("/F2", 10, "Strengths:"))
                for strength in report.strengths:
                    for wl in wrap_text(f"- {strength.skill}: {strength.reason}", 74):
                        lines.append(("/F1", 9, f"  {wl}"))
                lines.append(("/F1", 10, ""))

            if report.weak_areas:
                lines.append(("/F2", 10, "Areas to Improve:"))
                for weak in report.weak_areas:
                    for wl in wrap_text(f"- {weak.skill}: {weak.reason} [{weak.priority}]", 74):
                        lines.append(("/F1", 9, f"  {wl}"))
                lines.append(("/F1", 10, ""))

            if report.concept_gaps:
                lines.append(("/F2", 10, "Concept Gaps:"))
                for gap in report.concept_gaps:
                    for wl in wrap_text(f"- {gap.skill} -> {gap.concept}: {gap.reason} [{gap.priority}]", 74):
                        lines.append(("/F1", 9, f"  {wl}"))
                lines.append(("/F1", 10, ""))

            if report.recommendations:
                lines.append(("/F2", 10, "Actionable Recommendations:"))
                for i, rec in enumerate(report.recommendations[:10], 1):
                    for wl in wrap_text(f"{i}. {rec.topic}: {rec.action} [{rec.priority}]", 74):
                        lines.append(("/F1", 9, f"  {wl}"))
                lines.append(("/F1", 10, ""))

            if report.preparation_plan:
                lines.append(("/F2", 10, "Personalized Preparation Plan:"))
                for day in report.preparation_plan:
                    lines.append(("/F2", 9, f"Day {day.day}: {day.focus} ({day.estimated_hours:.1f} hours)"))
                    lines.append(("/F1", 9, f"  Topics: {', '.join(day.topics)}"))
                    lines.append(("/F1", 9, f"  Tasks: {', '.join(day.tasks)}"))
                lines.append(("/F1", 10, ""))

            # Paginate lines into pages (~44 lines per page)
            lines_per_page = 44
            pages_data = []
            for i in range(0, len(lines), lines_per_page):
                pages_data.append(lines[i:i + lines_per_page])

            if not pages_data:
                pages_data = [[("/F1", 12, "Empty Report")]]

            num_pages = len(pages_data)

            # Build PDF object table
            # Object 1: Catalog
            # Object 2: Pages
            # Object 3: Font Helvetica (/F1)
            # Object 4: Font Helvetica-Bold (/F2)
            # For each page k:
            #   Page Object: 5 + k*2
            #   Content Stream Object: 6 + k*2
            page_obj_refs = [f"{5 + k * 2} 0 R" for k in range(num_pages)]
            pages_kids_str = " ".join(page_obj_refs)

            objects = [
                '<< /Type /Catalog /Pages 2 0 R >>',
                f'<< /Type /Pages /Kids [{pages_kids_str}] /Count {num_pages} >>',
                '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
                '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
            ]

            for k, page_lines in enumerate(pages_data):
                content_ops = []
                y = 740
                for font_id, font_size, text in page_lines:
                    safe_text = pdf_escape(text)
                    content_ops.append(f"BT {font_id} {font_size} Tf 45 {y} Td ({safe_text}) Tj ET")
                    y -= 15

                content_ops.append(f"BT /F1 8 Tf 480 30 Td (Page {k + 1} of {num_pages}) Tj ET")
                stream_bytes = "\n".join(content_ops).encode('latin-1', 'replace')

                page_obj = (
                    f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
                    f'/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> '
                    f'/Contents {6 + k * 2} 0 R >>'
                )
                stream_obj = (
                    f'<< /Length {len(stream_bytes)} >>\nstream\n'
                    + stream_bytes.decode('latin-1', 'replace')
                    + '\nendstream'
                )
                objects.append(page_obj)
                objects.append(stream_obj)

            pdf = bytearray(b'%PDF-1.4\n')
            offsets = [0]
            for index, obj in enumerate(objects, 1):
                offsets.append(len(pdf))
                pdf.extend(f'{index} 0 obj\n{obj}\nendobj\n'.encode('latin-1', 'replace'))

            xref_offset = len(pdf)
            pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('latin-1', 'replace'))
            pdf.extend(b'0000000000 65535 f \n')
            for offset in offsets[1:]:
                pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
            pdf.extend(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode('latin-1', 'replace'))
            return bytes(pdf)

        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise

    @staticmethod
    def generate_docx(report: InterviewReport) -> bytes:
        """
        Generate DOCX report using a direct OOXML zip writer with full
        question-by-question review and performance details.
        """
        try:
            from io import BytesIO
            from zipfile import ZipFile, ZIP_DEFLATED
            from xml.sax.saxutils import escape

            def xml_text(value: str) -> str:
                return escape(str(value or ''))

            def build_paragraph(text: str, style: str = 'Normal') -> str:
                return (
                    f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
                    f'<w:r><w:t>{xml_text(text)}</w:t></w:r></w:p>'
                )

            sections = [
                build_paragraph('InterviewIQ', 'Title'),
                build_paragraph('Interview Performance Report', 'Subtitle'),
                build_paragraph('Interview Information'),
                build_paragraph(f"Target Role: {report.job_role}"),
                build_paragraph(f"Interview Date: {report.interview_date}"),
                build_paragraph(f"Total Questions: {report.total_questions}"),
                build_paragraph(f"Questions Answered: {report.questions_answered}"),
                build_paragraph(f"Completion Status: {report.completion_status.upper()}"),
                build_paragraph('Result Summary'),
                build_paragraph(f"Correct: {report.correct_count} / {report.total_questions}"),
                build_paragraph(f"Wrong: {report.wrong_count} / {report.total_questions}"),
                build_paragraph(f"Accuracy: {report.accuracy:.1f}%"),
                build_paragraph(f"Overall Score: {report.overall_score:.0f}%"),
                build_paragraph(f"Performance Level: {report.performance_level}"),
            ]

            if report.questions:
                sections.append(build_paragraph('Question-by-Question Review', 'Subtitle'))
                for q in report.questions:
                    res_mark = "✓ Correct" if q.result == "Correct" else ("✗ Wrong" if q.result == "Wrong" else q.result)
                    score_str = f"{q.score:.1f}" if q.score is not None else "N/A"
                    sections.extend([
                        build_paragraph(f"Question {q.question_number} [{q.skill} - {q.difficulty}]: {res_mark} (Score: {score_str}/10)"),
                        build_paragraph(f"Question: {q.question}"),
                        build_paragraph(f"Candidate Answer: {q.candidate_answer}"),
                        build_paragraph(f"Expected Answer: {q.expected_answer}"),
                        build_paragraph(f"Evaluation: {q.evaluation}"),
                    ])
                    if q.strengths:
                        sections.append(build_paragraph(f"Strengths: {', '.join(q.strengths)}"))
                    if q.weaknesses:
                        sections.append(build_paragraph(f"Areas to Improve: {', '.join(q.weaknesses)}"))
                    if q.improvement:
                        sections.append(build_paragraph(f"How to Answer Better: {q.improvement}"))

            sections.extend([
                build_paragraph('Overall Performance', 'Subtitle'),
                build_paragraph(f"Summary: {report.summary}"),
                build_paragraph('Skill Performance'),
            ])

            for skill in report.skill_scores:
                sections.append(
                    build_paragraph(
                        f"{skill.skill}: {skill.avg_score:.1f}/10 ({skill.performance_level}) across {skill.question_count} question(s)"
                    )
                )

            if report.strengths:
                sections.append(build_paragraph('Your Strengths'))
                for strength in report.strengths:
                    sections.append(build_paragraph(f"- {strength.skill}: {strength.reason}"))

            if report.weak_areas:
                sections.append(build_paragraph('Areas to Improve'))
                for weak in report.weak_areas:
                    sections.append(build_paragraph(f"- {weak.skill}: {weak.reason} [{weak.priority}]"))

            if report.concept_gaps:
                sections.append(build_paragraph('Concept Gaps'))
                for gap in report.concept_gaps:
                    sections.append(build_paragraph(f"- {gap.skill} -> {gap.concept}: {gap.reason}"))

            if report.recommendations:
                sections.append(build_paragraph('Personalized Recommendations'))
                for rec in report.recommendations[:10]:
                    sections.append(build_paragraph(f"- {rec.topic}: {rec.action} [{rec.priority}]"))

            if report.preparation_plan:
                sections.append(build_paragraph('Preparation Plan'))
                for day in report.preparation_plan:
                    sections.append(build_paragraph(f"Day {day.day}: {day.focus} ({day.estimated_hours:.1f} hours)"))
                    sections.append(build_paragraph(f"Topics: {', '.join(day.topics)}"))
                    sections.append(build_paragraph(f"Tasks: {', '.join(day.tasks)}"))

            document_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
                'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
                'xmlns:o="urn:schemas-microsoft-com:office:office" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
                'xmlns:v="urn:schemas-microsoft-com:vml" '
                'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
                'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
                'xmlns:w10="urn:schemas-microsoft-com:office:word" '
                'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
                'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" '
                'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
                'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
                'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
                'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
                'mc:Ignorable="w14 w15 wp14">'
                '<w:body>' + ''.join(sections) + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar '
                'w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" '
                'w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>'
            )

            styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:rPr><w:sz w:val="22"/></w:rPr></w:style>
</w:styles>'''

            content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''

            rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''

            core_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>InterviewIQ Report</dc:title>
  <dc:creator>InterviewIQ</dc:creator>
  <cp:lastModifiedBy>InterviewIQ</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2025-01-01T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2025-01-01T00:00:00Z</dcterms:modified>
</cp:coreProperties>'''

            app_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>InterviewIQ</Application>
</Properties>'''

            buffer = BytesIO()
            with ZipFile(buffer, 'w', compression=ZIP_DEFLATED) as zf:
                zf.writestr('[Content_Types].xml', content_types)
                zf.writestr('_rels/.rels', rels)
                zf.writestr('docProps/core.xml', core_xml)
                zf.writestr('docProps/app.xml', app_xml)
                zf.writestr('word/document.xml', document_xml)
                zf.writestr('word/styles.xml', styles_xml)

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Error generating DOCX: {e}")
            raise


def get_export_service() -> ReportExportService:
    """Factory function to create export service."""
    return ReportExportService()
