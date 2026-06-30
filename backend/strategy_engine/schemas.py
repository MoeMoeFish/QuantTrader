from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StrategyBase(BaseModel):
    code: str = Field(..., max_length=64, description="策略编码")
    name: str = Field(..., max_length=128, description="策略名称")
    strategy_type: str = Field(..., max_length=32, description="策略类型")
    description: Optional[str] = None
    status: str = Field(default="draft", max_length=16)
    version: str = Field(default="1.0.0", max_length=32)
    parameters: Optional[dict] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    risk_rules: Optional[str] = None
    tags: Optional[list[str]] = None
    author: Optional[str] = None
    is_default: bool = False


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    strategy_type: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=16)
    parameters: Optional[dict] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    risk_rules: Optional[str] = None
    tags: Optional[list[str]] = None


class StrategyResponse(StrategyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyVersionBase(BaseModel):
    strategy_id: int
    version: str = Field(..., max_length=32)
    change_log: Optional[str] = None
    code_content: Optional[str] = None
    parameters: Optional[dict] = None
    status: str = Field(default="active", max_length=16)
    backtest_result: Optional[dict] = None


class StrategyVersionCreate(StrategyVersionBase):
    pass


class StrategyVersionResponse(StrategyVersionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
