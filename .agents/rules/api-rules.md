# API Design & Contract Rules

## 1. HTTP Methods & REST Semantics
- **Method Alignment:** Use GET for safe read operations, POST for entity creation, PUT/PATCH for mutations, and DELETE for deletions.
- **Idempotency:** Ensure mutation endpoints behave safely if retried multiple times by the client.
- **Status Codes:** Return standard HTTP status codes: 200/201 on success, 400 for client validation failures, 401/403 for auth issues, 404 for missing resources, and 500 strictly for unexpected server defects.

## 2. Input Validation
- **Pydantic Validation:** All incoming request bodies and query parameters must be validated through explicit Pydantic models.
- **Length & Range Bounds:** Enforce min/max boundaries on numeric inputs and string lengths to prevent buffer or memory overflow.

## 3. External Dependencies & Resilience
- **Timeouts:** Every outbound HTTP request to external services must specify an explicit network timeout.
- **Graceful Fallbacks:** Implement fallback handling when third-party APIs fail so that core kitchen management features remain operational.
