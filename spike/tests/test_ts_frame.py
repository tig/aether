"""Unit tests for FOME envelope CRC scope — no serial port required."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

SPIKE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPIKE))

from ts_frame import (  # noqa: E402
    FrameError,
    crc32_ieee,
    frame_request,
    och_get_payload,
    parse_response,
    response_success_burn,
    response_success_identity,
)

GOLD = json.loads((SPIKE / "goldens" / "fome_envelope.json").read_text(encoding="utf-8"))


def _hx(name: str) -> bytes:
    return bytes.fromhex(GOLD["frames"][name])


def test_s_request_matches_golden():
    assert frame_request(b"S") == _hx("s_request")


def test_s_response_parse_signature():
    r = parse_response(_hx("s_response"))
    assert response_success_identity(r.flag)
    assert r.payload.startswith(b"rusEFI (FOME)")
    sig = r.payload.split(b"\x00", 1)[0].decode("ascii")
    assert sig == GOLD["signature"]


def test_s_response_bad_crc_rejected():
    with pytest.raises(FrameError, match="CRC"):
        parse_response(_hx("s_response_bad_crc"))


def test_request_crc_is_payload_only_not_size_inclusive():
    payload = b"S"
    framed = frame_request(payload)
    # size-inclusive CRC would differ
    size_incl = struct.pack(">H", 1) + payload
    bad = struct.pack(">H", 1) + payload + struct.pack(">I", crc32_ieee(size_incl))
    assert framed != bad
    assert framed == _hx("s_request")


def test_o_request_golden():
    assert frame_request(och_get_payload(0, 20)) == _hx("o_request_off0_cnt20")


def test_o_response_parse():
    r = parse_response(_hx("o_response_20b"))
    assert r.flag == 0
    assert len(r.payload) == 20


def test_burn_flag_policy():
    assert response_success_burn(0x04)
    assert response_success_burn(0x00)
    assert not response_success_burn(0x82)
