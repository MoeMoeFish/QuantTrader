"""
历史回放模块 - 数据库模型

5张表，覆盖模块全部存储需求：
    replay_session    — 回测会话（参数 + 指标快照）
    replay_bar        — 逐bar数据（行情 + 信号 + 账户快照）
    replay_order      — 订单记录
    replay_position   — 持仓记录
    replay_log        — 日志条目

关联方式：
    replay_order / replay_position / replay_log 通过 session_id + bar_time 关联到 replay_bar
    所有表通过 session_id 关联到 replay_session

设计原则：
    - 指标预存快照，跑完不变
    - 每 bar 一行，子数据拆子表
    - benchmark_close 存入 replay_bar，保证快照完整不依赖外部
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, Text, Index,
)
from sqlalchemy.orm import relationship
from common.database import Base, TimestampMixin


# ============================================================
# 1. 回测会话
# ============================================================

class ReplaySession(TimestampMixin, Base):
    """
    回测会话表。

    业务含义：每次用户点"开始回测"产生一条记录，包含用户选择的6个参数
    和跑完后calculator计算的全部指标快照。

    用途：
    - F2 启动回测：记录回测参数
    - F4 实时指标：从预存指标直接读取
    - F7 收益概述：从预存指标直接读取
    - F11 历史列表：列出用户跑过的回测，展示标的/策略/时间/收益
    """

    __tablename__ = "replay_session"

    # ── 主键 ──
    id = Column(BigInteger, primary_key=True, autoincrement=True,
                comment="会话ID，唯一标识一次回测")

    # ── 用户选择的6个参数（与配置栏一一对应） ──
    stock_code = Column(String(20), nullable=False,
                        comment="股票代码，如 000001.SZ")
    strategy_id = Column(Integer, nullable=False,
                         comment="策略ID，关联策略模块")
    strategy_name = Column(String(100), nullable=False,
                           comment="策略名称，快照，防止策略改名后历史记录对不上")
    account_id = Column(Integer, nullable=False,
                        comment="虚拟账户ID，关联账户模块")
    timeframe = Column(String(10), nullable=False,
                       comment="时间间隔，如 1d/1h/5m")
    start_date = Column(String(10), nullable=False,
                        comment="回测起始日期，格式 YYYY-MM-DD")
    end_date = Column(String(10), nullable=False,
                      comment="回测结束日期，格式 YYYY-MM-DD")

    # ── 回测基础信息 ──
    total_bars = Column(Integer, nullable=False, default=0,
                        comment="总bar数，即回测覆盖的交易时段数")
    time_elapsed = Column(Float, nullable=False, default=0.0,
                          comment="回测耗时（秒）")
    initial_capital = Column(Float, nullable=False, default=0.0,
                             comment="期初总资产")
    final_capital = Column(Float, nullable=False, default=0.0,
                           comment="期末总资产")

    # ── 预存指标快照（calculator 计算结果，跑完不可变） ──
    total_return = Column(Float, nullable=False, default=0.0,
                          comment="策略总收益率 %")
    benchmark_return = Column(Float, nullable=False, default=0.0,
                              comment="基准总收益率 %")
    annual_return = Column(Float, nullable=False, default=0.0,
                           comment="年化收益率 %")
    max_drawdown = Column(Float, nullable=False, default=0.0,
                          comment="最大回撤 %")
    sharpe_ratio = Column(Float, nullable=False, default=0.0,
                          comment="夏普比率")
    sortino_ratio = Column(Float, nullable=False, default=0.0,
                           comment="索提诺比率")
    alpha = Column(Float, nullable=False, default=0.0,
                   comment="Alpha，策略超额收益中无法被市场解释的部分")
    beta = Column(Float, nullable=False, default=0.0,
                  comment="Beta，策略收益对市场收益的敏感度")
    information_ratio = Column(Float, nullable=False, default=0.0,
                               comment="信息率，超额收益的稳定性")
    strategy_volatility = Column(Float, nullable=False, default=0.0,
                                 comment="策略年化波动率")
    benchmark_volatility = Column(Float, nullable=False, default=0.0,
                                  comment="基准年化波动率")
    win_rate = Column(Float, nullable=False, default=0.0,
                      comment="胜率 %")
    profit_loss_ratio = Column(Float, nullable=False, default=0.0,
                               comment="盈亏比")
    trade_count = Column(Integer, nullable=False, default=0,
                         comment="交易次数（一买一卖算一次）")
    total_pnl = Column(Float, nullable=False, default=0.0,
                       comment="总盈亏金额")

    # ── 关联 ──
    bars = relationship("ReplayBar", back_populates="session", lazy="selectin",
                        order_by="ReplayBar.bar_time")


# ============================================================
# 2. 逐bar数据
# ============================================================

class ReplayBar(TimestampMixin, Base):
    """
    逐bar数据表。

    业务含义：回测过程中每个交易时段（一天/一小时/一分钟）的完整快照，
    包含行情数据、策略信号、账户状态。每 bar 一行。

    用途：
    - F3 回放播放：K线OHLCV + 买卖信号
    - F5 资金曲线：从 total_assets 算净值和回撤
    - F7 收益概述：从 total_assets 算策略收益曲线，从 benchmark_close 算基准收益曲线
    - F9 每日持仓：关联 replay_position

    关联：
    - session_id → replay_session
    - bar_time + session_id → replay_order / replay_position / replay_log
    """

    __tablename__ = "replay_bar"

    id = Column(BigInteger, primary_key=True, autoincrement=True,
                comment="bar记录ID")

    session_id = Column(BigInteger, nullable=False, index=True,
                        comment="关联回测会话ID")

    # ── 行情数据 ──
    bar_time = Column(String(10), nullable=False,
                      comment="交易日期，格式 YYYY-MM-DD")
    open = Column(Float, nullable=False, comment="开盘价")
    high = Column(Float, nullable=False, comment="最高价")
    low = Column(Float, nullable=False, comment="最低价")
    close = Column(Float, nullable=False, comment="收盘价")
    volume = Column(BigInteger, nullable=False, default=0, comment="成交量（股）")
    amount = Column(Float, nullable=False, default=0.0, comment="成交额（元）")

    # ── 基准行情（快照，不依赖外部行情源） ──
    benchmark_close = Column(Float, nullable=False, default=0.0,
                             comment="基准收盘价（如沪深300），用于计算Alpha/Beta/信息率/基准收益")

    # ── 策略信号 ──
    signal = Column(String(10), nullable=True,
                    comment="触发的信号：buy/sell/None")
    signal_reason = Column(String(100), nullable=True,
                           comment="信号触发原因，如 均线金叉/RSI超卖")

    # ── 账户快照 ──
    cash = Column(Float, nullable=False, default=0.0,
                  comment="现金余额")
    total_assets = Column(Float, nullable=False, default=0.0,
                          comment="总资产 = cash + sum(持仓市值)，最核心字段，几乎所有指标从它派生")

    # ── 关联 ──
    session = relationship("ReplaySession", back_populates="bars")
    orders = relationship("ReplayOrder", back_populates="bar",
                          lazy="selectin",
                          order_by="ReplayOrder.id")
    positions = relationship("ReplayPosition", back_populates="bar",
                             lazy="selectin",
                             order_by="ReplayPosition.id")
    logs = relationship("ReplayLog", back_populates="bar",
                        lazy="selectin",
                        order_by="ReplayLog.id")

    __table_args__ = (
        # 同一会话内 bar_time 唯一，一个交易日只有一行
        Index("ix_replay_bar_session_time", "session_id", "bar_time", unique=True),
    )


# ============================================================
# 3. 订单记录
# ============================================================

class ReplayOrder(TimestampMixin, Base):
    """
    订单记录表。

    业务含义：回测过程中发生的一次虚拟交易（买入或卖出）。
    一个 bar 可能产生 0~N 笔订单（通常0或1笔）。

    用途：
    - F6/F8 交易详情表的数据源
    - 计算胜率：pnl > 0 的卖出订单占比
    - 计算盈亏比：avg(盈利pnl) / |avg(亏损pnl)|
    - 计算总盈亏：sum(卖出订单pnl)

    关联：session_id + bar_time → replay_bar
    """

    __tablename__ = "replay_order"

    id = Column(BigInteger, primary_key=True, autoincrement=True,
                comment="订单ID")

    session_id = Column(BigInteger, nullable=False, index=True,
                        comment="关联回测会话ID")
    bar_time = Column(String(10), nullable=False,
                      comment="成交日期，格式 YYYY-MM-DD，关联 replay_bar")

    # ── 订单信息 ──
    side = Column(String(4), nullable=False,
                  comment="交易方向：buy/sell")
    price = Column(Float, nullable=False,
                   comment="成交价格（每股），回测中通常取当bar收盘价")
    quantity = Column(Integer, nullable=False,
                      comment="成交数量（股数），由策略模块内部仓位管理决定")
    amount = Column(Float, nullable=False,
                    comment="成交金额 = price × quantity")
    commission = Column(Float, nullable=False, default=0.0,
                        comment="手续费（券商佣金+印花税等交易成本）")
    pnl = Column(Float, nullable=False, default=0.0,
                 comment="盈亏金额，卖出时为已实现盈亏，买入时为0；"
                         "计算方式：(卖价-买均价)×数量-双向手续费")
    signal = Column(String(100), nullable=True,
                    comment="触发信号名称，如 均线金叉/RSI超卖")

    # ── 关联 ──
    bar = relationship("ReplayBar", back_populates="orders")

    __table_args__ = (
        Index("ix_replay_order_session_time", "session_id", "bar_time"),
    )


# ============================================================
# 4. 持仓记录
# ============================================================

class ReplayPosition(TimestampMixin, Base):
    """
    持仓记录表。

    业务含义：某个交易日收盘时账户中持有某只股票的详细信息。
    一个 bar 可能产生 0~N 个持仓记录（当前只有单股票，通常0或1条）。

    用途：
    - F9 每日持仓&收益表的数据源
    - 验证 total_assets = cash + sum(所有持仓市值)

    关联：session_id + bar_time → replay_bar
    """

    __tablename__ = "replay_position"

    id = Column(BigInteger, primary_key=True, autoincrement=True,
                comment="持仓记录ID")

    session_id = Column(BigInteger, nullable=False, index=True,
                        comment="关联回测会话ID")
    bar_time = Column(String(10), nullable=False,
                      comment="交易日，格式 YYYY-MM-DD，关联 replay_bar")

    # ── 持仓信息 ──
    stock_code = Column(String(20), nullable=False,
                        comment="股票代码，如 000001.SZ")
    quantity = Column(Integer, nullable=False,
                      comment="持仓数量（股数）")
    cost_price = Column(Float, nullable=False,
                        comment="成本价（买入均价）")
    current_price = Column(Float, nullable=False,
                           comment="当前价格（当日收盘价）")
    market_value = Column(Float, nullable=False,
                          comment="市值 = quantity × current_price")
    floating_pnl = Column(Float, nullable=False, default=0.0,
                          comment="浮盈 = 市值 - (成本价×数量)，正数浮盈/负数浮亏")

    # ── 关联 ──
    bar = relationship("ReplayBar", back_populates="positions")

    __table_args__ = (
        Index("ix_replay_position_session_time", "session_id", "bar_time"),
    )


# ============================================================
# 5. 日志条目
# ============================================================

class ReplayLog(TimestampMixin, Base):
    """
    日志条目表。

    业务含义：回测过程中产生的运行日志，包括信息、警告、错误。
    一个 bar 可能产生 0~N 条日志。

    用途：
    - F10 日志输出面板的数据源
    - 辅助调试：了解回测过程中发生了什么（为什么忽略信号、现金不足等）

    关联：session_id + bar_time → replay_bar
    """

    __tablename__ = "replay_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True,
                comment="日志ID")

    session_id = Column(BigInteger, nullable=False, index=True,
                        comment="关联回测会话ID")
    bar_time = Column(String(10), nullable=False,
                      comment="日志产生的交易日，格式 YYYY-MM-DD，关联 replay_bar")

    # ── 日志内容 ──
    level = Column(String(10), nullable=False, default="info",
                   comment="日志级别：info/warn/error")
    message = Column(Text, nullable=False,
                     comment="日志内容，如 [TRADE] 买入 000001.SZ 28400股 @10.53")

    # ── 关联 ──
    bar = relationship("ReplayBar", back_populates="logs")

    __table_args__ = (
        Index("ix_replay_log_session_time", "session_id", "bar_time"),
    )
