from pydantic import BaseModel, ConfigDict, Field


class SupportTicketCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=4000)


class SupportTicketRead(BaseModel):
    id: str
    subject: str
    date: str
    status: str = "Open"

    model_config = ConfigDict(from_attributes=True)
