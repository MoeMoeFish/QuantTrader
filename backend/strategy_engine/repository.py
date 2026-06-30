from typing import Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ._db import Strategy, StrategyVersion


class StrategyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Strategy:
        strategy = Strategy(**data)
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def get_by_id(self, strategy_id: int) -> Optional[Strategy]:
        result = await self.session.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Strategy]:
        result = await self.session.execute(
            select(Strategy).where(Strategy.code == code)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status: Optional[str] = None,
        strategy_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Strategy]:
        query = select(Strategy)
        if status:
            query = query.where(Strategy.status == status)
        if strategy_type:
            query = query.where(Strategy.strategy_type == strategy_type)
        query = query.order_by(Strategy.updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, strategy_id: int, data: dict) -> Optional[Strategy]:
        await self.session.execute(
            update(Strategy).where(Strategy.id == strategy_id).values(**data)
        )
        await self.session.flush()
        return await self.get_by_id(strategy_id)

    async def delete(self, strategy_id: int) -> bool:
        result = await self.session.execute(
            delete(Strategy).where(Strategy.id == strategy_id)
        )
        return result.rowcount > 0

    async def count(self, status: Optional[str] = None) -> int:
        from sqlalchemy import func
        query = select(func.count(Strategy.id))
        if status:
            query = query.where(Strategy.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0


class StrategyVersionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> StrategyVersion:
        version = StrategyVersion(**data)
        self.session.add(version)
        await self.session.flush()
        await self.session.refresh(version)
        return version

    async def get_by_id(self, version_id: int) -> Optional[StrategyVersion]:
        result = await self.session.execute(
            select(StrategyVersion).where(StrategyVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def list_by_strategy(
        self,
        strategy_id: int,
        status: Optional[str] = None,
    ) -> list[StrategyVersion]:
        query = select(StrategyVersion).where(StrategyVersion.strategy_id == strategy_id)
        if status:
            query = query.where(StrategyVersion.status == status)
        query = query.order_by(StrategyVersion.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, strategy_id: int) -> Optional[StrategyVersion]:
        result = await self.session.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
