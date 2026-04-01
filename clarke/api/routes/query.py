"""Query endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from clarke.api.deps import get_broker_service, get_session
from clarke.api.schemas.query import BrokerQueryRequest, BrokerQueryResponse
from clarke.broker.service import BrokerService

router = APIRouter(tags=["query"])


@router.post("/query", response_model=BrokerQueryResponse)
async def query(
    request: BrokerQueryRequest,
    session: AsyncSession = Depends(get_session),
    broker: BrokerService = Depends(get_broker_service),
) -> BrokerQueryResponse:
    return await broker.handle_query(request, session)
