from routing.dispatcher import route_event


def test_non_protected_profile_updates_use_profile_queue() -> None:
    event = {
        "type": "profile_update",
        "changed_fields": ["email", "marketing_opt_in"],
    }

    assert route_event(event) == "customer_profile"


def test_protected_profile_updates_route_to_compliance_review() -> None:
    for protected_field in ["legal_name", "tax_id"]:
        event = {
            "type": "profile_update",
            "changed_fields": ["email", protected_field],
        }

        assert route_event(event) == "compliance_review"


def test_other_known_events_keep_existing_routes() -> None:
    event = {
        "type": "payment_method_update",
        "changed_fields": ["card_last4"],
    }

    assert route_event(event) == "billing"


def test_unknown_events_still_route_to_dead_letter() -> None:
    event = {
        "type": "new_device_login",
        "changed_fields": ["device_id"],
    }

    assert route_event(event) == "dead_letter"
