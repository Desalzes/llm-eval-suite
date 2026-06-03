from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .models import Product


class CatalogRepository:
    """Stores the current catalog records used by product detail pages."""

    def __init__(self, products: Iterable[Product]) -> None:
        self._products = {product.id: product for product in products}

    def list_products(self) -> list[Product]:
        return list(self._products.values())

    def get_product(self, product_id: str) -> Product:
        try:
            return self._products[product_id]
        except KeyError as exc:
            raise KeyError(f"unknown product id: {product_id}") from exc

    def update_title(self, product_id: str, title: str) -> Product:
        product = self.get_product(product_id)
        updated = replace(product, title=title)
        self._products[product_id] = updated
        return updated
