# EVEZ Control Plane

Status: DESIGN + REPOSITORY IMPLEMENTATION
Deployment state: NOT YET APPLIED TO SUPABASE

## Purpose

Unify the EVEZ system around four external capabilities:

- GitHub: source of truth, change history, review, releases.
- Supabase: durable operational state, evidence index, run metadata.
- Hugging Face: open-model discovery and optional compute/model artifacts.
- OpenAI Platform: hosted reasoning and application-model access.

The control plane must never confuse a declaration with an observation.

## Core invariant

CLAIMED != MEASURED != REPLICATED != EXPLAINED

Every agent operation therefore emits a record with:

- run_id
- actor
- intent
- inputs
- selected provider/model
- source artifacts
- transforms
- tests
- result
- confidence/state
- parent event
- content hash
- timestamp

Unknown data remains UNKNOWN. Proposed explanations remain PROPOSED until evidence promotes them.

## System flow

GitHub
  |
  | code/spec/review
  v
EVEZ Control Plane
  |
  +--> OpenAI: reasoning / structured synthesis
  |
  +--> Hugging Face: model registry / optional jobs
  |
  +--> Supabase: durable run + evidence index
  |
  +--> EventSpine: append-only cryptographic event history
  |
  v
deployments / research / products / agents

## Routing policy

1. Prefer deterministic/local execution when equivalent.
2. Route reasoning to the least expensive adequate model.
3. Use open models for reproducible experiments and batch work.
4. Use hosted models for high-value synthesis, planning, and tool orchestration.
5. Every external call must have a provider, model, purpose, and cost/latency record when available.
6. A failed provider is a routing event, not evidence that the underlying task is impossible.

## Evidence states

VERIFIED
SUPPORTED
INFERRED
PROPOSED
UNKNOWN
STALE
CONTRADICTED
RETRACTED

## Safety rails

- Never commit secrets.
- Never place OpenAI, Supabase service-role, or Hugging Face write credentials in client bundles or git.
- Never treat model output as an observation without an external evidence reference.
- Never silently overwrite EventSpine history.
- Never promote generated numerical precision to empirical status without preserved code, inputs, parameters, trace, and outputs.
- Destructive infrastructure changes require an explicit deployment step.

## Immediate build order

### Phase 0: source-of-truth
- Keep architecture and migrations in Git.
- Add provider/model manifests beside application code.
- Add CI checks for secret leakage and schema syntax.

### Phase 1: evidence spine
- Create the private `evez_control` database schema.
- Store runs, artifacts, claims, transitions, and model-routing records.
- Keep application data separate from evidence metadata.

### Phase 2: model routing
- Register OpenAI and Hugging Face models by capability, context, latency class, and cost class.
- Add fallback routing with explicit failure reasons.
- Emit one EventSpine event per route decision.

### Phase 3: agent orchestration
- Connect the existing agent-bridge and autonomous-research-orchestrator services.
- Require every autonomous action to create a run record.
- Require every published result to point to its evidence chain.

### Phase 4: deployment
- Deploy the control-plane API beside existing EVEZ infrastructure.
- Add health checks, provider probes, and replay tooling.
- Publish a machine-readable status endpoint.

## Current connector reality

Observed on 2026-10-04:

- GitHub account: EvezArt / Steven Crawford-Maggard.
- Hugging Face account: evez420; authenticated read-repo + jobs scopes; no visible organization memberships.
- Supabase: EVEZ project `vziaqxquzohqskesuxgz`, active/healthy.
- OpenAI Platform: EVEZ organization with the default project available.
- OpenAI key setup flow initialized for `EVEZ-Control-Plane`.

Supabase database inspection currently times out through the connected database endpoint. No live schema mutation is claimed or recorded from this pass.

## Definition of done

The control plane is complete when:

1. A task can be created once and routed across providers.
2. Every execution has a durable run id.
3. Every result can be replayed from source artifacts.
4. Contradictions are preserved instead of erased.
5. Provider failures and cost signals are observable.
6. A deployment can be reproduced from Git commits + migrations + model references.
