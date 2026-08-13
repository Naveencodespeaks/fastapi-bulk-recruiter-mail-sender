# FastAPI Bulk Recruiter Email Sender

A local FastAPI application that validates pasted recruiter email addresses,
removes duplicates, and sends a separate résumé-attached email to every valid
recipient.

## Privacy behavior

Each message is created independently:

```text
To: one-recruiter@company.com
Cc: not present
Bcc: not present
Attachment: your uploaded PDF résumé
```

The SMTP envelope also contains only that one recipient.

## Features

- Newline-, comma-, semicolon-, and space-separated input
- Syntax validation using `email-validator`
- Case-insensitive duplicate removal
- Configurable batch limit (default: 500)
- One recruiter per `To` header and SMTP envelope
- No `Cc` or `Bcc`
- PDF résumé upload and attachment
- Sequential background sending while the server is running
- Live progress using Server-Sent Events
- Processed, sent/simulated, and failed counters
- Per-address failure reporting
- Configurable delay and SMTP reconnection interval
- Cancellation endpoint and UI button
- Dry-run mode enabled by default
- Docker support

## Important limitations

- Jobs and progress are stored in memory. Restarting the application loses job
  state and stops active work.
- Run one Uvicorn worker. Multiple workers would each have a separate in-memory
  queue.
- SMTP providers can impose per-minute, daily, reputation, content, or account
  limits. This project does not bypass those limits.
- Use only for legitimate professional outreach. Follow applicable anti-spam,
  privacy, and provider policies.
- A connection loss after an SMTP server accepts a message can leave delivery
  status uncertain. The application retries once after `SMTPServerDisconnected`,
  so a rare duplicate delivery is theoretically possible.

For durable production processing across restarts, replace the in-memory queue
with a persistent job system such as Celery/RQ plus Redis and store job state in
a database.

## 1. Install

Python 3.11 or newer is recommended.

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configure

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
BULK_MAX_RECIPIENTS=500
BULK_SEND_DELAY_SECONDS=3
SMTP_RECONNECT_EVERY=40

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=Sai Naveen
SMTP_STARTTLS=true
SMTP_USE_SSL=false

SMTP_DRY_RUN=true
```

Keep `SMTP_DRY_RUN=true` for the first test. The application will build every
message and update progress without connecting to SMTP.

After verifying the UI and recipients, set:

```env
SMTP_DRY_RUN=false
```

Then restart the server.

For Gmail, use an app password when your account supports it; do not place your
normal account password in this project. Never commit `.env`.

## 3. Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open:

```text
http://127.0.0.1:8000
```

API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## 4. Docker

```bash
cp .env.example .env
docker compose up --build
```

Then open `http://127.0.0.1:8000`.

## Input examples

Newline-separated:

```text
recruiter1@company.com
recruiter2@company.com
recruiter3@company.com
```

Comma-separated:

```text
recruiter1@company.com, recruiter2@company.com, recruiter3@company.com
```

## Configuration reference

| Variable | Default | Purpose |
|---|---:|---|
| `BULK_MAX_RECIPIENTS` | `500` | Maximum unique valid recipients per job |
| `BULK_SEND_DELAY_SECONDS` | `3` | Delay between individual messages |
| `SMTP_RECONNECT_EVERY` | `40` | Reconnect after this many attempts |
| `SMTP_TIMEOUT_SECONDS` | `30` | SMTP connection/socket timeout |
| `MAX_RESUME_SIZE_MB` | `10` | Maximum uploaded PDF size |
| `SMTP_DRY_RUN` | `true` | Simulate without transmitting |
| `SMTP_STARTTLS` | `true` | Upgrade a plain connection using STARTTLS |
| `SMTP_USE_SSL` | `false` | Use SMTP-over-SSL from connection start |

Do not enable both `SMTP_STARTTLS` and `SMTP_USE_SSL` unless your provider
explicitly requires that combination.

## Tests

```bash
pytest -q
```

## Project layout

```text
app/
  config.py
  email_service.py
  email_utils.py
  job_manager.py
  main.py
  static/
  templates/
tests/
.env.example
Dockerfile
docker-compose.yml
requirements.txt
```
