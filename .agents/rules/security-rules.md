# Security & Privacy Rules

## 1. Authentication & Authorization
- **Endpoint Protection:** Verify that private endpoints enforce authentication middleware or dependency injection.
- **Role Verification:** Confirm that users cannot modify or inspect entities belonging to other accounts.
- **Fail Closed:** Return 401 Unauthorized or 404 Not Found for unauthorized resource access without leaking object existence.

## 2. Input Sanitization & Zero Trust
- **Zero Client Trust:** Never trust client-side data (cookies, localStorage, query params). Re-validate permissions and constraints on the server.
- **Sanitize User Content:** Sanitize user-generated text and HTML before rendering or echoing to prevent cross-site scripting (XSS).
- **SQL & Query Injection:** Use parameterized ORM queries or typed model filters. Never concatenate user strings into database queries.

## 3. Secrets & Sensitive Data
- **No Hardcoded Secrets:** Never commit passwords, tokens, API keys, or private keys to the repository.
- **Obfuscated Field Naming:** Avoid storing sensitive tokens in plainly obvious plain-text database fields without encryption.
- **PII Protection:** Do not send customer email addresses or IP addresses to third-party tracking services without explicit hashing or pseudonymization.
