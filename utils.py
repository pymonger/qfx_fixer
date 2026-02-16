#!/usr/bin/env python
import os
import re
from io import BytesIO
from typing import Any, Optional
from urllib.request import urlopen

from lxml.etree import XMLParser, _Element, parse, tostring


def getXmlEtree(xml: str) -> tuple[_Element, dict[str, str]]:
    """Return a tuple of [lxml etree element, prefix->namespace dict]."""

    parser = XMLParser(remove_blank_text=True)
    if xml.startswith('<?xml') or xml.startswith('<'):
        return (parse(BytesIO(xml.encode()), parser).getroot(),
                getNamespacePrefixDict(xml))
    else:
        if os.path.isfile(xml):
            with open(xml) as f:
                xmlStr = f.read()
        else:
            xmlStr = urlopen(xml).read().decode()
        return (parse(BytesIO(xmlStr.encode()), parser).getroot(),
                getNamespacePrefixDict(xmlStr))


def getNamespacePrefixDict(xmlString: str) -> dict[str, str]:
    """Take an xml string and return a dict of namespace prefixes to
    namespaces mapping."""

    nss: dict[str, str] = {}
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


def xpath(elt: _Element, xp: str, ns: dict[str, str],
          default: Optional[Any] = None) -> Any:
    """Run an xpath on an element and return the first result. If no results
    were returned then return the default value."""

    res = elt.xpath(xp, namespaces=ns)
    if len(res) == 0:
        return default
    else:
        return res[0]


def pprintXml(et: _Element) -> bytes:
    """Return pretty printed string of xml element."""

    return tostring(et, pretty_print=True)
