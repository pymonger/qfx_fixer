#!/usr/bin/env python
"""
Add missing 'name' field by extracting it from 'memo' field.
"""

import os
import sys
import re
import traceback
import argparse
import json
import logging
from io import BytesIO
from lxml.etree import SubElement

from ofxtools import OFXClient
from ofxtools.Parser import OFXTree

from utils import getXmlEtree, xpath, pprintXml


log_format = "[%(asctime)s: %(levelname)s/%(name)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


BASE_PATH = os.path.dirname(__file__)


# compiled regexes
INT_RE = re.compile(r'^Monthly Interest Paid', re.I)
TRN_RE = re.compile(r'^(?:Withdrawal\s+from|Debit\s+Card\s+Purchase\s+-|Deposit\s+from|ATM\s+Withdrawal\s+-)\s+(.*)$', re.I)
CHK_RE = re.compile(r'^Check\s+#\d+\s+Cashed', re.I)
PRENOTE_RE = re.compile(r'^Prenote', re.I)


def main(qfx_file_in, qfx_file_out):
    """Main."""

    # parse xml
    doc, ns = getXmlEtree(qfx_file_in)
    logger.debug("doc: {}".format(pprintXml(doc).decode()))
    logger.debug("ns: {}".format(json.dumps(ns, indent=2)))

    # fix transactions
    for trn in doc.xpath('.//STMTTRN', namespaces=ns):
        logger.info("#" * 80)
        logger.info("trn: {}".format(pprintXml(trn).decode()))
        memo_elt = xpath(trn, 'MEMO', ns)
        memo = memo_elt.text[:32]
        logger.info("memo: {}".format(memo))
        logger.info("type memo: {}".format(type(memo)))

        # extract name
        match = TRN_RE.search(memo)
        if match:
            name = match.group(1)
            logger.info("name: {}".format(name))
            name_elt = SubElement(trn, "NAME")
            name_elt.text = name
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # monthly interest paid?
        match = INT_RE.search(memo)
        if match:
            name_elt = SubElement(trn, "NAME")
            name_elt.text = "Capital One"
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # check
        match = CHK_RE.search(memo)
        if match:
            name_elt = SubElement(trn, "NAME")
            name_elt.text = match.group(0)
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # prenote
        match = PRENOTE_RE.search(memo)
        if match:
            name_elt = SubElement(trn, "NAME")
            name_elt.text = match.group(0)
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # refund
        match = re.search(r'LMU', memo)
        if match:
            name_elt = SubElement(trn, "NAME")
            name_elt.text = match.group(0)
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # refund
        match = re.search(r'360 Checking', memo)
        if match:
            name_elt = SubElement(trn, "NAME")
            name_elt.text = match.group(0)
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # zelle
        match = re.search(r'Zelle money (received from|sent to|returned)', memo)
        if match:
            name_elt = SubElement(trn, "NAME")
            name_elt.text = match.group(0)
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # transfer to savings
        match = re.search(r'Withdrawal to', memo)
        if match:
            name_elt = SubElement(trn, "NAME")
            name_elt.text = match.group(0)
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # checkbook order
        match = re.search(r'Checkbook Order', memo)
        if match:
            name_elt = SubElement(trn, "NAME")
            name_elt.text = match.group(0)
            trn.remove(memo_elt)
            logger.info("trn: {}".format(pprintXml(trn).decode()))
            continue

        # uncaught case
        logger.info("trn: {}".format(pprintXml(trn).decode()))
        raise RuntimeError("Unhandled transaction.")

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
    args = parser.parse_args()
    work_dir = os.getcwd()
    main(args.qfx_file_in, args.qfx_file_out)
