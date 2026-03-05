import kissbt


def test_top_level_exports():
    assert hasattr(kissbt, "Analyzer")
    assert hasattr(kissbt, "BacktestResult")
    assert hasattr(kissbt, "Broker")
    assert hasattr(kissbt, "ClosedPosition")
    assert hasattr(kissbt, "Engine")
    assert hasattr(kissbt, "OpenPosition")
    assert hasattr(kissbt, "Order")
    assert hasattr(kissbt, "OrderType")
    assert hasattr(kissbt, "Strategy")
    assert hasattr(kissbt, "__version__")
