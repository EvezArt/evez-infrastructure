-- EVEZ Control Plane schema proposal
-- STATUS: UNAPPLIED / REVIEW_REQUIRED
-- This migration is intentionally staged in Git because live Supabase
-- database inspection timed out during the 2026-10-04 integration pass.
--
-- Target: private schema "evez_control"
-- Design goal: keep evidence metadata isolated from public Data API exposure.

create schema if not exists evez_control;

create table if not exists evez_control.runs (
  run_id uuid primary key,
  parent_run_id uuid references evez_control.runs(run_id),
  actor text not null,
  intent text not null,
  status text not null default 'started',
  evidence_state text not null default 'UNKNOWN',
  provider text,
  model text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  input_sha256 text,
  output_sha256 text,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists evez_control.artifacts (
  artifact_id uuid primary key,
  run_id uuid not null references evez_control.runs(run_id) on delete cascade,
  kind text not null,
  uri text,
  sha256 text,
  media_type text,
  observed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists evez_control.claims (
  claim_id uuid primary key,
  run_id uuid references evez_control.runs(run_id) on delete set null,
  claim_text text not null,
  state text not null default 'PROPOSED',
  source_artifact_id uuid references evez_control.artifacts(artifact_id),
  contradiction_of uuid references evez_control.claims(claim_id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists evez_control.transitions (
  transition_id bigserial primary key,
  run_id uuid not null references evez_control.runs(run_id) on delete cascade,
  sequence_no bigint not null,
  event_type text not null,
  parent_event_hash text,
  event_hash text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (run_id, sequence_no),
  unique (event_hash)
);

create table if not exists evez_control.model_routes (
  route_id bigserial primary key,
  run_id uuid not null references evez_control.runs(run_id) on delete cascade,
  provider text not null,
  model text not null,
  capability text not null,
  selected boolean not null default false,
  outcome text,
  latency_ms integer,
  estimated_cost_usd numeric(12,6),
  failure_reason text,
  created_at timestamptz not null default now()
);

create index if not exists runs_started_at_idx
  on evez_control.runs (started_at desc);

create index if not exists artifacts_run_id_idx
  on evez_control.artifacts (run_id);

create index if not exists claims_state_idx
  on evez_control.claims (state);

create index if not exists transitions_run_seq_idx
  on evez_control.transitions (run_id, sequence_no);

create index if not exists model_routes_run_idx
  on evez_control.model_routes (run_id, created_at desc);

-- Intentionally no Data API grants and no public-schema exposure are declared here.
-- Access policy must be decided after the live database inspection succeeds.
