-- ============================================================================
-- Iðunn — Supabase Database Schema
-- Run this script in your Supabase Project -> SQL Editor to initialize tables.
-- ============================================================================

-- Enable UUID extension if not already enabled
create extension if not exists "uuid-ossp";

-- ----------------------------------------------------------------------------
-- 1. Pantry Inventory Items (items)
-- ----------------------------------------------------------------------------
create table if not exists items (
    id text primary key,
    name text not null,
    quantity double precision not null default 1.0,
    unit text not null default 'piece',
    location text not null default 'fridge',
    expiry_date timestamptz,
    notes text,
    barcode text,
    consumed boolean not null default false,
    added_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_items_location on items(location);
create index if not exists idx_items_consumed on items(consumed);
create index if not exists idx_items_expiry on items(expiry_date);

-- ----------------------------------------------------------------------------
-- 2. Canonical Ingredients Catalog (ingredients)
-- ----------------------------------------------------------------------------
create table if not exists ingredients (
    id text primary key,
    name text not null unique,
    category text not null,
    synonyms jsonb not null default '[]'::jsonb,
    storage_life_days jsonb not null default '{}'::jsonb,
    unit_conversions jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_ingredients_name on ingredients(name);
create index if not exists idx_ingredients_category on ingredients(category);

-- ----------------------------------------------------------------------------
-- 3. Recipe Vault (recipes)
-- ----------------------------------------------------------------------------
create table if not exists recipes (
    id text primary key,
    title text not null,
    description text,
    cuisine_type text,
    region text,
    difficulty text,
    prep_time_minutes integer,
    cook_time_minutes integer,
    servings integer,
    source_url text,
    source_name text,
    image_url text,
    video_url text,
    tags text[] not null default '{}',
    ingredients jsonb not null default '[]'::jsonb,
    steps jsonb not null default '[]'::jsonb,
    nutrition jsonb,
    embedding jsonb,
    embedding_model text,
    normalized_ingredients text[] not null default '{}',
    ingredient_matches jsonb not null default '[]'::jsonb,
    ingest_source text,
    ingest_confidence double precision,
    needs_review boolean not null default false,
    extraction_reviewed boolean not null default true,
    revision integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_recipes_title on recipes(title);
create index if not exists idx_recipes_cuisine on recipes(cuisine_type);
create index if not exists idx_recipes_needs_review on recipes(needs_review);
create index if not exists idx_recipes_created_at on recipes(created_at desc);

-- ----------------------------------------------------------------------------
-- Row Level Security (RLS) - Permissive for self-hosted / household kitchen app
-- ----------------------------------------------------------------------------
alter table items enable row level security;
alter table ingredients enable row level security;
alter table recipes enable row level security;

-- Allow read/write with anon key for household OS
create policy "Allow all on items" on items for all using (true) with check (true);
create policy "Allow all on ingredients" on ingredients for all using (true) with check (true);
create policy "Allow all on recipes" on recipes for all using (true) with check (true);
