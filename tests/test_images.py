from zume_assets.images import (
    placeholder_to_image_key,
    resolve_image_key,
    resolve_paragraph_items,
)


def test_placeholder_to_image_key():
    assert placeholder_to_image_key("pace1_image") == "image_pace1"
    assert placeholder_to_image_key("image_fourfields") == "image_fourfields"
    assert placeholder_to_image_key("") is None


def test_resolve_image_key_from_manifest():
    assert resolve_image_key(content_key="fourfields_example") == "image_fourfields"
    assert resolve_image_key(activity_key="genmapping") == "image_genmap"
    assert resolve_image_key(placeholder="pace2_image") == "image_pace2"


def test_resolve_paragraph_items_downloads(tmp_path, monkeypatch):
    images = {
        "image_pace1": {
            "url": "https://example.test/pace1.png",
            "alt": "Pace 1",
        }
    }

    def fake_urlopen(req, timeout=90):
        class Resp:
            def read(self):
                return b"PNGDATA"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return Resp()

    monkeypatch.setattr("zume_assets.images.urlopen", fake_urlopen)
    items = resolve_paragraph_items(
        ["Intro text.", "{{ pace1_image }}", "{{ missing_image }}"],
        images,
        tmp_path,
    )
    assert items[0] == "Intro text."
    assert items[1]["image"].startswith("images/image_pace1")
    assert items[1]["alt"] == "Pace 1"
    assert len(items) == 2
    assert (tmp_path / items[1]["image"]).read_bytes() == b"PNGDATA"
