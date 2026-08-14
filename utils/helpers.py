"""
Helper Utilities

Data formatting and string manipulation helper functions.
"""

from __future__ import annotations

import re
from typing import Union


def extract_base_asset(symbol: str) -> str:
    """
    Extracts the underlying base crypto asset from ticker symbols.

    Examples:
        'SUNUSDT.P'   -> 'SUN'
        'SUNUSDT'     -> 'SUN'
        'PEOPLETRY'   -> 'PEOPLE'
        'PEOPLEUSDT'  -> 'PEOPLE'
        'GUSDT.P'     -> 'G'
        'GTRY'        -> 'G'
        'SOLUSDC.P'   -> 'SOL'
    """
    if not symbol:
        return ""

    sym = str(symbol).strip().upper()

    # Remove futures / derivative suffixes (.P, _PERP, PERP, etc.)
    sym = re.sub(r"(\.P|_PERP|PERP|[UZ]\d{4})$", "", sym)

    # Common quote currencies sorted by length descending to match longest first
    quote_currencies = [
        "USDT", "USDC", "USDS", "RLUSD", "BFUSD",
        "TRY", "BRL", "EUR", "JPY", "UAH", "USD",
        "BTC", "ETH", "SOL", "BNB"
    ]

    for quote in quote_currencies:
        if sym.endswith(quote) and len(sym) > len(quote):
            sym = sym[:-len(quote)]
            break

    return sym or str(symbol)


def format_price(price: Union[int, float]) -> str:
    """Formats numeric price into human readable string with appropriate precision."""
    if price is None:
        return "$0.00"
    val = float(price)
    if val < 0.0001:
        return f"${val:.8f}"
    elif val < 1.0:
        return f"${val:.4f}"
    else:
        return f"${val:,.2f}"


def format_volume(volume: Union[int, float]) -> str:
    """Formats large numeric volume into abbreviated string (K, M, B)."""
    if volume is None:
        return "0"
    val = float(volume)
    if val >= 1_000_000_000:
        return f"${val / 1_000_000_000:.2f}B"
    elif val >= 1_000_000:
        return f"${val / 1_000_000:.2f}M"
    elif val >= 1_000:
        return f"${val / 1_000:.2f}K"
    else:
        return f"${val:.2f}"


def format_number(val: Union[int, float], decimals: int = 2) -> str:
    """Formats numbers with comma separators and precision."""
    if val is None:
        return "0"
    return f"{float(val):,.{decimals}f}"


def truncate(text: str, max_len: int = 50) -> str:
    """Truncates string to max_len adding ellipsis if needed."""
    if not text or len(text) <= max_len:
        return text or ""
    return text[: max_len - 3] + "..."
