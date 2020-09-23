'''

'''

import logging
import requests
import urllib.parse

class IGSN():

    def __init__(self, igsn_str, resolver_url="http://hdl.handle.net/10273/"):
        self._L = logging.getLogger(self.__class__.__name__)
        if not isinstance(igsn_str, str):
            raise ValueError("igsn_str string required")
        self.igsn_str = igsn_str.strip().upper()
        self.resolver_url = resolver_url


    def idValue(self, igsn_str):
        '''
        Return the value part of an IGSN.

        e.g. given "10273/ABCD" returns "ABCD"

        Args:
            igsn_str: IGSN string

        Returns: string, value part of IGSN.
        '''
        parts = igsn_str.split("/", 1)
        if len(parts) > 1:
            return parts[1]
        return parts[0]


    def resolve(self, igsn_str=None, headers = {}):
        if igsn_str is None:
            igsn_str = self.igsn_str
        self._L.debug("Resolving: %s", igsn_str)
        igsn_id = self.idValue(igsn_str)
        url = self.resolver_url + urllib.parse.quote(igsn_id)
        response = requests.get(url, headers=headers)
        return response

