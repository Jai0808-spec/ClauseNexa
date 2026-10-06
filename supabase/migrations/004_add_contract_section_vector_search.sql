create or replace function public.match_contract_sections(
    query_embedding vector(384),
    match_contract_id uuid,
    match_count integer default 5
)
returns table (
    id uuid,
    contract_id uuid,
    section_title text,
    section_text text,
    page_number integer,
    chunk_index integer,
    similarity double precision
)
language sql
stable
as $$
    select
        cs.id,
        cs.contract_id,
        cs.section_title,
        cs.section_text,
        cs.page_number,
        cs.chunk_index,
        1 - (cs.embedding <=> query_embedding) as similarity
    from public.contract_sections cs
    where
        cs.contract_id = match_contract_id
        and cs.embedding is not null
    order by cs.embedding <=> query_embedding
    limit match_count;
$$;