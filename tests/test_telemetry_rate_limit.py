from src.api.routes.skills import receive_telemetry
from src.core.rate_limit import limiter


def test_telemetry_endpoint_has_rate_limit():
    route_limits = limiter._route_limits[receive_telemetry.__module__ + "." + receive_telemetry.__name__]

    assert len(route_limits) == 1
    assert str(route_limits[0].limit) == "10 per 1 minute"
