"""Call the LLM with constitutional prompt + context pack + user message."""

from clarke.api.schemas.retrieval import ContextPack
from clarke.graph.state import BrokerState
from clarke.llm.gateway import LLMGateway
from clarke.llm.prompts import CONSTITUTIONAL_PROMPT_V1, build_context_template
from clarke.settings import get_settings


async def call_answer_model(state: BrokerState) -> dict:
    """Call the answer model with composed context.

    When agent_session_context is present (Phase 7), uses the agent's
    custom system prompt and injects skill/directive context alongside
    the retrieved context pack.
    """
    settings = get_settings()
    gateway = LLMGateway(settings.llm)

    context_pack_data = state.get("context_pack") or {}
    context_pack = ContextPack(**context_pack_data)
    context_section = build_context_template(context_pack)

    # Phase 7: use agent session context if available
    agent_ctx = state.get("agent_session_context")
    if agent_ctx:
        system_prompt = agent_ctx.get("system_prompt", CONSTITUTIONAL_PROMPT_V1)
        agent_context_parts = []
        if agent_ctx.get("directives"):
            agent_context_parts.append("## Agent Directives")
            for d in agent_ctx["directives"]:
                agent_context_parts.append(f"- {d}")
        if agent_ctx.get("skills"):
            agent_context_parts.append("\n## Agent Skills")
            for skill in agent_ctx["skills"]:
                name = skill.get("skill_name", "unknown")
                content = skill.get("content", "")
                agent_context_parts.append(f"### {name}\n{content}")
        agent_section = "\n".join(agent_context_parts) if agent_context_parts else ""

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if agent_section:
            messages.append({"role": "system", "content": agent_section})
        messages.append({"role": "system", "content": f"## Retrieved Context\n{context_section}"})
        messages.append({"role": "user", "content": state["message"]})
    else:
        messages = [
            {"role": "system", "content": CONSTITUTIONAL_PROMPT_V1},
            {"role": "system", "content": f"## Retrieved Context\n{context_section}"},
            {"role": "user", "content": state["message"]},
        ]

    response = await gateway.call(messages)

    return {
        "model_response": response.content,
        "answer": response.content,
    }
