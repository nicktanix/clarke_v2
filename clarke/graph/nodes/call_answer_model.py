"""Call the LLM with constitutional prompt + context pack + user message."""

from clarke.api.schemas.retrieval import ContextPack
from clarke.graph.state import BrokerState
from clarke.llm.gateway import LLMGateway
from clarke.llm.prompts import CONSTITUTIONAL_PROMPT_V1, build_context_template
from clarke.settings import get_settings


async def call_answer_model(state: BrokerState) -> dict:
    """Call the answer model with composed context."""
    settings = get_settings()
    gateway = LLMGateway(settings.llm)

    context_pack_data = state.get("context_pack") or {}
    context_pack = ContextPack(**context_pack_data)
    context_section = build_context_template(context_pack)

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
