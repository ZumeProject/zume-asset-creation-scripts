"""Unit tests for localhost → zume.training QR payload rewrite."""

from zume_assets.qr import SITE, rewrite_localhost_qr_url


def test_rewrite_localhost_app_qr():
    src = "http://localhost:3000/app/qr/?l=pus&c=5678"
    assert rewrite_localhost_qr_url(src) == f"{SITE}/app/qr/?l=pus&c=5678"


def test_rewrite_127_activity_qr():
    src = "http://127.0.0.1:3000/app/qr/?l=ky&a=soaps"
    assert rewrite_localhost_qr_url(src) == f"{SITE}/app/qr/?l=ky&a=soaps"


def test_rewrite_leaves_production_alone():
    src = f"{SITE}/app/qr/?l=en&v=1"
    assert rewrite_localhost_qr_url(src) is None


def test_rewrite_empty():
    assert rewrite_localhost_qr_url("") is None
    assert rewrite_localhost_qr_url("   ") is None
