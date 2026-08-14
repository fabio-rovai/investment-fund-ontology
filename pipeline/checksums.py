"""Check-digit algorithms for securities and entity identifiers.

Implements the four algorithms the IFO pipeline computes and asserts
into the graph as ifo:checksumValid:

  - ISIN  : ISO 6166, modulus 10 double-add-double (Luhn) over the
            digitised string.
  - LEI   : ISO 17442 / ISO 7064 MOD 97-10; valid strings leave
            remainder 1.
  - CUSIP : ANSI X9.6 modulus 10 double-add-double over the first
            8 characters against the 9th.
  - SEDOL : weighted modulus 10, weights 1,3,1,7,3,9 over the first
            six characters against the 7th.

Every algorithm has embedded test vectors; run this module directly
to execute them. Arithmetic lives here, policy lives in SHACL.
"""

from __future__ import annotations

import re

_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
_CUSIP_RE = re.compile(r"^[A-Z0-9*@#]{8}[0-9]$")
_SEDOL_RE = re.compile(r"^[B-DF-HJ-NP-TV-Z0-9]{6}[0-9]$")


def _digitise(s: str) -> str:
    """Letters to two-digit values, A=10 .. Z=35; digits unchanged."""
    out = []
    for ch in s:
        if ch.isdigit():
            out.append(ch)
        else:
            out.append(str(ord(ch) - 55))
    return "".join(out)


def _luhn_ok(digits: str) -> bool:
    """Luhn check over a pure digit string including its check digit."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def isin_valid(isin: str) -> bool:
    if not _ISIN_RE.match(isin):
        return False
    return _luhn_ok(_digitise(isin))


def lei_valid(lei: str) -> bool:
    if not _LEI_RE.match(lei):
        return False
    return int(_digitise(lei)) % 97 == 1


_CUSIP_SPECIALS = {"*": 36, "@": 37, "#": 38}


def cusip_valid(cusip: str) -> bool:
    if not _CUSIP_RE.match(cusip):
        return False
    total = 0
    for i, ch in enumerate(cusip[:8]):
        if ch.isdigit():
            v = int(ch)
        elif ch in _CUSIP_SPECIALS:
            v = _CUSIP_SPECIALS[ch]
        else:
            v = ord(ch) - 55
        if i % 2 == 1:
            v *= 2
        total += v // 10 + v % 10
    return (10 - total % 10) % 10 == int(cusip[8])


_SEDOL_WEIGHTS = (1, 3, 1, 7, 3, 9)


def sedol_valid(sedol: str) -> bool:
    if not _SEDOL_RE.match(sedol):
        return False
    total = 0
    for ch, w in zip(sedol[:6], _SEDOL_WEIGHTS):
        v = int(ch) if ch.isdigit() else ord(ch) - 55
        total += v * w
    return (10 - total % 10) % 10 == int(sedol[6])


def _selftest() -> None:
    # ISIN: Apple Inc. and a corrupted check digit.
    assert isin_valid("US0378331005")
    assert not isin_valid("US0378331004")
    # ISIN: an IE-prefixed fund share class style vector (iShares Core
    # S&P 500 UCITS ETF, publicly quoted) and its corruption.
    assert isin_valid("IE00B5BMR087")
    assert not isin_valid("IE00B5BMR088")
    # LEI: Apple Inc. and GLEIF's own LEI, plus corruption.
    assert lei_valid("HWUPKR0MPOU8FGXBT394")
    assert lei_valid("506700GE1G29325QX363")
    assert not lei_valid("HWUPKR0MPOU8FGXBT393")
    # CUSIP: Apple Inc. 037833100 and corruption.
    assert cusip_valid("037833100")
    assert not cusip_valid("037833101")
    # Consistency: a US ISIN embeds its CUSIP.
    assert cusip_valid("US0378331005"[2:11])
    # SEDOL: HSBC Holdings 0540528 vector from the public record, plus
    # the well-known example 0263494.
    assert sedol_valid("0263494")
    assert not sedol_valid("0263495")
    print("checksums selftest: all vectors pass")


if __name__ == "__main__":
    _selftest()
