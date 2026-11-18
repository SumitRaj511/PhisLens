from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser, Parser
from email.utils import parseaddr
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit


MAX_EMAIL_CHARS = 300_000
URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>\"'`)\]}]+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
UNUSUAL_EXTENSION = re.compile(
    r"\.(?:zip|rar|7z|iso|img|html?|js|vbs|jse|wsf|hta|lnk|jar|ps1|reg|one|docm|xlsm|pptm)\b",
    re.IGNORECASE,
)
EXECUTABLE_EXTENSION = re.compile(
    r"\.(?:exe|scr|msi|bat|cmd|pif|dll|hta|js|vbs|ps1|jar)\b",
    re.IGNORECASE,
)
SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "rebrand.ly",
    "cutt.ly",
    "shorturl.at",
    "rb.gy",
}

SCORING_RULES = [
    {"id": "urgency", "title": "Urgency or pressure", "points": 12, "explanation": "The message pushes for immediate action or uses time pressure."},
    {"id": "account_threat", "title": "Account threat", "points": 16, "explanation": "The message threatens suspension, closure, or loss of access."},
    {"id": "password", "title": "Password request", "points": 30, "explanation": "It asks for a password or other login credentials."},
    {"id": "mfa", "title": "MFA or verification-code request", "points": 30, "explanation": "It asks for a one-time passcode, MFA approval, or verification code."},
    {"id": "payment", "title": "Payment or gift-card request", "points": 24, "explanation": "It asks for money, an unusual payment, or gift cards."},
    {"id": "bank_change", "title": "Bank-detail change", "points": 25, "explanation": "It asks to change or use new bank or payment details."},
    {"id": "confidentiality", "title": "Secrecy or confidential-information request", "points": 12, "explanation": "It asks the recipient to keep an unusual request secret or share confidential information."},
    {"id": "suspicious_url", "title": "Suspicious URL pattern", "points": 18, "explanation": "A link has a pattern often used to obscure or disguise its destination. This is a heuristic, not a reputation check."},
    {"id": "shortened_url", "title": "Shortened URL", "points": 22, "explanation": "A link uses a URL-shortening service, which hides its final destination."},
    {"id": "raw_ip", "title": "Link uses a raw IP address", "points": 30, "explanation": "A link points to a numeric internet address instead of a recognizable domain."},
    {"id": "misleading_link", "title": "Link text does not match destination", "points": 25, "explanation": "The visible domain in a link differs from its link destination."},
    {"id": "impersonation", "title": "Possible brand impersonation", "points": 15, "explanation": "The message names a known organization, but the pasted sender domain does not match its common official domains."},
    {"id": "unusual_attachment", "title": "Unusual attachment type", "points": 15, "explanation": "The message includes or mentions an archive, disk image, or script-like attachment."},
    {"id": "executable", "title": "Executable attachment", "points": 30, "explanation": "The message includes or mentions a file type that can run code on a device."},
    {"id": "macros", "title": "Request to enable macros", "points": 20, "explanation": "It asks the recipient to enable document macros or active content."},
    {"id": "invoice", "title": "Unexpected invoice language", "points": 10, "explanation": "It refers to an invoice, overdue balance, or payment due; verify expected invoices independently."},
    {"id": "credential_harvesting", "title": "Credential-harvesting language", "points": 25, "explanation": "It directs the recipient to sign in, confirm an account, or unlock access through the message."},
    {"id": "reply_mismatch", "title": "From / Reply-To mismatch", "points": 24, "explanation": "The Reply-To address differs from the sender address shown in the pasted headers."},
    {"id": "spf", "title": "SPF authentication failure", "points": 20, "explanation": "Pasted authentication headers report an SPF failure."},
    {"id": "dkim", "title": "DKIM authentication failure", "points": 16, "explanation": "Pasted authentication headers report a DKIM failure."},
    {"id": "dmarc", "title": "DMARC authentication failure", "points": 20, "explanation": "Pasted authentication headers report a DMARC failure."},
]
SCORING_BY_ID = {rule["id"]: rule for rule in SCORING_RULES}


@dataclass
class ParsedEmail:
    headers: dict[str, list[str]]
    body: str
    html_body: str
    attachments: list[str]


class EmailHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._active_link: tuple[str, list[str]] | None = None
        self._skip_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "head"}:
            self._skip_tags.append(tag)
        if tag == "a":
            href = next((value for name, value in attrs if name.lower() == "href"), None)
            self._active_link = (href or "", [])

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active_link:
            href, label_parts = self._active_link
            self.links.append((href, "".join(label_parts).strip()))
            self._active_link = None
        if self._skip_tags and tag == self._skip_tags[-1]:
            self._skip_tags.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_tags:
            return
        self.text_parts.append(data)
        if self._active_link:
            self._active_link[1].append(data)


def parse_eml(raw: bytes) -> ParsedEmail:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    headers = {
        name.lower(): [str(value) for value in message.get_all(name, [])]
        for name in ("From", "Reply-To", "To", "Subject", "Authentication-Results", "Received-SPF")
        if message.get_all(name)
    }
    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[str] = []

    for part in message.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        if filename or part.get_content_disposition() == "attachment":
            attachments.append(filename or "unnamed attachment")
            continue
        if part.get_content_type() not in {"text/plain", "text/html"}:
            continue

        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            decoded = payload.decode(charset, errors="replace")
        except LookupError:
            decoded = payload.decode("utf-8", errors="replace")
        if part.get_content_type() == "text/html":
            html_parts.append(decoded)
            parser = EmailHTMLParser()
            parser.feed(decoded)
            plain_parts.extend(parser.text_parts)
        else:
            plain_parts.append(decoded)

    return ParsedEmail(
        headers=headers,
        body="\n".join(plain_parts),
        html_body="\n".join(html_parts),
        attachments=attachments,
    )


def parse_pasted_headers(text: str) -> dict[str, list[str]]:
    header_block = re.split(r"\r?\n\r?\n", text, maxsplit=1)[0]
    if not re.search(r"^(?:From|Reply-To|To|Subject|Authentication-Results|Received-SPF)\s*:", header_block, re.IGNORECASE | re.MULTILINE):
        return {}
    parsed = Parser(policy=policy.default).parsestr(f"{header_block}\n\n")
    wanted = {"from", "reply-to", "to", "subject", "authentication-results", "received-spf"}
    return {
        name.lower(): [str(value) for value in parsed.get_all(name, [])]
        for name in wanted
        if parsed.get_all(name)
    }


def analyze_email(
    text: str,
    headers: dict[str, list[str]] | None = None,
    attachments: list[str] | None = None,
    html_body: str = "",
) -> dict[str, Any]:
    if len(text) > MAX_EMAIL_CHARS:
        raise ValueError(f"Email text must be {MAX_EMAIL_CHARS:,} characters or fewer.")
    headers = headers if headers is not None else parse_pasted_headers(text)
    attachments = attachments or []
    header_text = "\n".join(
        f"{name}: {value}"
        for name, values in headers.items()
        for value in values
    )
    combined = "\n".join(part for part in (header_text, text, html_body, *attachments) if part)
    findings: list[dict[str, Any]] = []
    found: set[str] = set()

    def add(rule_id: str, evidence: str = "") -> None:
        if rule_id in found:
            return
        found.add(rule_id)
        rule = SCORING_BY_ID[rule_id]
        findings.append({
            "id": rule_id,
            "title": rule["title"],
            "points": rule["points"],
            "explanation": rule["explanation"],
            "evidence": evidence[:220],
        })

    checks = [
        ("urgency", r"\b(?:urgent(?:ly)?|immediately|act now|asap|within\s+\d+\s*(?:hours?|minutes?)|expires? (?:today|soon)|final notice|do not delay|time[- ]sensitive)\b"),
        ("account_threat", r"\b(?:account|mailbox|profile|service).{0,45}\b(?:suspend(?:ed|ing)?|suspens(?:ion|ions)?|clos(?:e|ed|ure)|deactivat(?:e|ed|ion)|terminat(?:e|ed|ion)|lock(?:ed|out)?)\b|\b(?:suspend|suspension|close|deactivate|terminate|lock).{0,40}\b(?:account|mailbox|profile|access)\b"),
        ("password", r"\b(?:send|share|reply with|provide|enter|confirm|verify|submit).{0,50}\b(?:your )?(?:password|passphrase|login credentials)\b|\bpassword\s+(?:is|=)\s*[\w!@#$%]"),
        ("mfa", r"\b(?:mfa|2fa|one[- ]time|verification|authentication|security)\s*(?:code|passcode|token)\b|\b(?:code|passcode).{0,35}\b(?:mfa|verification|authentication|login|sign[- ]in)\b|\bapprove (?:the )?(?:mfa|sign[- ]in|login)\b"),
        ("payment", r"\b(?:gift cards?|itunes cards?|google play cards?|steam cards?|wire transfer|pay(?:ment)? (?:now|today|immediately)|bitcoin|cryptocurrency|send (?:the )?money|re[- ]?delivery fee)\b"),
        ("bank_change", r"\b(?:bank|banking|payment|wire|account) details?\s+(?:have |has )?(?:changed|chang(?:e|ing))\b|\bnew (?:bank|wire|payment) (?:account|details|instructions)\b|\b(?:change|update|replace).{0,35}\b(?:bank|routing|account|payment) details\b"),
        ("confidentiality", r"\b(?:keep (?:this|it) confidential|keep (?:this|it) secret|do not (?:tell|discuss|share)|don't (?:tell|discuss|share)|confidential information|share sensitive information|keep this within)\b"),
        ("macros", r"\b(?:enable|allow|turn on|activate).{0,40}\bmacros?\b|\bmacros?.{0,40}\b(?:enable|allow|activate)\b|\b(?:enable|allow) editing\b"),
        ("invoice", r"\b(?:invoice|overdue balance|payment due|past due|outstanding balance|late fee)\b"),
        ("credential_harvesting", r"\b(?:verify|confirm|restore|unlock|validate|secure).{0,40}\b(?:your )?(?:account|identity|mailbox|credentials|sign[- ]?in)\b|\b(?:sign in|log ?in).{0,40}\b(?:confirm|verify|restore|unlock|secure)\b"),
    ]
    for rule_id, pattern in checks:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            add(rule_id, match.group(0))

    links = extract_links(combined, html_body)
    if links:
        shortened = next((link for link in links if is_shortened(link["hostname"])), None)
        if shortened:
            add("shortened_url", shortened["url"])
        raw_ip = next((link for link in links if is_ip_address(link["hostname"])), None)
        if raw_ip:
            add("raw_ip", raw_ip["url"])
        suspicious = next((link for link in links if is_suspicious_url(link)), None)
        if suspicious:
            add("suspicious_url", suspicious["url"])
        misleading = next((link for link in links if link.get("mismatch")), None)
        if misleading:
            add("misleading_link", f"Visible: {misleading['visible']} → destination: {misleading['hostname']}")

    impersonation = detect_brand_mismatch(combined, headers)
    if impersonation:
        add("impersonation", impersonation)
    elif re.search(
        r"\b(?:we are|i am|this is|on behalf of).{0,45}\b(?:microsoft|paypal|amazon|apple|google|it department|help ?desk|ceo|director|supplier|vendor|courier|delivery team)\b",
        combined,
        re.IGNORECASE,
    ):
        match = re.search(
            r"\b(?:we are|i am|this is|on behalf of).{0,45}\b(?:microsoft|paypal|amazon|apple|google|it department|help ?desk|ceo|director|supplier|vendor|courier|delivery team)\b",
            combined,
            re.IGNORECASE,
        )
        add("impersonation", match.group(0) if match else "")

    mentioned_files = list(dict.fromkeys(
        [match.group(0) for match in UNUSUAL_EXTENSION.finditer(combined)]
        + [match.group(0) for match in EXECUTABLE_EXTENSION.finditer(combined)]
        + attachments
    ))
    unusual_files = [name for name in mentioned_files if UNUSUAL_EXTENSION.search(name)]
    executable_files = [name for name in mentioned_files if EXECUTABLE_EXTENSION.search(name)]
    if unusual_files:
        add("unusual_attachment", ", ".join(dict.fromkeys(unusual_files)))
    if executable_files:
        add("executable", ", ".join(dict.fromkeys(executable_files)))

    from_address = get_header_address(headers, "from")
    reply_to = get_header_address(headers, "reply-to")
    if from_address and reply_to and from_address.casefold() != reply_to.casefold():
        add("reply_mismatch", f"From: {from_address} | Reply-To: {reply_to}")

    authentication_results = " ".join(
        value
        for header_name in ("authentication-results", "received-spf")
        for value in headers.get(header_name, [])
    )
    for auth_id in ("spf", "dkim", "dmarc"):
        match = re.search(rf"\b{auth_id}\s*=\s*(fail|softfail|permerror)\b", authentication_results, re.IGNORECASE)
        if auth_id == "spf" and not match:
            received_spf = " ".join(headers.get("received-spf", []))
            match = re.search(r"\b(fail|softfail|permerror)\b", received_spf, re.IGNORECASE)
        if match:
            add(auth_id, f"{auth_id.upper()}={match.group(1).lower()}")

    total_points = sum(finding["points"] for finding in findings)
    score = min(total_points, 100)
    if score >= 55:
        classification = "High Risk"
        summary = "Several strong warning signs were detected. Treat this message with caution."
    elif score >= 25:
        classification = "Suspicious"
        summary = "Warning signs were detected. Verify the message independently before acting."
    else:
        classification = "Low Risk"
        summary = "Few listed warning signs were detected. This is not proof the email is safe."

    return {
        "score": score,
        "raw_points": total_points,
        "score_capped": total_points > 100,
        "classification": classification,
        "summary": summary,
        "findings": findings,
        "recommendations": build_recommendations(found, score),
        "scoring_weights": [
            {"id": rule["id"], "title": rule["title"], "points": rule["points"]}
            for rule in SCORING_RULES
        ],
    }


def extract_links(text: str, html_body: str = "") -> list[dict[str, str | bool]]:
    raw_urls = {trim_url(value) for value in URL_PATTERN.findall(text)}
    anchor_parser = EmailHTMLParser()
    if html_body:
        anchor_parser.feed(html_body)
    else:
        anchor_parser.feed(text)
    anchor_map: dict[str, str] = {}
    for href, label in anchor_parser.links:
        destination = parse_url(href)
        visible = extract_visible_domain(label)
        if destination and visible and not domains_match(destination["hostname"], visible):
            anchor_map[destination["url"]] = visible
        if destination:
            raw_urls.add(destination["url"])

    results: list[dict[str, str | bool]] = []
    for raw_url in sorted(value for value in raw_urls if value):
        parsed = parse_url(raw_url)
        if not parsed:
            continue
        visible = anchor_map.get(parsed["url"], "")
        results.append({
            **parsed,
            "visible": visible,
            "mismatch": bool(visible),
        })

    markdown_links = re.finditer(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", text, re.IGNORECASE)
    for match in markdown_links:
        destination = parse_url(match.group(2))
        visible = extract_visible_domain(match.group(1))
        if destination and visible and not domains_match(destination["hostname"], visible):
            existing = next((link for link in results if link["url"] == destination["url"]), None)
            if existing:
                existing["visible"] = visible
                existing["mismatch"] = True
            else:
                results.append({**destination, "visible": visible, "mismatch": True})
    return results


def parse_url(value: str) -> dict[str, str] | None:
    normalized = value if re.match(r"^(?:https?://)", value, re.IGNORECASE) else f"http://{value}"
    try:
        parsed = urlsplit(normalized)
        hostname = (parsed.hostname or "").rstrip(".").lower()
        if parsed.scheme not in {"http", "https"} or not hostname:
            return None
        return {
            "url": normalized,
            "hostname": hostname,
            "scheme": parsed.scheme.lower(),
            "username": parsed.username or "",
            "password": parsed.password or "",
        }
    except ValueError:
        return None


def trim_url(value: str) -> str:
    return value.rstrip(".,!?;:")


def is_shortened(hostname: str) -> bool:
    return hostname in SHORTENERS or any(hostname.endswith(f".{domain}") for domain in SHORTENERS)


def is_ip_address(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def is_suspicious_url(link: dict[str, str]) -> bool:
    hostname = link["hostname"]
    if link["scheme"] == "http" or link["username"] or link["password"]:
        return True
    if hostname.startswith("xn--") or ".xn--" in hostname:
        return True
    if len(hostname.split(".")) >= 5:
        return True
    if re.search(r"\b(?:login|verify|secure|account|update|auth|payment)\b", hostname):
        return True
    return False


def extract_visible_domain(value: str) -> str:
    match = re.search(
        r"(?:https?://)?(?:www\.)?([a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,})(?:[/:?#\s]|$)",
        value,
        re.IGNORECASE,
    )
    return match.group(1).lower() if match else ""


def domains_match(hostname: str, visible: str) -> bool:
    return (
        hostname == visible
        or hostname.endswith(f".{visible}")
        or visible.endswith(f".{hostname}")
    )


def detect_brand_mismatch(text: str, headers: dict[str, list[str]]) -> str:
    from_address = get_header_address(headers, "from")
    if not from_address:
        return ""
    sender_domain = from_address.rsplit("@", 1)[-1].lower()
    trusted_domains = {
        "microsoft": ("microsoft.com", "office.com", "outlook.com"),
        "paypal": ("paypal.com",),
        "amazon": ("amazon.com", "amazon.co.uk"),
        "apple": ("apple.com",),
        "google": ("google.com", "gmail.com"),
    }
    for brand, domains in trusted_domains.items():
        if re.search(rf"\b{brand}\b", text, re.IGNORECASE) and not any(
            sender_domain == domain or sender_domain.endswith(f".{domain}")
            for domain in domains
        ):
            return f"Message mentions {brand.title()}, but the sender address is {from_address}."
    return ""


def get_header_address(headers: dict[str, list[str]], name: str) -> str:
    values = headers.get(name.lower(), [])
    if not values:
        return ""
    address = parseaddr(values[0])[1]
    match = EMAIL_PATTERN.search(address or values[0])
    return match.group(0).lower() if match else ""


def build_recommendations(found: set[str], score: int) -> list[dict[str, str]]:
    actions = [
        {
            "when": {"password", "mfa"},
            "text": "Do not share passwords or verification codes. If you already did, change your password through the official site or app and contact your IT/security team.",
        },
        {
            "when": {"payment", "bank_change", "invoice", "confidentiality"},
            "text": "Independently verify payment or bank-detail requests with a known contact. If money was sent, contact your bank using its official number immediately.",
        },
        {
            "when": {"unusual_attachment", "executable", "macros"},
            "text": "Do not open the attachment or enable macros. Report the message through your organisation’s normal security process.",
        },
        {
            "when": {"suspicious_url", "shortened_url", "raw_ip", "misleading_link", "credential_harvesting"},
            "text": "Do not click the link or enter credentials. Navigate to the organisation’s official website or app yourself.",
        },
        {
            "when": {"reply_mismatch", "spf", "dkim", "dmarc", "impersonation"},
            "text": "Verify the sender using contact details you already know are genuine; authentication failures and address mismatches need context.",
        },
    ]
    recommendations = [
        {"text": action["text"], "supported_by": sorted(found.intersection(action["when"]))}
        for action in actions
        if found.intersection(action["when"])
    ]
    if score >= 25:
        recommendations.insert(0, {
            "text": "Pause. Do not reply, click suspicious links, or open attachments while you verify the message.",
            "supported_by": [],
        })
    if not recommendations:
        recommendations.append({
            "text": "No common warning signs were found, but stay cautious. Confirm unexpected requests through a known official channel.",
            "supported_by": [],
        })
    return recommendations
