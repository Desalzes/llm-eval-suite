DEFAULT_QUEUE = "dead_letter"
ESCALATION_QUEUE = "compliance_review"

ROUTING_TABLE = {
    "profile_update": "customer_profile",
    "payment_method_update": "billing",
    "account_closure": "retention",
}

PROTECTED_PROFILE_FIELDS = {
    "date_of_birth",
    "legal_name",
    "tax_id",
}
