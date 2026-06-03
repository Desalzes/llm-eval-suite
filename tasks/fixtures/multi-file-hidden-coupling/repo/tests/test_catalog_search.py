from __future__ import annotations

from catalog.models import Product
from catalog.service import CatalogService


def build_service() -> CatalogService:
    return CatalogService.from_products(
        [
            Product(
                id="kettle-001",
                title="Alpine Tea Kettle",
                description="A stainless kettle for camp kitchens.",
            ),
            Product(
                id="mug-002",
                title="Harbor Ceramic Mug",
                description="A diner-weight mug with a wide handle.",
            ),
            Product(
                id="press-003",
                title="Trail Coffee Press",
                description="A compact coffee press for travel.",
            ),
        ]
    )


def result_ids(results):
    return [result.product_id for result in results]


def test_search_finds_seeded_products_by_normalized_title() -> None:
    service = build_service()

    assert result_ids(service.search("ALPINE kettle")) == ["kettle-001"]
    assert service.search("ceramic")[0].title == "Harbor Ceramic Mug"


def test_title_update_is_visible_on_product_detail() -> None:
    service = build_service()

    updated = service.update_product_title("kettle-001", "Copper Summit Kettle")

    assert updated.title == "Copper Summit Kettle"
    assert service.product_detail("kettle-001").title == "Copper Summit Kettle"


def test_title_update_refreshes_search_index() -> None:
    service = build_service()

    service.update_product_title("kettle-001", "Copper Summit Kettle")

    copper_results = service.search("copper summit")
    assert result_ids(copper_results) == ["kettle-001"]
    assert copper_results[0].title == "Copper Summit Kettle"
    assert service.search("alpine") == []


def test_multiple_title_updates_replace_previous_index_terms() -> None:
    service = build_service()

    service.update_product_title("mug-002", "Stoneware Desk Cup")
    service.update_product_title("mug-002", "Porcelain Travel Tumbler")

    assert result_ids(service.search("porcelain tumbler")) == ["mug-002"]
    assert service.search("stoneware") == []
    assert service.search("harbor") == []
