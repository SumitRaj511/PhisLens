import unittest
from email.message import EmailMessage

from backend.analyzer import analyze_email, parse_eml, parse_pasted_headers


class AnalyzerTests(unittest.TestCase):
    def test_evidence_records_each_detected_signal_with_points(self):
        message = """From: Microsoft Help Desk <notice@example.net>
Reply-To: reply@example.org
Authentication-Results: mx.example; spf=fail; dkim=fail; dmarc=fail
Subject: URGENT account suspension

Confirm your account now. Reply with your password and MFA verification code.
Keep this confidential. Pay with gift cards and use the new bank details.
https://bit.ly/demo http://192.0.2.10 [accounts.example.com](https://evil.example)
Enable macros and open payload.exe. Invoice payment is overdue.
"""
        headers = parse_pasted_headers(message)
        report = analyze_email(message, headers=headers)
        finding_ids = {finding["id"] for finding in report["findings"]}

        self.assertTrue({
            "urgency",
            "account_threat",
            "password",
            "mfa",
            "payment",
            "bank_change",
            "confidentiality",
            "shortened_url",
            "raw_ip",
            "suspicious_url",
            "misleading_link",
            "impersonation",
            "executable",
            "macros",
            "invoice",
            "credential_harvesting",
            "reply_mismatch",
            "spf",
            "dkim",
            "dmarc",
        }.issubset(finding_ids))
        self.assertTrue(all(finding["points"] > 0 for finding in report["findings"]))
        self.assertEqual(report["score"], 100)
        self.assertTrue(report["score_capped"])
        self.assertTrue(report["recommendations"])
        executable = next(finding for finding in report["findings"] if finding["id"] == "executable")
        self.assertNotIn(".com", executable["evidence"])

    def test_safe_fictional_library_message_has_no_url_warning(self):
        message = """From: Library Services <library@example.edu>
Subject: Your book is ready

Check https://library.example.edu/hours for opening times.
"""
        report = analyze_email(message, headers=parse_pasted_headers(message))
        finding_ids = {finding["id"] for finding in report["findings"]}

        self.assertEqual(report["classification"], "Low Risk")
        self.assertNotIn("suspicious_url", finding_ids)
        self.assertNotIn("misleading_link", finding_ids)

    def test_received_spf_failure_header_is_recognized(self):
        message = """Received-SPF: fail (mail.example: domain does not authorize sender)
Subject: Routine notice

The weekly update is ready.
"""
        report = analyze_email(message, headers=parse_pasted_headers(message))
        spf = next(finding for finding in report["findings"] if finding["id"] == "spf")

        self.assertIn("fail", spf["evidence"])

    def test_eml_parser_extracts_headers_body_and_attachment_name_only(self):
        message = EmailMessage()
        message["From"] = "Accounts <accounts@example.net>"
        message["Reply-To"] = "reply@example.org"
        message["Subject"] = "Invoice update"
        message.set_content("The overdue invoice is attached.")
        message.add_attachment(
            b"fictional attachment bytes",
            maintype="application",
            subtype="octet-stream",
            filename="invoice.xlsm",
        )

        parsed = parse_eml(message.as_bytes())
        report = analyze_email(
            parsed.body,
            headers=parsed.headers,
            attachments=parsed.attachments,
        )
        finding_ids = {finding["id"] for finding in report["findings"]}

        self.assertEqual(parsed.headers["subject"], ["Invoice update"])
        self.assertEqual(parsed.attachments, ["invoice.xlsm"])
        self.assertIn("unusual_attachment", finding_ids)
        self.assertNotIn("fictional attachment bytes", parsed.body)

    def test_score_is_capped_but_raw_points_are_exposed(self):
        message = (
            "Urgent. Account suspended. Reply with your password and MFA code. "
            "Pay gift cards. Change bank details. Keep it secret. "
            "Enable macros. Verify your account at http://192.0.2.1/login. "
            "Open payload.exe and invoice.zip."
        )
        report = analyze_email(message)

        self.assertEqual(report["score"], 100)
        self.assertGreater(report["raw_points"], 100)
        self.assertTrue(report["score_capped"])
        weight_ids = {rule["id"] for rule in report["scoring_weights"]}
        finding_ids = {finding["id"] for finding in report["findings"]}
        self.assertTrue(finding_ids.issubset(weight_ids))


if __name__ == "__main__":
    unittest.main()
