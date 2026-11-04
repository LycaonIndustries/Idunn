# Database & Storage

Iðunn employs a flexible data layer configured via the `DATABASE_BACKEND` environment variable (`supabase` or `mongodb`).

---

## 1. Supabase (PostgreSQL)

When `DATABASE_BACKEND=supabase` is configured, Iðunn connects using the modern Supabase Python client with RLS policies enabled.

### Schema Definition (`db/schema.sql`)

```sql
-- 1. Inventory Items Table
create table if not exists items (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  quantity numeric not null,
  unit text not null,
  location text not null,
  expiry_date timestamptz,
  created_at timestamptz default timezone('utc'::text, now()) not null,
  updated_at timestamptz default timezone('utc'::text, now()) not null
);

-- 2. Recipes Table
create table if not exists recipes (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text,
  ingredients jsonb not null default '[]'::jsonb,
  steps jsonb not null default '[]'::jsonb,
  region text,
  cuisine_type text,
  difficulty text,
  prep_time_minutes integer,
  cook_time_minutes integer,
  servings integer,
  source_url text,
  source_name text,
  image_url text,
  video_url text,
  tags text[] default '{}',
  nutrition jsonb,
  needs_review boolean default false,
  ingest_source text,
  ingest_confidence numeric,
  created_at timestamptz default timezone('utc'::text, now()) not null,
  updated_at timestamptz default timezone('utc'::text, now()) not null
);

-- 3. Normalized Ingredients Table
create table if not exists ingredients (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  hindi_name text,
  category text,
  synonyms text[] default '{}',
  shelf_life_days integer,
  default_storage text
);
```

---

## 2. MongoDB Atlas / In-Memory Mock

When `DATABASE_BACKEND=mongodb` is set:
- Connects asynchronously via Motor (`motor.motor_asyncio.AsyncIOMotorClient`).
- Collections: `items`, `recipes`, `ingredients`.
- Search & vector indexing definitions live in `backend/db/recipe_search_indexes.py`.
- **In-Memory Fallback**: When neither Supabase nor MongoDB is configured, `mongomock_motor` automatically activates, allowing full local CRUD, unit tests, and CI/CD without database setup.
