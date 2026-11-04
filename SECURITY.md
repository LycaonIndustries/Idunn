# Security Policy

The Iðunn team and Lycaon Industries take the security of our software and users seriously. This document outlines how to report vulnerabilities and our supported version policies.

---

## Supported Versions

Only the latest release and the current `main` branch receive active security updates.

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| `main`  | :white_check_mark: | Active Development |
| < 0.1.0 | :x:                | Unsupported |

---

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

If you believe you have discovered a vulnerability in Iðunn:

### 1. Preferred Method: GitHub Private Vulnerability Reporting
Submit an advisory privately via GitHub:
1. Navigate to the [Iðunn Security Advisories page](https://github.com/LycaonIndustries/Idunn/security/advisories).
2. Click **"Report a vulnerability"** to open a confidential draft advisory.

### 2. Alternative Method: Security Email
Email the maintainers directly at:
- **`thefenrislycaon@gmail.com`**

### What to Include in Your Report
To help us triage and resolve the issue quickly, please provide:
- A clear description of the vulnerability and its potential impact.
- Step-by-step instructions or proof-of-concept (PoC) code to reproduce the issue.
- Details regarding the affected environment (OS, Python version, database backend).
- Any proposed remediation or patches, if available.

---

## Response & Disclosure Process

- **Acknowledgement**: We will acknowledge receipt of your vulnerability report within **48 hours**.
- **Investigation**: We will investigate and provide regular status updates during triage and reproduction.
- **Remediation**: Once verified, we will develop a patch and prepare a release.
- **Coordinated Disclosure**: We adhere to coordinated vulnerability disclosure and will credit researchers who discover and report issues responsibly.

---

## Built-in Security Measures

Iðunn enforces several defensive controls in its core architecture:

1. **SSRF Protection on Recipe Ingest**: All remote recipe URLs are strictly validated to public HTTP/HTTPS endpoints on ports 80/443; local, private, and loopback IP addresses are systematically rejected.
2. **BYOK Secret Isolation**: API keys for external LLMs (Gemini, Anthropic, OpenAI) are masked in responses and never exposed via public endpoints.
3. **Database Authorization**: Supabase tables enforce Row Level Security (RLS) policies by default.
4. **Environment Integrity**: `.env` and sensitive credential files are excluded from version control via `.gitignore`.
