'''
Command line cient for working with International Geo Sample Numbers (IGSNs).

Supported by NSF Award 2004815
'''
import sys
import logging
import click
import igsn_tools
import lxml.etree as ET
import json
import extruct
import pprint
from bs4 import BeautifulSoup as BS
import html2text
from subprocess import Popen, PIPE, STDOUT
import igsn_tools.pmh_igsn

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
    return logging.getLogger("photokml")

def dumpResponse(response, indent=''):
    print(f"{indent}URL: {response.url}")
    print(f"{indent}Encoding: {response.encoding}")
    print(f"{indent}Headers:")
    for h in response.headers:
        print(f"{indent}  {h:>18} : {response.headers[h]}")

def dumpResponseHTML(response):
    meta = extruct.extract(response.text, base_url=response.url)
    print("HTML Embedded Metadata:")
    pprint.pprint(meta, indent=2)
    #print("HTML Body:")
    #print(BS(response.text, 'html.parser').prettify())
    print("HTML as text:")
    mdtext = html2text.html2text(response.text)
    args = [
        'pandoc',
        '-f','markdown',
        '-t','plain'
    ]
    pd = Popen(args, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    txt = pd.communicate(input=mdtext.encode('utf-8'))[0].decode()
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
    ctype_parts = ctype_h.split(';')
    ctype = ctype_parts[0].lower()
    if ctype in ('text/xml', 'application/xml'):
        return dumpResponseXML(response)
    if ctype in ('text/json', 'application/json', 'application/ld+json'):
        return dumpResponseJSON(response)
    return dumpResponseHTML(response)


@click.group()
@click.option(
    "-v", "--verbosity", default="INFO", help="Specify logging level", show_default=True
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


@click.argument(
    "igsn_str",
    default=None
)
@click.option(
    '-a',
    '--accept',
    default='text/xml',
    help='Accept header value',
    show_default=True
)
@main.command()
@click.pass_context
def resolve(ctx, igsn_str, accept):
    '''
    Show results of resolving an IGSN

    Args:
        ctx: The click context passed in from main
        igsn_str: The IGSN string
        accept: optional accept header value

    Returns:
        outputs response information to stdout
    '''
    L = getLogger()
    if igsn_str is None:
        L.error("IGSN value is required")
        return 1
    #Trim space and make upper case
    tool = igsn_tools.IGSN(igsn_str)
    headers = {
        'Accept':accept,
    }
    response = tool.resolve(igsn_str, headers=headers)
    nsteps = len(response.history) + 1
    print("History:")
    cntr = 1
    for r in response.history:
        print(f"Step {cntr}/{nsteps}:")
        dumpResponse(r, indent='  ')
        cntr += 1
    print(f"Step {cntr}/{nsteps}:")
    dumpResponse(response, indent='  ')
    dumpResponseBody(response)
    return 0

@click.option(
    '--url',
    default='http://doidb.wdc-terra.org/igsnoaip/oai',
    help='OAI-PMH endpoint to enumerate',
    show_default=True
)
@main.command()
@click.pass_context
def pmhlist(ctx, url):
    '''
    List IGSNs from an OAI-PMH endpoint.

    Args:
        ctx:
        url:

    Returns:

    '''
    service = igsn_tools.pmh_igsn.IGSNs(url)
    items = service.identifiers()
    cnt = 0
    for item in items:
        print(item)
        cnt += 1
        if cnt > 10:
            break
    


if __name__ == "__main__":
    sys.exit(main(obj={}))