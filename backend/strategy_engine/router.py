from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ._db import get_db, Strategy, StrategyVersion
from .schemas import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategyVersionCreate,
    StrategyVersionResponse,
)
from .repository import StrategyRepository, StrategyVersionRepository

router = APIRouter(prefix="/api/strategy", tags=["策略引擎"])


@router.get("/list", response_model=dict)
async def get_strategies(
    status: Optional[str] = Query(None, description="状态过滤"),
    strategy_type: Optional[str] = Query(None, description="类型过滤"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取策略列表"""
    repo = StrategyRepository(db)
    strategies = await repo.list_all(status=status, strategy_type=strategy_type, limit=limit, offset=offset)
    total = await repo.count(status=status)
    return {
        "success": True,
        "data": [StrategyResponse.model_validate(s).model_dump() for s in strategies],
        "total": total,
        "message": "success",
    }


@router.post("/create", response_model=dict)
async def create_strategy(
    data: StrategyCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建策略"""
    repo = StrategyRepository(db)
    
    # 检查编码是否已存在
    existing = await repo.get_by_code(data.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"策略编码 {data.code} 已存在")
    
    strategy = await repo.create(data.model_dump())
    return {
        "success": True,
        "data": StrategyResponse.model_validate(strategy).model_dump(),
        "message": "策略创建成功",
    }


@router.get("/{strategy_id}", response_model=dict)
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取策略详情"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    return {
        "success": True,
        "data": StrategyResponse.model_validate(strategy).model_dump(),
        "message": "success",
    }


@router.put("/{strategy_id}", response_model=dict)
async def update_strategy(
    strategy_id: int,
    data: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新策略"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    updated = await repo.update(strategy_id, update_data)
    return {
        "success": True,
        "data": StrategyResponse.model_validate(updated).model_dump(),
        "message": "策略更新成功",
    }


@router.delete("/{strategy_id}", response_model=dict)
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除策略"""
    repo = StrategyRepository(db)
    deleted = await repo.delete(strategy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="策略不存在")
    return {
        "success": True,
        "data": {},
        "message": "策略删除成功",
    }


@router.get("/{strategy_id}/versions", response_model=dict)
async def get_strategy_versions(
    strategy_id: int,
    status: Optional[str] = Query(None, description="版本状态过滤"),
    db: AsyncSession = Depends(get_db),
):
    """获取策略版本历史"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    version_repo = StrategyVersionRepository(db)
    versions = await version_repo.list_by_strategy(strategy_id, status=status)
    return {
        "success": True,
        "data": [StrategyVersionResponse.model_validate(v).model_dump() for v in versions],
        "message": "success",
    }


@router.post("/{strategy_id}/versions", response_model=dict)
async def create_strategy_version(
    strategy_id: int,
    data: StrategyVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建策略新版本"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 将 strategy_id 设为当前策略 ID
    version_data = data.model_dump()
    version_data["strategy_id"] = strategy_id
    
    version_repo = StrategyVersionRepository(db)
    version = await version_repo.create(version_data)
    
    # 更新策略版本号
    await repo.update(strategy_id, {"version": data.version})
    
    return {
        "success": True,
        "data": StrategyVersionResponse.model_validate(version).model_dump(),
        "message": "版本创建成功",
    }
