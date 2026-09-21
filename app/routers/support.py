from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user
from ..database import get_async_session
from ..schemas.support import SupportTicketCreate, SupportTicketRead

router = APIRouter(prefix="/api/v1/support", tags=["support"])

# In-memory ticket store for support requests to keep the API functional without
# changing the rest of the backend or introducing a database migration.
TICKETS: list[dict] = []


@router.get("/tickets", response_model=list[SupportTicketRead])
async def list_support_tickets(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    del session
    del user
    return [
        {
            "id": ticket["id"],
            "subject": ticket["subject"],
            "date": ticket["date"],
            "status": ticket["status"],
        }
        for ticket in TICKETS
    ]


@router.post("/tickets", response_model=SupportTicketRead, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    payload: SupportTicketCreate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    del session
    del user

    if not payload.subject.strip() or not payload.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject and message are required")

    ticket_id = f"TKT-{len(TICKETS) + 1001}"
    ticket = {
        "id": ticket_id,
        "subject": payload.subject.strip(),
        "date": datetime.utcnow().strftime("%b %d, %Y"),
        "status": "Open",
    }
    TICKETS.insert(0, ticket)
    return ticket
