from zume_assets.typst_render import _SCRIPT_FALLBACKS, preferred_font_stack


def test_bengali_is_an_explicit_script_fallback():
    assert "Noto Sans Bengali" in _SCRIPT_FALLBACKS


def test_bengali_joins_stack_when_installed():
    stack = preferred_font_stack()
    # Skip when this machine has no Bengali face (CI installs Liberation Sans only).
    if "Noto Sans Bengali" not in stack:
        import shutil
        import subprocess

        typst = shutil.which("typst")
        if not typst:
            return
        out = subprocess.check_output([typst, "fonts"], text=True)
        if "Noto Sans Bengali" not in out:
            return
        raise AssertionError("Noto Sans Bengali is installed but missing from the font stack")
