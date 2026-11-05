# Database & Model Rules (Motor, Supabase & Pydantic v2)

## 1. Entity & Model Design
- **Pydantic v2 Models:** Define all database schemas and API request/response payloads using Pydantic v2 `BaseModel` with strict field type annotations.
- **Minimal Stored Data:** Minimize persisted fields. Avoid storing redundant or easily recomputed attributes.
- **UUID Keys:** Use UUID strings or standard ObjectId formats rather than user emails or mutable identifiers as entity primary keys.
- **Timestamps:** Every persistent entity model should track `created_at` and `updated_at` timestamps in UTC.

## 2. Query Hygiene & Performance
- **Bounded Queries:** Always apply explicit pagination limits (`limit=...`) to database queries. Never execute unbounded collections queries.
- **Handle Empty Query Results:** Handle zero-entity and None results gracefully for all lookups and queries before accessing model properties.
- **Async Safety:** Ensure all Motor and Supabase database interactions use `await` properly in async routes without blocking the FastAPI event loop.
- **Connection Pooling:** Reuse global database clients and connection pools across requests rather than opening ad-hoc database connections in request handlers.

## 3. Data Integrity & Lifecycle
- **Cascading Deletion:** Ensure user-associated database documents and records are cleaned up safely during account deletion.
- **Write Aggregation:** Avoid chatty point-writes. Aggregate or batch updates where possible to minimize I/O overhead.
- **Recovery & Backup Readiness:** Ensure mission-critical user collections have deterministic schemas to support data exports and recovery.
