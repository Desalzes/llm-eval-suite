"""Tiny catalog package used by the benchmark fixture."""

from .models import Product, SearchResult
from .repository import CatalogRepository
from .service import CatalogService

__all__ = [
    "CatalogRepository",
    "CatalogService",
    "Product",
    "SearchResult",
]
