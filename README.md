# PhisLens

PhisLens is a local-first phishing email analysis project. It combines evidence-based security rules with a separately labeled scikit-learn text-model experiment.

## What stays local

The React page sends pasted text or `.eml` bytes only to the FastAPI service on `127.0.0.1` on the same computer. The service does not save email content, query threat-intelligence services, call an AI provider, or use a database. The sample ML model is trained when the local service starts using fictional examples included in the source.

The ML experiment is intentionally not used to calculate the risk score. It is not trained or evaluated on a real-world email corpus and must not be treated as a reliable classifier. The score is based on explicit rules and lists the evidence and point contribution for each finding.

## Start on Windows

1. Install Python 3.10 or newer and Node.js 20.19 or newer if they are not already installed.
2. Double-click `start.bat`.
3. On the first run, it creates a project-local Python environment and installs the listed Python and JavaScript packages. This step needs an internet connection to retrieve software dependencies; email content is not sent during installation.
4. The page opens at `http://127.0.0.1:5173`. Keep the two server windows open while using it.

The servers bind to the local computer only. This is a local development app, not a static website deployment.

## Run checks manually

In one terminal, from the project folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In another terminal:

```powershell
npm run dev
```

Run backend tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend -p "test_*.py"
```

Create a production frontend bundle:

```powershell
npm run build
```

## Safety limitations

PhisLens is an educational triage aid, not a verdict. It cannot prove that a message is malicious or safe. SPF, DKIM, and DMARC are only assessed when corresponding results are already present in pasted headers; PhisLens does not perform DNS lookups or cryptographic verification. Attachments are never opened or executed. QR images and remote threat-intelligence checks are not part of this version.
