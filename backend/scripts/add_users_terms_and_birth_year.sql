-- Add missing columns to users table (if migration b2c3d4e5f6a7 was not applied).
-- Run with: psql $DATABASE_URL -f scripts/add_users_terms_and_birth_year.sql
-- Or paste into your DB client.

ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_year INTEGER NULL;
