from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from backend.analyzer import MAX_EMAIL_CHARS, SCORING_RULES, analyze_email, parse_eml
from backend.model import preview_model


MAX_EML_BYTES = 2 * 1024 * 1024
app = FastAPI(
    title="PhisLens Local Analysis API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_EMAIL_CHARS)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "local"}


@app.get("/api/rules")
def rules() -> dict[str, Any]:
    return {"scoring_weights": SCORING_RULES}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict[str, Any]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Paste email text before analysis.")
    try:
        report = analyze_email(text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    report["model_preview"] = preview_model(text)
    return report


@app.post("/api/analyze-eml")
async def analyze_eml(
    request: Request,
) -> dict[str, Any]:
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_EML_BYTES:
            raise HTTPException(status_code=413, detail="Email files must be 2 MB or smaller.")
        chunks.append(chunk)

    if not chunks:
        raise HTTPException(status_code=422, detail="The selected email file is empty.")

    parsed = parse_eml(b"".join(chunks))
    subject = parsed.headers.get("subject", [""])[0]
    display_text = "\n".join(part for part in (subject, parsed.body, parsed.html_body) if part)
    if not display_text.strip() and not parsed.attachments:
        raise HTTPException(status_code=422, detail="No readable email content was found in the .eml file.")

    report = analyze_email(
        display_text,
        headers=parsed.headers,
        attachments=parsed.attachments,
        html_body=parsed.html_body,
    )
    report["email"] = {
        "subject": subject,
        "from": parsed.headers.get("from", [""])[0],
        "reply_to": parsed.headers.get("reply-to", [""])[0],
        "attachment_names": parsed.attachments,
    }
    report["model_preview"] = preview_model(display_text)
    return report
