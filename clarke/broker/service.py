"""Broker service — orchestrates the LangGraph workflow and persistence."""

from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.schemas.query import BrokerQueryRequest, BrokerQueryResponse
from clarke.graph.nodes.persist_episode import _persist
from clarke.graph.registry import get_compiled_workflow
from clarke.memory.episodic import store_episodic_memory
from clarke.storage.postgres.repositories.request_repo import get_request_by_id
from clarke.telemetry.logging import get_logger
from clarke.utils.ids import generate_request_id
from clarke.utils.time import ms_since, utc_now

logger = get_logger(__name__)


class BrokerService:
    async def handle_query(
        self,
        request: BrokerQueryRequest,
        session: AsyncSession,
    ) -> BrokerQueryResponse:
        start = utc_now()
        request_id = request.request_id or generate_request_id()

        # Idempotency: if this request_id was already processed, return the prior result
        existing = await get_request_by_id(session, request_id)
        if existing and existing.status == "completed":
            logger.info("idempotent_replay", request_id=request_id)
            return BrokerQueryResponse(
                request_id=request_id,
                answer=existing.answer_summary or "Previously processed.",
                degraded_mode=existing.degraded_mode,
                prompt_version_id=existing.prompt_version_id,
                context_template_version_id=existing.context_template_version_id,
            )

        logger.info(
            "broker_query_start",
            request_id=request_id,
            tenant_id=request.tenant_id,
        )

        initial_state = {
            "request_id": request_id,
            "tenant_id": request.tenant_id,
            "project_id": request.project_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "message": request.message,
            "agent_id": request.agent_id,
            "agent_depth": 0,
            "degraded_mode": False,
            "agent_session_context": None,
        }

        # Phase 7: inject pre-built session context if available
        if request.session_id:
            try:
                from clarke.settings import get_settings

                settings = get_settings()
                if settings.agent_context.session_context_enabled:
                    from clarke.storage.postgres.repositories.agent_profile_repo import (
                        get_session_context_by_session,
                    )

                    ctx_record = await get_session_context_by_session(session, request.session_id)
                    if ctx_record and ctx_record.context_snapshot:
                        initial_state["agent_session_context"] = ctx_record.context_snapshot
                        logger.info(
                            "session_context_injected",
                            request_id=request_id,
                            session_id=request.session_id,
                        )
            except Exception:
                logger.warning(
                    "session_context_injection_failed",
                    request_id=request_id,
                    exc_info=True,
                )

        workflow = get_compiled_workflow()
        result = await workflow.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": request_id}},
        )

        latency = ms_since(start)
        result["latency_ms"] = latency

        # Persist request log and episode
        try:
            await _persist(result, session)
        except Exception:
            logger.exception("persist_episode_failed", request_id=request_id)

        answer = result.get("answer") or result.get("error") or "No answer generated."

        # Store episodic memory (best-effort, non-blocking)
        if answer and not result.get("error"):
            try:
                # Extract agent_profile_id from session context if available
                agent_profile_id = None
                agent_ctx = result.get("agent_session_context")
                if agent_ctx:
                    agent_profile_id = agent_ctx.get("session_context_id")
                    # The session_context_id links to AgentSessionContext which has agent_profile_id

                await store_episodic_memory(
                    tenant_id=request.tenant_id,
                    project_id=request.project_id,
                    user_id=request.user_id,
                    session_id=request.session_id,
                    request_id=request_id,
                    message=request.message,
                    answer=answer,
                    query_features=result.get("query_features"),
                    agent_profile_id=agent_profile_id,
                )
            except Exception:
                logger.warning("episodic_memory_failed", request_id=request_id, exc_info=True)

        # Build response with optional subagent handle
        subagent_handle = result.get("subagent_handle")
        return BrokerQueryResponse(
            request_id=request_id,
            answer=answer,
            degraded_mode=result.get("degraded_mode", False),
            prompt_version_id=result.get("prompt_version_id"),
            context_template_version_id=result.get("context_template_version_id"),
            subagent_handle=subagent_handle,
            subagent_query_url=f"/query?agent_id={subagent_handle}" if subagent_handle else None,
        )
