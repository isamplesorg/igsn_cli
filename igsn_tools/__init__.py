'''

'''

import logging
import requests
import urllib.parse


def normalizeIGSN(igsn_str):
    '''
    Return the value part of an IGSN.

    e.g.:
      "10273/ABCD" -> "ABCD"
      "http://hdl.handle.net/10273/ABCD" -> "ABCD"
      "IGSN: ABCD" -> "ABCD"

    Args:
        igsn_str: IGSN string

    Returns: string, value part of IGSN.
    '''
    igsn_str = igsn_str.strip().upper()
    # url or path form
    parts = igsn_str.split("/")
    if len(parts) > 1:
        return parts[-1]
    # igsn:XXX form
    parts = igsn_str.split(':')
    if len(parts) > 1:
        return parts[-1].strip()
    return igsn_str


class IGSN():

    def __init__(self, igsn_str, resolver_url="http://hdl.handle.net/10273/"):
        self._L = logging.getLogger(self.__class__.__name__)
        if not isinstance(igsn_str, str):
            raise ValueError("igsn_str string required")
        self.igsn_str = igsn_str
        self.resolver_url = resolver_url



    def asURI(self, igsn_str):
        igsn_str = normalizeIGSN(igsn_str)
        return f"https://hdl.handle.net/10273/{igsn_str}"

    def resolve(self, igsn_str=None, headers = {}):
        if igsn_str is None:
            igsn_str = self.igsn_str
        self._L.debug("Resolving: %s", igsn_str)
        igsn_id = normalizeIGSN(igsn_str)
        self._L.debug("normalized: %s", igsn_str)
        url = self.resolver_url + urllib.parse.quote(igsn_id)
        response = requests.get(url, headers=headers)
        return response

