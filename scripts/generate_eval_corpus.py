#!/usr/bin/env python3
"""Generate a synthetic technical documentation corpus for CLARKE evaluation.

Produces 150 interconnected documents (~600K tokens total) and 100 questions
with gold answers referencing specific source documents.

Usage:
    python scripts/generate_eval_corpus.py
    python scripts/generate_eval_corpus.py --output evals/corpus
"""

import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Document templates — each generates realistic technical content with
# embedded factual claims that can be queried against.
# ---------------------------------------------------------------------------

CATEGORIES = {
    "arch": {
        "count": 20,
        "title_prefix": "Architecture",
        "topics": [
            ("System Overview", "microservices", "event-driven", "API gateway"),
            ("Data Flow Pipeline", "ingestion", "transformation", "enrichment"),
            ("Service Mesh", "sidecar proxies", "mTLS", "service discovery"),
            ("Message Queue", "RabbitMQ", "dead letter queues", "retry policies"),
            ("Caching Strategy", "Redis cluster", "TTL policies", "invalidation"),
            ("Load Balancing", "round-robin", "health checks", "circuit breakers"),
            ("Authentication Flow", "OAuth 2.0", "JWT tokens", "refresh rotation"),
            ("Authorization Model", "RBAC", "attribute-based", "policy engine"),
            ("Event Sourcing", "event store", "projections", "snapshots"),
            ("CQRS Pattern", "command handlers", "query side", "read models"),
            ("Domain Model", "aggregates", "value objects", "domain events"),
            ("Integration Layer", "API adapters", "webhooks", "polling"),
            ("Notification System", "email", "push", "in-app"),
            ("Search Infrastructure", "Elasticsearch", "indexing", "relevance"),
            ("File Storage", "S3", "presigned URLs", "lifecycle policies"),
            ("Logging Architecture", "structured logs", "correlation IDs", "log levels"),
            ("Metrics Collection", "Prometheus", "custom metrics", "alerting"),
            ("Tracing System", "OpenTelemetry", "span propagation", "sampling"),
            ("Configuration Management", "feature flags", "environment configs", "secrets"),
            ("Error Handling", "retry strategies", "circuit breakers", "fallback"),
        ],
    },
    "api": {
        "count": 20,
        "title_prefix": "API",
        "topics": [
            ("User Management", "CRUD operations", "profile updates", "deactivation"),
            ("Authentication Endpoints", "login", "logout", "token refresh"),
            ("Project Management", "create project", "permissions", "archival"),
            ("Document Upload", "multipart upload", "validation", "processing"),
            ("Search API", "full-text search", "filters", "pagination"),
            ("Webhook Management", "registration", "retry", "payload signing"),
            ("Rate Limiting", "per-user limits", "burst allowance", "429 responses"),
            ("Batch Operations", "bulk create", "bulk update", "async processing"),
            ("Export API", "CSV export", "JSON streaming", "large dataset handling"),
            ("Admin API", "system health", "user management", "configuration"),
            ("Versioning Strategy", "URL versioning", "header versioning", "deprecation"),
            ("Error Responses", "error codes", "validation errors", "retry guidance"),
            ("Pagination", "cursor-based", "offset-based", "page size limits"),
            ("Filtering", "query parameters", "complex filters", "date ranges"),
            ("Sorting", "multi-field sort", "default ordering", "null handling"),
            ("CORS Configuration", "allowed origins", "preflight", "credentials"),
            ("Content Negotiation", "JSON", "CSV", "Accept headers"),
            ("Idempotency", "idempotency keys", "retry safety", "duplicate detection"),
            ("Request Validation", "schema validation", "business rules", "custom validators"),
            ("Response Caching", "ETag", "Cache-Control", "conditional requests"),
        ],
    },
    "db": {
        "count": 15,
        "title_prefix": "Database",
        "topics": [
            ("Schema Design", "normalization", "indexes", "constraints"),
            ("Migration Strategy", "zero-downtime", "rollback", "data backfill"),
            ("Connection Pooling", "PgBouncer", "pool sizing", "connection limits"),
            ("Query Optimization", "EXPLAIN plans", "index usage", "query caching"),
            ("Partitioning", "range partitioning", "hash partitioning", "partition pruning"),
            ("Replication", "streaming replication", "read replicas", "failover"),
            ("Backup Strategy", "point-in-time recovery", "WAL archiving", "restore testing"),
            ("Data Retention", "TTL policies", "archival", "purge schedules"),
            ("Multi-Tenancy", "row-level security", "tenant isolation", "shared schema"),
            ("JSON Storage", "JSONB columns", "GIN indexes", "path queries"),
            ("Full-Text Search", "tsvector", "tsquery", "ranking"),
            ("Temporal Tables", "history tracking", "as-of queries", "audit trail"),
            ("Connection Security", "SSL/TLS", "certificate rotation", "IP allowlisting"),
            ("Performance Monitoring", "pg_stat_statements", "slow query log", "auto-vacuum"),
            ("Stored Procedures", "PL/pgSQL", "triggers", "event-driven logic"),
        ],
    },
    "deploy": {
        "count": 15,
        "title_prefix": "Deployment",
        "topics": [
            ("Kubernetes Setup", "namespaces", "resource limits", "HPA"),
            ("CI/CD Pipeline", "GitHub Actions", "staging", "production rollout"),
            ("Container Registry", "image tagging", "vulnerability scanning", "retention"),
            ("Helm Charts", "values files", "chart dependencies", "upgrades"),
            ("Infrastructure as Code", "Terraform", "state management", "modules"),
            ("Blue-Green Deployment", "traffic switching", "rollback", "health checks"),
            ("Canary Releases", "traffic splitting", "metrics monitoring", "auto-rollback"),
            ("Secret Management", "Vault", "rotation", "access policies"),
            ("DNS Configuration", "Route53", "failover routing", "health checks"),
            ("SSL Certificate Management", "Let's Encrypt", "auto-renewal", "wildcard certs"),
            ("Monitoring Setup", "Grafana dashboards", "alert rules", "on-call"),
            ("Log Aggregation", "Loki", "retention policies", "query language"),
            ("Disaster Recovery", "RTO/RPO targets", "failover procedures", "testing"),
            ("Cost Optimization", "right-sizing", "spot instances", "reserved capacity"),
            ("Network Security", "VPC design", "security groups", "NAT gateways"),
        ],
    },
    "security": {
        "count": 15,
        "title_prefix": "Security",
        "topics": [
            ("Threat Model", "attack surface", "trust boundaries", "data flow"),
            ("Encryption at Rest", "AES-256", "key management", "rotation schedule"),
            ("Encryption in Transit", "TLS 1.3", "certificate pinning", "HSTS"),
            ("PII Handling", "data classification", "masking", "retention"),
            ("Audit Logging", "immutable logs", "access tracking", "compliance"),
            ("Vulnerability Management", "scanning", "patching", "SLA"),
            ("Incident Response", "playbooks", "escalation", "post-mortem"),
            ("Access Control", "least privilege", "service accounts", "rotation"),
            ("API Security", "input validation", "rate limiting", "WAF"),
            ("Supply Chain Security", "dependency scanning", "SBOM", "lockfiles"),
            ("Penetration Testing", "scope", "frequency", "remediation"),
            ("Compliance", "SOC 2", "GDPR", "data residency"),
            ("Security Training", "secure coding", "phishing awareness", "exercises"),
            ("Data Loss Prevention", "DLP rules", "egress monitoring", "classification"),
            (
                "Zero Trust Architecture",
                "identity verification",
                "micro-segmentation",
                "continuous auth",
            ),
        ],
    },
    "testing": {
        "count": 10,
        "title_prefix": "Testing",
        "topics": [
            ("Unit Testing Strategy", "pytest", "fixtures", "mocking"),
            ("Integration Testing", "test databases", "API testing", "cleanup"),
            ("End-to-End Testing", "Playwright", "test scenarios", "CI integration"),
            ("Performance Testing", "load testing", "stress testing", "benchmarks"),
            ("Security Testing", "SAST", "DAST", "dependency scanning"),
            ("Contract Testing", "Pact", "provider verification", "consumer tests"),
            ("Chaos Engineering", "fault injection", "game days", "blast radius"),
            ("Test Data Management", "factories", "fixtures", "anonymization"),
            ("Code Coverage", "coverage targets", "mutation testing", "branch coverage"),
            ("Test Automation", "CI triggers", "parallel execution", "flaky test handling"),
        ],
    },
    "decision": {
        "count": 20,
        "title_prefix": "Decision Record",
        "topics": [
            ("PostgreSQL over MongoDB", "ACID guarantees", "JSON support", "ecosystem"),
            ("Kubernetes over ECS", "portability", "ecosystem", "team expertise"),
            ("gRPC for Internal APIs", "performance", "type safety", "streaming"),
            ("Redis for Session Storage", "latency", "TTL support", "cluster mode"),
            ("Event Sourcing Adoption", "audit trail", "replay capability", "complexity"),
            ("Microservices Split", "team autonomy", "deployment independence", "overhead"),
            ("GraphQL Rejection", "complexity", "caching difficulties", "REST sufficiency"),
            ("Async Processing with Celery", "task queues", "retry logic", "monitoring"),
            ("S3 for File Storage", "durability", "cost", "presigned URLs"),
            ("Prometheus over Datadog", "cost", "self-hosted", "PromQL flexibility"),
            ("Feature Flags with LaunchDarkly", "gradual rollout", "kill switches", "targeting"),
            ("API Versioning via URL Path", "simplicity", "discoverability", "routing"),
            (
                "Connection Pool Size of 50",
                "load testing results",
                "memory constraints",
                "concurrency",
            ),
            ("JWT Token Expiry of 15 Minutes", "security", "refresh flow", "UX tradeoff"),
            ("Rate Limit of 100 RPM per User", "abuse prevention", "fair usage", "burst allowance"),
            ("Log Retention of 90 Days", "compliance", "storage cost", "incident investigation"),
            ("Password Hashing with Argon2", "security", "performance", "migration"),
            ("Two-Factor Authentication", "security posture", "user friction", "recovery"),
            ("CDN for Static Assets", "latency reduction", "cache hit ratio", "origin offload"),
            ("WebSocket for Real-Time", "bidirectional", "connection management", "scaling"),
        ],
    },
    "policy": {
        "count": 10,
        "title_prefix": "Policy",
        "topics": [
            ("Data Classification", "public", "internal", "confidential", "restricted"),
            ("Incident Severity Levels", "P0 critical", "P1 high", "P2 medium", "P3 low"),
            ("Change Management", "approval process", "rollback criteria", "communication"),
            ("On-Call Rotation", "schedule", "escalation", "handoff"),
            ("Code Review", "approval requirements", "auto-merge", "CODEOWNERS"),
            ("Dependency Updates", "automated PRs", "security patches", "major versions"),
            ("Data Retention", "30-day hot", "90-day warm", "365-day cold"),
            ("Access Provisioning", "request process", "approval chain", "periodic review"),
            ("Release Cadence", "weekly releases", "hotfix process", "feature freezes"),
            ("SLA Definitions", "99.9% uptime", "response times", "maintenance windows"),
        ],
    },
    "runbook": {
        "count": 15,
        "title_prefix": "Runbook",
        "topics": [
            ("Database Failover", "detection", "promotion", "DNS update", "verification"),
            ("High CPU Alert", "diagnosis", "scaling", "root cause"),
            ("Memory Leak Investigation", "heap dump", "profiling", "restart"),
            ("API Latency Spike", "tracing", "slow queries", "cache miss"),
            ("Disk Space Alert", "cleanup", "log rotation", "expansion"),
            ("Certificate Expiry", "renewal", "deployment", "verification"),
            ("Service Restart", "graceful shutdown", "health check", "traffic drain"),
            ("Data Recovery", "backup identification", "restore", "verification"),
            ("Security Incident", "containment", "investigation", "communication"),
            ("Deployment Rollback", "version identification", "rollback", "validation"),
            ("Queue Backlog", "consumer scaling", "dead letter review", "replay"),
            ("Network Partition", "detection", "failover", "recovery"),
            ("Third-Party Outage", "fallback", "communication", "retry"),
            ("Configuration Drift", "detection", "remediation", "prevention"),
            ("Performance Degradation", "profiling", "optimization", "capacity planning"),
        ],
    },
    "onboard": {
        "count": 10,
        "title_prefix": "Onboarding",
        "topics": [
            ("Developer Setup", "prerequisites", "repository clone", "local stack"),
            ("Architecture Overview", "service map", "data flow", "key components"),
            ("Coding Standards", "style guide", "linting", "naming conventions"),
            ("Git Workflow", "branching strategy", "PR process", "merge conventions"),
            ("Testing Guide", "running tests", "writing tests", "CI expectations"),
            ("Deployment Guide", "staging process", "production checklist", "rollback"),
            ("Monitoring Guide", "dashboards", "alerts", "on-call expectations"),
            ("Security Practices", "credential management", "code scanning", "reporting"),
            ("Communication Channels", "Slack channels", "meetings", "documentation"),
            ("Key Contacts", "team leads", "on-call", "stakeholders"),
        ],
    },
}


def generate_document(category: str, index: int, topic: tuple) -> tuple[str, str, dict]:
    """Generate a single document. Returns (filename, content, metadata)."""
    title = topic[0]
    keywords = list(topic[1:])
    safe_title = title.lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    filename = f"{category}_{index:03d}_{safe_title}.md"

    # Generate substantive content with embedded facts
    random.seed(f"{category}_{index}_{title}")

    sections = []
    sections.append(f"# {CATEGORIES[category]['title_prefix']}: {title}\n")

    # Overview section with specific facts
    fact_1 = f"The {title.lower()} component handles approximately {random.randint(100, 10000)} operations per second under normal load."
    fact_2 = f"This system was designed in Q{random.randint(1, 4)} {random.randint(2023, 2025)} and has been in production for {random.randint(1, 24)} months."
    sections.append(f"## Overview\n\n{fact_1} {fact_2}\n")

    # Detail sections with keyword-specific content
    for kw in keywords:
        detail_lines = [
            f"## {kw.title()}\n",
            f"The {kw} configuration uses a {random.choice(['conservative', 'aggressive', 'balanced', 'adaptive'])} approach.",
            f"Default setting for {kw} is {random.choice(['enabled', 'disabled', 'auto'])} with a threshold of {random.randint(1, 1000)}.",
            f"When {kw} is active, the system achieves {random.randint(50, 99)}% {random.choice(['efficiency', 'accuracy', 'throughput', 'reliability'])}.",
            f"The {kw} module was last updated on {random.randint(2024, 2026)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}.",
            "",
            "### Configuration\n",
            f"- Maximum {kw} capacity: {random.randint(10, 500)} units",
            f"- Timeout for {kw} operations: {random.randint(100, 30000)}ms",
            f"- Retry count for {kw}: {random.randint(1, 10)}",
            f"- {kw.title()} monitoring interval: {random.randint(5, 300)} seconds",
            "",
        ]
        sections.append("\n".join(detail_lines))

    # Cross-references
    other_cats = [c for c in CATEGORIES if c != category]
    ref_cat = random.choice(other_cats)
    ref_topic = random.choice(CATEGORIES[ref_cat]["topics"])
    sections.append(
        f"\n## Related\n\nSee also: {CATEGORIES[ref_cat]['title_prefix']}: {ref_topic[0]}\n"
    )

    content = "\n".join(sections)
    metadata = {
        "filename": filename,
        "category": category,
        "title": title,
        "keywords": keywords,
        "token_estimate": len(content) // 4,
    }

    return filename, content, metadata


def generate_questions(documents: list[dict]) -> list[dict]:
    """Generate 100 questions with gold answers referencing specific documents."""
    questions = []
    random.seed(42)

    # Group docs by category
    by_cat: dict[str, list[dict]] = {}
    for doc in documents:
        by_cat.setdefault(doc["category"], []).append(doc)

    q_id = 0

    # Fact lookup questions (30)
    for doc in random.sample(documents, min(30, len(documents))):
        q_id += 1
        kw = random.choice(doc["keywords"]) if doc["keywords"] else doc["title"]
        questions.append(
            {
                "id": f"q_{q_id:03d}",
                "query": f"What is the default configuration for {kw} in the {doc['title'].lower()} system?",
                "gold_answer": f"The {kw} configuration details are documented in the {doc['title']} specification.",
                "source_docs": [doc["filename"]],
                "category": "fact_lookup",
                "difficulty": "easy",
            }
        )

    # Cross-document questions (25)
    categories = list(by_cat.keys())
    for _ in range(25):
        q_id += 1
        cat1, cat2 = random.sample(categories, 2)
        doc1 = random.choice(by_cat[cat1])
        doc2 = random.choice(by_cat[cat2])
        questions.append(
            {
                "id": f"q_{q_id:03d}",
                "query": f"How does the {doc1['title'].lower()} relate to the {doc2['title'].lower()}?",
                "gold_answer": f"The relationship between {doc1['title']} and {doc2['title']} involves integration considerations.",
                "source_docs": [doc1["filename"], doc2["filename"]],
                "category": "cross_document",
                "difficulty": "medium",
            }
        )

    # Decision recall questions (15)
    decision_docs = by_cat.get("decision", [])
    for doc in random.sample(decision_docs, min(15, len(decision_docs))):
        q_id += 1
        questions.append(
            {
                "id": f"q_{q_id:03d}",
                "query": f"Why was {doc['title'].lower()} chosen? What alternatives were considered?",
                "gold_answer": f"The decision record for {doc['title']} documents the rationale and alternatives.",
                "source_docs": [doc["filename"]],
                "category": "decision_recall",
                "difficulty": "medium",
            }
        )

    # Policy questions (10)
    policy_docs = by_cat.get("policy", [])
    for doc in random.sample(policy_docs, min(10, len(policy_docs))):
        q_id += 1
        questions.append(
            {
                "id": f"q_{q_id:03d}",
                "query": f"What is the current policy for {doc['title'].lower()}?",
                "gold_answer": f"The {doc['title']} policy defines the organizational standards.",
                "source_docs": [doc["filename"]],
                "category": "policy_lookup",
                "difficulty": "easy",
            }
        )

    # Runbook questions (10)
    runbook_docs = by_cat.get("runbook", [])
    for doc in random.sample(runbook_docs, min(10, len(runbook_docs))):
        q_id += 1
        questions.append(
            {
                "id": f"q_{q_id:03d}",
                "query": f"What are the steps to handle a {doc['title'].lower()} incident?",
                "gold_answer": f"The {doc['title']} runbook provides step-by-step incident response procedures.",
                "source_docs": [doc["filename"]],
                "category": "procedural",
                "difficulty": "medium",
            }
        )

    # No-answer questions (10) — questions about topics not in the corpus
    no_answer_topics = [
        "quantum computing integration",
        "blockchain consensus mechanism",
        "AR/VR rendering pipeline",
        "satellite communication protocol",
        "biometric authentication hardware",
        "nuclear power monitoring",
        "submarine navigation system",
        "space station life support",
        "DNA sequencing pipeline",
        "autonomous vehicle perception",
    ]
    for topic in no_answer_topics:
        q_id += 1
        questions.append(
            {
                "id": f"q_{q_id:03d}",
                "query": f"What is the system's approach to {topic}?",
                "gold_answer": "No information about this topic exists in the documentation.",
                "source_docs": [],
                "category": "no_answer",
                "difficulty": "easy",
            }
        )

    return questions


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CLARKE evaluation corpus")
    parser.add_argument("--output", default="evals/corpus", help="Output directory")
    args = parser.parse_args()

    output = Path(args.output)
    docs_dir = output / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    all_docs = []
    total_tokens = 0

    print("Generating evaluation corpus...")

    for category, config in CATEGORIES.items():
        topics = config["topics"]
        for i, topic in enumerate(topics[: config["count"]]):
            filename, content, metadata = generate_document(category, i + 1, topic)

            # Write document
            (docs_dir / filename).write_text(content)
            all_docs.append(metadata)
            total_tokens += metadata["token_estimate"]

    # Generate questions
    questions = generate_questions(all_docs)

    # Write questions
    questions_path = output / "questions.json"
    with open(questions_path, "w") as f:
        json.dump({"questions": questions}, f, indent=2)

    # Write manifest
    manifest = {
        "document_count": len(all_docs),
        "total_token_estimate": total_tokens,
        "question_count": len(questions),
        "categories": {cat: config["count"] for cat, config in CATEGORIES.items()},
        "documents": all_docs,
    }
    manifest_path = output / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {len(all_docs)} documents ({total_tokens:,} estimated tokens)")
    print(f"Generated {len(questions)} questions")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()
