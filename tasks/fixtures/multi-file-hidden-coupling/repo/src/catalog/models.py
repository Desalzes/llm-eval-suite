from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Product:
    id: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class SearchResult:
    product_id: str
    title: str
