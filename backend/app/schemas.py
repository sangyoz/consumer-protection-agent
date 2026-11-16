from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

Stage = Literal['collecting', 'analyzing', 'negotiating', 'complaining', 'following', 'resolved']
MaterialKind = Literal['order', 'contract', 'photo', 'chat', 'other']
MaterialSource = Literal['user', 'extracted', 'inferred']


class CaseInput(BaseModel):
    title: str = Field(default='', max_length=100)
    summary: str = Field(min_length=1, max_length=10000)
    merchant: str = Field(default='', max_length=200)
    amount: float = Field(default=0, ge=0, le=100000000, allow_inf_nan=False)
    goal: str = Field(default='', max_length=1000)
    tradeTime: str = Field(default='', max_length=20)
    platform: str = Field(default='', max_length=100)
    product: str = Field(default='', max_length=200)
    payee: str = Field(default='', max_length=200)
    creditCode: str = Field(default='', max_length=30)

    @field_validator('summary')
    @classmethod
    def nonempty_summary(cls, value):
        if not value.strip():
            raise ValueError('请描述案件情况')
        return value.strip()

    @field_validator('creditCode')
    @classmethod
    def normalize_credit_code(cls, value):
        value = (value or '').strip().upper()
        if value and not value.replace(' ', '').isalnum():
            raise ValueError('统一社会信用代码应为字母或数字')
        return value.replace(' ', '')


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)
    summary: Optional[str] = Field(default=None, max_length=10000)
    merchant: Optional[str] = Field(default=None, max_length=200)
    amount: Optional[float] = Field(default=None, ge=0, le=100000000, allow_inf_nan=False)
    goal: Optional[str] = Field(default=None, max_length=1000)
    tradeTime: Optional[str] = Field(default=None, max_length=20)
    platform: Optional[str] = Field(default=None, max_length=100)
    product: Optional[str] = Field(default=None, max_length=200)
    payee: Optional[str] = Field(default=None, max_length=200)
    creditCode: Optional[str] = Field(default=None, max_length=30)
    complaintAttachments: Optional[list[str]] = None
    goalPlan: Optional[dict] = None

    @field_validator('summary')
    @classmethod
    def nonempty_summary(cls, value):
        if value is not None and not value.strip():
            raise ValueError('案件描述不能为空')
        return value.strip() if value is not None else value

    @field_validator('creditCode')
    @classmethod
    def normalize_credit_code(cls, value):
        if value is None:
            return value
        value = value.strip().upper().replace(' ', '')
        if value and not value.isalnum():
            raise ValueError('统一社会信用代码应为字母或数字')
        return value


class MessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=10000)

    @field_validator('content')
    @classmethod
    def nonempty_content(cls, value):
        if not value.strip():
            raise ValueError('请输入商家回复')
        return value.strip()


AcceptStatus = Literal['pending', 'accepted', 'supplement', 'rejected', 'contacted', 'resolved']


class ProgressInput(BaseModel):
    note: str = Field(min_length=1, max_length=3000)
    stage: Optional[Stage] = None
    confirmed: bool = False
    channel: Optional[str] = Field(default=None, max_length=100)
    caseNo: Optional[str] = Field(default=None, max_length=100)
    acceptStatus: Optional[AcceptStatus] = None
    deadline: Optional[str] = Field(default=None, max_length=20)
    resolution: Optional[dict] = None

    @field_validator('note')
    @classmethod
    def nonempty_note(cls, value):
        if not value.strip():
            raise ValueError('请输入处理反馈')
        return value.strip()


class MaterialKindInput(BaseModel):
    kind: MaterialKind


class ExtractInput(BaseModel):
    """从一段自由描述中按规则抽取案件字段，不做推断。"""

    text: str = Field(min_length=1, max_length=10000)

    @field_validator('text')
    @classmethod
    def nonempty_text(cls, value):
        if not value.strip():
            raise ValueError('请先描述案件情况')
        return value.strip()
