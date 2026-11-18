import pytest

from catalog.models import stock_status


@pytest.mark.parametrize(
    ("stock", "threshold", "expected"),
    [
        (0, 5, "Out of Stock"),
        (1, 5, "Low Stock — act soon"),
        (5, 5, "Low Stock — act soon"),
        (6, 5, "In Stock"),
        (0, 0, "Out of Stock"),
        (1, 0, "In Stock"),
    ],
)
def test_stock_status_boundaries(stock, threshold, expected):
    assert stock_status(stock, threshold).label == expected


def test_stock_status_has_stable_identifiers_alongside_labels():
    assert stock_status(0, 5).value == "out_of_stock"
    assert stock_status(3, 5).value == "low_stock"
    assert stock_status(9, 5).value == "in_stock"
