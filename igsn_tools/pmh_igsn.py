'''
PMH access for IGSNs
'''

import sickle

class IGSNs(sickle.Sickle):

    def identifiers(self, metadata='oai_dc', set_spec=None):
        params = {
            'metadataPrefix':metadata,
        }
        if set_spec is not None:
            params['set'] = set_spec
        return self.ListRecords(ignore_deleted=True, **params)


