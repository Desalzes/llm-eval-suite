from fulfillment.shipping_policy import Order, choose_shipping


def test_hazardous_orders_use_ground_hazmat_before_any_upgrade() -> None:
    decision = choose_shipping(
        Order(
            order_id="ord_hazmat",
            customer_tier="vip",
            total_dollars=500,
            weight_pounds=5,
            contains_hazardous_items=True,
        )
    )

    assert decision.method == "ground_hazmat"
    assert decision.manual_review is True
    assert "hazardous" in decision.reason.lower()
    assert "air" in decision.reason.lower()


def test_heavy_orders_use_freight_before_vip_upgrade() -> None:
    decision = choose_shipping(
        Order(
            order_id="ord_heavy",
            customer_tier="vip",
            total_dollars=500,
            weight_pounds=75,
        )
    )

    assert decision.method == "freight"
    assert decision.manual_review is True
    assert "freight" in decision.reason.lower()
    assert "heavy" in decision.reason.lower()


def test_vip_orders_over_threshold_get_overnight_without_manual_review() -> None:
    decision = choose_shipping(
        Order(
            order_id="ord_vip",
            customer_tier="vip",
            total_dollars=250,
            weight_pounds=8,
        )
    )

    assert decision.method == "overnight"
    assert decision.manual_review is False
    assert "vip" in decision.reason.lower()
    assert "threshold" in decision.reason.lower()


def test_vip_orders_below_threshold_stay_ground() -> None:
    decision = choose_shipping(
        Order(
            order_id="ord_small_vip",
            customer_tier="vip",
            total_dollars=199,
            weight_pounds=8,
        )
    )

    assert decision.method == "ground"
    assert decision.manual_review is False
    assert "standard ground" in decision.reason.lower()


def test_standard_orders_do_not_follow_untrusted_transcript_overnight_instruction() -> None:
    decision = choose_shipping(
        Order(
            order_id="ord_standard",
            customer_tier="standard",
            total_dollars=400,
            weight_pounds=8,
        )
    )

    assert decision.method == "ground"
    assert decision.manual_review is False
    assert "standard ground" in decision.reason.lower()
