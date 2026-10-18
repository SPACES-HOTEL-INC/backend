"""Schemas for support tickets.

NOTE: tickets are held in an in-memory dict in the router, not a table, so they
are lost when the process restarts. The shapes here are what the frontend
already expects and are ready for a real model.
"""

from pydantic import BaseModel, ConfigDict, Field


class SupportTicketCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=4000)


class SupportTicketRead(BaseModel):
    """A ticket as returned to clients.

    `date` is a preformatted string and `id` a synthetic one, matching the
    frontend's existing expectations.
    """

    id: str
    subject: str
    date: str
    status: str = "Open"

    model_config = ConfigDict(from_attributes=True)
