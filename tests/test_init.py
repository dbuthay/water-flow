"""Smoke tests for the irrigation_monitor integration."""
from custom_components.irrigation_monitor.const import DOMAIN


def test_domain_constant():
    """Verify the DOMAIN constant is correctly set."""
    assert DOMAIN == "irrigation_monitor"
