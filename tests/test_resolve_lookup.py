import pytest
from convert import resolve_lookup


def test_missing_file_exits(tmp_path, capsys):
    with pytest.raises(SystemExit):
        resolve_lookup(tmp_path, str(tmp_path / "nonexistent.xml"))
    assert "[ERROR]" in capsys.readouterr().out


def test_valid_file_returned(tmp_path):
    lookup = tmp_path / "my_lookup.xml"
    lookup.write_text("<records/>")
    result = resolve_lookup(tmp_path, str(lookup))
    assert result == lookup


def test_csv_auto_detected(tmp_path):
    (tmp_path / "data.csv").write_text("number,value\n1,100\n")
    result = resolve_lookup(tmp_path, None)
    assert result == tmp_path / "lookup.xml"
    assert result.exists()


def test_multiple_csvs_warn(tmp_path, capsys):
    (tmp_path / "a.csv").write_text("x\n1\n")
    (tmp_path / "b.csv").write_text("x\n2\n")
    result = resolve_lookup(tmp_path, None)
    assert "[WARN]" in capsys.readouterr().out
    assert result == tmp_path / "lookup.xml"


def test_no_csv_returns_none(tmp_path):
    assert resolve_lookup(tmp_path, None) is None
