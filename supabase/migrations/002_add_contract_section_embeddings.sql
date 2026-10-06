create extension if not exists vector;

alter table public.contract_sections
add column if not exists embedding vector(1536);