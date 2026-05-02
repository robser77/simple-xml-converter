from lxml import etree
from convert import csv_to_xml


def test_normal_columns_preserved(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("number,value\n42,100\n")
    out = tmp_path / "out.xml"
    csv_to_xml(csv, out)
    record = etree.parse(str(out)).getroot().find("record")
    assert record.find("number").text == "42"
    assert record.find("value").text == "100"


def test_record_count(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("a,b\n1,2\n3,4\n5,6\n")
    out = tmp_path / "out.xml"
    csv_to_xml(csv, out)
    root = etree.parse(str(out)).getroot()
    assert len(root.findall("record")) == 3


def test_column_with_spaces_sanitized(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("field name,other\nval1,val2\n")
    out = tmp_path / "out.xml"
    csv_to_xml(csv, out)
    record = etree.parse(str(out)).getroot().find("record")
    assert record.find("field_name") is not None
    assert record.find("field name") is None


def test_column_with_leading_digit_sanitized(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("1first,normal\nval1,val2\n")
    out = tmp_path / "out.xml"
    csv_to_xml(csv, out)
    record = etree.parse(str(out)).getroot().find("record")
    assert record.find("_1first") is not None


def test_column_with_special_chars_sanitized(tmp_path):
    csv = tmp_path / "data.csv"
    csv.write_text("field@name!,ok\nval1,val2\n")
    out = tmp_path / "out.xml"
    csv_to_xml(csv, out)
    record = etree.parse(str(out)).getroot().find("record")
    assert record.find("field_name_") is not None
