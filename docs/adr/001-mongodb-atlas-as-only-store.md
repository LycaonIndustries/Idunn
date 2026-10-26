# ADR-001: MongoDB Atlas as the Only Store

## Status
Accepted

## Context

Iðunn needs to store several types of data:
- **Inventory items** — pantry items with expiry dates, locations, quantities
- **Ingredients** — canonical ingredient master with synonyms, regional names
- **Recipes** — nested documents with ingredients, steps, embeddings
- **Meal plans** — weekly plans referencing recipes
- **Shopping lists** — generated lists with deduped items
- **Receipts** — OCR runs with raw images and extracted rows
- **Nutrition** — IFCT-backed nutrient profiles
- **Eval runs** — RAGAS + Promptfoo run history

We evaluated three approaches:
1. **Split store**: PostgreSQL (relational) + Qdrant/Pinecone (vectors) + Typesense (full-text)
2. **PostgreSQL + pgvector**: Single relational store with vector extension
3. **MongoDB Atlas**: Document store with Vector Search + Atlas Search (BM25)

## Decision

We will use **MongoDB Atlas** as the single data store for Iðunn.

## Rationale

### 1. Document model fits recipe data naturally
Recipe documents are nested and irregular — some have macros, some don't; ingredients vary in granularity (some have "2 cups chopped onions", others just "onions"). A document model accommodates this without complex joins or NULL-handling schemas.

```json
{
  "title": "Aloo Gobi",
  "ingredients": [
    {"name": "potato", "quantity": 3, "unit": "piece", "optional": false},
    {"name": "cauliflower", "quantity": 1, "unit": "piece", "optional": false}
  ],
  "steps": ["Heat oil...", "Add spices..."],
  "embedding": [0.123, 0.456, ...],
  "macros": {"kcal": 180, "protein": 4.2}  // optional
}
```

### 2. Atlas Vector + Search + $scoreFusion = hybrid retrieval in one query
The headline feature ("What can I cook?") requires hybrid retrieval:
- **Vector search**: semantic match on recipe embeddings
- **BM25**: keyword match on title/ingredients/steps
- **Reciprocal Rank Fusion (RRF)**: combine both result sets

MongoDB Atlas provides all three in a single aggregation pipeline via `$vectorSearch`, `$search` (BM25), and `$scoreFusion`. No need to operate separate vector DB + search engine.

```javascript
// Single aggregation for hybrid retrieval
{
  "$scoreFusion": {
    "inputs": [
      {"$vectorSearch": { ... }},
      {"$search": { ... }}
    ],
    "technique": "rrf"
  }
}
```

### 3. NoSQL-with-discipline via JSON Schema validation
We apply JSON Schema validation at the collection level (`validationLevel: strict`, `validationAction: error`). This gives us schema enforcement without sacrificing document flexibility.

```python
# Schema validation applied at collection creation
ITEMS_SCHEMA = {
    "bsonType": "object",
    "required": ["name", "quantity", "unit", "location"],
    "properties": {
        "name": {"bsonType": "string", "minLength": 1, "maxLength": 200},
        "quantity": {"bsonType": "double", "minimum": 0.0001},
        ...
    }
}
```

### 4. "74% of orgs moving to vector DBs" — but we need one that does both
Industry data shows 74% of organizations are moving to vector databases. However, most vector DBs (Pinecone, Qdrant, Weaviate) don't handle full-text search as well as Atlas Search, nor do they handle general document storage.

### 5. Resume signal: "MongoDB Atlas Vector + Search" is a specific 2026 hiring keyword
The design doc identifies this as a portfolio signal:
- "MongoDB Atlas Vector + Search" appears in job postings
- Shows understanding of modern, consolidated data architecture
- Demonstrates "NoSQL-with-discipline" (JSON Schema validation)

### 6. Operational simplicity for a single-developer project
One Atlas cluster handles:
- Document storage (items, ingredients, recipes, etc.)
- Vector storage (recipe embeddings, 768-dim or 1024-dim)
- Full-text search (BM25 on recipe text)
- TTL indexes (expiry alerts)

Compare to operating:
- PostgreSQL + pgvector + Typesense (3 services)
- Or: Qdrant + PostgreSQL + Typesense (3 services)

## Consequences

### Positive
- **Single infrastructure** to manage (one Atlas cluster)
- **Atomic operations** across related data (e.g., updating a recipe and its embedding)
- **Flexible schema** for recipes that vary in structure
- **Hybrid retrieval** in one query (no application-side merging)
- **Free tier available** for development (Atlas M0)
- **Grows with us**: Can split to microservices later with typed contracts already in place

### Negative
- **Vendor lock-in** to MongoDB Atlas (but can migrate to self-hosted MongoDB with some feature loss)
- **Vector search maturity**: Atlas Vector Search is newer than dedicated vector DBs (but sufficient for our scale)
- **RAGAS eval must account for** Atlas-specific scoring nuances

### Neutral
- **Learning curve**: Team must understand MongoDB aggregation pipeline and Atlas Search syntax
- **Cost**: Atlas pricing (but M0 free tier covers initial development)

## Alternatives Considered

### PostgreSQL + pgvector
- **Pros**: Familiar relational model, ACID transactions, mature ecosystem
- **Cons**: Full-text search (tsvector) weaker than Atlas Search; JSONB can get messy for nested recipe data; hybrid retrieval requires application-side merging

### Qdrant + Typesense + PostgreSQL
- **Pros**: Best-in-class for each function
- **Cons**: 3 services to operate, 3 sets of credentials, 3 failure modes; complex data synchronization

### Single-store Qdrant (with metadata)
- **Pros**: Purpose-built vector DB
- **Cons**: Metadata filtering not as powerful as Atlas Search; no BM25; poor fit for general document storage (items, ingredients)

## References
- [MongoDB Atlas Vector Search Docs](https://www.mongodb.com/docs/atlas/atlas-vector-search/)
- [Hybrid Search with $scoreFusion](https://www.mongodb.com/docs/atlas/atlas-vector-search/hybrid-search/)
- [Design Doc Section 4.2: Data layer](../../C:/Users/aesir/Work/Projects/Full/Mimir/300%20-%20Work/320%20-%20Personal/322%20-%20Idunn/Idunn-design.md#4.2-data-layer--mongodb-atlas-vector--search)
- "74% of orgs moving to vector DBs" — 2026 RAG production guide

## Date
2026-05-07
