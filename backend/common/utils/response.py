"""
通用 API 响应模型
"""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool
    data: Any = None
    message: str = ""


class PageResult(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int


def success_response(data: Any = None, message: str = "") -> dict:
    """快捷成功响应"""
    return ApiResponse(success=True, data=data, message=message).model_dump()


def error_response(message: str, data: Any = None) -> dict:
    """快捷错误响应"""
    return ApiResponse(success=False, data=data, message=message).model_dump()
