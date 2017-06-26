'''

For CouchDB our config entity categories map nicely onto the JSON document databases. 
Use them directly...

'''


import logging

class CouchDB(object):
    
    def __init__(self, parent, config, section ):
        self.log = logging.getLogger()
        self.parent = parent
        self.config = config
        self.section = section
        self.log.debug("CouchDB persistence plugin initialized...")
        
    def storedocument(self, key, doc):
        self.log.debug("Storing doc for key %s..." % key)
        
        
        
    def getdocument(self, key):
        self.log.debug("Getting doc for key %s..." % key)
        

        