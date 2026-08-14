import subprocess, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from checksums import isin_valid, lei_valid, cusip_valid, sedol_valid


def test_isin_vectors():
    assert isin_valid("US0378331005")
    assert isin_valid("IE00B5BMR087")
    assert not isin_valid("US0378331004")
    assert not isin_valid("US03783310")


def test_lei_vectors():
    assert lei_valid("HWUPKR0MPOU8FGXBT394")
    assert lei_valid("506700GE1G29325QX363")
    assert not lei_valid("HWUPKR0MPOU8FGXBT393")
    assert not lei_valid("00000000000000238096") or True  # syntax passes, mod-97 decides
    assert lei_valid("00000000000000238096") is False


def test_cusip_vectors():
    assert cusip_valid("037833100")
    assert not cusip_valid("037833101")
    assert cusip_valid("US0378331005"[2:11])


def test_sedol_vectors():
    assert sedol_valid("0263494")
    assert not sedol_valid("0263495")
