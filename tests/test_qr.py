from zume_assets.qr import activity_url, checkin_url, video_url


def test_workbook_qr_urls():
    assert checkin_url("5678", locale="en") == "https://zume.training/app/qr/?l=en&c=5678"
    assert video_url("3", locale="es") == "https://zume.training/app/qr/?l=es&v=3"
    assert activity_url("listof100", locale="ar") == (
        "https://zume.training/app/qr/?l=ar&a=listof100"
    )


def test_open_checkin_falls_back_to_page():
    assert checkin_url(None, locale="en") == "https://zume.training/checkin"
    assert checkin_url("", locale="en") == "https://zume.training/checkin"
