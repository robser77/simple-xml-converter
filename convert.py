import argparse
import csv
import re
import sys
from pathlib import Path

import saxonche
from lxml import etree, isoschematron


def _sanitize_tag(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized or "_"


def csv_to_xml(csv_path: Path, xml_path: Path) -> None:
    root = etree.Element("records")
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            inv = etree.SubElement(root, "record")
            for field, value in row.items():
                etree.SubElement(inv, _sanitize_tag(field)).text = value
    xml_path.write_bytes(
        etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    )
    print(f"Written {xml_path.name} from {csv_path.name} ({len(root)} records)")


def validate_schematron(xml_file: Path, sch_file: Path) -> list[str]:
    try:
        schema_doc = etree.parse(str(sch_file))
    except etree.XMLSyntaxError as e:
        return [f"malformed Schematron {sch_file.name}: {e}"]
    schematron = isoschematron.Schematron(schema_doc, store_report=True)
    try:
        doc = etree.parse(str(xml_file))
    except etree.XMLSyntaxError as e:
        return [f"malformed XML: {e}"]
    if not schematron.validate(doc):
        svrl_ns = "http://purl.oclc.org/dsdl/svrl"
        failures = []
        for failed in schematron.validation_report.findall(f"{{{svrl_ns}}}failed-assert"):
            text_el = failed.find(f"{{{svrl_ns}}}text")
            failures.append(text_el.text.strip() if text_el is not None else "assertion failed")
        return failures
    return []


class _PluginDirResolver(etree.Resolver):
    """Resolve XSD imports by looking them up in the plugin directory."""
    def __init__(self, plugin_dir: Path):
        self._dir = plugin_dir

    def resolve(self, url, id, context):
        name = url.rsplit("/", 1)[-1]
        local = self._dir / name
        if local.exists():
            return self.resolve_filename(str(local), context)
        return None


def load_schema(schema_file: Path | None) -> etree.XMLSchema | None:
    if schema_file is None:
        return None
    if not schema_file.exists():
        print(f"[ERROR] Schema file not found: {schema_file}")
        sys.exit(1)
    parser = etree.XMLParser()
    parser.resolvers.add(_PluginDirResolver(schema_file.parent))
    try:
        return etree.XMLSchema(etree.parse(str(schema_file), parser))
    except etree.XMLSchemaParseError as e:
        print(f"[ERROR] Malformed XSD {schema_file}: {e}")
        sys.exit(1)


def _fmt(label: str, detail: str) -> str:
    pos = len(label)
    tabs = 0
    while pos < 24:
        pos = (pos // 8 + 1) * 8
        tabs += 1
    return label + "\t" * tabs + detail


def validate_xsd(schema: etree.XMLSchema, xml_file: Path, schema_path: Path, label: str = "XSD") -> None:
    doc = etree.parse(str(xml_file))
    if schema.validate(doc):
        print(_fmt(f"  [{label} OK]", str(schema_path)))
    else:
        print(_fmt(f"  [{label} FAIL]", str(schema_path)))
        for err in schema.error_log:
            print(f"             line {err.line}: {err.message}")
        sys.exit(1)


def validate_plugin(plugin_dir: Path) -> None:
    if not plugin_dir.is_dir():
        print(f"[ERROR] Plugin directory not found: {plugin_dir}")
        sys.exit(1)
    missing = [
        name for name in ("transform.xsl",)
        if not (plugin_dir / name).exists()
    ]
    if missing:
        print(f"[ERROR] Missing artifacts in {plugin_dir}:")
        for name in missing:
            print(f"         {name}")
        sys.exit(1)


def run_pipeline(
    plugin_dir: Path,
    input_dir: Path,
    output_dir: Path,
    lookup_file: Path | None,
    schema_file: Path | None,
    check_only: bool = False,
    input_sch: Path | None = None,
    output_sch: Path | None = None,
    input_schema_file: Path | None = None,
) -> None:
    validate_plugin(plugin_dir)

    if not input_dir.is_dir():
        print(f"[ERROR] Input directory not found: {input_dir}")
        sys.exit(1)

    if input_sch is None:
        candidate = plugin_dir / "input_check.sch"
        input_sch = candidate if candidate.exists() else None
    if output_sch is None:
        candidate = plugin_dir / "output_check.sch"
        output_sch = candidate if candidate.exists() else None

    transform_xsl = plugin_dir / "transform.xsl"

    xml_files = sorted(input_dir.glob("*.xml"))
    if not xml_files:
        print(f"No XML files found in {input_dir}")
        return

    input_schema = load_schema(input_schema_file)

    if check_only:
        for xml_file in xml_files:
            print(f"\nChecking: {xml_file.name}")
            if input_schema:
                validate_xsd(input_schema, xml_file, input_schema_file, label="INPUT XSD")
            else:
                print(_fmt("  [INPUT XSD SKIP]", "no input schema provided"))
            if input_sch is not None:
                failures = validate_schematron(xml_file, input_sch)
                if failures:
                    print(_fmt("  [INPUT FAIL]", str(input_sch)))
                    for msg in failures:
                        print(f"               {msg}")
                    sys.exit(1)
                print(_fmt("  [INPUT OK]", str(input_sch)))
            else:
                print(_fmt("  [INPUT SCH SKIP]", "no input_check.sch"))
        return

    schema = load_schema(schema_file)
    output_dir.mkdir(exist_ok=True)

    with saxonche.PySaxonProcessor(license=False) as proc:
        xslt_proc = proc.new_xslt30_processor()
        try:
            executable = xslt_proc.compile_stylesheet(stylesheet_file=str(transform_xsl))
        except saxonche.PySaxonApiError as e:
            print(f"[ERROR] Failed to compile {transform_xsl.name}: {e}")
            sys.exit(1)
        if xslt_proc.exception_occurred:
            print(f"[ERROR] Failed to compile {transform_xsl.name}: {xslt_proc.error_message}")
            sys.exit(1)
        if lookup_file:
            executable.set_parameter(
                "lookupFile",
                proc.make_string_value(lookup_file.resolve().as_uri()),
            )

        for xml_file in xml_files:
            print(f"\nProcessing: {xml_file.name}")

            if input_schema:
                validate_xsd(input_schema, xml_file, input_schema_file, label="INPUT XSD")
            else:
                print(_fmt("  [INPUT XSD SKIP]", "no input schema provided"))

            if input_sch is not None:
                failures = validate_schematron(xml_file, input_sch)
                if failures:
                    print(_fmt("  [INPUT FAIL]", str(input_sch)))
                    for msg in failures:
                        print(f"               {msg}")
                    sys.exit(1)
                print(_fmt("  [INPUT OK]", str(input_sch)))
            else:
                print(_fmt("  [INPUT SCH SKIP]", "no input_check.sch"))

            out_file = output_dir / (xml_file.stem + "_output.xml")
            try:
                executable.transform_to_file(
                    source_file=str(xml_file),
                    output_file=str(out_file),
                )
            except Exception as e:
                print(f"  [TRANSFORM FAIL] {e}")
                sys.exit(1)
            if not out_file.exists():
                print(f"  [TRANSFORM FAIL] no output produced")
                sys.exit(1)
            print(_fmt("  [TRANSFORM]", f"-> {out_file.name}"))

            if schema:
                validate_xsd(schema, out_file, schema_file)
            else:
                print(_fmt("  [OUTPUT XSD SKIP]", "no schema provided"))

            if output_sch is not None:
                failures = validate_schematron(out_file, output_sch)
                if failures:
                    print(_fmt("  [OUTPUT FAIL]", str(output_sch)))
                    for msg in failures:
                        print(f"                {msg}")
                    sys.exit(1)
                print(_fmt("  [OUTPUT OK]", str(output_sch)))
            else:
                print(_fmt("  [OUTPUT SCH SKIP]", "no output_check.sch"))


def resolve_schematron(plugin_dir: Path, arg: str | None, default_name: str) -> Path | None:
    if arg:
        p = Path(arg)
        if not p.exists():
            print(f"[ERROR] Schematron file not found: {p}")
            sys.exit(1)
        return p
    candidate = plugin_dir / default_name
    return candidate if candidate.exists() else None


def resolve_schema(plugin_dir: Path, schema_arg: str | None, subdir: str) -> Path | None:
    if schema_arg:
        p = Path(schema_arg)
        if not p.exists():
            print(f"[ERROR] Schema file not found: {p}")
            sys.exit(1)
        return p
    search_dir = plugin_dir / subdir
    if not search_dir.is_dir():
        return None
    xsd_files = sorted(search_dir.glob("*.xsd"))
    if len(xsd_files) > 1:
        print(f"[WARN] Multiple XSD files found in {search_dir}, using {xsd_files[0].name}")
    if xsd_files:
        return xsd_files[0]
    return None


def resolve_lookup(plugin_dir: Path, lookup_arg: str | None) -> Path | None:
    if lookup_arg:
        p = Path(lookup_arg)
        if not p.exists():
            print(f"[ERROR] Lookup file not found: {p}")
            sys.exit(1)
        return p
    csv_files = sorted(plugin_dir.glob("*.csv"))
    if len(csv_files) > 1:
        print(f"[WARN] Multiple CSV files found in {plugin_dir}, using {csv_files[0].name}")
    if csv_files:
        lookup_file = plugin_dir / "lookup.xml"
        csv_to_xml(csv_files[0], lookup_file)
        return lookup_file
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Generic XML pipeline: input-check-schematron → XSLT transform → output-check-schematron"
    )
    parser.add_argument("--plugin", required=True, metavar="DIR",
                        help="Plugin dir containing input_check.sch, transform.xsl, output_check.sch")
    parser.add_argument("--input", default="documents", metavar="DIR",
                        help="Directory of input XML files (default: documents)")
    parser.add_argument("--output", default="output", metavar="DIR",
                        help="Directory for transformed output XML files (default: output)")
    parser.add_argument("--lookup", metavar="FILE",
                        help="XML lookup file; passed to XSLT as $lookupFile (overrides plugin CSV)")
    parser.add_argument("--input-schema", metavar="FILE",
                        help="XSD entry-point file for input validation (overrides plugin input_schema/*.xsd)")
    parser.add_argument("--output-schema", metavar="FILE",
                        help="XSD entry-point file for output validation (overrides plugin output_schema/*.xsd)")
    parser.add_argument("--input-check", metavar="FILE",
                        help="Schematron file for input validation (overrides plugin input_check.sch)")
    parser.add_argument("--output-check", metavar="FILE",
                        help="Schematron file for output validation (overrides plugin output_check.sch)")
    parser.add_argument("--check-only", action="store_true",
                        help="Validate inputs against input_check.sch only; skip transform and output check")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin)
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    lookup_file = resolve_lookup(plugin_dir, args.lookup)
    input_schema_file = resolve_schema(plugin_dir, args.input_schema, "input_schema")
    schema_file = resolve_schema(plugin_dir, args.output_schema, "output_schema")
    input_sch = resolve_schematron(plugin_dir, args.input_check, "input_check.sch")
    output_sch = resolve_schematron(plugin_dir, args.output_check, "output_check.sch")
    run_pipeline(plugin_dir, input_dir, output_dir, lookup_file, schema_file,
                 check_only=args.check_only, input_sch=input_sch, output_sch=output_sch,
                 input_schema_file=input_schema_file)


if __name__ == "__main__":
    main()
