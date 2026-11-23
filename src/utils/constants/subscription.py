from typing import Tuple

SUBSCRIPTION_STATUS: Tuple[Tuple[bool, str], ...] = (
    (True, "5427009714745517609"),
    (False, "5465665476971471368"),
)

RELOAD_ICON: str = "5264727218734524899"

CHECK_SUBSCRIPTIONS_CALLBACK: str = "check_subscriptions"

# How long (seconds) a successful subscription check is trusted before re-checking.
SUBSCRIPTION_OK_TTL: int = 60
