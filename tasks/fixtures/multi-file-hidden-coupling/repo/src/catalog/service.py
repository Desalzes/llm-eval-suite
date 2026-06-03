from __future__ import annotations

from typing import Iterable

from .index import ProductSearchIndex
from .models import Product, SearchResult
from .repository import CatalogRepository


class CatalogService:
    """Coordinates repository-backed product details and catalog search."""

    def __init__(self, repository: CatalogRepository, index: ProductSearchIndex) -> None:
        self._repository = repository
        self._index = index

    @classmethod
    def from_products(cls, products: Iterable[Product]) -> "CatalogService":
        repository = CatalogRepository(products)
        index = ProductSearchIndex(repository.list_products())
        return cls(repository=repository, index=index)

    def product_detail(self, product_id: str) -> Product:
        return self._repository.get_product(product_id)

    def search(self, query: str) -> list[SearchResult]:
        return self._index.search(query)

    def update_product_title(self, product_id: str, title: str) -> Product:
        return self._repository.update_title(product_id, title)
