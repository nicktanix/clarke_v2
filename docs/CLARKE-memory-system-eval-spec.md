# CLARKE Memory System Evaluation Specification
## Cognitive Learning Augmentation Retrieval Knowledge Engine

This document defines how to test, compare, and continuously evaluate CLARKE as a brokered context and memory system.

It is intentionally broader than standard chatbot evaluation. CLARKE must be evaluated as a:

- retrieval system
- context composition system
- trust-ordering system
- escalation system
- bounded hierarchical agent system
- learning and optimization system

The goal is not just “did the answer sound good?” The goal is:

**Did CLARKE retrieve the right information, compose the smallest sufficient grounded context, respect policy and isolation boundaries, escalate only when needed, and improve over time?**

---

## 1. Evaluation Goals

CLARKE evaluation should answer these questions:

1. **Retrieval quality**  
   Did the system fetch the right evidence?

2. **Context composition quality**  
   Did the broker assemble the right context pack?

3. **Answer quality**  
   Did the model produce a grounded, correct, policy-compliant answer?

4. **Escalation quality**  
   Did the system use `CONTEXT_REQUEST` or `SUBAGENT_SPAWN` only when appropriate?

5. **Efficiency**  
   Did the system achieve good answers with acceptable latency and token cost?

6. **Safety and isolation**  
   Did the system maintain tenant boundaries, redaction rules, and trust precedence?

7. **Learning-loop quality**  
   Is the system getting better over time?

---

## 2. Evaluation Layers

CLARKE should be evaluated at five layers.

### 2.1 Retrieval layer
Measures whether the correct leaves, anchors, policies, and decisions were retrieved.

Key questions:
- Did relevant evidence appear in the candidate set?
- Did forbidden evidence stay out?
- Did trust-ordered sources rank correctly?
- Did graph anchors improve or degrade retrieval?

### 2.2 Context composition layer
Measures whether the broker assembled the best prompt-ready context pack.

Key questions:
- Was the injected context minimal but sufficient?
- Were duplicates collapsed?
- Were anchors shown before evidence?
- Did the final context reflect trust order?

### 2.3 Answer layer
Measures the quality of the final answer.

Key questions:
- Was the answer grounded in the context pack?
- Was it correct?
- Did it comply with policy?
- Did it avoid hallucinated constraints?

### 2.4 Escalation layer
Measures whether additional context or sub-agents were used appropriately.

Key questions:
- Was a second pass justified?
- Was a sub-agent actually needed?
- Would better retrieval have avoided escalation?

### 2.5 Learning layer
Measures whether planner changes, weight tuning, and proto-class routing improve results over time.

Key questions:
- Are useful-context ratios improving?
- Is answer groundedness improving?
- Is wasted context decreasing?
- Are exploration strategies discovering better retrieval plans?

---

## 3. Evaluation Modes

CLARKE should be tested in three complementary modes.

### 3.1 Offline benchmark evaluation
A fixed labeled dataset of representative tasks.

Purpose:
- regression testing
- controlled system comparison
- launch gating
- feature isolation testing

### 3.2 Replay evaluation
Historical real episodes replayed against alternate planners, prompts, retrieval blends, and escalation policies.

Purpose:
- compare candidate changes against real traffic
- test new strategies without user exposure
- estimate token/cost impact
- estimate escalation necessity

### 3.3 Online shadow / A-B evaluation
Real traffic is evaluated with shadow execution or controlled experiments.

Purpose:
- validate that offline gains transfer to real traffic
- catch real-world drift
- compare conservative and exploratory planners
- monitor cost/latency tradeoffs

---

## 4. Baselines to Compare Against

Every CLARKE evaluation should compare against baseline systems.

### Baseline 1: No memory
- raw user query
- constitutional prompt only
- no retrieval

Purpose:
- determine whether memory helps at all

### Baseline 2: Naive vector RAG
- top-k semantic retrieval only
- no graph
- no trust ordering
- no learning loop

Purpose:
- compare against the simplest memory baseline

### Baseline 3: Hybrid RAG
- semantic + lexical/BM25 retrieval
- reranking
- no graph
- no adaptive planner

Purpose:
- isolate the value of graph and learned routing

### Baseline 4: Hybrid + graph
- hybrid retrieval
- graph anchors
- no learning loop
- no sub-agents

Purpose:
- isolate the value of learned planner and escalation

### Baseline 5: Hybrid + graph + context escalation
- retrieval plus `CONTEXT_REQUEST`
- no sub-agent spawning

Purpose:
- isolate the incremental value of sub-agents

### Full CLARKE
- hybrid retrieval
- graph retrieval
- context composition
- trust ordering
- learning loop
- optional `CONTEXT_REQUEST`
- optional `SUBAGENT_SPAWN`

Purpose:
- measure the full system

---

## 5. Benchmark Dataset Design

A benchmark example must include more than just a query and answer.

Each example should include:

- `example_id`
- `tenant_id`
- `project_id`
- `query`
- `task_family`
- `gold_required_evidence`
- `gold_optional_evidence`
- `gold_forbidden_evidence`
- `expected_trust_precedence`
- `expected_answer`
- `acceptable_answers`
- `escalation_expectation`
- `subagent_expectation`
- `notes`

### 5.1 Evidence labeling
Evidence labels should use three categories:

- **Required evidence**  
  Must be present for a correct grounded answer.

- **Optional evidence**  
  Helpful but not strictly required.

- **Forbidden evidence**  
  Must not be used, due to irrelevance, staleness, wrong tenant, or policy conflict.

### 5.2 Escalation labels
For each benchmark example, label:

- `context_request_not_needed`
- `context_request_acceptable`
- `context_request_preferred`

And separately:

- `spawn_not_needed`
- `spawn_acceptable`
- `spawn_preferred`

### 5.3 Spawn-specific labels
For examples where spawn is acceptable or preferred, include:

- expected child task
- allowed inherited memory types
- forbidden inherited memory types
- expected child result structure

---

## 6. Scenario Coverage Matrix

The benchmark corpus should cover at least the following scenario classes.

### 6.1 Fact lookup
- simple stable facts
- direct canonical memory retrieval
- should not trigger heavy graph expansion or spawn

### 6.2 Document QA
- answer depends on authoritative chunk(s)
- retrieval precision matters
- policy/decision precedence may matter

### 6.3 Decision recall
- answer depends on historical decision records
- episodic summaries may conflict with structured decisions

### 6.4 Architecture and tradeoff questions
- likely to benefit from leaf-first retrieval and convergence anchors
- may justify escalation in hard multi-hop cases

### 6.5 Recent-history recall
- recent discussion or unresolved issue is important
- recency weighting matters

### 6.6 Policy conflict resolution
- multiple sources disagree
- trust ordering must be tested explicitly

### 6.7 Insufficient-memory / no-answer cases
- no sufficient evidence exists
- system should not hallucinate missing memory

### 6.8 Degraded-mode scenarios
- Qdrant unavailable
- Neo4j unavailable
- tokenizer unavailable
- sub-agent spawning disabled

### 6.9 Multi-agent delegation
- child spawn justified
- child spawn unnecessary
- child inheritance correctness
- child result ingestion correctness

### 6.10 Security and isolation
- cross-tenant leakage attempts
- parent attempts forbidden handoff
- stale or unauthorized sub-agent handle reuse

---

## 7. Core Metrics

## 7.1 Retrieval metrics

### Recall@k
Fraction of required evidence retrieved in the top-k candidates.

### Precision@k
Fraction of retrieved top-k candidates that are truly relevant.

### MRR
Useful for tasks where one critical evidence item should rank highly.

### nDCG
Useful for weighted evidence relevance and ranking quality.

### Leaf hit rate
Whether the correct leaf evidence was retrieved.

### Anchor quality rate
Whether the selected anchor/convergence concept was useful and relevant.

### Trust precedence correctness
Whether, in conflicting cases, the highest-priority valid source won.

### Forbidden evidence rate
How often forbidden items appeared in candidate or injected sets.

### Cross-tenant leakage rate
Must be zero in production-quality evaluations.

---

## 7.2 Context composition metrics

### Injected token count
Actual token count of the final context pack.

### Useful Context Ratio
Defined as:

```text
useful_context_ratio = attributed_tokens / total_injected_tokens
```

This is one of the most important metrics in the whole system.

### Duplicate evidence ratio
Fraction of injected context that duplicates already-injected evidence.

### Irrelevant evidence ratio
Fraction of injected context that did not materially contribute to the answer.

### Anchor-before-evidence correctness
Whether anchors were rendered before evidence.

### Budget adherence rate
Whether the composer stayed inside target token budgets.

---

## 7.3 Answer metrics

### Grounded Answer Rate
Fraction of answers that are supported by injected evidence.

### Correctness
Match against gold or acceptable answer set.

### Completeness
Whether the answer covers the necessary dimensions of the question.

### Contradiction rate
Whether the answer contradicts injected canonical policy, decision records, or trusted docs.

### Hallucinated constraint rate
Whether the answer invents policy, constraints, or prior decisions that were not in the context pack.

### Policy compliance rate
Whether trust ordering and policy memory were respected.

### User acceptance / correction rate
For online experiments, whether the answer was accepted or corrected.

---

## 7.4 Escalation metrics

### Second-pass request rate
How often `CONTEXT_REQUEST` was used.

### Second-pass usefulness rate
How often the second pass materially improved outcome quality.

### Unnecessary second-pass rate
How often the second pass was not needed.

### Spawn requested rate
How often the model asked for a sub-agent.

### Spawn approved rate
How often the broker allowed the spawn.

### Spawn usefulness rate
How often the child meaningfully improved the final answer.

### Spawn necessity rate
How often spawning was truly the right decision versus improved retrieval being enough.

### Escalation cost per successful case
Token/latency cost divided by successful escalated outcomes.

---

## 7.5 Efficiency metrics

### End-to-end latency
Total request latency.

### Stage latency
Latency for:
- query parsing
- retrieval planning
- retrieval
- reranking
- composition
- model call
- second pass
- sub-agent creation

### Total token cost
Across all model calls.

### Retrieval fanout
Number of sources hit.

### Calls per successful answer
Useful especially when comparing no-escalation vs escalation vs child-spawn paths.

---

## 7.6 Learning-loop metrics

### Improvement over time
Track trends in:
- useful context ratio
- grounded answer rate
- retrieval precision
- contradiction rate
- context waste ratio

### Exploration yield
How often exploration discovered a retrieval plan that beat the prior default.

### Proto-class routing gain
Improvement attributable to routing via learned proto-classes.

### Spawn-vs-retrieval learning gain
Whether the system is learning to avoid unnecessary spawns over time.

---

## 8. Composite Scorecard

A single composite score is useful for release comparisons, but should never replace layer-by-layer analysis.

Suggested weighting:

```text
overall_score =
  0.25 * retrieval_quality +
  0.20 * composition_quality +
  0.30 * answer_quality +
  0.10 * escalation_quality +
  0.15 * efficiency
```

Example sub-scores:

- `retrieval_quality`: normalized recall, precision, trust precedence, leakage penalty
- `composition_quality`: useful context ratio, duplicate penalty, budget adherence
- `answer_quality`: groundedness, correctness, policy compliance
- `escalation_quality`: justified context requests, justified spawns
- `efficiency`: latency and token cost

---

## 9. Gold Dataset Schema

Example benchmark item:

```json
{
  "example_id": "ex_001",
  "tenant_id": "tenant_01",
  "project_id": "project_alpha",
  "query": "Should reconnect state live in the websocket session object or separately?",
  "task_family": "architecture_tradeoff",
  "gold_required_evidence": ["dec_014", "doc_201_chunk_7"],
  "gold_optional_evidence": ["sum_884"],
  "gold_forbidden_evidence": ["tenant_other_doc_91", "stale_decision_003"],
  "expected_trust_precedence": [
    "policy",
    "decision",
    "document",
    "episodic_summary",
    "semantic_neighbor"
  ],
  "expected_answer": "Reconnect state should be separated from the live transport object.",
  "acceptable_answers": [
    "Reconnect state should not live solely in the websocket session object.",
    "A separate durable state holder is preferred over keeping reconnect state in the active socket object."
  ],
  "escalation_expectation": "context_request_acceptable",
  "subagent_expectation": "spawn_not_needed",
  "notes": "Design-oriented query that benefits from decisions and docs, but should not require spawn."
}
```

---

## 10. Replay Evaluation Methodology

Replay is one of the highest-value evaluation methods for CLARKE.

### 10.1 Replay inputs
Each replay run should include:
- historical `retrieval_episode`
- original query
- original tenant/project scope
- original context pack
- original answer
- candidate system variant

### 10.2 Replay comparisons
Replay should compare:
- old planner vs new planner
- old prompt version vs new prompt version
- with and without graph retrieval
- with and without anchor composition
- with and without `CONTEXT_REQUEST`
- with and without `SUBAGENT_SPAWN`

### 10.3 Replay outputs
For each replay:
- original overall score
- candidate overall score
- delta in useful context ratio
- delta in answer groundedness
- delta in latency
- delta in token cost
- delta in unnecessary escalation rate

### 10.4 Replay safety
Replay must:
- preserve tenant scoping
- not create live side effects
- not duplicate runtime lineage state
- use unique replay identifiers separate from production request IDs

---

## 11. Online Experimentation Guidance

### 11.1 Shadow evaluation
Run candidate planner or prompt changes in shadow mode first.

Compare:
- retrieval candidates
- injected context
- answer judgment
- latency and cost

Shadow mode should not affect user-visible outputs.

### 11.2 Controlled A/B testing
After shadow validation, use small controlled online experiments.

Suitable comparisons:
- conservative planner vs exploratory planner
- no anchors vs anchor-first composition
- spawn-enabled vs spawn-disabled
- new trust-order weighting vs prior weighting

### 11.3 Guardrails
Never experiment with:
- relaxed tenant isolation
- relaxed policy enforcement
- weaker redaction
- unbounded spawn depth
- child-to-child communication in V1

---

## 12. Multi-Agent Evaluation

Sub-agent support needs its own test plan.

### 12.1 Child spawn correctness
Test:
- spawn requested but denied correctly
- spawn requested and approved correctly
- spawn denied because retrieval was enough
- spawn denied because depth/budget/policy blocked it

### 12.2 Inheritance correctness
Test:
- child receives allowed policy memory
- child receives allowed decision memory
- child cannot see forbidden memory
- child cannot directly mutate parent memory

### 12.3 Child result correctness
Test:
- structured result shape
- evidence references valid broker-known items
- result can be explicitly consumed by parent
- result does not implicitly overwrite parent state

### 12.4 Child lifecycle correctness
Test:
- expiry
- cancellation
- timeout
- stale handle rejection
- orphan cleanup

### 12.5 Multi-agent metrics
Track:
- spawn requested vs approved
- child success rate
- child usefulness rate
- child cost
- child latency
- child necessity
- inherited memory sufficiency

---

## 13. Failure-Mode Evaluation

You should explicitly test failure scenarios.

### 13.1 Dependency failures
- Qdrant unavailable
- Neo4j unavailable
- LiteLLM provider unavailable
- tokenizer unavailable
- Phoenix unavailable
- Temporal unavailable

Expected behavior:
- safe degradation
- trace emitted
- no cross-tenant leakage
- policy precedence preserved

### 13.2 Data quality failures
- duplicate memory artifacts
- stale memory outranking fresh decisions
- semantically similar but wrong project
- low-quality graph anchor
- partial redaction failure

### 13.3 Escalation failures
- repeated unnecessary second passes
- repeated spawn requests for trivial tasks
- child chain attempts beyond max depth
- child result arrives after parent timeout

### 13.4 Security failures
- cross-tenant retrieval attempt
- parent attempts forbidden handoff
- invalid retrieved item IDs in handoff
- unauthorized agent handle reuse

---

## 14. Evaluation Workflow

Recommended evaluation process:

### Step 1
Build and maintain a labeled offline benchmark set.

### Step 2
Run deterministic scoring wherever possible:
- evidence recall
- trust precedence correctness
- token budget adherence
- leakage checks
- escalation policy compliance

### Step 3
Use model-based judges where deterministic checks are insufficient:
- subtle groundedness
- answer completeness
- anchor usefulness
- spawn necessity

### Step 4
Run replay evaluation for every planner, prompt, retrieval blend, or escalation change.

### Step 5
Track trend dashboards over time rather than only point-in-time scores.

---

## 15. Model-Based Judge Guidance

Model judges are useful, but should not be your only signal.

Use them for:
- completeness
- nuanced groundedness
- answer clarity
- anchor usefulness
- whether a child spawn was justified

Do not rely on them alone for:
- tenant isolation
- trust precedence correctness
- exact evidence recall
- token budget adherence
- lifecycle correctness

Those should be scored deterministically.

---

## 16. Minimum Launch Gates

A CLARKE release candidate should not launch unless it meets minimum gates.

Suggested minimum gates:

- cross-tenant leakage rate: **0**
- trust precedence correctness: **>= 99%**
- hallucinated constraint rate: below agreed threshold
- useful context ratio: above agreed threshold
- grounded answer rate: above agreed threshold
- unnecessary second-pass rate: below agreed threshold
- spawn necessity precision: above agreed threshold
- degraded-mode correctness: **pass**
- replay regression against current production baseline: **non-negative overall**

Use exact thresholds once you have enough benchmark data.

---

## 17. Recommended Dashboards

At minimum, build dashboards for:

- useful context ratio
- context waste ratio
- grounded answer rate
- policy/precedence correctness
- degraded mode rate
- retrieval precision by source type
- latency by stage
- spawn requested vs approved
- spawn usefulness vs direct retrieval
- proto-class stability over time

---

## 18. Evaluation Artifacts to Version-Control

Keep the following versioned:

- benchmark dataset
- scoring rubric
- judge prompts
- replay configuration
- baseline definitions
- launch gates
- evaluation notebooks or jobs
- metric definitions

Evaluation should be treated like code, not an ad hoc report.

---

## 19. Recommended Initial Benchmark Size

A practical starting point:

- **200–500 labeled examples**
- spread across all scenario classes
- at least:
  - 20 fact lookups
  - 20 doc QA
  - 20 decision recall
  - 30 architecture/tradeoff
  - 20 policy conflict
  - 20 recent-history
  - 20 insufficient-memory
  - 20 degraded-mode
  - 20 multi-agent delegation
  - 20 security/isolation cases

Grow the set over time from replay and production incidents.

---

## 20. One-Line Evaluation Philosophy

CLARKE should not be judged only by whether the final answer sounds good.

It should be judged by whether it:

**retrieved the right evidence, composed the smallest sufficient grounded context, respected trust order and tenant boundaries, escalated only when needed, and delivered the answer efficiently.**
