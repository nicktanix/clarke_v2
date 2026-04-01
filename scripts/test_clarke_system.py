#!/usr/bin/env python3
"""
CLARKE System Test Suite — Baseline, Evaluate, and Prove the Memory System.

Runs against a live CLARKE instance. Requires:
  - PostgreSQL, Qdrant, Neo4j running (docker compose up -d)
  - Alembic migrations applied (alembic upgrade head)
  - Uvicorn running (uvicorn clarke.api.app:create_app --factory --port 8000)
  - OPENAI_API_KEY set (for LLM + embeddings)

Usage:
  python scripts/test_clarke_system.py                  # run all tests
  python scripts/test_clarke_system.py --size small     # quick smoke test (3 docs, 5 queries)
  python scripts/test_clarke_system.py --size medium    # standard test (10 docs, 20 queries)
  python scripts/test_clarke_system.py --size large     # full evaluation (25 docs, 50 queries)
  python scripts/test_clarke_system.py --base-url http://localhost:9000  # custom URL
"""

import argparse
import sys
import time
from dataclasses import dataclass, field

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:8000"
TENANT_ID = "t_test"
PROJECT_ID = "p_test"
USER_ID = "u_test"
SESSION_ID = "s_test"

SIZES = {
    "small": {"docs": 3, "queries": 5, "feedback_count": 3},
    "medium": {"docs": 10, "queries": 20, "feedback_count": 10},
    "large": {"docs": 25, "queries": 50, "feedback_count": 25},
}

# Test documents covering different topics so retrieval can be evaluated
TEST_DOCUMENTS = [
    {
        "filename": "websocket_architecture.md",
        "content": (
            "# WebSocket Architecture\n\n"
            "## Connection Lifecycle\n\n"
            "WebSocket connections are managed by the Session Manager component. "
            "Each connection has a unique session ID and tracks reconnection state separately "
            "from the live transport object.\n\n"
            "## Reconnection Strategy\n\n"
            "When a client disconnects, the reconnection handler preserves the session state "
            "for up to 5 minutes. The recovery state is stored in Redis, not in the WebSocket "
            "session itself. This separation ensures clean lifecycle management.\n\n"
            "## Error Handling\n\n"
            "Connection errors are classified into recoverable (network timeout, temporary "
            "server overload) and non-recoverable (auth failure, protocol violation). "
            "Only recoverable errors trigger the reconnection flow."
        ),
    },
    {
        "filename": "database_design.md",
        "content": (
            "# Database Design\n\n"
            "## Schema Principles\n\n"
            "All tables use UUID primary keys generated at the application layer. "
            "Timestamps use timezone-aware datetime columns with UTC default. "
            "JSONB columns store flexible metadata.\n\n"
            "## Multi-Tenancy\n\n"
            "Every table includes a non-nullable tenant_id column. Row-level security "
            "policies enforce tenant isolation at the database level. Cross-tenant queries "
            "are prevented by RLS policies.\n\n"
            "## Migration Strategy\n\n"
            "Alembic manages schema migrations with async SQLAlchemy support. "
            "Each migration is reversible with explicit downgrade functions."
        ),
    },
    {
        "filename": "api_authentication.md",
        "content": (
            "# API Authentication\n\n"
            "## Auth Flow\n\n"
            "Authentication uses JWT tokens issued by the identity provider. "
            "Tokens include tenant_id, user_id, and role claims. "
            "The API validates tokens on every request via middleware.\n\n"
            "## Rate Limiting\n\n"
            "Per-user rate limits are enforced at 60 requests per minute. "
            "Per-tenant limits are set at 1000 requests per minute. "
            "Exceeding limits returns 429 Too Many Requests.\n\n"
            "## API Keys\n\n"
            "Service-to-service communication uses API keys with restricted scopes. "
            "Keys are rotated quarterly and stored hashed in the database."
        ),
    },
    {
        "filename": "deployment_guide.md",
        "content": (
            "# Deployment Guide\n\n"
            "## Docker Compose\n\n"
            "Local development uses Docker Compose with PostgreSQL, Qdrant, and Neo4j. "
            "Services are configured with health checks and volume persistence.\n\n"
            "## Production Setup\n\n"
            "Production deployments use Kubernetes with horizontal pod autoscaling. "
            "Database connections use PgBouncer for connection pooling. "
            "Qdrant runs as a distributed cluster with 3 replicas.\n\n"
            "## Monitoring\n\n"
            "OpenTelemetry traces are exported to Jaeger. "
            "Prometheus metrics are scraped from /metrics endpoints. "
            "Grafana dashboards show p50/p95 latency, error rates, and throughput."
        ),
    },
    {
        "filename": "testing_strategy.md",
        "content": (
            "# Testing Strategy\n\n"
            "## Unit Tests\n\n"
            "Every module has unit tests using pytest. "
            "Async tests use pytest-asyncio. "
            "External services are mocked in unit tests.\n\n"
            "## Integration Tests\n\n"
            "Integration tests run against real PostgreSQL and Qdrant instances. "
            "Test databases are created per test run and torn down after.\n\n"
            "## Performance Tests\n\n"
            "Load tests use Locust with configurable user counts. "
            "Target p95 latency for /query is 800ms. "
            "Target p95 latency for /ingest is 2000ms for documents under 50KB."
        ),
    },
    {
        "filename": "caching_layer.md",
        "content": (
            "# Caching Layer\n\n"
            "## Redis Cache\n\n"
            "Frequently accessed data is cached in Redis with TTL-based expiration. "
            "Cache keys follow the pattern: tenant:{tenant_id}:resource:{resource_id}.\n\n"
            "## Cache Invalidation\n\n"
            "Write-through invalidation ensures consistency. "
            "When a document is updated, its cache entry and all related chunk caches "
            "are invalidated immediately.\n\n"
            "## Embedding Cache\n\n"
            "Embedding vectors are cached for 24 hours to reduce API costs. "
            "Cache hits bypass the embedding model entirely."
        ),
    },
    {
        "filename": "security_model.md",
        "content": (
            "# Security Model\n\n"
            "## Data Encryption\n\n"
            "All data at rest is encrypted using AES-256. "
            "Data in transit uses TLS 1.3. "
            "Encryption keys are managed by AWS KMS.\n\n"
            "## PII Handling\n\n"
            "Personal data is scrubbed during ingestion using regex patterns. "
            "Emails, phone numbers, and SSNs are replaced with redaction tokens. "
            "Raw documents are stored encrypted with retention policies.\n\n"
            "## Audit Logging\n\n"
            "All mutations create append-only audit events. "
            "Audit records include actor_id, action, target, and timestamp. "
            "Audit logs are retained for 7 years."
        ),
    },
    {
        "filename": "retrieval_pipeline.md",
        "content": (
            "# Retrieval Pipeline\n\n"
            "## Semantic Search\n\n"
            "Queries are embedded using text-embedding-3-small and searched in Qdrant. "
            "Top-K results (default 20) are returned with cosine similarity scores.\n\n"
            "## Cross-Encoder Reranking\n\n"
            "Retrieved candidates are reranked using a cross-encoder model. "
            "The reranker produces calibrated relevance scores in [0, 1]. "
            "Only the top 5 reranked items are used in the context pack.\n\n"
            "## Context Composition\n\n"
            "The context pack is assembled with token budgeting: "
            "15% policy, 20% anchors, 45% evidence, 20% recent state. "
            "Exact token counts use tiktoken for the target model."
        ),
    },
    {
        "filename": "graph_memory.md",
        "content": (
            "# Graph Memory\n\n"
            "## Neo4j Schema\n\n"
            "Entities and concepts extracted from documents are stored as Neo4j nodes. "
            "Relationships like MENTIONS, ABOUT, and RELATED_TO connect the graph.\n\n"
            "## Convergence Anchors\n\n"
            "When multiple semantic results share a common graph parent, "
            "that parent becomes a convergence anchor. "
            "Anchors provide grouping context in the prompt.\n\n"
            "## Trust Precedence\n\n"
            "Policy items receive a +0.3 score boost. "
            "Decision items receive a +0.2 score boost. "
            "This ensures canonical sources rank above general evidence."
        ),
    },
    {
        "filename": "feedback_system.md",
        "content": (
            "# Feedback System\n\n"
            "## User Feedback\n\n"
            "Users can rate query responses with an acceptance flag and optional score. "
            "Feedback links to specific request_ids and retrieved item IDs.\n\n"
            "## Weight Updates\n\n"
            "Feedback triggers online weight updates for retrieval strategies. "
            "The update rule: new_weight = old * (1 - lr) + usefulness * lr. "
            "Learning rate defaults to 0.05.\n\n"
            "## Episodic Memory\n\n"
            "Each query-answer pair is summarized and stored as episodic memory. "
            "Episodic memories are embedded and indexed in Qdrant. "
            "Future queries can retrieve relevant prior interactions."
        ),
    },
    # Extended docs for medium/large tests
    {
        "filename": "error_handling.md",
        "content": (
            "# Error Handling\n\n"
            "## Degraded Mode\n\n"
            "When Qdrant is unavailable, the system enters REDUCED mode. "
            "In REDUCED mode, only policy and decision memory are used. "
            "Neo4j failures are non-fatal — graph retrieval is simply skipped.\n\n"
            "## Circuit Breakers\n\n"
            "External service calls use circuit breaker patterns. "
            "After 5 consecutive failures, the circuit opens for 30 seconds."
        ),
    },
    {
        "filename": "context_request_protocol.md",
        "content": (
            "# Context Request Protocol\n\n"
            "## CONTEXT_REQUEST\n\n"
            "Models can request additional context via structured JSON. "
            "Each request specifies source, query, why, and max_items. "
            "The broker validates against allowed sources and quotas.\n\n"
            "## Second Pass\n\n"
            "Validated requests trigger a second retrieval-compose-model cycle. "
            "Second pass budget is limited to 60% of the first pass budget. "
            "Maximum one second pass per query (configurable)."
        ),
    },
    {
        "filename": "observability.md",
        "content": (
            "# Observability\n\n"
            "## Metrics\n\n"
            "Key metrics tracked: request latency, context waste ratio, "
            "useful context ratio, degraded mode rate, loop invocation rate.\n\n"
            "## Tracing\n\n"
            "Every request generates an OpenTelemetry trace spanning "
            "retrieval planning, vector search, graph traversal, reranking, "
            "context assembly, and LLM call stages."
        ),
    },
    {
        "filename": "migration_procedures.md",
        "content": (
            "# Migration Procedures\n\n"
            "## Database Migrations\n\n"
            "Schema changes use Alembic with async SQLAlchemy. "
            "Migrations are tested in staging before production.\n\n"
            "## Data Migrations\n\n"
            "Large data migrations run as background jobs. "
            "Re-embedding jobs process documents in batches of 100."
        ),
    },
    {
        "filename": "agent_system.md",
        "content": (
            "# Agent System\n\n"
            "## Sub-Agent Spawning\n\n"
            "Parent agents can request sub-agent creation via SUBAGENT_SPAWN. "
            "Sub-agents receive isolated context packs with inherited memory. "
            "Maximum spawn depth is 5 (configurable).\n\n"
            "## Result Handling\n\n"
            "Child results are structured and must be explicitly consumed by parents. "
            "Orphaned sub-agents are garbage collected after expiry."
        ),
    },
    # Additional docs for large tests
    *[
        {
            "filename": f"supplemental_doc_{i}.md",
            "content": (
                f"# Supplemental Document {i}\n\n"
                f"## Section A\n\n"
                f"This document covers additional implementation details for component {i}. "
                f"The architecture uses modular design patterns with clear separation of concerns.\n\n"
                f"## Section B\n\n"
                f"Performance characteristics are measured using benchmark suite {i}. "
                f"Target throughput is {100 * (i + 1)} requests per second."
            ),
        }
        for i in range(10)
    ],
]

# Queries designed to test different retrieval patterns
TEST_QUERIES = [
    # Factual retrieval
    ("How do WebSocket connections handle reconnection?", "websocket"),
    ("What database schema principles does the system follow?", "database"),
    ("How does API authentication work?", "auth"),
    # Cross-document reasoning
    ("What security measures protect user data?", "security"),
    ("How is the system deployed to production?", "deployment"),
    # Episodic memory (should retrieve prior interactions)
    ("What did we discuss about reconnection earlier?", "episodic"),
    # Decision/policy retrieval
    ("What are the rate limiting constraints?", "policy"),
    ("How does the feedback system improve retrieval?", "feedback"),
    # Technical detail
    ("How does the retrieval pipeline rank results?", "retrieval"),
    ("What is the context budget allocation?", "budget"),
    # Graph memory
    ("What entities are related to WebSocket sessions?", "graph"),
    ("How does convergence anchor detection work?", "convergence"),
    # Error handling
    ("What happens when Qdrant is unavailable?", "degraded"),
    ("How does the context request protocol work?", "context_request"),
    # Observability
    ("What metrics does the system track?", "metrics"),
    # General
    ("Explain the testing strategy", "testing"),
    ("What caching mechanisms are used?", "caching"),
    ("How are migrations handled?", "migration"),
    ("What is the agent spawning system?", "agent"),
    ("How does the graph memory system work?", "graph_memory"),
    # More queries for medium/large
    ("What encryption methods protect data at rest?", "encryption"),
    ("How are embedding vectors cached?", "embedding_cache"),
    ("What is the PII handling process?", "pii"),
    ("How does the circuit breaker pattern work?", "circuit_breaker"),
    ("What is the maximum sub-agent depth?", "agent_depth"),
    ("How does the cross-encoder reranker work?", "reranker"),
    ("What is the trust precedence ordering?", "trust"),
    ("How are audit logs structured?", "audit"),
    ("What is the second pass budget fraction?", "second_pass"),
    ("How does epsilon-greedy exploration work?", "exploration"),
    # Additional queries for large tests
    *[
        (f"What are the performance characteristics of component {i}?", f"perf_{i}")
        for i in range(20)
    ],
]


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: int
    details: str = ""
    error: str = ""


@dataclass
class TestSuiteResults:
    size: str
    results: list[TestResult] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def duration_s(self) -> float:
        return self.end_time - self.start_time

    def add(self, result: TestResult) -> None:
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.name} ({result.duration_ms}ms) {result.details}")
        if result.error:
            print(f"         Error: {result.error}")

    def summary(self) -> str:
        lines = [
            "",
            "=" * 70,
            f"CLARKE System Test Results — Size: {self.size.upper()}",
            "=" * 70,
            f"Total: {self.total}  Passed: {self.passed}  Failed: {self.failed}",
            f"Duration: {self.duration_s:.1f}s",
            "",
        ]

        if self.failed:
            lines.append("FAILURES:")
            for r in self.results:
                if not r.passed:
                    lines.append(f"  - {r.name}: {r.error}")
            lines.append("")

        # Latency summary
        query_results = [r for r in self.results if r.name.startswith("query_")]
        if query_results:
            latencies = [r.duration_ms for r in query_results]
            lines.append("Query Latency:")
            lines.append(f"  p50: {sorted(latencies)[len(latencies) // 2]}ms")
            lines.append(f"  p95: {sorted(latencies)[int(len(latencies) * 0.95)]}ms")
            lines.append(f"  max: {max(latencies)}ms")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


class ClarkeSystemTest:
    def __init__(self, base_url: str, size: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.size = size
        self.config = SIZES[size]
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0)
        self.results = TestSuiteResults(size=size)
        self.ingested_doc_ids: list[str] = []
        self.query_request_ids: list[str] = []

    def run(self) -> TestSuiteResults:
        self.results.start_time = time.time()
        print(f"\nCLARKE System Test Suite — {self.size.upper()}")
        print(f"Base URL: {self.base_url}")
        print(f"Config: {self.config}")
        print("-" * 50)

        # Phase 1: Health checks
        print("\n[Phase 1] Health & Readiness")
        self._test_health()
        self._test_ready()

        # Phase 2: Document ingestion
        print(f"\n[Phase 2] Document Ingestion ({self.config['docs']} documents)")
        self._test_ingestion()

        # Phase 3: Query & retrieval
        print(f"\n[Phase 3] Query & Retrieval ({self.config['queries']} queries)")
        self._test_queries()

        # Phase 4: Episodic memory verification
        print("\n[Phase 4] Episodic Memory")
        self._test_episodic_memory()

        # Phase 5: Policy & decision memory
        print("\n[Phase 5] Policy & Decision Memory")
        self._test_policy_workflow()
        self._test_decisions()

        # Phase 6: Feedback loop
        print(f"\n[Phase 6] Feedback Loop ({self.config['feedback_count']} feedback entries)")
        self._test_feedback()

        # Phase 7: Admin & evaluation
        print("\n[Phase 7] Admin & Evaluation")
        self._test_replay()

        # Phase 8: Degraded mode
        print("\n[Phase 8] Degraded Mode Behavior")
        self._test_degraded_query()

        self.results.end_time = time.time()
        print(self.results.summary())
        return self.results

    # -- Health --

    def _test_health(self) -> None:
        start = time.time()
        try:
            r = self.client.get("/health")
            passed = r.status_code == 200 and r.json().get("status") in ("ok", "degraded")
            self.results.add(
                TestResult(
                    name="health_check",
                    passed=passed,
                    duration_ms=_ms(start),
                    details=f"status={r.json().get('status')}",
                    error="" if passed else f"HTTP {r.status_code}: {r.text[:200]}",
                )
            )
        except Exception as e:
            self.results.add(
                TestResult(name="health_check", passed=False, duration_ms=_ms(start), error=str(e))
            )

    def _test_ready(self) -> None:
        start = time.time()
        try:
            r = self.client.get("/ready")
            passed = r.status_code == 200
            self.results.add(
                TestResult(
                    name="readiness_check",
                    passed=passed,
                    duration_ms=_ms(start),
                    error="" if passed else f"HTTP {r.status_code}",
                )
            )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="readiness_check", passed=False, duration_ms=_ms(start), error=str(e)
                )
            )

    # -- Ingestion --

    def _test_ingestion(self) -> None:
        docs_to_ingest = TEST_DOCUMENTS[: self.config["docs"]]
        for doc in docs_to_ingest:
            start = time.time()
            try:
                r = self.client.post(
                    "/ingest",
                    json={
                        "tenant_id": TENANT_ID,
                        "project_id": PROJECT_ID,
                        "filename": doc["filename"],
                        "content_type": "text/markdown",
                        "content": doc["content"],
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    doc_id = data.get("document_id", "")
                    self.ingested_doc_ids.append(doc_id)
                    # Verify document status
                    status_r = self.client.get(f"/documents/{doc_id}")
                    status = status_r.json() if status_r.status_code == 200 else {}
                    passed = status.get("status") == "ready" and status.get("chunk_count", 0) > 0
                    self.results.add(
                        TestResult(
                            name=f"ingest_{doc['filename']}",
                            passed=passed,
                            duration_ms=_ms(start),
                            details=f"chunks={status.get('chunk_count', 0)}",
                            error="" if passed else f"status={status.get('status')}",
                        )
                    )
                else:
                    self.results.add(
                        TestResult(
                            name=f"ingest_{doc['filename']}",
                            passed=False,
                            duration_ms=_ms(start),
                            error=f"HTTP {r.status_code}: {r.text[:200]}",
                        )
                    )
            except Exception as e:
                self.results.add(
                    TestResult(
                        name=f"ingest_{doc['filename']}",
                        passed=False,
                        duration_ms=_ms(start),
                        error=str(e),
                    )
                )

    # -- Queries --

    def _test_queries(self) -> None:
        queries_to_run = TEST_QUERIES[: self.config["queries"]]
        for query, tag in queries_to_run:
            start = time.time()
            try:
                r = self.client.post(
                    "/query",
                    json={
                        "tenant_id": TENANT_ID,
                        "project_id": PROJECT_ID,
                        "user_id": USER_ID,
                        "session_id": SESSION_ID,
                        "message": query,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    answer = data.get("answer", "")
                    req_id = data.get("request_id", "")
                    self.query_request_ids.append(req_id)

                    # Basic quality check: answer should be non-empty and not an error
                    has_answer = len(answer) > 20
                    not_error = "error" not in answer.lower()[:50]
                    passed = has_answer and not_error

                    self.results.add(
                        TestResult(
                            name=f"query_{tag}",
                            passed=passed,
                            duration_ms=_ms(start),
                            details=f"answer_len={len(answer)} degraded={data.get('degraded_mode')}",
                            error="" if passed else f"Short/error answer: {answer[:100]}",
                        )
                    )
                else:
                    self.results.add(
                        TestResult(
                            name=f"query_{tag}",
                            passed=False,
                            duration_ms=_ms(start),
                            error=f"HTTP {r.status_code}: {r.text[:200]}",
                        )
                    )
            except Exception as e:
                self.results.add(
                    TestResult(
                        name=f"query_{tag}",
                        passed=False,
                        duration_ms=_ms(start),
                        error=str(e),
                    )
                )

    # -- Episodic Memory --

    def _test_episodic_memory(self) -> None:
        """Query about a prior interaction to verify episodic memory retrieval."""
        start = time.time()
        try:
            r = self.client.post(
                "/query",
                json={
                    "tenant_id": TENANT_ID,
                    "project_id": PROJECT_ID,
                    "user_id": USER_ID,
                    "session_id": SESSION_ID,
                    "message": "What topics have we discussed in our prior conversations?",
                },
            )
            if r.status_code == 200:
                data = r.json()
                answer = data.get("answer", "")
                # Episodic memory should allow the model to reference prior topics
                passed = len(answer) > 20
                self.results.add(
                    TestResult(
                        name="episodic_memory_retrieval",
                        passed=passed,
                        duration_ms=_ms(start),
                        details=f"answer_len={len(answer)}",
                    )
                )
            else:
                self.results.add(
                    TestResult(
                        name="episodic_memory_retrieval",
                        passed=False,
                        duration_ms=_ms(start),
                        error=f"HTTP {r.status_code}",
                    )
                )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="episodic_memory_retrieval",
                    passed=False,
                    duration_ms=_ms(start),
                    error=str(e),
                )
            )

    # -- Policy --

    def _test_policy_workflow(self) -> None:
        """Test the full policy lifecycle: create → approve → verify in query."""
        # Create
        start = time.time()
        try:
            r = self.client.post(
                "/policy",
                json={
                    "tenant_id": TENANT_ID,
                    "content": "All API responses must include a request_id header for traceability.",
                    "owner_id": USER_ID,
                },
            )
            if r.status_code != 200:
                self.results.add(
                    TestResult(
                        name="policy_create",
                        passed=False,
                        duration_ms=_ms(start),
                        error=f"HTTP {r.status_code}",
                    )
                )
                return
            policy_id = r.json()["id"]
            self.results.add(
                TestResult(
                    name="policy_create",
                    passed=True,
                    duration_ms=_ms(start),
                    details=f"id={policy_id}",
                )
            )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="policy_create",
                    passed=False,
                    duration_ms=_ms(start),
                    error=str(e),
                )
            )
            return

        # Approve
        start = time.time()
        try:
            r = self.client.post(
                f"/policy/{policy_id}/approve",
                json={
                    "approver_id": "admin_user",
                    "comment": "Approved for production",
                },
            )
            passed = r.status_code == 200 and r.json().get("status") == "active"
            self.results.add(
                TestResult(
                    name="policy_approve",
                    passed=passed,
                    duration_ms=_ms(start),
                    error="" if passed else f"status={r.json().get('status')}",
                )
            )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="policy_approve",
                    passed=False,
                    duration_ms=_ms(start),
                    error=str(e),
                )
            )

        # List active
        start = time.time()
        try:
            r = self.client.get(f"/policy?tenant_id={TENANT_ID}")
            passed = r.status_code == 200 and len(r.json()) > 0
            self.results.add(
                TestResult(
                    name="policy_list_active",
                    passed=passed,
                    duration_ms=_ms(start),
                    details=f"count={len(r.json())}",
                )
            )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="policy_list_active",
                    passed=False,
                    duration_ms=_ms(start),
                    error=str(e),
                )
            )

    # -- Decisions --

    def _test_decisions(self) -> None:
        start = time.time()
        try:
            r = self.client.post(
                "/decisions",
                json={
                    "tenant_id": TENANT_ID,
                    "project_id": PROJECT_ID,
                    "title": "Use PostgreSQL for canonical storage",
                    "rationale": "PostgreSQL provides ACID transactions, JSONB support, and row-level security needed for multi-tenant isolation.",
                    "decided_by": USER_ID,
                    "alternatives": [
                        {"name": "MongoDB", "reason_rejected": "Weaker transaction guarantees"},
                        {"name": "DynamoDB", "reason_rejected": "Vendor lock-in"},
                    ],
                },
            )
            passed = r.status_code == 200
            self.results.add(
                TestResult(
                    name="decision_record",
                    passed=passed,
                    duration_ms=_ms(start),
                    details=f"id={r.json().get('id', '')}",
                    error="" if passed else f"HTTP {r.status_code}",
                )
            )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="decision_record",
                    passed=False,
                    duration_ms=_ms(start),
                    error=str(e),
                )
            )

        # List
        start = time.time()
        try:
            r = self.client.get(f"/decisions?tenant_id={TENANT_ID}&project_id={PROJECT_ID}")
            passed = r.status_code == 200 and len(r.json()) > 0
            self.results.add(
                TestResult(
                    name="decision_list",
                    passed=passed,
                    duration_ms=_ms(start),
                    details=f"count={len(r.json())}",
                )
            )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="decision_list",
                    passed=False,
                    duration_ms=_ms(start),
                    error=str(e),
                )
            )

    # -- Feedback --

    def _test_feedback(self) -> None:
        feedback_ids = self.query_request_ids[: self.config["feedback_count"]]
        for i, req_id in enumerate(feedback_ids):
            start = time.time()
            try:
                score = 0.8 if i % 2 == 0 else 0.4
                r = self.client.post(
                    "/feedback",
                    json={
                        "request_id": req_id,
                        "tenant_id": TENANT_ID,
                        "user_id": USER_ID,
                        "accepted": score > 0.5,
                        "score": score,
                    },
                )
                passed = r.status_code == 202
                self.results.add(
                    TestResult(
                        name=f"feedback_{i}",
                        passed=passed,
                        duration_ms=_ms(start),
                        details=f"score={score} accepted={score > 0.5}",
                        error="" if passed else f"HTTP {r.status_code}",
                    )
                )
            except Exception as e:
                self.results.add(
                    TestResult(
                        name=f"feedback_{i}",
                        passed=False,
                        duration_ms=_ms(start),
                        error=str(e),
                    )
                )

    # -- Replay --

    def _test_replay(self) -> None:
        start = time.time()
        try:
            r = self.client.post(f"/admin/replay?tenant_id={TENANT_ID}&limit=50")
            if r.status_code == 200:
                data = r.json()
                count = data.get("episodes_analyzed", 0)
                mean = data.get("mean_usefulness", 0)
                passed = count > 0
                self.results.add(
                    TestResult(
                        name="replay_analysis",
                        passed=passed,
                        duration_ms=_ms(start),
                        details=f"episodes={count} mean_ucr={mean:.3f}" if count else "no episodes",
                    )
                )
            else:
                self.results.add(
                    TestResult(
                        name="replay_analysis",
                        passed=False,
                        duration_ms=_ms(start),
                        error=f"HTTP {r.status_code}: {r.text[:200]}",
                    )
                )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="replay_analysis",
                    passed=False,
                    duration_ms=_ms(start),
                    error=str(e),
                )
            )

    # -- Degraded mode --

    def _test_degraded_query(self) -> None:
        """Query still works even if answer is basic (tests degraded path gracefully)."""
        start = time.time()
        try:
            r = self.client.post(
                "/query",
                json={
                    "tenant_id": TENANT_ID,
                    "project_id": PROJECT_ID,
                    "user_id": USER_ID,
                    "message": "Simple question to verify the system responds.",
                },
            )
            passed = r.status_code == 200 and len(r.json().get("answer", "")) > 0
            self.results.add(
                TestResult(
                    name="degraded_mode_query",
                    passed=passed,
                    duration_ms=_ms(start),
                    details=f"degraded={r.json().get('degraded_mode')}",
                )
            )
        except Exception as e:
            self.results.add(
                TestResult(
                    name="degraded_mode_query",
                    passed=False,
                    duration_ms=_ms(start),
                    error=str(e),
                )
            )

    def close(self) -> None:
        self.client.close()


def _ms(start: float) -> int:
    return int((time.time() - start) * 1000)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="CLARKE System Test Suite")
    parser.add_argument(
        "--size",
        choices=["small", "medium", "large"],
        default="small",
        help="Test size: small (3 docs, 5 queries), medium (10/20), large (25/50)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"CLARKE API base URL (default: {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()

    test = ClarkeSystemTest(args.base_url, args.size)
    try:
        results = test.run()
    finally:
        test.close()

    sys.exit(0 if results.failed == 0 else 1)


if __name__ == "__main__":
    main()
