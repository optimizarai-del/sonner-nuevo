-- ════════════════════════════════════════════════════════════════════════════
-- VECTOR STORE (memoria del agente) — recrear en el proyecto PLATAFORMA
-- Correr en el SQL Editor del proyecto wndfjicwzmsuxxcsnccl.
-- Embeddings de dimensión 1536 (OpenAI text-embedding-3-small / ada-002).
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Extensión pgvector
create extension if not exists vector;

-- 2) Tabla documents (misma estructura que la memoria original)
create table if not exists public.documents (
  id        bigserial primary key,
  content   text,
  metadata  jsonb,
  embedding vector(1536)
);

-- Índice para búsqueda por similitud (coseno)
create index if not exists idx_documents_embedding
  on public.documents using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index if not exists idx_documents_metadata on public.documents using gin (metadata);

-- 3) Función de búsqueda que usa el nodo Supabase Vector Store de n8n
create or replace function public.match_documents (
  query_embedding vector(1536),
  match_count int default null,
  filter jsonb default '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where documents.metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
