#!/usr/bin/env python
"""
Add missing 'name' field by extracting it from 'memo' field.
"""

import os
import re
import argparse
import logging
from io import BytesIO
from typing import Union

from lxml.etree import SubElement

from ofxtools import OFXClient
from ofxtools.Parser import OFXTree

from utils import getXmlEtree, xpath, pprintXml


log_format = "[%(asctime)s: %(levelname)s/%(name)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


# Maximum length for the NAME field in OFX/QFX transactions
MAX_NAME_LEN = 31

# Transaction matching rules: (compiled_regex, name_source)
#   name_source can be:
#     - int: use match.group(N), truncated to MAX_NAME_LEN
#     - str: use this static string as the name
TRANSACTION_RULES: list[tuple[re.Pattern[str], Union[int, str]]] = [
    (re.compile(r'^(?:Withdrawal\s+from|Debit\s+Card\s+Purchase\s+-|Deposit\s+from|ATM\s+Withdrawal\s+-|Digital\s+Card\s+Purchase\s+-|Miscellaneous)\s+(.*)$', re.I), 1),
    (re.compile(r'^Monthly Interest Paid', re.I), "Capital One"),
    (re.compile(r'^Check\s+#\d+\s+Cashed', re.I), 0),
    (re.compile(r'Check\s+Deposit\s+\(Mobile\)', re.I), 0),
    (re.compile(r'^Prenote', re.I), 0),
    (re.compile(r'360 Checking', re.I), 0),
    (re.compile(r'(Zelle money|Money) (received from|sent to|returned).*', re.I), 0),
    (re.compile(r'Withdrawal to', re.I), 0),
    (re.compile(r'Checkbook Order', re.I), 0),
    # Note: "Deposit from MONEY" and "Deposit from Savings" are already
    # handled by the first rule's "Deposit from" prefix.
]


def main(qfx_file_in: str, qfx_file_out: str, skip_unknown: bool = False) -> None:
    """Parse a QFX file and add NAME elements extracted from MEMO fields."""

    # parse xml
    doc, ns = getXmlEtree(qfx_file_in)
    logger.debug("doc: %s", pprintXml(doc).decode())

    # fix transactions
    for trn in doc.xpath('.//STMTTRN', namespaces=ns):
        logger.info("#" * 80)
        logger.info("trn: %s", pprintXml(trn).decode())
        memo_elt = xpath(trn, 'MEMO', ns)
        memo = memo_elt.text
        logger.info("memo: %s", memo)

        for pattern, name_source in TRANSACTION_RULES:
            match = pattern.search(memo)
            if match:
                if isinstance(name_source, int):
                    name = match.group(name_source)[:MAX_NAME_LEN]
                else:
                    name = name_source
                name_elt = SubElement(trn, "NAME")
                name_elt.text = name
                trn.remove(memo_elt)
                logger.info("name: %s", name)
                break
        else:
            if skip_unknown:
                logger.warning("Skipping unhandled transaction: %s", memo)
            else:
                raise RuntimeError(f"Unhandled transaction: {memo}")

        logger.info("trn: %s", pprintXml(trn).decode())

    # write output file
    v2_message = '<?xml version="1.0" encoding="utf-8"?>\n'
    v2_message += '<?OFX OFXHEADER="200" VERSION="202" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>\n'
    v2_message += pprintXml(doc).decode()
    parser = OFXTree()
    parser.parse(BytesIO(v2_message.encode()))
    ofx = parser.convert()
    client = OFXClient(None)
    v1_message = client.serialize(ofx, version=102, prettyprint=True, close_elements=False).decode()
    with open(qfx_file_out, 'w') as f:
        f.write(v1_message)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qfx_file_in", help="input QFX file")
    parser.add_argument("qfx_file_out", help="output QFX file")
    parser.add_argument("--skip-unknown", action="store_true",
                        help="skip unrecognized transactions instead of crashing")
    args = parser.parse_args()
    main(args.qfx_file_in, args.qfx_file_out, skip_unknown=args.skip_unknown)
