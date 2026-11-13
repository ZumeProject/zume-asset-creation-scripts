from zume_assets.cli import main


def test_rejects_non_pdf_targets(capsys):
    code = main(["build", "--targets", "pptx,keynote"])
    assert code == 2
    err = capsys.readouterr().err
    assert "pptx" in err
    assert "keynote" in err
    assert "only pdf is implemented" in err
