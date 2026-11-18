import React, { useEffect, useRef, useState } from "react";

const DEMOS = {
  obvious: `From: Security Team <security@example.com>
Reply-To: verify@example.net
Subject: URGENT: Your account will be closed today

We detected unusual activity. Your account will be suspended in 30 minutes unless you verify now.
Reply with your password and the six-digit MFA verification code to prevent permanent closure.
Sign in immediately: http://account-security.example/verify

Attachment: account_recovery.exe`,
  sophisticated: `From: Dana Lee <dana.lee@example.net>
Reply-To: dana.lee@external-example.org
Subject: Updated supplier payment details

Hi team,

Following our call, please update the bank details for tomorrow's scheduled invoice payment. The supplier portal is temporarily unavailable, so use the attached revised instructions instead.
This is time-sensitive; please confirm once the transfer is arranged. Keep this within the finance group until the vendor announcement goes out.

Attachment: revised-remittance-details.xlsm`,
  m365: `From: Microsoft 365 Notifications <notice@example.net>
Subject: Action required: mailbox access expires

Your Microsoft 365 mailbox is scheduled for deactivation due to a storage policy update.
Confirm your account now to keep access to email and shared files:
https://microsoft365-login.example/continue

If you do not verify within 2 hours, your account will be permanently closed.
Enter your password and current verification code when prompted.`,
  parcel: `From: Parcel Delivery <delivery@example.net>
Subject: Delivery could not be completed

We were unable to deliver your parcel because a small address fee is outstanding.
Pay the re-delivery fee today to avoid returning your package to sender:
https://parcel-track.example/redelivery

Please open the attached delivery notice for the collection details.
Attachment: delivery_notice.zip`,
  invoice: `From: Accounts Payable <ap@example.org>
Reply-To: finance@example.net
Subject: Overdue invoice — payment due today

Hello,

Our records show an overdue invoice balance. Please arrange payment today to avoid a late fee.
Our banking information has changed; use the new account details in the attached invoice.
Please keep this confidential and reply once the transfer has been completed.

Attachment: invoice_1048.docm`,
  legitimate: `From: Library Services <library@example.edu>
Subject: Your book is ready for collection

Hello,

The book you requested is ready to collect from the main desk during our usual opening hours.
You can check the library schedule at https://library.example.edu/hours or reply to this message if you have a question.

Best,
Library Services`,
};

const DEMO_BUTTONS = [
  ["obvious", "Obvious phish"],
  ["sophisticated", "Sophisticated"],
  ["m365", "Account warning"],
  ["parcel", "Parcel notice"],
  ["invoice", "Invoice / BEC"],
  ["legitimate", "Legitimate"],
];

export default function App() {
  const [emailText, setEmailText] = useState("");
  const [report, setReport] = useState(null);
  const [apiState, setApiState] = useState("checking");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState("");
  const [weights, setWeights] = useState([]);
  const fileInput = useRef(null);

  useEffect(() => {
    let active = true;
    let timer;

    async function checkLocalApi() {
      try {
        const response = await fetch("/api/health");
        if (!response.ok) throw new Error(`Local service returned ${response.status}.`);
        const health = await response.json();
        if (!active || health.status !== "ok") return;
        setApiState("online");
        const rulesResponse = await fetch("/api/rules");
        if (!rulesResponse.ok) throw new Error(`Could not load scoring rules (${rulesResponse.status}).`);
        const ruleData = await rulesResponse.json();
        if (active) setWeights(ruleData.scoring_weights);
        window.clearInterval(timer);
      } catch {
        if (active) setApiState("offline");
      }
    }

    checkLocalApi();
    timer = window.setInterval(checkLocalApi, 2500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  async function sendForAnalysis({ file } = {}) {
    setError("");
    setBusy(true);
    try {
      const response = file
        ? await fetch("/api/analyze-eml", {
            method: "POST",
            headers: { "Content-Type": "message/rfc822" },
            body: file,
          })
        : await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: emailText }),
          });
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error(`The local service returned an unreadable response (${response.status}).`);
      }
      if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : `Analysis failed (${response.status}).`);
      }
      setReport(data);
    } catch (requestError) {
      setError(
        requestError instanceof TypeError
          ? "Could not reach the local analysis service. Keep the PhisLens server windows open and try again."
          : requestError.message,
      );
    } finally {
      setBusy(false);
    }
  }

  function loadDemo(name) {
    setEmailText(DEMOS[name]);
    setFileName("");
    setError("");
    setReport(null);
  }

  function clearInput() {
    setEmailText("");
    setFileName("");
    setError("");
    setReport(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".eml")) {
      setError("Choose an email file ending in .eml.");
      event.target.value = "";
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError("Email files must be 2 MB or smaller.");
      event.target.value = "";
      return;
    }
    setFileName(file.name);
    setEmailText("");
    await sendForAnalysis({ file });
  }

  function handleTextChange(event) {
    setEmailText(event.target.value);
    setFileName("");
    setError("");
  }

  const scoreColor = report
    ? report.score >= 55
      ? "var(--red)"
      : report.score >= 25
        ? "var(--yellow)"
        : "var(--green)"
    : "var(--green)";

  return (
    <>
      <div className="page-noise" aria-hidden="true" />
      <header className="site-header">
        <a className="brand" href="#top" aria-label="PhisLens home">
          <BrandMark />
          <span>Phis<span className="brand-accent">Lens</span></span>
        </a>
        <nav className="main-nav" aria-label="Main navigation">
          <a href="#analyser">Analyser</a>
          <a href="#method">How it works</a>
          <a href="#safety">Stay safe</a>
        </nav>
        <div className={`local-status ${apiState}`}>
          <span className="status-dot" />
          {apiState === "online" ? "LOCAL API READY" : apiState === "checking" ? "CONNECTING" : "API OFFLINE"}
        </div>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow"><span className="eyebrow-line" /> PHISLENS / EMAIL THREAT ANALYSIS <span className="eyebrow-version">LOCAL BUILD</span></p>
            <h1 id="hero-title" className="glitch" data-text="TRUST LESS." aria-label="TRUST LESS.">TRUST LESS.</h1>
            <h2>Read the signals.<br /><span>Not the bait.</span></h2>
            <p className="hero-description">Inspect suspicious email for evidence-backed warning signs, hidden link and sender clues, and business email compromise tactics.</p>
            <a className="hero-cta" href="#analyser">ANALYSE AN EMAIL <span aria-hidden="true">↘</span></a>
            <p className="hero-footnote"><span className="tiny-lock" aria-hidden="true">▣</span> LOCAL PYTHON ANALYSIS. YOUR EMAIL IS NEVER SENT OFF THIS DEVICE.</p>
          </div>
          <HeroArt />
          <div className="hero-bottom-line"><span>01 — INSPECT</span><span>02 — VERIFY EVIDENCE</span><span>03 — TAKE ACTION</span></div>
        </section>

        <section className="analyser-section section-wrap" id="analyser" aria-labelledby="analyser-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow"><span className="eyebrow-line" /> LOCAL ANALYSIS CONSOLE</p>
              <h2 id="analyser-title">Put it under <span>the lens.</span></h2>
            </div>
            <p className="section-aside">Paste a message or inspect a .eml file. Each finding is tied to evidence and a defined score contribution.</p>
          </div>

          <div className="analyser-grid">
            <div className="input-panel panel">
              <div className="panel-topline">
                <span className="panel-label"><span className="live-pulse" /> INPUT / EMAIL CONTENT</span>
                <span className="panel-index">LOCAL PROCESSING</span>
              </div>
              <label className="sr-only" htmlFor="email-content">Paste suspicious email content, including headers if available</label>
              <textarea
                id="email-content"
                spellCheck="false"
                value={emailText}
                onChange={handleTextChange}
                onKeyDown={(event) => {
                  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") sendForAnalysis();
                }}
                placeholder="Paste the email text here. Include the sender, Reply-To, and authentication headers if you have them."
              />
              <div className="input-meta">
                <span>{emailText.length.toLocaleString()} character{emailText.length === 1 ? "" : "s"}</span>
                <span>{fileName ? `Loaded: ${fileName}` : "Not stored after analysis"}</span>
              </div>
              {error && <p className="error-message" role="alert">{error}</p>}
              {apiState === "offline" && (
                <p className="api-hint" role="status">Start the local services by double-clicking <strong>start.bat</strong>. Email analysis is unavailable until the local API is ready.</p>
              )}
              <div className="input-actions">
                <button className="button button-primary" type="button" onClick={() => sendForAnalysis()} disabled={busy || !emailText.trim() || apiState !== "online"}>
                  {busy ? "ANALYSING…" : "ANALYSE EMAIL"} <span aria-hidden="true">↗</span>
                </button>
                <button className="button button-quiet" type="button" onClick={clearInput}>CLEAR</button>
                <label className={`file-button ${apiState !== "online" || busy ? "disabled" : ""}`}>
                  OPEN .EML
                  <input
                    ref={fileInput}
                    type="file"
                    accept=".eml,message/rfc822"
                    onChange={handleFileChange}
                    disabled={apiState !== "online" || busy}
                  />
                </label>
              </div>
              <div className="demo-picker">
                <p className="demo-label">OR LOAD A FICTIONAL EXAMPLE</p>
                <div className="demo-buttons" role="group" aria-label="Load a fictional demonstration email">
                  {DEMO_BUTTONS.map(([name, label]) => (
                    <button key={name} type="button" onClick={() => loadDemo(name)}>{label}</button>
                  ))}
                </div>
              </div>
            </div>

            <section className="result-panel panel" aria-labelledby="result-title" aria-live="polite">
              <div className="panel-topline">
                <span className="panel-label"><span className="result-mark" /> ANALYSIS / REPORT</span>
                <span className="panel-index">{busy ? "ANALYSING" : report ? "ANALYSIS COMPLETE" : "AWAITING INPUT"}</span>
              </div>
              {!report ? (
                <div className="empty-result">
                  <div className="empty-glyph" aria-hidden="true"><span>?</span></div>
                  <h3 id="result-title">No signal yet.</h3>
                  <p>Your evidence report and recommended next steps will appear here after analysis.</p>
                  <div className="empty-readout"><span>RISK SCORE</span><span>— / 100</span></div>
                </div>
              ) : (
                <AnalysisResult report={report} scoreColor={scoreColor} />
              )}
            </section>
          </div>

          <p className="privacy-strip">
            <span className="privacy-lock" aria-hidden="true">▣</span>
            <span><strong>YOUR EMAIL STAYS ON THIS COMPUTER.</strong> The page sends it only to the local PhisLens service at 127.0.0.1. No cloud, database, external API, analytics, or saved email content.</span>
            <span className="privacy-tag">LOCAL ONLY</span>
          </p>
        </section>

        <section className="method-section section-wrap" id="method" aria-labelledby="method-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow"><span className="eyebrow-line" /> UNDER THE HOOD</p>
              <h2 id="method-title">Every point has <span>a reason.</span></h2>
            </div>
            <p className="section-aside">The score sums the points for detected evidence and caps at 100. The experimental ML preview is separate and never changes this score.</p>
          </div>
          <div className="method-grid">
            <article className="method-card"><span className="method-number">01</span><h3>Low risk</h3><p>0–24 points</p><span className="method-color low" /></article>
            <article className="method-card"><span className="method-number">02</span><h3>Suspicious</h3><p>25–54 points</p><span className="method-color medium" /></article>
            <article className="method-card"><span className="method-number">03</span><h3>High risk</h3><p>55–100 points</p><span className="method-color high" /></article>
          </div>
          <details className="scoring-details">
            <summary>View the scoring weights</summary>
            <div className="weight-list">
              {weights.map((rule) => (
                <span key={rule.id}>{rule.title}<b>+{rule.points}</b></span>
              ))}
              {!weights.length && <span>Waiting for the local scoring rules…</span>}
            </div>
            <p className="weight-note">Each indicator contributes once. Scores are capped at 100. Indicators are clues, not proof; legitimate messages can contain similar language.</p>
          </details>
        </section>

        <section className="safety-section section-wrap" id="safety" aria-labelledby="safety-title">
          <div className="safety-symbol" aria-hidden="true"><span>!</span></div>
          <div>
            <p className="eyebrow"><span className="eyebrow-line" /> KEEP YOURSELF SAFE</p>
            <h2 id="safety-title">Don’t click to <span>find out.</span></h2>
            <p>This educational triage tool cannot prove whether an email is malicious or safe. Do not click suspicious links or open attachments to test them. Verify important requests through an organisation’s official website or app, or contact someone using details you already know are genuine.</p>
          </div>
          <span className="safety-watermark" aria-hidden="true">VERIFY</span>
        </section>
      </main>

      <footer className="site-footer">
        <a className="brand footer-brand" href="#top" aria-label="PhisLens home"><BrandMark /><span>Phis<span className="brand-accent">Lens</span></span></a>
        <p>PHISLENS <span>—</span> LOCAL-FIRST EMAIL TRIAGE</p>
        <a className="back-top" href="#top">BACK TO TOP ↑</a>
      </footer>
    </>
  );
}

function AnalysisResult({ report, scoreColor }) {
  const findings = report.findings ?? [];
  const model = report.model_preview;

  return (
    <div className="analysis-result">
      {report.email && (
        <div className="email-metadata">
          {report.email.subject && <p><strong>SUBJECT</strong> {report.email.subject}</p>}
          {report.email.from && <p><strong>FROM</strong> {report.email.from}</p>}
          {report.email.reply_to && <p><strong>REPLY-TO</strong> {report.email.reply_to}</p>}
          {report.email.attachment_names?.length > 0 && <p><strong>ATTACHMENTS</strong> {report.email.attachment_names.join(", ")}</p>}
        </div>
      )}
      <div className="score-area">
        <div
          className="score-ring"
          role="img"
          aria-label={`Risk score ${report.score} out of 100`}
          style={{ "--ring-color": scoreColor, "--score-angle": `${report.score * 3.6}deg` }}
        >
          <div className="score-ring-inner"><span className="score-number">{report.score}</span><span className="score-out-of">/ 100</span></div>
        </div>
        <div className="score-copy">
          <p className="score-caption">EVIDENCE-BASED RISK SCORE</p>
          <h3 style={{ color: scoreColor }}>{report.classification}</h3>
          <p>{report.summary}</p>
        </div>
      </div>
      {report.score_capped && <p className="cap-note">Detected evidence totals {report.raw_points} points; displayed score is capped at 100.</p>}

      <div className="findings-heading"><h4>Signals found</h4><span>{findings.length} INDICATOR{findings.length === 1 ? "" : "S"}</span></div>
      {findings.length ? (
        <div className="findings-list">
          {findings.map((finding) => <Finding key={finding.id} finding={finding} />)}
        </div>
      ) : (
        <div className="no-findings">No listed warning signs were detected. That does not prove the email is safe.</div>
      )}

      <div className="recommendation">
        <span className="recommendation-icon" aria-hidden="true">↗</span>
        <div>
          <h4>What to do next</h4>
          <ul>
            {report.recommendations.map((recommendation, index) => (
              <li key={`${index}-${recommendation.text}`}>
                <span>{recommendation.text}</span>
                {recommendation.supported_by?.length > 0 && (
                  <small className="recommendation-basis">
                    Evidence: {recommendation.supported_by
                      .map((id) => findings.find((finding) => finding.id === id)?.title)
                      .filter(Boolean)
                      .join(", ")}
                  </small>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {model && (
        <details className="model-preview">
          <summary>Experimental scikit-learn text model <span>NOT IN SCORE</span></summary>
          {model.available ? (
            <div className="model-preview-content">
              <div className="model-score"><strong>{model.score}%</strong><span>{model.tendency}</span></div>
              {model.terms?.length > 0 && <p>Terms influencing this preview: <strong>{model.terms.join(", ")}</strong></p>}
              <p>{model.message}</p>
            </div>
          ) : <p className="model-preview-content">{model.message}</p>}
          <p className="model-disclaimer">This prototype uses fictional training examples and has not been evaluated on real email. Do not rely on it to judge a message.</p>
        </details>
      )}

      <p className="result-disclaimer">Educational triage only—not a verdict. A low score does not guarantee safety.</p>
    </div>
  );
}

function Finding({ finding }) {
  return (
    <article className="finding">
      <div>
        <h5>{finding.title}</h5>
        <p>{finding.explanation}</p>
        {finding.evidence && <p className="finding-evidence"><strong>Evidence:</strong> “{finding.evidence}”</p>}
      </div>
      <span className="finding-points">+{finding.points}</span>
    </article>
  );
}

function BrandMark() {
  return <span className="brand-mark" aria-hidden="true"><span /><span /><span /></span>;
}

function HeroArt() {
  return (
    <div className="hero-art" aria-hidden="true">
      <div className="art-orbit orbit-one" />
      <div className="art-orbit orbit-two" />
      <div className="art-core">
        <div className="core-crosshair" />
        <div className="core-eye"><span /></div>
        <span className="core-caption">EVIDENCE<br />DETECTED</span>
      </div>
      <div className="art-scanline" />
      <span className="art-coordinate coordinate-one">LOCAL / 127.0.0.1</span>
      <span className="art-coordinate coordinate-two">SYSTEM // ONLINE</span>
      <span className="art-bit bit-one" /><span className="art-bit bit-two" /><span className="art-bit bit-three" />
      <span className="art-fragment">ML / RULES / EVIDENCE</span>
    </div>
  );
}
