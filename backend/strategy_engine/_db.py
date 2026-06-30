from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from datetime import datetime
from common.config import get_settings


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """时间戳 Mixin"""
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


settings = get_settings()
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class Strategy(Base, TimestampMixin):
    """策略主档"""

    __tablename__ = "strategy"
    __table_args__ = (
        UniqueConstraint("code", name="uk_strategy_code"),
        Index("idx_strategy_type", "strategy_type"),
        Index("idx_strategy_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, comment="策略编码")
    name = Column(String(128), nullable=False, comment="策略名称")
    strategy_type = Column(String(32), nullable=False, comment="策略类型：trend/mean_reversion/arbitrage/sentiment")
    description = Column(Text, nullable=True, comment="策略描述")
    status = Column(String(16), nullable=False, default="draft", comment="状态：draft/active/archived")
    version = Column(String(32), nullable=False, default="1.0.0", comment="当前版本")
    parameters = Column(JSON, nullable=True, comment="策略参数配置")
    entry_rules = Column(Text, nullable=True, comment="入场规则")
    exit_rules = Column(Text, nullable=True, comment="出场规则")
    risk_rules = Column(Text, nullable=True, comment="风控规则")
    backtest_result = Column(JSON, nullable=True, comment="回测结果摘要")
    tags = Column(JSON, nullable=True, comment="标签")
    author = Column(String(64), nullable=True, comment="创建者")
    is_default = Column(Boolean, default=False, comment="是否默认策略")


class StrategyVersion(Base, TimestampMixin):
    """策略版本历史"""

    __tablename__ = "strategy_version"
    __table_args__ = (
        UniqueConstraint("strategy_id", "version", name="uk_strategy_version"),
        Index("idx_sv_strategy", "strategy_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, nullable=False, index=True, comment="关联 strategy.id")
    version = Column(String(32), nullable=False, comment="版本号")
    change_log = Column(Text, nullable=True, comment="变更日志")
    code_content = Column(Text, nullable=True, comment="策略代码内容")
    parameters = Column(JSON, nullable=True, comment="参数快照")
    status = Column(String(16), nullable=False, default="active", comment="状态：active/historical")
    backtest_result = Column(JSON, nullable=True, comment="该版本的回测结果")
