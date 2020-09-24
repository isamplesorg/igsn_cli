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
import xmltodict
import sickle

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
    links = response.headers.get('Link','').split(",")
    for link in links:
        ldata = link.split(';')
        print(f'{indent}  {ldata[0]}')
        for ld in ldata[1:]:
            print(f'{indent}    {ld}')
    #print(f"{indent}Links:")
    #for ltype in response.links:
    #    print(f"{indent}  {ltype}:")
    #    for lname in response.links[ltype]:
    #        print(f"{indent}    {lname} : {response.links[ltype][lname]}")


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
@click.option(
    '-m',
    '--metadata',
    help='Metadata type to request',
    default='oai_dc'
)
@click.option(
    '-x',
    '--max_records',
    help='Maximum number of records to return',
    default=50
)
@click.option(
    '-s',
    '--set_spec',
    help='Set spec to use in request',
    default=None
)
@click.option(
    '--list_sets',
    help='List sets available on service',
    default=False,
    is_flag=True
)
@click.option(
    '--raw',
    help='Show raw xml for each record',
    default=False,
    is_flag=True
)
@main.command()
@click.pass_context
def pmhlist(ctx, url, metadata, max_records, set_spec, list_sets, raw):
    '''
    List IGSNs from an OAI-PMH endpoint.

    Endpoints include:

    * http://doidb.wdc-terra.org/igsnaaoaip/oai (default)
    * http://pid.geoscience.gov.au/sample/oai
    * https://handle.ands.org.au/igsn/api/service/30/oai
    * https://igsn.csiro.au/csiro/service/oai

    Args:
        ctx:
        url:

    Returns:

    '''
    L = getLogger()
    service = igsn_tools.pmh_igsn.IGSNs(url)
    if list_sets:
        items = service.ListSets()
        cnt = 0
        for item in items:
            entry = xmltodict.parse(item.raw)
            print(f"{cnt:03} {entry['set']['setSpec']:>24} : {entry['set']['setName']}")
            cnt += 1
            if cnt >= max_records:
                print("More available...")
                break
        return
    try:
        items = service.identifiers(metadata=metadata, set_spec=set_spec)
    except sickle.oaiexceptions.NoRecordsMatch as e:
        L.error(e)
        return
    cnt = 0
    namespaces = {
        'http://www.openarchives.org/OAI/2.0/':'oai',
        'http://www.openarchives.org/OAI/2.0/oai_dc/':'oai_dc',
        'http://purl.org/dc/elements/1.1/':'dc',
    }
    for item in items:
        print(f"{cnt:06}")
        if raw:
          xml = ET.fromstring(item.raw)
          print(ET.tostring(xml, pretty_print=True).decode())
        else:
          jitem = xmltodict.parse(item.raw, process_namespaces=True, namespaces=namespaces)
          print(json.dumps(jitem, indent=2))
          rec = jitem['oai:record']
          igsn = igsn_tools.normalizeIGSN(rec['oai:metadata']['oai_dc:dc']['dc:identifier'][0])
          print(f"   IGSN: {igsn}")
          print(f"   Date: {rec['oai:header']['oai:datestamp']}")
          print(f"    Set: {', '.join(rec['oai:header']['oai:setSpec'])}")
          print(f"Creator: {rec['oai:metadata']['oai_dc:dc']['dc:creator']}")
        cnt += 1
        if cnt >= max_records:
            print("More available...")
            break



if __name__ == "__main__":
    sys.exit(main(obj={}))