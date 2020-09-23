'''
PMH access for IGSNs
'''

import sickle

class IGSNs(sickle.Sickle):

    def identifiers(self):
        return self.ListRecords(ignore_deleted=False, metadataPrefix='oai_dc')


