# ClauseNexa — Backend Overview

Notes on what the backend currently does, how it's structured, and how it talks to Supabase. Written as a reference for explaining the work (e.g. to a professor/reviewer).

## 1. What exists today

A **FastAPI** service backed by **Supabase** (hosted Postgres + object storage). The implemented feature is a full upload pipeline: a client sends a contract file (PDF/DOCX), the backend stores the raw file in Supabase Storage and records its metadata in Supabase Postgres.

The database schema also provisions tables for clause detection, risk flagging, and RAG-based Q&A — but those are **schema-only** so far; no API code uses them yet. That's the planned next phase (NLP/RAG pipeline).

## 2. File map

```
backend/
├── app/
│   ├── main.py              → FastAPI app entrypoint
│   ├── database.py          → Supabase client singleton
│   ├── models/
│   │   └── contract.py      → Pydantic response schema
│   ├── routes/
│   │   └── contracts.py     → POST /contracts/upload endpoint
│   └── services/
│       └── storage.py       → Supabase Storage upload helper
├── requirements.txt
└── test_database.py         → manual DB insert smoke test
supabase/
└── schema.sql                → full Postgres schema (9 tables)
```

## 3. Database connection — `app/database.py`

```python
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
```

- Loads `SUPABASE_URL` and `SUPABASE_SECRET_KEY` from a `.env` file (`python-dotenv`).
- Fails fast (`RuntimeError`) at import time if either variable is missing.
- Creates a single `supabase` client object that every other module imports and reuses.

**Key detail:** this uses the **secret key** (service role), not the anon/public key. That gives the backend full DB access and bypasses Row Level Security — appropriate since it's a trusted server and the frontend never talks to Supabase directly. RLS is enabled on every table in the schema, but no policies are defined yet, so only the secret-key backend can read/write this data.

## 4. Database schema — `supabase/schema.sql`

Applied directly via the Supabase SQL editor (no migration tool yet). Nine tables:

| Table | Purpose |
|---|---|
| `contracts` | One row per uploaded file (filename, storage path, status: `uploaded → processing → processed / failed`) |
| `contract_sections` | Chunked contract text for RAG retrieval, each with a `chunk_index` |
| `detected_clauses` | Output of the NLP clause-classification model (termination, payment, confidentiality, liability, non_compete, governing_law) with a confidence score |
| `risk_flags` | Rule-based risk annotations tied to a clause (`low` / `attention` / `high`) |
| `questions` | User questions asked about a contract |
| `answers` | LLM/RAG-generated answers, with a faithfulness score |
| `source_references` | Links an answer back to the `contract_sections` it was retrieved from — the RAG citation trail |

Other details:
- `pgvector` extension enabled (for embeddings later — no `vector` column exists yet).
- Foreign keys cascade deletes from `contracts` down through all related tables.
- Indexes added on all foreign-key columns for query performance.
- RLS (`enable row level security`) turned on for every table.

**Only `contracts` is used by the API today.** The rest is schema-ready, code-empty — reserved for the NLP/RAG phase.

## 5. Response model — `app/models/contract.py`

```python
class ContractResponse(BaseModel):
    contract_id: str
    file_name: str
    storage_path: str
    status: str
    message: Optional[str] = None
```

A Pydantic model FastAPI uses to validate/serialize the upload endpoint's response, and to auto-generate the OpenAPI/Swagger docs at `/docs`.

## 6. Storage upload — `app/services/storage.py`

```python
storage_path = f"{contract_id}/{uuid.uuid4()}.{file_extension}"
file_bytes = await file.read()
supabase.storage.from_(BUCKET_NAME).upload(
    path=storage_path,
    file=file_bytes,
    file_options={"content-type": file.content_type, "upsert": "false"},
)
```

- Uploads raw file bytes to the Supabase Storage bucket `"contracts"`.
- Path is namespaced by `contract_id` (a folder per contract) plus a random filename — avoids collisions even if two uploads share an original filename.
- `upsert: "false"` — errors rather than silently overwriting.
- Returns the storage path string (not a public URL) — files stay private, accessed later only via the backend.

## 7. Upload endpoint — `app/routes/contracts.py`

`POST /contracts/upload` — this is the core request flow:

1. **Validate filename** exists on the `UploadFile`.
2. **Validate extension** — only `.pdf` / `.docx` allowed.
3. **Validate MIME type** — `file.content_type` checked against an allowlist (extension + declared type must both match; basic anti-spoofing).
4. **Generate `contract_id`** (`uuid.uuid4()`) — used as both the DB primary key and the storage folder name, correlating the file and its metadata before either write happens.
5. **Upload to Storage** via `upload_contract_file()` — **call #1** to Supabase (Storage REST API).
6. **Insert contract row into Postgres**:
   ```python
   supabase.table("contracts").insert(contract_data).execute()
   ```
   — **call #2** to Supabase, via **PostgREST** (Supabase's REST layer over Postgres). The `supabase-py` SDK builds a REST request; Supabase translates it into an `INSERT`. This is *not* a raw SQL/psycopg2 connection.
7. **Check `response.data`** — if the insert returned no rows, raise an error.
8. **Return `ContractResponse`** — FastAPI serializes it to JSON.
9. **Rollback on failure**: if step 6 fails after step 5 succeeded, the `except` block calls `supabase.storage.from_("contracts").remove([storage_path])` to delete the orphaned file. This is a manual compensating action (Storage and Postgres aren't in one ACID transaction) — it avoids leaking files with no matching DB row.

### Request flow diagram

```
Client → POST /contracts/upload (multipart file)
   → FastAPI validates extension + MIME type
   → generate contract_id (uuid)
   → supabase.storage.from_("contracts").upload(...)     [Supabase Storage REST API]
   → supabase.table("contracts").insert(...).execute()   [Supabase PostgREST]
   → return ContractResponse JSON
   (on DB failure: storage file is deleted to avoid orphans)
```

## 8. App entrypoint — `app/main.py`

```python
app = FastAPI(title="ClauseNexa API", ...)
app.include_router(contracts_router)
```

- `GET /` — basic root check.
- `GET /health` — health/readiness probe.
- Contracts router mounted with its `/contracts` prefix, so the full upload path is `/contracts/upload`.

## 9. Smoke test — `test_database.py`

A standalone script (not pytest — no assertions) that inserts a dummy contract row directly and prints the result. Used to manually verify the Supabase client/credentials are working: `python test_database.py`.

## 10. Key architectural points to remember

- **No raw SQL connection** — everything goes through the `supabase-py` SDK, which talks to Supabase's HTTP APIs (PostgREST for the database, a separate REST API for Storage).
- **Two calls per upload** — Storage upload happens *before* the Postgres insert, because it's cheaper to clean up an orphaned file (via the rollback step) than an orphaned DB row that references a missing file.
- **Service-role key** — the backend has full DB/storage access; RLS is enabled but has no policies yet, since the frontend never talks to Supabase directly (it goes through this FastAPI backend).
- **Schema is ahead of the code** — clause detection, risk flags, and Q&A/RAG tables are already modeled in Postgres, ready for the NLP pipeline to fill in.
