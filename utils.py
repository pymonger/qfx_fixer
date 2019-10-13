#!/usr/bin/env python
import os
import sys
import re
import json
from io import BytesIO
from lxml.etree import XMLParser, parse, tostring


def getXmlEtree(xml):
    """Return a tuple of [lxml etree element, prefix->namespace dict].
    """

    parser = XMLParser(remove_blank_text=True)
    if xml.startswith('<?xml') or xml.startswith('<'):
        return (parse(BytesIO(xml), parser).getroot(),
                getNamespacePrefixDict(xml))
    else:
        if os.path.isfile(xml):
            xmlStr = open(xml).read()
        else:
            xmlStr = urlopen(xml).read()
        return (parse(BytesIO(xmlStr.encode()), parser).getroot(),
                getNamespacePrefixDict(xmlStr))


def getNamespacePrefixDict(xmlString):
    """Take an xml string and return a dict of namespace prefixes to
    namespaces mapping."""

    nss = {}
    defCnt = 0
    matches = re.findall(r'\s+xmlns:?(\w*?)\s*=\s*[\'"](.*?)[\'"]', xmlString)
    for match in matches:
        prefix = match[0]
        ns = match[1]
        if prefix == '':
            defCnt += 1
            prefix = '_' * defCnt
        nss[prefix] = ns
    return nss


def xpath(elt, xp, ns, default=None):
    """
    Run an xpath on an element and return the first result.  If no results
    were returned then return the default value.
    """

    res = elt.xpath(xp, namespaces=ns)
    if len(res) == 0:
        return default
    else:
        return res[0]


def pprintXml(et):
    """Return pretty printed string of xml element."""

    return tostring(et, pretty_print=True)
