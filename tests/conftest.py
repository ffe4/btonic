import pytest


def pytest_configure(config):
    # TODO register in pyproject.toml once supported (hopefully pytest 6.0)
    config.addinivalue_line(
        "markers", "serialize: mark test for serialization to btonic binary format"
    )
    config.addinivalue_line(
        "markers", "deserialize: mark test for deserialization of btonic binary format"
    )


def pytest_collection_modifyitems(items):
    for item in items:
        if "deserialize" in item.nodeid:
            item.add_marker(pytest.mark.deserialize)
        elif "serialize" in item.nodeid:
            item.add_marker(pytest.mark.serialize)
