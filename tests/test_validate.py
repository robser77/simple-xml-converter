import pytest
from lxml import etree
from convert import validate_schematron, load_schema, validate_xsd, validate_plugin, resolve_schema, resolve_schematron


PASS_SCH = """\
<?xml version="1.0"?>
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt">
  <sch:pattern>
    <sch:rule context="/">
      <sch:assert test="true()">always passes</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>"""

FAIL_SCH = """\
<?xml version="1.0"?>
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt">
  <sch:pattern>
    <sch:rule context="/">
      <sch:assert test="false()">always fails</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>"""

SIMPLE_XML = "<root/>"

SIMPLE_XSD = """\
<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root"/>
</xs:schema>"""

MALFORMED_XSD = """\
<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:badElement/>
</xs:schema>"""


# --- validate_schematron ---

def test_schematron_passes(tmp_path):
    xml = tmp_path / "doc.xml"
    sch = tmp_path / "check.sch"
    xml.write_text(SIMPLE_XML)
    sch.write_text(PASS_SCH)
    assert validate_schematron(xml, sch) == []

def test_schematron_fails(tmp_path):
    xml = tmp_path / "doc.xml"
    sch = tmp_path / "check.sch"
    xml.write_text(SIMPLE_XML)
    sch.write_text(FAIL_SCH)
    failures = validate_schematron(xml, sch)
    assert len(failures) == 1
    assert "always fails" in failures[0]

def test_schematron_malformed_sch(tmp_path):
    xml = tmp_path / "doc.xml"
    sch = tmp_path / "check.sch"
    xml.write_text(SIMPLE_XML)
    sch.write_text("not valid xml<<<")
    failures = validate_schematron(xml, sch)
    assert len(failures) == 1
    assert "malformed Schematron" in failures[0]

def test_schematron_malformed_xml(tmp_path):
    xml = tmp_path / "doc.xml"
    sch = tmp_path / "check.sch"
    xml.write_text("not valid xml<<<")
    sch.write_text(PASS_SCH)
    failures = validate_schematron(xml, sch)
    assert len(failures) == 1
    assert "malformed XML" in failures[0]


# --- load_schema ---

def test_load_schema_none():
    assert load_schema(None) is None

def test_load_schema_missing_file(tmp_path, capsys):
    with pytest.raises(SystemExit):
        load_schema(tmp_path / "nonexistent.xsd")
    assert "[ERROR]" in capsys.readouterr().out

def test_load_schema_valid(tmp_path):
    xsd = tmp_path / "schema.xsd"
    xsd.write_text(SIMPLE_XSD)
    assert isinstance(load_schema(xsd), etree.XMLSchema)

def test_load_schema_malformed(tmp_path, capsys):
    xsd = tmp_path / "schema.xsd"
    xsd.write_text(MALFORMED_XSD)
    with pytest.raises(SystemExit):
        load_schema(xsd)
    assert "[ERROR]" in capsys.readouterr().out


# --- validate_xsd ---

def test_validate_xsd_passes(tmp_path, capsys):
    xsd = tmp_path / "schema.xsd"
    xsd.write_text(SIMPLE_XSD)
    schema = load_schema(xsd)
    doc = tmp_path / "doc.xml"
    doc.write_text(SIMPLE_XML)
    validate_xsd(schema, doc, xsd)
    out = capsys.readouterr().out
    assert "[XSD OK]" in out
    assert "schema.xsd" in out

def test_validate_xsd_fails(tmp_path, capsys):
    xsd = tmp_path / "schema.xsd"
    xsd.write_text(SIMPLE_XSD)
    schema = load_schema(xsd)
    doc = tmp_path / "doc.xml"
    doc.write_text("<wrong/>")
    with pytest.raises(SystemExit):
        validate_xsd(schema, doc, xsd)
    out = capsys.readouterr().out
    assert "[XSD FAIL]" in out
    assert "schema.xsd" in out


# --- validate_plugin ---

def test_validate_plugin_dir_missing(tmp_path, capsys):
    with pytest.raises(SystemExit):
        validate_plugin(tmp_path / "nonexistent")
    assert "[ERROR]" in capsys.readouterr().out

def test_validate_plugin_artifacts_missing(tmp_path, capsys):
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    with pytest.raises(SystemExit):
        validate_plugin(plugin)
    out = capsys.readouterr().out
    assert "[ERROR]" in out
    assert "transform.xsl" in out

def test_validate_plugin_sch_files_optional(tmp_path):
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "transform.xsl").write_text("")
    validate_plugin(plugin)  # should not raise without .sch files

def test_validate_plugin_all_present(tmp_path):
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    for name in ("input_check.sch", "transform.xsl", "output_check.sch"):
        (plugin / name).write_text("")
    validate_plugin(plugin)  # should not raise


# --- resolve_schema ---

def test_resolve_schema_explicit_arg(tmp_path):
    xsd = tmp_path / "schema.xsd"
    xsd.write_text(SIMPLE_XSD)
    assert resolve_schema(tmp_path, str(xsd), "output_schema") == xsd

def test_resolve_schema_explicit_arg_missing(tmp_path, capsys):
    with pytest.raises(SystemExit):
        resolve_schema(tmp_path, str(tmp_path / "nonexistent.xsd"), "output_schema")
    assert "[ERROR]" in capsys.readouterr().out

def test_resolve_schema_auto_detect(tmp_path):
    subdir = tmp_path / "output_schema"
    subdir.mkdir()
    xsd = subdir / "schema.xsd"
    xsd.write_text(SIMPLE_XSD)
    assert resolve_schema(tmp_path, None, "output_schema") == xsd

def test_resolve_schema_no_xsd(tmp_path):
    assert resolve_schema(tmp_path, None, "output_schema") is None

def test_resolve_schema_no_subdir(tmp_path):
    assert resolve_schema(tmp_path, None, "output_schema") is None

def test_resolve_schema_multiple_xsd_warns(tmp_path, capsys):
    subdir = tmp_path / "output_schema"
    subdir.mkdir()
    for name in ("a.xsd", "b.xsd"):
        (subdir / name).write_text(SIMPLE_XSD)
    result = resolve_schema(tmp_path, None, "output_schema")
    assert result == subdir / "a.xsd"
    assert "[WARN]" in capsys.readouterr().out

def test_resolve_schema_input_subdir(tmp_path):
    subdir = tmp_path / "input_schema"
    subdir.mkdir()
    xsd = subdir / "schema.xsd"
    xsd.write_text(SIMPLE_XSD)
    assert resolve_schema(tmp_path, None, "input_schema") == xsd


# --- resolve_schematron ---

def test_resolve_schematron_explicit_arg(tmp_path):
    sch = tmp_path / "custom.sch"
    sch.write_text(PASS_SCH)
    assert resolve_schematron(tmp_path, str(sch), "input_check.sch") == sch

def test_resolve_schematron_explicit_arg_missing(tmp_path, capsys):
    with pytest.raises(SystemExit):
        resolve_schematron(tmp_path, str(tmp_path / "nonexistent.sch"), "input_check.sch")
    assert "[ERROR]" in capsys.readouterr().out

def test_resolve_schematron_auto_detect(tmp_path):
    sch = tmp_path / "input_check.sch"
    sch.write_text(PASS_SCH)
    assert resolve_schematron(tmp_path, None, "input_check.sch") == sch

def test_resolve_schematron_no_file(tmp_path):
    assert resolve_schematron(tmp_path, None, "input_check.sch") is None

def test_resolve_schematron_explicit_overrides_plugin(tmp_path):
    plugin_sch = tmp_path / "input_check.sch"
    plugin_sch.write_text(PASS_SCH)
    custom_sch = tmp_path / "other.sch"
    custom_sch.write_text(PASS_SCH)
    assert resolve_schematron(tmp_path, str(custom_sch), "input_check.sch") == custom_sch
