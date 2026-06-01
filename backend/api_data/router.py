from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any

from common.database import get_db
from common.dependencies import get_data_source
from .adapters.base import DataSourceAdapter
from .adapters.mock import MockAdapter
from .schemas import (
    StockBaseInfo,
    KLineData,
    RealTimeQuote,
    SectorInfo,
    StockListItem,
    KLineQuery,
    BatchStockQuery,
    StockSyncRequest,
    KLineSyncRequest,
    SectorStocksQuery,
    StockSearchQuery,
)
from .service import StockService, KLineService, MarketDataService, SectorService
from .repository import (
    StockRepository,
    KLineRepository,
    RealtimeQuoteRepository,
    SectorRepository,
)
from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import APIRouter, Query


router = APIRouter(prefix="/api/api-data", tags=["API对接-行情数据"])

EASTMONEY_SUGGEST_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://quote.eastmoney.com/",
}


def ok(data: Any, message: str = "ok") -> dict[str, Any]:
    return {"success": True, "data": data, "message": message}


def _http_get_text(url: str, timeout: int = 5, encoding: str = "utf-8") -> str:
    request = Request(url, headers=HTTP_HEADERS)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - trusted quote endpoints configured here.
        return response.read().decode(encoding, errors="ignore")


def _market_prefix(symbol: str) -> str:
    code = symbol[-6:]
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith(("4", "8")):
        return "bj"
    return "sz"


def _exchange(symbol: str) -> str:
    prefix = _market_prefix(symbol)
    return {"sh": "SH", "sz": "SZ", "bj": "BJ"}.get(prefix, "")


def _decimal_text(value: Any) -> str:
    try:
        decimal = Decimal(str(value or "0").strip())
    except (InvalidOperation, ValueError):
        return ""
    if decimal <= 0:
        return ""
    return f"{decimal:.4f}"


def _int_value(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except (TypeError, ValueError):
        return 0


def _security_from_suggest_item(item: dict[str, Any]) -> dict[str, Any]:
    code = str(item.get("Code") or item.get("UnifiedCode") or "").strip()
    quote_id = str(item.get("QuoteID") or "").strip()
    return {
        "symbol": code,
        "name": str(item.get("Name") or "").strip(),
        "exchange": _exchange(code),
        "quote_id": quote_id,
        "security_type": str(item.get("SecurityTypeName") or item.get("Classify") or "").strip(),
        "source": "eastmoney_suggest",
    }


def search_securities(keyword: str, limit: int = 10) -> list[dict[str, Any]]:
    text = keyword.strip()
    if not text:
        return []
    url = (
        "https://searchapi.eastmoney.com/api/suggest/get"
        f"?input={quote(text)}&type=14&token={EASTMONEY_SUGGEST_TOKEN}&count={limit}"
    )
    try:
        payload = json.loads(_http_get_text(url))
    except Exception:
        return []
    rows = (((payload or {}).get("QuotationCodeTable") or {}).get("Data") or [])[:limit]
    return [
        security
        for item in rows
        for security in [_security_from_suggest_item(item)]
        if security["symbol"]
    ]


def fetch_tencent_quote(symbol: str) -> dict[str, Any] | None:
    code = symbol[-6:]
    market_code = f"{_market_prefix(code)}{code}"
    try:
        text = _http_get_text(f"https://qt.gtimg.cn/q={market_code}", encoding="gbk")
    except Exception:
        return None
    match = re.search(r'="([^"]*)"', text)
    if not match:
        return None
    fields = match.group(1).split("~")
    if len(fields) < 35:
        return None
    last_price = _decimal_text(fields[3])
    bid_price_1 = _decimal_text(fields[9]) or last_price
    ask_price_1 = _decimal_text(fields[19]) or last_price
    timestamp = fields[30] if len(fields) > 30 else ""
    bid_levels = [
        {"level": index + 1, "price": _decimal_text(fields[9 + index * 2]), "volume": _int_value(fields[10 + index * 2])}
        for index in range(5)
        if len(fields) > 10 + index * 2 and _decimal_text(fields[9 + index * 2])
    ]
    ask_levels = [
        {"level": index + 1, "price": _decimal_text(fields[19 + index * 2]), "volume": _int_value(fields[20 + index * 2])}
        for index in range(5)
        if len(fields) > 20 + index * 2 and _decimal_text(fields[19 + index * 2])
    ]
    return {
        "symbol": fields[2] or code,
        "name": fields[1] or "",
        "exchange": _exchange(fields[2] or code),
        "last_price": last_price,
        "pre_close": _decimal_text(fields[4]),
        "open_price": _decimal_text(fields[5]),
        "high_price": _decimal_text(fields[33]),
        "low_price": _decimal_text(fields[34]),
        "bid_price_1": bid_price_1,
        "bid_volume_1": _int_value(fields[10]),
        "ask_price_1": ask_price_1,
        "ask_volume_1": _int_value(fields[20]),
        "bid_levels": bid_levels,
        "ask_levels": ask_levels,
        "timestamp": timestamp,
        "source": "tencent_quote",
    }


def build_lookup(keyword: str, side: str = "buy") -> dict[str, Any]:
    text = keyword.strip()
    candidates = search_securities(text, limit=5)
    if not candidates and re.fullmatch(r"\d{6}", text):
        candidates = [{"symbol": text, "name": "", "exchange": _exchange(text), "quote_id": "", "source": "code_rule"}]
    primary = candidates[0] if candidates else {"symbol": text[-6:] if re.fullmatch(r"\d{6}", text[-6:]) else "", "name": text}
    quote_data = fetch_tencent_quote(primary["symbol"]) if primary.get("symbol") else None
    data = {**primary, **(quote_data or {})}
    default_price = data.get("ask_price_1") if side == "buy" else data.get("bid_price_1")
    data.update(
        {
            "query": text,
            "side": side,
            "default_price": default_price or data.get("last_price") or "",
            "default_price_source": "卖一价" if side == "buy" else "买一价",
            "candidates": candidates,
            "resolved_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
        }
    )
    return data


def get_stock_service(
    db: AsyncSession = Depends(get_db),
    data_source: DataSourceAdapter = Depends(get_data_source),
) -> StockService:
    return StockService(data_source, StockRepository(db))


def get_kline_service(
    db: AsyncSession = Depends(get_db),
    data_source: DataSourceAdapter = Depends(get_data_source),
) -> KLineService:
    return KLineService(data_source, KLineRepository(db))


def get_market_data_service(
    db: AsyncSession = Depends(get_db),
    data_source: DataSourceAdapter = Depends(get_data_source),
) -> MarketDataService:
    return MarketDataService(data_source, RealtimeQuoteRepository(db))


def get_sector_service(
    db: AsyncSession = Depends(get_db),
    data_source: DataSourceAdapter = Depends(get_data_source),
) -> SectorService:
    return SectorService(data_source, SectorRepository(db))


def success_response(data: Any, message: str = "操作成功") -> dict:
    """统一响应格式"""
    return {"success": True, "data": data, "message": message}


def error_response(message: str, status_code: int = 400) -> None:
    """统一错误响应"""
    raise HTTPException(status_code=status_code, detail={"success": False, "message": message})


# ========== 个股接口 ==========


@router.get("/stock/{symbol}/base")
async def get_stock_base_info(symbol: str, service: StockService = Depends(get_stock_service)):
    """获取个股基础信息"""
    data = await service.get_stock_base_info(symbol)
    return success_response(data, "获取成功")


@router.post("/stock/sync")
async def sync_stocks(request: StockSyncRequest, service: StockService = Depends(get_stock_service)):
    """批量同步个股信息"""
    data = await service.sync_stocks(request.symbols)
    return success_response(data, "同步成功")

@router.get("/symbols")
async def get_symbols(keyword: str = Query(default="", description="证券代码、名称或拼音"), limit: int = Query(default=10, ge=1, le=30)):
    return ok(search_securities(keyword, limit), "证券列表已获取")

@router.get("/stock/list")
async def get_stock_list(
    market: Optional[str] = Query(None, description="市场类型 A/HK/US"),
    service: StockService = Depends(get_stock_service),
):
    """获取所有个股列表"""
    data = await service.list_stocks(market)
    return success_response(data, "获取成功")


@router.get("/stock/search")
async def search_stocks(
    keyword: str = Query(..., min_length=1, max_length=50, description="搜索关键词（股票代码或名称）"),
    market: Optional[str] = Query(None, description="市场类型 A/HK/US"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    service: StockService = Depends(get_stock_service),
):
    """根据股票名称或代码模糊搜索"""
    data = await service.search_stocks(keyword, market, limit)
    return success_response(data, "搜索成功")


# ========== K线接口 ==========


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    timeframe: str = Query("1d", description="时间周期: 1m/5m/15m/30m/1h/1d/1w"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    service: KLineService = Depends(get_kline_service),
):
    """获取K线数据"""
    data = await service.get_kline_data(symbol, timeframe, start_date, end_date, limit)
    return success_response(data, "获取成功")


@router.post("/kline/{symbol}/sync")
async def sync_kline(
    symbol: str,
    request: KLineSyncRequest,
    service: KLineService = Depends(get_kline_service),
):
    """同步K线数据"""
    data = await service.sync_kline_data(symbol, request.timeframe, request.start_date, request.end_date)
    return success_response(data, "同步成功")


# ========== 实时行情接口 ==========


@router.get("/realtime/{symbol}")
async def get_realtime_quote(symbol: str, service: MarketDataService = Depends(get_market_data_service)):
    """获取实时行情"""
    data = await service.get_realtime_quote(symbol)
    return success_response(data, "获取成功")


@router.post("/realtime/batch")
async def get_batch_realtime_quote(request: BatchStockQuery, service: MarketDataService = Depends(get_market_data_service)):
    """批量获取实时行情"""
    data = await service.get_batch_realtime_quote(request.symbols)
    return success_response(data, "获取成功")


# ========== 板块接口 ==========


@router.get("/sector")
async def get_sector_list(
    market: Optional[str] = Query(None, description="市场类型"),
    service: SectorService = Depends(get_sector_service),
):
    """获取板块列表"""
    data = await service.list_sectors(market)
    return success_response(data, "获取成功")


@router.get("/sector/{sector_code}/stocks")
async def get_sector_stocks(sector_code: str, service: SectorService = Depends(get_sector_service)):
    """获取板块成分股"""
    data = await service.get_sector_stocks(sector_code)
    return success_response(data, "获取成功")
    return ok([], "模块开发中")


@router.get("/ticker")
async def get_ticker(symbol: str = Query(default="")):
    data = fetch_tencent_quote(symbol[-6:]) if symbol else None
    return ok(data or {}, "实时行情已获取" if data else "未获取到实时行情")


@router.get("/security-lookup")
async def security_lookup(
    keyword: str = Query(..., min_length=1, description="证券代码、名称或拼音"),
    side: str = Query(default="buy", pattern="^(buy|sell)$"),
):
    data = build_lookup(keyword, side)
    return ok(data, "证券信息已识别" if data.get("symbol") else "未识别到证券信息")
