-- ============================================================
-- CLAUSENEXA
-- Initial Supabase Database Schema
-- ============================================================


-- ============================================================
-- 1. EXTENSIONS
-- ============================================================

create extension if not exists vector
with schema extensions;

create extension if not exists pgcrypto;


-- ============================================================
-- 2. CONTRACTS
-- One row = one uploaded legal contract
-- ============================================================

create table if not exists public.contracts (
    id uuid primary key default gen_random_uuid(),

    file_name text not null,
    original_file_name text,
    file_type text,
    storage_path text,

    status text not null default 'uploaded'
        check (
            status in (
                'uploaded',
                'processing',
                'processed',
                'failed'
            )
        ),

    total_pages integer
        check (total_pages is null or total_pages >= 0),

    uploaded_at timestamptz not null default now(),
    processed_at timestamptz,

    metadata jsonb not null default '{}'::jsonb
);


-- ============================================================
-- 3. CONTRACT SECTIONS / RAG CHUNKS
-- One contract can contain many sections/chunks
-- ============================================================

create table if not exists public.contract_sections (
    id uuid primary key default gen_random_uuid(),

    contract_id uuid not null
        references public.contracts(id)
        on delete cascade,

    section_title text,

    section_text text not null,

    page_number integer
        check (page_number is null or page_number >= 1),

    chunk_index integer not null
        check (chunk_index >= 0),

    start_char integer,
    end_char integer,

    created_at timestamptz not null default now(),

    unique (contract_id, chunk_index)
);


-- ============================================================
-- 4. DETECTED CLAUSES
-- Output from Kavyah's NLP / Legal-BERT pipeline
-- ============================================================

create table if not exists public.detected_clauses (
    id uuid primary key default gen_random_uuid(),

    contract_id uuid not null
        references public.contracts(id)
        on delete cascade,

    section_id uuid
        references public.contract_sections(id)
        on delete set null,

    clause_type text not null
        check (
            clause_type in (
                'termination',
                'payment',
                'confidentiality',
                'liability',
                'non_compete',
                'governing_law'
            )
        ),

    clause_text text not null,

    confidence_score double precision
        check (
            confidence_score is null
            or (
                confidence_score >= 0
                and confidence_score <= 1
            )
        ),

    model_name text,

    created_at timestamptz not null default now()
);


-- ============================================================
-- 5. RISK / ATTENTION FLAGS
-- Rule-based risk layer
-- ============================================================

create table if not exists public.risk_flags (
    id uuid primary key default gen_random_uuid(),

    contract_id uuid not null
        references public.contracts(id)
        on delete cascade,

    clause_id uuid
        references public.detected_clauses(id)
        on delete cascade,

    risk_level text not null default 'attention'
        check (
            risk_level in (
                'low',
                'attention',
                'high'
            )
        ),

    risk_reason text not null,

    rule_triggered text,

    created_at timestamptz not null default now()
);


-- ============================================================
-- 6. QUESTIONS
-- User questions about a particular contract
-- ============================================================

create table if not exists public.questions (
    id uuid primary key default gen_random_uuid(),

    contract_id uuid not null
        references public.contracts(id)
        on delete cascade,

    question_text text not null,

    created_at timestamptz not null default now()
);


-- ============================================================
-- 7. ANSWERS
-- LLM/RAG generated answers
-- ============================================================

create table if not exists public.answers (
    id uuid primary key default gen_random_uuid(),

    question_id uuid not null
        references public.questions(id)
        on delete cascade,

    answer_text text not null,

    model_name text,

    faithfulness_score double precision
        check (
            faithfulness_score is null
            or (
                faithfulness_score >= 0
                and faithfulness_score <= 1
            )
        ),

    created_at timestamptz not null default now()
);


-- ============================================================
-- 8. SOURCE REFERENCES
-- Links a RAG answer back to retrieved contract sections
-- ============================================================

create table if not exists public.source_references (
    id uuid primary key default gen_random_uuid(),

    answer_id uuid not null
        references public.answers(id)
        on delete cascade,

    section_id uuid not null
        references public.contract_sections(id)
        on delete cascade,

    similarity_score double precision,

    retrieval_rank integer
        check (
            retrieval_rank is null
            or retrieval_rank >= 1
        ),

    created_at timestamptz not null default now(),

    unique (answer_id, section_id)
);


-- ============================================================
-- 9. NORMAL DATABASE INDEXES
-- ============================================================

create index if not exists idx_contract_sections_contract
on public.contract_sections(contract_id);

create index if not exists idx_detected_clauses_contract
on public.detected_clauses(contract_id);

create index if not exists idx_detected_clauses_section
on public.detected_clauses(section_id);

create index if not exists idx_detected_clauses_type
on public.detected_clauses(clause_type);

create index if not exists idx_risk_flags_contract
on public.risk_flags(contract_id);

create index if not exists idx_risk_flags_clause
on public.risk_flags(clause_id);

create index if not exists idx_questions_contract
on public.questions(contract_id);

create index if not exists idx_answers_question
on public.answers(question_id);

create index if not exists idx_sources_answer
on public.source_references(answer_id);

create index if not exists idx_sources_section
on public.source_references(section_id);


-- ============================================================
-- 10. ENABLE ROW LEVEL SECURITY
-- ============================================================

alter table public.contracts enable row level security;
alter table public.contract_sections enable row level security;
alter table public.detected_clauses enable row level security;
alter table public.risk_flags enable row level security;
alter table public.questions enable row level security;
alter table public.answers enable row level security;
alter table public.source_references enable row level security;


-- ============================================================
-- DONE
-- ============================================================