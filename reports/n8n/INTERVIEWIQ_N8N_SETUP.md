# InterviewIQ n8n Setup Guide

## Overview
This workflow receives a POST JSON payload from InterviewIQ after a report is generated and sends an email to the candidate with the generated PDF attached.

## Required environment variable
Set this in the backend environment before running the app:

N8N_WEBHOOK_URL=https://your-n8n-instance.example.com/webhook/interviewiq-report

Do not expose the Gemini API key, internal prompts, or any hidden reasoning in the payload.

---

## n8n workflow

Create a new workflow in n8n with the following steps:

1. Webhook
   - Method: POST
   - Response Mode: Respond immediately
   - Authentication: none (unless your instance requires it)
   - JSON body: accepted

2. Validate Payload
   - Check that the request contains:
     - session_id
     - job_role
     - candidate_email
     - overall_score
     - performance_level
     - summary
     - report_download_url
   - If missing, stop and return a structured error response.

3. Prepare Email
   - Build email subject:
     `InterviewIQ — Your Interview Performance Report`
   - Build email body:

```
Hi,

Your InterviewIQ mock interview has been completed.

Overall Score:
78%

Performance:
Developing

Strong Areas:
- Python
- Machine Learning

Areas to Improve:
- SQL
- Statistics

Your personalized interview report is attached.

Best,
InterviewIQ
```

4. Send Email
   - Use an email node such as SMTP, Gmail, SendGrid, or another configured provider.
   - Set the recipient from `candidate_email`.
   - Attach the PDF using the `report_download_url` value by fetching it via HTTP Request.

5. Log Delivery
   - Store a success/failure result in your n8n execution log.
   - Return a JSON status like:

```json
{
  "success": true,
  "automation_status": "queued"
}
```

---

## Expected webhook payload

InterviewIQ will send a POST body like this:

```json
{
  "session_id": "a1b2c3",
  "job_role": "Backend Engineer",
  "candidate_email": "candidate@example.com",
  "overall_score": 78,
  "performance_level": "Developing",
  "summary": "You performed well in core backend reasoning but need stronger SQL and systems depth.",
  "strengths": [
    { "skill": "Python", "reason": "Strong coding fundamentals" }
  ],
  "weak_areas": [
    { "skill": "SQL", "reason": "Needs more optimization practice", "priority": "High" }
  ],
  "recommendations": [
    { "skill": "SQL", "topic": "Indexes", "action": "Practice query optimization", "priority": "High" }
  ],
  "report_download_url": "http://localhost:8000/api/interview/a1b2c3/report/pdf"
}
```

---

## PDF attachment method

The PDF should be fetched from the controlled endpoint on the InterviewIQ backend:

`GET /api/interview/{session_id}/report/pdf`

This endpoint is intentionally restricted to the session report and returns only the generated PDF file. It does not expose arbitrary filesystem paths or internal data.

---

## Notes

- Use the delivered `candidate_email` only for the email recipient.
- Do not send internal reasoning or hidden prompts.
- Do not expose the n8n webhook secret in the frontend or public docs.
- If the email provider is unavailable, the Report could not be delivered right now message should be returned to the user.
