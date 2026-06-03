from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .models import Product, SearchResult

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_title(title: str) -> str:
    return " ".join(_TOKEN_PATTERN.findall(title.lower()))


@dataclass(frozen=True, slots=True)
class _IndexedProduct:
    product_id: str
    title: str
    normalized_title: str


class ProductSearchIndex:
    """In-memory title index shared by catalog search requests."""

    def __init__(self, products: Iterable[Product]) -> None:
        self._documents: dict[str, _IndexedProduct] = {}
        self._term_to_product_ids: dict[str, set[str]] = defaultdict(set)
        for product in products:
            self._add_product(product)

    def refresh_product(self, product: Product) -> None:
        normalized = normalize_title(product.title)
        self._documents[product.id] = _IndexedProduct(
            product_id=product.id,
            title=product.title,
            normalized_title=normalized,
        )

    def search(self, query: str) -> list[SearchResult]:
        terms = normalize_title(query).split()
        if not terms:
            return []

        matching_ids = self._ids_for_terms(terms)
        results = [
            SearchResult(product_id=product_id, title=self._documents[product_id].title)
            for product_id in matching_ids
        ]
        return sorted(results, key=lambda result: (result.title, result.product_id))

    def _add_product(self, product: Product) -> None:
        normalized = normalize_title(product.title)
        self._documents[product.id] = _IndexedProduct(
            product_id=product.id,
            title=product.title,
            normalized_title=normalized,
        )
        for term in normalized.split():
            self._term_to_product_ids[term].add(product.id)

    def _ids_for_terms(self, terms: list[str]) -> set[str]:
        matching_ids = self._term_to_product_ids.get(terms[0], set()).copy()
        for term in terms[1:]:
            matching_ids &= self._term_to_product_ids.get(term, set())
        return matching_ids
