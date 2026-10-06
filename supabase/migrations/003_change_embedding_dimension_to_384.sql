alter table public.contract_sections
drop column if exists embedding;

alter table public.contract_sections
add column embedding vector(384);