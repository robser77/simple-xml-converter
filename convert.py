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


def validate_xsd(schema: etree.XMLSchema, out_file: Path) -> None:
    doc = etree.parse(str(out_file))
    if schema.validate(doc):
        print(f"  [XSD OK]")
    else:
        print(f"  [XSD FAIL]")
        for err in schema.error_log:
            print(f"             line {err.line}: {err.message}")
        sys.exit(1)


def validate_plugin(plugin_dir: Path) -> None:
    if not plugin_dir.is_dir():
        print(f"[ERROR] Plugin directory not found: {plugin_dir}")
        sys.exit(1)
    missing = [
        name for name in ("input_check.sch", "transform.xsl", "output_check.sch")
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
) -> None:
    validate_plugin(plugin_dir)

    if not input_dir.is_dir():
        print(f"[ERROR] Input directory not found: {input_dir}")
        sys.exit(1)

    input_sch = plugin_dir / "input_check.sch"
    transform_xsl = plugin_dir / "transform.xsl"
    output_sch = plugin_dir / "output_check.sch"

    xml_files = sorted(input_dir.glob("*.xml"))
    if not xml_files:
        print(f"No XML files found in {input_dir}")
        return

    if check_only:
        for xml_file in xml_files:
            print(f"\nChecking: {xml_file.name}")
            failures = validate_schematron(xml_file, input_sch)
            if failures:
                print(f"  [INPUT FAIL]")
                for msg in failures:
                    print(f"               {msg}")
                sys.exit(1)
            print(f"  [INPUT OK]")
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

            failures = validate_schematron(xml_file, input_sch)
            if failures:
                print(f"  [INPUT FAIL]")
                for msg in failures:
                    print(f"               {msg}")
                sys.exit(1)
            print(f"  [INPUT OK]")

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
            print(f"  [TRANSFORM] -> {out_file.name}")

            if schema:
                validate_xsd(schema, out_file)
            else:
                print(f"  [XSD SKIP]  no schema provided")

            failures = validate_schematron(out_file, output_sch)
            if failures:
                print(f"  [OUTPUT FAIL]")
                for msg in failures:
                    print(f"                {msg}")
                sys.exit(1)
            print(f"  [OUTPUT OK]")


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
    parser.add_argument("--schema", metavar="FILE",
                        help="XSD entry-point file for output validation; imports resolved from its directory")
    parser.add_argument("--check-only", action="store_true",
                        help="Validate inputs against input_check.sch only; skip transform and output check")
    args = parser.parse_args()

    plugin_dir = Path(args.plugin)
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    lookup_file = resolve_lookup(plugin_dir, args.lookup)
    schema_file = Path(args.schema) if args.schema else None
    run_pipeline(plugin_dir, input_dir, output_dir, lookup_file, schema_file, check_only=args.check_only)


if __name__ == "__main__":
    main()
