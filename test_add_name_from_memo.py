#!/usr/bin/env python
"""Tests for add_name_from_memo and utils modules."""

import os
import re
import tempfile

import pytest
from lxml.etree import SubElement, tostring

from add_name_from_memo import MAX_NAME_LEN, TRANSACTION_RULES, main
from utils import getXmlEtree, getNamespacePrefixDict, xpath, pprintXml


SAMPLE_QFX = os.path.join(
    os.path.dirname(__file__),
    "bad_format_capital_one",
    "2019-10-04_transaction_download.qfx",
)


def _make_qfx(memo_texts: list[str]) -> str:
    """Build a minimal QFX/XML string with STMTTRN entries for given memos."""
    trns = ""
    for i, memo in enumerate(memo_texts):
        trns += f"""
          <STMTTRN>
            <TRNTYPE>DEBIT</TRNTYPE>
            <DTPOSTED>20191004000000.000</DTPOSTED>
            <TRNAMT>-10.00</TRNAMT>
            <FITID>20191004{i:04d}</FITID>
            <MEMO>{memo}</MEMO>
          </STMTTRN>"""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<?OFX OFXHEADER="200" VERSION="202" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>
<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
      <DTSERVER>20191004133818.472</DTSERVER>
      <LANGUAGE>ENG</LANGUAGE>
      <FI><ORG>Capital One Bank</ORG><FID>1001</FID></FI>
    </SONRS>
  </SIGNONMSGSRSV1>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <TRNUID>0</TRNUID>
      <STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
      <STMTRS>
        <CURDEF>USD</CURDEF>
        <BANKACCTFROM>
          <BANKID>031176110</BANKID>
          <ACCTID>1684</ACCTID>
          <ACCTTYPE>CHECKING</ACCTTYPE>
        </BANKACCTFROM>
        <BANKTRANLIST>
          <DTSTART>20190919000000.000</DTSTART>
          <DTEND>20191004000000.000</DTEND>
          {trns}
        </BANKTRANLIST>
        <LEDGERBAL>
          <BALAMT>1000.00</BALAMT>
          <DTASOF>20191004133818.472</DTASOF>
        </LEDGERBAL>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>"""


def _run_main_with_memos(memos: list[str], skip_unknown: bool = False) -> str:
    """Write a QFX with the given memos, run main(), return output content."""
    qfx_content = _make_qfx(memos)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.qfx', delete=False) as fin:
        fin.write(qfx_content)
        in_path = fin.name
    out_path = in_path + '.out'
    try:
        main(in_path, out_path, skip_unknown=skip_unknown)
        with open(out_path) as f:
            return f.read()
    finally:
        os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


# ---------------------------------------------------------------------------
# utils.py tests
# ---------------------------------------------------------------------------

class TestGetXmlEtree:
    def test_parse_from_file(self):
        doc, ns = getXmlEtree(SAMPLE_QFX)
        assert doc is not None
        assert doc.tag == 'OFX'

    def test_parse_from_string(self):
        xml_str = '<?xml version="1.0"?><root><child>text</child></root>'
        doc, ns = getXmlEtree(xml_str)
        assert doc.tag == 'root'
        assert doc.find('child').text == 'text'

    def test_namespace_extraction(self):
        xml_str = '<?xml version="1.0"?><root xmlns:foo="http://example.com"><child/></root>'
        doc, ns = getXmlEtree(xml_str)
        assert 'foo' in ns
        assert ns['foo'] == 'http://example.com'


class TestGetNamespacePrefixDict:
    def test_no_namespaces(self):
        assert getNamespacePrefixDict('<root/>') == {}

    def test_prefixed_namespace(self):
        result = getNamespacePrefixDict('<root xmlns:ns1="http://example.com"/>')
        assert result == {'ns1': 'http://example.com'}

    def test_default_namespace(self):
        result = getNamespacePrefixDict('<root xmlns="http://default.com"/>')
        assert result == {'_': 'http://default.com'}

    def test_multiple_namespaces(self):
        xml = '<root xmlns:a="http://a.com" xmlns:b="http://b.com"/>'
        result = getNamespacePrefixDict(xml)
        assert result == {'a': 'http://a.com', 'b': 'http://b.com'}


class TestXpath:
    def test_found(self):
        doc, ns = getXmlEtree(SAMPLE_QFX)
        result = xpath(doc, './/BANKID', ns)
        assert result is not None
        assert result.text == '031176110'

    def test_not_found_returns_default(self):
        doc, ns = getXmlEtree(SAMPLE_QFX)
        result = xpath(doc, './/NONEXISTENT', ns, default='fallback')
        assert result == 'fallback'

    def test_not_found_returns_none(self):
        doc, ns = getXmlEtree(SAMPLE_QFX)
        result = xpath(doc, './/NONEXISTENT', ns)
        assert result is None


class TestPprintXml:
    def test_returns_bytes(self):
        doc, _ = getXmlEtree('<?xml version="1.0"?><root/>')
        result = pprintXml(doc)
        assert isinstance(result, bytes)
        assert b'<root/>' in result


# ---------------------------------------------------------------------------
# Transaction pattern matching tests
# ---------------------------------------------------------------------------

class TestTransactionRules:
    """Test each transaction pattern matches expected memo formats."""

    @pytest.mark.parametrize("memo,expected_name", [
        ("Withdrawal from CHASE CREDIT CRD EPAY", "CHASE CREDIT CRD EPAY"),
        ("Debit Card Purchase - GEICO AUTO 800 841 3000 DC", "GEICO AUTO 800 841 3000 DC"),
        ("Deposit from CALTECH/JPL SALARY", "CALTECH/JPL SALARY"),
        ("ATM Withdrawal - CARDTRONICS C2SJ VSD38839 CARSON, CA", "CARDTRONICS C2SJ VSD38839 CAR"),
        ("Digital Card Purchase - AMAZON.COM", "AMAZON.COM"),
        ("Miscellaneous SOMETHING HERE", "SOMETHING HERE"),
    ])
    def test_trn_pattern_extracts_group1(self, memo, expected_name):
        """TRN_RE captures the payee name (group 1), truncated to 31 chars."""
        output = _run_main_with_memos([memo])
        assert expected_name[:MAX_NAME_LEN] in output

    def test_monthly_interest(self):
        output = _run_main_with_memos(["Monthly Interest Paid"])
        assert "Capital One" in output

    def test_check_cashed(self):
        output = _run_main_with_memos(["Check #477 Cashed"])
        assert "Check #477 Cashed" in output

    def test_mobile_deposit(self):
        output = _run_main_with_memos(["Check Deposit (Mobile)"])
        assert "Check Deposit (Mobile)" in output

    def test_prenote(self):
        output = _run_main_with_memos(["Prenote"])
        assert "Prenote" in output

    def test_360_checking(self):
        output = _run_main_with_memos(["360 Checking"])
        assert "360 Checking" in output

    @pytest.mark.parametrize("memo,expected", [
        ("Zelle money received from JOHN DOE", "Zelle money received from JOHN"),
        ("Zelle money sent to JANE DOE", "Zelle money sent to JANE DOE"),
        ("Money received from JOHN DOE", "Money received from JOHN DOE"),
        ("Money sent to JANE DOE", "Money sent to JANE DOE"),
        ("Money returned from JOHN DOE", "Money returned from JOHN DOE"),
    ])
    def test_zelle(self, memo, expected):
        output = _run_main_with_memos([memo])
        assert expected in output

    def test_withdrawal_to(self):
        output = _run_main_with_memos(["Withdrawal to Savings"])
        assert "Withdrawal to" in output

    def test_checkbook_order(self):
        output = _run_main_with_memos(["Checkbook Order"])
        assert "Checkbook Order" in output

    def test_deposit_from_money(self):
        """'Deposit from MONEY' matches TRN_RE, extracting 'MONEY' as the name."""
        output = _run_main_with_memos(["Deposit from MONEY"])
        assert "MONEY" in output

    def test_deposit_from_savings(self):
        """'Deposit from Savings' matches TRN_RE, extracting 'Savings' as the name."""
        output = _run_main_with_memos(["Deposit from Savings"])
        assert "Savings" in output


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_unhandled_transaction_raises(self):
        with pytest.raises(RuntimeError, match="Unhandled transaction"):
            _run_main_with_memos(["COMPLETELY UNKNOWN MEMO TEXT"])

    def test_unhandled_transaction_includes_memo(self):
        with pytest.raises(RuntimeError, match="COMPLETELY UNKNOWN MEMO TEXT"):
            _run_main_with_memos(["COMPLETELY UNKNOWN MEMO TEXT"])

    def test_skip_unknown_does_not_raise(self):
        output = _run_main_with_memos(
            ["COMPLETELY UNKNOWN MEMO TEXT"],
            skip_unknown=True,
        )
        assert output  # should produce output without crashing


# ---------------------------------------------------------------------------
# End-to-end test with sample file
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_sample_qfx_file(self):
        """Process the actual sample QFX file and verify output is valid."""
        with tempfile.NamedTemporaryFile(suffix='.qfx', delete=False) as f:
            out_path = f.name
        try:
            main(SAMPLE_QFX, out_path)
            with open(out_path) as f:
                output = f.read()
            # Should contain NAME elements
            assert "NAME" in output
            # Should not contain MEMO elements (they get replaced)
            assert "MEMO" not in output
            # Spot-check a few expected names
            assert "CALTECH/JPL SALARY" in output
            assert "Capital One" in output
            assert "Check #477 Cashed" in output
        finally:
            os.unlink(out_path)


# ---------------------------------------------------------------------------
# Name length truncation test
# ---------------------------------------------------------------------------

class TestNameTruncation:
    def test_name_truncated_to_max_len(self):
        long_payee = "A" * 50
        memo = f"Withdrawal from {long_payee}"
        output = _run_main_with_memos([memo])
        # The extracted name (group 1) should be truncated
        assert long_payee[:MAX_NAME_LEN] in output
        assert long_payee[:MAX_NAME_LEN + 1] not in output


# ---------------------------------------------------------------------------
# Multiple transactions test
# ---------------------------------------------------------------------------

class TestMultipleTransactions:
    def test_processes_all_transactions(self):
        memos = [
            "Withdrawal from CHASE CREDIT CRD EPAY",
            "Monthly Interest Paid",
            "Check #100 Cashed",
        ]
        output = _run_main_with_memos(memos)
        assert "CHASE CREDIT CRD EPAY" in output
        assert "Capital One" in output
        assert "Check #100 Cashed" in output
