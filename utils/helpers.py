"""
Yardımcı Fonksiyonlar

Formatlama, dönüştürme ve genel amaçlı araçlar.
"""

from typing import Union


def format_number(value: Union[int, float], decimals: int = 2) -> str:
    """
    Büyük sayıları okunabilir formata çevirir.
    1_500_000 -> "1.50M"
    """
    if value is None:
        return "--"

    abs_val = abs(value)
    sign = "-" if value < 0 else ""

    if abs_val >= 1_000_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000_000:.{decimals}f}T"
    elif abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.{decimals}f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.{decimals}f}M"
    elif abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.{decimals}f}K"
    else:
        return f"{sign}{abs_val:.{decimals}f}"


def format_price(price: float) -> str:
    """
    Fiyatı uygun hassasiyetle formatlar.
    BTC -> $65,432.10
    Küçük altcoin -> $0.00001234
    """
    if price is None:
        return "--"

    if price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    elif price >= 0.0001:
        return f"${price:.6f}"
    else:
        return f"${price:.8f}"


def format_percent(value: float) -> str:
    """Yüzde formatlar. Pozitif ise + ekler."""
    if value is None:
        return "--"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def truncate(text: str, max_length: int = 50) -> str:
    """Uzun metinleri kısaltır."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
