from rae_core.version import __author__, __email__, __license__, __version__


def test_version_info():
    assert isinstance(__version__, str)
    assert isinstance(__author__, str)
    assert isinstance(__email__, str)
    assert isinstance(__license__, str)
    assert "0.4" in __version__
