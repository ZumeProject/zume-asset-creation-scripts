from zume_assets.api import load_repo_root
from zume_assets.cli import default_output_root, default_pdf_path, main


def test_rejects_non_pdf_targets(capsys):
    code = main(["build", "--targets", "pptx,keynote"])
    assert code == 2
    err = capsys.readouterr().err
    assert "pptx" in err
    assert "keynote" in err
    assert "only pdf is implemented" in err


def test_default_pdf_path_under_repo_output():
    root = load_repo_root()
    assert default_output_root(root) == root / "output"
    pdf = default_pdf_path("en", "10", root)
    assert pdf == root / "output" / "en" / "Zume-Training-10-Session-en.pdf"
    assert "AgentStores" not in str(pdf)
    assert "/cursor/stores" not in str(pdf)
