from typing import Literal
from pydantic import BaseModel, Field, field_validator

Stage = Literal['collecting', 'analyzing', 'negotiating', 'complaining', 'following', 'resolved']


class CaseInput(BaseModel):
    title: str = Field(default='', max_length=100)
    summary: str = Field(min_length=1, max_length=10000)
    merchant: str = Field(default='', max_length=200)
    amount: float = Field(default=0, ge=0, le=100000000, allow_inf_nan=False)
    goal: str = Field(default='', max_length=1000)

    @field_validator('summary')
    @classmethod
    def nonempty_summary(cls, value):
        if not value.strip():
            raise ValueError('请描述案件情况')
        return value.strip()


class MessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=10000)

    @field_validator('content')
    @classmethod
    def nonempty_content(cls, value):
        if not value.strip():
            raise ValueError('请输入商家回复')
        return value.strip()


class ProgressInput(BaseModel):
    note: str = Field(min_length=1, max_length=3000)
    stage: Stage | None = None
    confirmed: bool = False

    @field_validator('note')
    @classmethod
    def nonempty_note(cls, value):
        if not value.strip():
            raise ValueError('请输入处理反馈')
        return value.strip()
