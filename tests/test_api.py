from api.main import app


def test_api_registers_operational_routes():
    paths = {route.path for route in app.routes}
    assert "/optimization/solve" in paths
    assert "/dashboard/health" in paths
    assert "/dashboard/state" in paths
    assert "/forecast/health" in paths
    assert "/forecast/next-24h" in paths
    assert "/what-if/health" in paths
