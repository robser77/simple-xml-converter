import pytest
from pathlib import Path
from convert import run_pipeline


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

IDENTITY_XSL = """\
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>"""

BAD_XSL = """\
<?xml version="1.0"?>
<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="this is not valid xpath!!!">
  </xsl:template>
</xsl:stylesheet>"""

SIMPLE_XML = "<root/>"

SIMPLE_XSD = """\
<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root"/>
</xs:schema>"""


def _make_plugin(
    plugin_dir: Path,
    xsl: str,
    input_sch: str | None = PASS_SCH,
    output_sch: str | None = PASS_SCH,
) -> None:
    plugin_dir.mkdir()
    if input_sch is not None:
        (plugin_dir / "input_check.sch").write_text(input_sch)
    (plugin_dir / "transform.xsl").write_text(xsl)
    if output_sch is not None:
        (plugin_dir / "output_check.sch").write_text(output_sch)


@pytest.mark.integration
def test_pipeline_happy_path(tmp_path):
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(SIMPLE_XML)
    output_dir = tmp_path / "output"

    run_pipeline(plugin, input_dir, output_dir, lookup_file=None, schema_file=None)

    assert (output_dir / "doc_output.xml").exists()


@pytest.mark.integration
def test_pipeline_xslt_compile_failure(tmp_path, capsys):
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, BAD_XSL)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(SIMPLE_XML)

    with pytest.raises(SystemExit):
        run_pipeline(plugin, input_dir, tmp_path / "output", lookup_file=None, schema_file=None)
    assert "[ERROR]" in capsys.readouterr().out


@pytest.mark.integration
def test_pipeline_input_dir_missing(tmp_path, capsys):
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL)
    with pytest.raises(SystemExit):
        run_pipeline(plugin, tmp_path / "nonexistent", tmp_path / "output", None, None)
    assert "[ERROR]" in capsys.readouterr().out


@pytest.mark.integration
def test_pipeline_no_xml_files(tmp_path, capsys):
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    run_pipeline(plugin, input_dir, tmp_path / "output", None, None)
    assert "No XML files" in capsys.readouterr().out


@pytest.mark.integration
def test_pipeline_input_schematron_fails(tmp_path, capsys):
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL, input_sch=FAIL_SCH)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(SIMPLE_XML)
    with pytest.raises(SystemExit):
        run_pipeline(plugin, input_dir, tmp_path / "output", None, None)
    assert "[INPUT FAIL]" in capsys.readouterr().out


@pytest.mark.integration
def test_pipeline_output_schematron_fails(tmp_path, capsys):
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL, output_sch=FAIL_SCH)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(SIMPLE_XML)
    with pytest.raises(SystemExit):
        run_pipeline(plugin, input_dir, tmp_path / "output", None, None)
    assert "[OUTPUT FAIL]" in capsys.readouterr().out


@pytest.mark.integration
def test_pipeline_no_schematron(tmp_path, capsys):
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL, input_sch=None, output_sch=None)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(SIMPLE_XML)
    run_pipeline(plugin, input_dir, tmp_path / "output", lookup_file=None, schema_file=None)
    out = capsys.readouterr().out
    assert "[INPUT SCH SKIP]" in out
    assert "[OUTPUT SCH SKIP]" in out


@pytest.mark.integration
def test_pipeline_xsd_validation_passes(tmp_path, capsys):
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(SIMPLE_XML)
    xsd = tmp_path / "schema.xsd"
    xsd.write_text(SIMPLE_XSD)
    run_pipeline(plugin, input_dir, tmp_path / "output", None, xsd)
    assert "[XSD OK]" in capsys.readouterr().out


@pytest.mark.integration
def test_pipeline_xsd_auto_detected_from_plugin(tmp_path, capsys):
    from convert import resolve_schema
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL)
    out_schema_dir = plugin / "output_schema"
    out_schema_dir.mkdir()
    (out_schema_dir / "schema.xsd").write_text(SIMPLE_XSD)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(SIMPLE_XML)
    schema_file = resolve_schema(plugin, None, "output_schema")
    run_pipeline(plugin, input_dir, tmp_path / "output", lookup_file=None, schema_file=schema_file)
    assert "[XSD OK]" in capsys.readouterr().out


@pytest.mark.integration
def test_pipeline_input_xsd_auto_detected_from_plugin(tmp_path, capsys):
    from convert import resolve_schema
    plugin = tmp_path / "plugin"
    _make_plugin(plugin, IDENTITY_XSL)
    in_schema_dir = plugin / "input_schema"
    in_schema_dir.mkdir()
    (in_schema_dir / "schema.xsd").write_text(SIMPLE_XSD)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc.xml").write_text(SIMPLE_XML)
    input_schema_file = resolve_schema(plugin, None, "input_schema")
    run_pipeline(plugin, input_dir, tmp_path / "output", lookup_file=None, schema_file=None,
                 input_schema_file=input_schema_file)
    assert "[INPUT XSD OK]" in capsys.readouterr().out
