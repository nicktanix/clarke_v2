"""SessionContextBuilder — dynamically compose agent session context from CLARKE."""

import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.schemas.retrieval import ContextBudget
from clarke.api.schemas.session_context import (
    AgentIdentity,
    BuildSessionContextRequest,
    SessionConstraints,
    SessionContextPack,
    SkillEntry,
)
from clarke.llm.token_counting import count_tokens
from clarke.retrieval.composer.budgeter import allocate_session_budget
from clarke.settings import get_settings
from clarke.storage.postgres.models import AgentProfile
from clarke.storage.postgres.repositories.agent_profile_repo import (
    create_session_context,
    get_agent_profile,
    get_agent_profile_by_slug,
)
from clarke.telemetry.logging import get_logger
from clarke.utils.time import ms_since, utc_now

logger = get_logger(__name__)


class SessionContextBuilder:
    """Build a complete session context pack for an agent."""

    async def build(
        self,
        request: BuildSessionContextRequest,
        session: AsyncSession,
    ) -> SessionContextPack:
        start = utc_now()

        # 1. Load agent profile
        profile = await self._load_profile(request, session)

        # 2. Check dependency health
        degraded_mode, qdrant_available = await self._check_health()

        # 3. Determine budget
        settings = get_settings()
        budget_tokens = (
            request.budget_tokens_override
            or profile.budget_tokens
            or settings.agent_context.default_session_budget_tokens
        )
        section_budget = allocate_session_budget(budget_tokens)

        # 4. Concurrent fetch from all sources
        capabilities = profile.capabilities or []
        query_text = " ".join(capabilities)
        if request.task_context:
            query_text = f"{query_text} {request.task_context}"

        policies, decisions, skills, evidence, recent_state = await self._fetch_all(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            capabilities=capabilities,
            query_text=query_text,
            session_id=request.session_id,
            task_context=request.task_context,
            qdrant_available=qdrant_available,
            session=session,
        )

        # 5. Build identity
        identity = AgentIdentity(
            name=profile.name,
            slug=profile.slug,
            model_id=profile.model_id,
            capabilities=capabilities,
        )

        # 6. Build directives
        directives = profile.behavioral_directives or []

        # 7. System prompt
        system_prompt = profile.system_prompt_override or self._default_system_prompt()

        # 8. Rank and budget-cap skills (with learned effectiveness)
        skills = await self._rank_and_cap_skills(
            skills, section_budget["skills"], profile.id, session
        )

        # 9. Budget-cap evidence
        evidence = self._budget_cap_items(evidence, section_budget["evidence"])

        # 10. Budget-cap decisions
        decisions = self._budget_cap_items(decisions, section_budget["decisions"])

        # 11. Budget-cap policies
        policies = self._budget_cap_strings(policies, section_budget["policies"])

        # 12. Budget-cap recent state
        recent_state = self._budget_cap_items(recent_state, section_budget["recent_state"])

        # 13. Build constraints
        constraints = SessionConstraints(
            budget_tokens=budget_tokens,
            allowed_sources=profile.allowed_sources,
            tool_access=profile.tool_access or [],
        )

        # 14. Total token count
        total_tokens = self._estimate_total_tokens(
            identity,
            directives,
            system_prompt,
            policies,
            skills,
            evidence,
            decisions,
            recent_state,
        )

        # 15. Build pack
        session_context_id = str(uuid4())
        pack = SessionContextPack(
            identity=identity,
            directives=directives,
            system_prompt=system_prompt,
            policies=policies,
            skills=skills,
            evidence=evidence,
            decisions=decisions,
            recent_state=recent_state,
            constraints=constraints,
            budget=ContextBudget(input_tokens=total_tokens, actual_tokenizer="estimated"),
            session_context_id=session_context_id,
            degraded_mode=degraded_mode,
        )

        # 16. Persist audit record
        latency = ms_since(start)
        try:
            await create_session_context(
                session,
                {
                    "id": session_context_id,
                    "tenant_id": request.tenant_id,
                    "agent_profile_id": profile.id,
                    "session_id": request.session_id,
                    "context_snapshot": pack.model_dump(),
                    "skills_included": [s.skill_name for s in skills],
                    "policies_included": policies,
                    "token_count": total_tokens,
                    "degraded_mode": degraded_mode,
                    "build_latency_ms": latency,
                },
            )
            await session.commit()
        except Exception:
            logger.warning("session_context_persist_failed", exc_info=True)

        logger.info(
            "session_context_built",
            agent_slug=profile.slug,
            token_count=total_tokens,
            skill_count=len(skills),
            degraded_mode=degraded_mode,
            latency_ms=latency,
        )

        return pack

    async def _load_profile(
        self,
        request: BuildSessionContextRequest,
        session: AsyncSession,
    ) -> AgentProfile:
        profile = None
        if request.agent_profile_id:
            profile = await get_agent_profile(session, request.agent_profile_id)
        elif request.agent_slug:
            profile = await get_agent_profile_by_slug(
                session, request.tenant_id, request.agent_slug
            )

        if not profile:
            raise ValueError("Agent profile not found")
        if profile.status == "archived":
            raise ValueError("Agent profile is archived")

        return profile

    async def _check_health(self) -> tuple[bool, bool]:
        """Return (degraded_mode, qdrant_available)."""
        try:
            from clarke.broker.degraded_mode import check_dependency_health

            mode, _health_details = await check_dependency_health()
            # mode is a DegradedMode enum: FULL, REDUCED, CANONICAL_ONLY
            mode_str = mode.value if hasattr(mode, "value") else str(mode)
            qdrant_ok = mode_str in ("full", "reduced")
            return mode_str != "full", qdrant_ok
        except Exception:
            logger.warning("health_check_failed_in_session_builder", exc_info=True)
            return True, False

    async def _fetch_all(
        self,
        tenant_id: str,
        project_id: str,
        capabilities: list[str],
        query_text: str,
        session_id: str | None,
        task_context: str | None,
        qdrant_available: bool,
        session: AsyncSession,
    ) -> tuple[list[str], list[dict], list[SkillEntry], list[dict], list[dict]]:
        """Fetch all context sources concurrently."""
        results = await asyncio.gather(
            self._fetch_policies(tenant_id),
            self._fetch_decisions(tenant_id, project_id, capabilities),
            self._fetch_skills(tenant_id, project_id, capabilities, query_text, qdrant_available),
            self._fetch_domain_docs(tenant_id, project_id, query_text, qdrant_available)
            if task_context
            else _empty_list(),
            self._fetch_session_history(tenant_id, project_id, session_id, qdrant_available)
            if session_id
            else _empty_list(),
            return_exceptions=True,
        )

        policies = results[0] if isinstance(results[0], list) else []
        decisions = results[1] if isinstance(results[1], list) else []
        skills = results[2] if isinstance(results[2], list) else []
        evidence = results[3] if isinstance(results[3], list) else []
        recent_state = results[4] if isinstance(results[4], list) else []

        return policies, decisions, skills, evidence, recent_state

    async def _fetch_policies(self, tenant_id: str) -> list[str]:
        try:
            from clarke.memory.policy import PolicyService
            from clarke.storage.postgres.database import get_db_session

            service = PolicyService()
            async for db_session in get_db_session():
                return await service.get_active(db_session, tenant_id)
        except Exception:
            logger.warning("session_context_policy_fetch_failed", exc_info=True)
        return []

    async def _fetch_decisions(
        self, tenant_id: str, project_id: str, capabilities: list[str]
    ) -> list[dict]:
        try:
            from clarke.memory.decisions import DecisionService
            from clarke.storage.postgres.database import get_db_session

            if not capabilities:
                return []
            service = DecisionService()
            async for db_session in get_db_session():
                return await service.get_relevant_decisions(
                    db_session, tenant_id, project_id, capabilities
                )
        except Exception:
            logger.warning("session_context_decision_fetch_failed", exc_info=True)
        return []

    async def _fetch_skills(
        self,
        tenant_id: str,
        project_id: str,
        capabilities: list[str],
        query_text: str,
        qdrant_available: bool,
    ) -> list[SkillEntry]:
        if not qdrant_available or not query_text.strip():
            return []

        try:
            from clarke.ingestion.embeddings import embed_single
            from clarke.retrieval.qdrant.client import get_qdrant_store
            from clarke.retrieval.qdrant.filters import build_skill_search_filter
            from clarke.settings import get_settings

            settings = get_settings()
            store = get_qdrant_store()
            query_embedding = await embed_single(
                query_text,
                model=settings.embedding.embedding_model,
                dimensions=settings.embedding.embedding_dimensions,
            )

            skill_filter = build_skill_search_filter(tenant_id, project_id, capabilities or None)
            results = await store.client.query_points(
                collection_name=store.collection_name,
                query=query_embedding,
                query_filter=skill_filter,
                limit=settings.agent_context.max_skills_per_session,
                with_payload=True,
            )

            skills: list[SkillEntry] = []
            for point in results.points:
                payload = point.payload or {}
                skills.append(
                    SkillEntry(
                        skill_name=payload.get("skill_name", "unknown"),
                        content=payload.get("content", ""),
                        trigger_conditions=payload.get("trigger_conditions", []),
                        priority=payload.get("priority", 1),
                        score=point.score or 0.0,
                    )
                )
            return skills
        except Exception:
            logger.warning("session_context_skill_fetch_failed", exc_info=True)
        return []

    async def _fetch_domain_docs(
        self,
        tenant_id: str,
        project_id: str,
        query_text: str,
        qdrant_available: bool,
    ) -> list[dict]:
        if not qdrant_available:
            return []

        try:
            from clarke.ingestion.embeddings import embed_single
            from clarke.retrieval.qdrant.client import get_qdrant_store
            from clarke.retrieval.qdrant.search import semantic_search
            from clarke.settings import get_settings

            settings = get_settings()
            store = get_qdrant_store()
            query_embedding = await embed_single(
                query_text,
                model=settings.embedding.embedding_model,
                dimensions=settings.embedding.embedding_dimensions,
            )

            items = await semantic_search(
                store,
                query_embedding,
                tenant_id,
                project_id,
                top_k=10,
                source_type="docs",
                hybrid=True,
                query_text=query_text,
            )
            return [item.model_dump() for item in items]
        except Exception:
            logger.warning("session_context_docs_fetch_failed", exc_info=True)
        return []

    async def _fetch_session_history(
        self,
        tenant_id: str,
        project_id: str,
        session_id: str | None,
        qdrant_available: bool,
    ) -> list[dict]:
        if not qdrant_available or not session_id:
            return []

        try:
            from clarke.ingestion.embeddings import embed_single
            from clarke.retrieval.qdrant.client import get_qdrant_store
            from clarke.retrieval.qdrant.search import semantic_search
            from clarke.settings import get_settings

            settings = get_settings()
            store = get_qdrant_store()
            query_embedding = await embed_single(
                f"session history {session_id}",
                model=settings.embedding.embedding_model,
                dimensions=settings.embedding.embedding_dimensions,
            )

            items = await semantic_search(
                store,
                query_embedding,
                tenant_id,
                project_id,
                top_k=5,
                source_type="memory",
            )
            return [item.model_dump() for item in items]
        except Exception:
            logger.warning("session_context_history_fetch_failed", exc_info=True)
        return []

    async def _rank_and_cap_skills(
        self,
        skills: list[SkillEntry],
        max_tokens: int,
        agent_profile_id: str,
        session: AsyncSession,
    ) -> list[SkillEntry]:
        """Sort skills by priority, blended score+effectiveness, cap by token budget."""
        settings = get_settings()
        skills = [s for s in skills if s.priority <= settings.agent_context.skill_priority_cutoff]

        # Load learned effectiveness scores
        effectiveness_map: dict[str, float] = {}
        if settings.self_improvement.self_improvement_enabled:
            try:
                from clarke.storage.postgres.repositories.skill_effectiveness_repo import (
                    get_all_for_agent,
                )

                records = await get_all_for_agent(session, agent_profile_id)
                effectiveness_map = {r.skill_name: r.effectiveness for r in records}
            except Exception:
                logger.debug("skill_effectiveness_load_skipped", exc_info=True)

        # Apply effectiveness to each skill
        sw = settings.self_improvement.skill_semantic_weight
        ew = settings.self_improvement.skill_effectiveness_weight
        for skill in skills:
            skill.effectiveness = effectiveness_map.get(skill.skill_name, 0.5)

        # Sort by priority (ASC), then blended score (DESC)
        skills.sort(key=lambda s: (s.priority, -(s.score * sw + s.effectiveness * ew)))

        selected: list[SkillEntry] = []
        used = 0
        for skill in skills:
            tokens = count_tokens(skill.content)
            if used + tokens > max_tokens:
                break
            selected.append(skill)
            used += tokens
        return selected

    def _budget_cap_items(self, items: list[dict], max_tokens: int) -> list[dict]:
        """Greedily select items within token budget."""
        selected: list[dict] = []
        used = 0
        for item in items:
            text = item.get("summary", item.get("content", str(item)))
            tokens = count_tokens(text)
            if used + tokens > max_tokens:
                break
            selected.append(item)
            used += tokens
        return selected

    def _budget_cap_strings(self, items: list[str], max_tokens: int) -> list[str]:
        """Greedily select string items within token budget."""
        selected: list[str] = []
        used = 0
        for item in items:
            tokens = count_tokens(item)
            if used + tokens > max_tokens:
                break
            selected.append(item)
            used += tokens
        return selected

    def _estimate_total_tokens(
        self,
        identity: AgentIdentity,
        directives: list[str],
        system_prompt: str,
        policies: list[str],
        skills: list[SkillEntry],
        evidence: list[dict],
        decisions: list[dict],
        recent_state: list[dict],
    ) -> int:
        total = count_tokens(system_prompt)
        total += count_tokens(identity.model_dump_json())
        for d in directives:
            total += count_tokens(d)
        for p in policies:
            total += count_tokens(p)
        for s in skills:
            total += count_tokens(s.content)
        for e in evidence:
            total += count_tokens(e.get("summary", ""))
        for d in decisions:
            total += count_tokens(d.get("title", "") + " " + d.get("rationale", ""))
        for r in recent_state:
            total += count_tokens(r.get("summary", ""))
        return total

    def _default_system_prompt(self) -> str:
        from clarke.llm.prompts import CONSTITUTIONAL_PROMPT_V1

        return CONSTITUTIONAL_PROMPT_V1


async def _empty_list() -> list:
    return []


def render_session_context_markdown(pack: SessionContextPack) -> str:
    """Render a SessionContextPack as markdown for direct injection.

    This output is read by OpenClaw's Brain on every LLM call (via SOUL.md)
    and by Claude Code at session start. It must be self-explanatory to the
    model — trust tiers, source attribution, and learning loop guidance are
    built into the rendered output.
    """
    sections: list[str] = []

    # Identity
    sections.append(f"# Agent: {pack.identity.name}")
    if pack.identity.capabilities:
        sections.append(f"**Capabilities**: {', '.join(pack.identity.capabilities)}")
    sections.append("")
    sections.append(
        "This context was composed by CLARKE at session start. "
        "Policies and decisions are authoritative. Evidence and recent context "
        "are supporting material. Cite sources when using retrieved content."
    )
    sections.append("")

    # Directives — behavioral rules for this agent
    if pack.directives:
        sections.append("## Behavioral Directives")
        sections.append("*Follow these rules for all interactions.*")
        for d in pack.directives:
            sections.append(f"- {d}")
        sections.append("")

    # Policies — highest trust, organizational rules
    if pack.policies:
        sections.append("## Policies (trust: highest)")
        sections.append("*Canonical organizational rules. Follow unconditionally.*")
        for p in pack.policies:
            sections.append(f"- {p}")
        sections.append("")

    # Decisions — high trust, recorded choices with rationale
    if pack.decisions:
        sections.append("## Decisions (trust: high)")
        sections.append("*Recorded architectural and process decisions. Reference when relevant.*")
        for dec in pack.decisions:
            title = dec.get("title", "Untitled")
            rationale = dec.get("rationale", "")
            sections.append(f"- **{title}**: {rationale}")
        sections.append("")

    # Skills — capabilities this agent has access to
    if pack.skills:
        sections.append("## Skills")
        for skill in pack.skills:
            sections.append(f"### {skill.skill_name}")
            sections.append(skill.content)
            sections.append("")

    # Domain Knowledge — medium trust, ingested documents
    if pack.evidence:
        sections.append("## Domain Knowledge (trust: medium)")
        sections.append("*Retrieved from ingested documents. Cite when using.*")
        for ev in pack.evidence:
            source = ev.get("source", "unknown")
            summary = ev.get("summary", "")
            sections.append(f"[{source}] {summary}")
        sections.append("")

    # Recent Context — low trust, past interactions
    if pack.recent_state:
        sections.append("## Recent Interactions (trust: low)")
        sections.append("*Past conversations. Useful for continuity, not authority.*")
        for item in pack.recent_state:
            sections.append(f"- {item.get('summary', str(item))}")
        sections.append("")

    # Constraints
    sections.append("## Constraints")
    sections.append(f"- Token budget: {pack.constraints.budget_tokens}")
    if pack.constraints.allowed_sources:
        sections.append(f"- Allowed sources: {', '.join(pack.constraints.allowed_sources)}")
    if pack.constraints.tool_access:
        sections.append(f"- Tool access: {', '.join(pack.constraints.tool_access)}")
    sections.append("")

    # Learning loop guidance
    sections.append("## Feedback")
    sections.append(
        "Every interaction builds CLARKE's memory. If the user corrects you, "
        "that correction is stored and may become a behavioral directive over time. "
        "When you're unsure about a project-specific convention, say so — "
        "a correction now prevents the same mistake across all future sessions."
    )

    return "\n".join(sections)
