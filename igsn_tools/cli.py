"""
Command line client for working with International Geo Sample Numbers (IGSNs).

Supported by NSF Award 2004815
"""
import sys
import logging
import datetime
import click
import igsn_tools
import lxml.etree as ET
import json
import extruct
import pprint
from bs4 import BeautifulSoup as BS
import html2text
from subprocess import Popen, PIPE, STDOUT
import xmltodict
import sickle
import igsn_lib

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.CRITICAL,
    "CRITICAL": logging.CRITICAL,
}
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
LOG_FORMAT = "%(asctime)s %(name)s:%(levelname)s: %(message)s"


def getLogger():
    return logging.getLogger("igsn")


def dumpResponse(response, indent=""):
    print(f"{indent}URL: {response.url}")
    print(f"{indent}Encoding: {response.encoding}")
    print(f"{indent}Headers:")
    for h in response.headers:
        print(f"{indent}  {h:>18} : {response.headers[h]}")
    links = response.headers.get("Link", "").split(",")
    for link in links:
        ldata = link.split(";")
        print(f"{indent}  {ldata[0]}")
        for ld in ldata[1:]:
            print(f"{indent}    {ld}")
    # print(f"{indent}Links:")
    # for ltype in response.links:
    #    print(f"{indent}  {ltype}:")
    #    for lname in response.links[ltype]:
    #        print(f"{indent}    {lname} : {response.links[ltype][lname]}")


def dumpResponseHTML(response):
    meta = extruct.extract(response.text, base_url=response.url)
    print("HTML Embedded Metadata:")
    pprint.pprint(meta, indent=2)
    # print("HTML Body:")
    # print(BS(response.text, 'html.parser').prettify())
    print("HTML as text:")
    mdtext = html2text.html2text(response.text)
    args = ["pandoc", "-f", "markdown", "-t", "plain"]
    pd = Popen(args, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    txt = pd.communicate(input=mdtext.encode("utf-8"))[0].decode()
    print(txt)


def dumpResponseXML(response):
    print("XML:")
    xml = ET.fromstring(response.content)
    print(ET.tostring(xml, pretty_print=True).decode())


def dumpResponseJSON(response):
    print("JSON:")
    obj = json.loads(response.text)
    print(json.dumps(obj, indent=2))


def dumpResponseBody(response):
    ctype_h = response.headers.get("Content-Type", "text/html")
    ctype_parts = ctype_h.split(";")
    ctype = ctype_parts[0].lower()
    if ctype in ("text/xml", "application/xml"):
        return dumpResponseXML(response)
    if ctype in ("text/json", "application/json", "application/ld+json"):
        return dumpResponseJSON(response)
    return dumpResponseHTML(response)


@click.group()
@click.option(
    "-v", "--verbosity", default="WARNING", help="Specify logging level", show_default=True
)
@click.pass_context
def main(ctx, verbosity):
    ctx.ensure_object(dict)
    verbosity = verbosity.upper()
    logging.basicConfig(
        level=LOG_LEVELS.get(verbosity, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    L = getLogger()
    if verbosity not in LOG_LEVELS.keys():
        L.warning("%s is not a log level, set to INFO", verbosity)


@click.argument("igsn_str", default=None)
@main.command()
@click.pass_context
def parse(ctx, igsn_str):
    print(igsn_lib.normalize(igsn_str))
    return 0

@click.argument("igsn_str", default=None)
@click.option(
    "-a", "--accept", default=None, help="Accept header value", show_default=True
)
@click.option(
    "-u",
    "--url-only",
    default=False,
    help="Show resolved URL only",
    show_default=True,
    is_flag=True,
)
@click.option(
    "-s",
    "--show-steps",
    default=False,
    help="Show intermediate hosts",
    show_default=True,
    is_flag=True,
)
@click.option(
    "-n",
    "--use_n2t",
    default=False,
    help="Use N2T to resolve",
    show_default=True,
    is_flag=True,
)
@main.command()
@click.pass_context
def resolve(ctx, igsn_str, accept, url_only, show_steps, use_n2t):
    """
    Show results of resolving an IGSN

    Args:
        ctx: The click context passed in from main
        igsn_str: The IGSN string
        accept: optional accept header value

    Returns:
        outputs response information to stdout

    Examples::

        $ igsn resolve 10273/847000106
        https://app.geosamples.org/webservices/display.php?igsn=847000106

    """
    L = getLogger()
    if igsn_str is None:
        L.error("IGSN value is required")
        return 1
    headers = None
    if not accept is None:
        headers = {
            "Accept": accept,
        }
    if use_n2t:
        if accept is None:
            L.warning("N2T does not support content negotiation. Changing default Accept header to */*")
            headers = {
                "Accept": "*/*",
            }
        identifier = igsn_str
        igsn_val = igsn_lib.normalize(igsn_str)
        if igsn_val is not None:
            identifier = f"IGSN:{igsn_val}"
        response = igsn_lib.resolveN2T(identifier, headers=headers)
    else:
        igsn_val = igsn_lib.normalize(igsn_str)
        L.info("Normalized IGSN = %s", igsn_val)
        if igsn_val is None:
            L.error("Provided identifier not recogized as an IGSN")
            return 1
        response = igsn_lib.resolve(igsn_val, headers=headers)
    # Trim space and make upper case
    if show_steps:
        nsteps = len(response.history) + 1
        print("History:")
        cntr = 1
        for r in response.history:
            print(f"Step {cntr}/{nsteps}:")
            dumpResponse(r, indent="  ")
            cntr += 1
        print(f"Step {cntr}/{nsteps}:")
        dumpResponse(response, indent="  ")
    if url_only:
        print(f"{response.url}")
        return 0
    dumpResponseBody(response)
    return 0


if __name__ == "__main__":
    sys.exit(main(obj={}))
