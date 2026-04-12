# ADR 0003: Vector Store Choice for Research Memory

- Status: Accepted
- Date: 2026-04-08
- Owners: HaruQuant engineering
- Related Plan Item: `docs/agentic_ai/implementation_plan.md`

## Context

The target agentic architecture requires semantic retrieval for:
- approved internal research notes
- prior experiments and postmortems
- playbooks and operator-authored knowledge
- document fragments used by grounded research workflows

The architecture documents describe a vector memory capability but leave the concrete store open:
- the design names Pinecone, Weaviate, or an equivalent vector store as valid options
- retrieval is required to stay behind approved tools and include freshness and source references
- vector memory is explicitly advisory until validated against current structured data

Current repo state:
- there is no existing vector database deployment to preserve
- the current migration phases are focused on delivery foundations and governance, not scale tuning
- PostgreSQL is already the planned authoritative state store for workflow and governance records

Constraints that matter now:
- the first research-oriented slices should minimize new infrastructure
- local development and test environments should stay easy to run
- the retrieval boundary must remain replaceable if scale, recall, or operational needs change later

## Decision

HaruQuant will use PostgreSQL with `pgvector` as the initial vector store for research memory and retrieval.

Scope of this decision:
- embeddings and vector indexes for research-oriented document chunks
- similarity search used by approved retrieval tools
- metadata joins between vector hits and authoritative relational records

This decision does not finalize:
- the long-term embedding model lifecycle policy
- chunking strategy for every document family
- a permanent exclusion of specialized managed vector databases later

## Consequences

Positive:
- keeps the first retrieval implementation close to the existing planned PostgreSQL backbone
- reduces infrastructure sprawl during early migration phases
- simplifies local, test, and staging setups compared with introducing a separate vector platform immediately
- supports joining semantic search results with relational metadata and governance state in one system

Negative:
- may not be the best long-term fit if corpus size, recall requirements, or retrieval throughput grow materially
- places vector indexing and OLTP concerns on the same database platform
- later migration to a dedicated vector store may be needed for scale or operational isolation

## Alternatives Considered

### Pinecone

- summary: managed vector database with strong operational simplicity for semantic search workloads
- reason not chosen: adds a new external platform before the first research slice proves the retrieval workload and data shape

### Weaviate

- summary: dedicated vector database with rich retrieval features and hybrid search support
- reason not chosen: introduces extra infrastructure and operational complexity earlier than the migration currently needs

### No vector store initially

- summary: delay semantic retrieval and rely only on SQL/document search
- reason not chosen: does not satisfy the target architecture's retrieval direction for research memory and would postpone a core boundary decision

## Implementation Notes

- hide vector operations behind a retrieval service or MCP boundary rather than binding application logic directly to `pgvector`
- store authoritative source metadata, freshness fields, and governance attributes in relational tables
- treat vector hits as advisory evidence that must still carry source references and freshness metadata
- define a re-evaluation point once corpus size, latency, and recall benchmarks exist

Re-evaluation triggers:
- corpus growth large enough to pressure PostgreSQL operational limits
- retrieval latency or recall misses against research workflow targets
- need for specialized hybrid retrieval or multi-tenant vector isolation

## Follow-Up

- [ ] define the embedding record schema and metadata fields needed for freshness, provenance, and legal-hold-aware retrieval
- [ ] benchmark initial `pgvector` retrieval latency and recall before Phase 3 research workflows are considered complete
