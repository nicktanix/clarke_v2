"""Create sub-agent instance, build inherited context + skill context, record lineage."""

from clarke.agents.spawn import create_agent
from clarke.broker.lineage import record_lineage
from clarke.graph.state import BrokerState
from clarke.memory.inheritance import build_inherited_context
from clarke.telemetry.logging import get_logger

logger = get_logger(__name__)


async def create_subagent_instance(state: BrokerState) -> dict:
    """Create AgentInstance, build inherited context, fetch skills for capabilities, record lineage."""
    if not state.get("subagent_spawn_approved"):
        return {}

    spawn_req = state.get("spawn_request") or {}

    try:
        from clarke.storage.postgres.database import get_db_session

        async for session in get_db_session():
            agent_id, handle = await create_agent(
                session=session,
                spawn_request=spawn_req,
                tenant_id=state["tenant_id"],
                project_id=state["project_id"],
                parent_agent_id=state.get("agent_id"),
                root_agent_id=state.get("root_agent_id") or state.get("agent_id"),
                parent_request_id=state["request_id"],
                current_depth=state.get("agent_depth", 0),
            )

            # Build inherited context (policies, evidence from parent)
            handoff_mode = spawn_req.get("memory_scope_mode", "hybrid")
            handoff_evidence = spawn_req.get("handoff_evidence", [])
            inherited = build_inherited_context(
                parent_context_pack=state.get("context_pack") or {},
                handoff_mode=handoff_mode,
                handoff_evidence=handoff_evidence,
            )

            # Build session context with skills matched to requested capabilities
            capabilities = spawn_req.get("capabilities", [])
            session_context = None
            if capabilities:
                try:
                    from clarke.agents.session_context import SessionContextBuilder
                    from clarke.api.schemas.session_context import BuildSessionContextRequest

                    builder = SessionContextBuilder()
                    ctx_request = BuildSessionContextRequest(
                        tenant_id=state["tenant_id"],
                        project_id=state["project_id"],
                        agent_slug=None,
                        agent_profile_id=None,
                        task_context=spawn_req.get("task", ""),
                        capabilities_override=capabilities,
                    )
                    session_context = await builder.build_for_capabilities(
                        ctx_request, capabilities, session
                    )
                except Exception:
                    logger.warning(
                        "subagent_skill_context_failed",
                        agent_id=agent_id,
                        exc_info=True,
                    )

            # Record lineage
            if state.get("agent_id"):
                await record_lineage(
                    session=session,
                    tenant_id=state["tenant_id"],
                    parent_agent_id=state["agent_id"],
                    child_agent_id=agent_id,
                    handoff_type=handoff_mode,
                    linked_item_ids=handoff_evidence,
                )

            await session.commit()
            break

        result = {
            "subagent_handle": handle.subagent_handle,
            "subagent_instance_id": agent_id,
        }
        if session_context:
            result["subagent_context"] = session_context

        return result

    except Exception:
        logger.exception("create_subagent_failed")
        return {"subagent_spawn_approved": False}
