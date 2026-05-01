# simple-xml-updater

A generic, plugin-driven XML transformation framework. Each plugin encapsulates three pipeline artifacts — an input Schematron check, an XSLT transform, and an output Schematron check — allowing the same runner to handle any XML format without code changes.

## Pipeline

For every input XML file the runner executes the following steps in order:

```
input_check.sch  →  transform.xsl  →  [XSD validation]  →  output_check.sch
```

| Step | Artifact | Required |
|---|---|---|
| Input Schematron | `input_check.sch` | yes |
| XSLT transform | `transform.xsl` | yes |
| XSD validation | provided via `--schema` | no |
| Output Schematron | `output_check.sch` | yes |

The pipeline stops on the first failure in any step.

## Usage

```
python3 convert.py \
  --plugin <plugin-dir> \
  --input  <input-dir> \
  --output <output-dir> \
  [--schema <schema.xsd>] \
  [--lookup <lookup.xml>]
```

### Arguments

| Argument | Description |
|---|---|
| `--plugin DIR` | Plugin directory containing `input_check.sch`, `transform.xsl`, and `output_check.sch` |
| `--input DIR` | Directory of input XML files to process |
| `--output DIR` | Directory where transformed output files are written (created if missing) |
| `--schema FILE` | XSD entry-point file for structural validation of the output; XSD imports are resolved relative to the schema file's directory. If omitted, the XSD step is skipped and reported as `[XSD SKIP]` |
| `--lookup FILE` | XML lookup file passed to the XSLT as `$lookupFile`; overrides a plugin-bundled CSV |

### Lookup data (CSV auto-detection)

If the plugin directory contains a `.csv` file, it is automatically converted to `lookup.xml` in the output directory and passed to the XSLT as `$lookupFile`. The CSV must have a header row; all columns become child elements of each `<record>` under the `<records>` root.

Use `--lookup` to supply a pre-built XML lookup file instead, bypassing CSV conversion.

### Output filenames

Each input file `<name>.xml` produces `<name>_output.xml` in the output directory.

## Plugin structure

```
plugins/
└── my-plugin/
    ├── input_check.sch    # Schematron: validates input before transformation
    ├── transform.xsl      # XSLT 2.0: transforms the input to the target format
    ├── output_check.sch   # Schematron: validates business rules on the output
    └── data.csv           # Optional: lookup data, auto-converted to XML
```

The XSD schema (if used) can live anywhere — it does not need to be inside the plugin directory. All XSD imports are resolved relative to the schema file's own directory.

### XSLT lookup parameter

If a lookup file is provided (via CSV auto-detection or `--lookup`), it is passed to the XSLT as the string parameter `$lookupFile` containing a `file://` URI. Declare it in your stylesheet as:

```xml
<xsl:param name="lookupFile" select="''"/>
<xsl:variable name="lookupDoc"
    select="if ($lookupFile != '') then doc($lookupFile) else ()"/>
```

### Schematron conventions

- `queryBinding="xslt"` (XSLT 1.0 / XPath 1.0) is used by the runner's Schematron engine (`lxml.isoschematron`)
- Declare namespaces with `<ns prefix="..." uri="..."/>`
- Use `<value-of select="..."/>` inside `<assert>` messages to include the actual value in failure output

## Templates

Starter templates for new plugins are in `plugins/templates/`:

- `check.sch` — Schematron with a commented-out namespace declaration and one always-failing assert as a placeholder
- `transform.xsl` — XSLT 2.0 with only the identity transform

## Bundled plugin: fa3-kor

Transforms Polish KSeF FA(3) VAT invoices into KOR (correction) invoices.

**Input requirements** (enforced by `input_check.sch`):
- `RodzajFaktury` must be `VAT`
- `P_14_1W` must be present and zero
- `P_14_1` must be present and non-zero
- Only `P_13_1` is allowed among `P_13_*` fields

**Transform** (`transform.xsl`):
- Sets `RodzajFaktury` to `KOR` and injects correction metadata (`PrzyczynaKorekty`, `TypKorekty`, `DaneFaKorygowanej`) from the lookup
- Appends `_cor` to the invoice number (`P_2`)
- Sets the issue date (`P_1`) to today
- Zeroes all summary amount fields (`P_13_*`, `P_14_*`, `P_15*`)
- Sets `P_14_1W` (tax amount in PLN) from the lookup, matched by invoice number
- Strips all line-item detail from `FaWiersz`, keeping only `NrWierszaFa`

**Lookup CSV columns**: `number`, `date`, `ksefNumber`, `taxAmountPLN`

**Output requirements** (enforced by `output_check.sch`):
- `P_14_1W` must be present and non-zero
- All other amount fields must be zero

**XSD schemas** (pass via `--schema`):
- Entry point: `plugins/fa3-kor/schemat.xsd`
- Supporting schemas in the same directory: `StrukturyDanych_v10-0E.xsd`, `KodyKrajow_v10-0E.xsd`, `ElementarneTypyDanych_v10-0E.xsd`

**Example invocation:**

```bash
python3 convert.py \
  --plugin plugins/fa3-kor \
  --input  path/to/invoices \
  --output path/to/output \
  --schema plugins/fa3-kor/schemat.xsd
```

## Dependencies

- [`saxonche`](https://pypi.org/project/saxonche/) — Saxon-HE Python binding for XSLT 2.0 processing
- [`lxml`](https://pypi.org/project/lxml/) — XML parsing, XSD validation, and ISO Schematron validation
