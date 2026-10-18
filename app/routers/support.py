"""Support ticket endpoints.

Tickets are held in a module-level list, not in the database. That was a
deliberate shortcut to avoid a migration: tickets vanish on restart and are
shared across all users, so listing is not yet scoped to the caller. Treat this
as a placeholder to be replaced with a real table.
"""

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
    """All tickets, newest first. Not filtered by owner (see module docstring)."""
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
    """Open a support ticket.

    Only the subject is stored; the message body is accepted and validated but
    discarded, so there is no way to read back what the user submitted.
    """
    del session
    del user

    # Whitespace-only input is rejected even though the schema accepts a string.
    if not payload.subject.strip() or not payload.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject and message are required")

    # Sequential ids derived from list length, so ids are reused after a restart.
    ticket_id = f"TKT-{len(TICKETS) + 1001}"
    ticket = {
        "id": ticket_id,
        "subject": payload.subject.strip(),
        "date": datetime.utcnow().strftime("%b %d, %Y"),
        "status": "Open",
    }
    # Newest first, matching what the UI expects to show at the top.
    TICKETS.insert(0, ticket)
    return ticket
