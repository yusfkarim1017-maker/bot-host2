from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.models import BotMode


class BotBase(BaseModel):
    token: str = Field(..., min_length=1, max_length=255)
    username: Optional[str] = Field(None, max_length=255)
    owner_id: Optional[str] = Field(None, max_length=255)
    mode: BotMode = BotMode.POLLING


class BotCreate(BotBase):
    pass


class BotUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    mode: Optional[BotMode] = None
    owner_id: Optional[str] = Field(None, max_length=255)


class BotResponse(BotBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BotListResponse(BaseModel):
    bots: List[BotResponse]
    total: int


class BotLogResponse(BaseModel):
    id: UUID
    bot_id: UUID
    level: str
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class BotLogListResponse(BaseModel):
    logs: List[BotLogResponse]
    total: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    secret_key: str


class WebhookUpdate(BaseModel):
    update_id: int
    message: Optional[dict] = None
    edited_message: Optional[dict] = None
    channel_post: Optional[dict] = None
    edited_channel_post: Optional[dict] = None
    inline_query: Optional[dict] = None
    chosen_inline_result: Optional[dict] = None
    callback_query: Optional[dict] = None
    shipping_query: Optional[dict] = None
    pre_checkout_query: Optional[dict] = None
    poll: Optional[dict] = None
    poll_answer: Optional[dict] = None
    my_chat_member: Optional[dict] = None
    chat_member: Optional[dict] = None
    chat_join_request: Optional[dict] = None