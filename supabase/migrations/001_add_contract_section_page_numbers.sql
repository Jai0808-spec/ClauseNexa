alter table public.contract_sections
add column if not exists page_numbers integer[]
not null
default '{}'::integer[];
