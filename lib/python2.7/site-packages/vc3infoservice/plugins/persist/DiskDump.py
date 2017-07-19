import logging
import os
import json

class DiskDump(object):
    
    def __init__(self, parent, config, section ):
        self.log = logging.getLogger()
        self.parent = parent
        self.config = config
        self.section = section
        self.documents = {}

        try:
            self.dbname = os.path.expanduser(self.config.get('plugin-diskdump', 'filename', '~/var/infoservice.diskdump'))
        except Exception, e:
            raise e

        self.load_db()
        self.log.debug("DiskDump persistence plugin initialized...")
        
    def storedocument(self, key, doc):
        self.log.debug("Storing doc for key %s..." % key)
        self.documents[key] = doc

        self.store_db()
        return self.documents[key]

    def getdocument(self, key):
        self.load_db()

        self.log.debug("Getting doc for key %s..." % key)
        try:
            s = self.documents[key]
        except KeyError, e:
            s = {}
        return s

    def deletesubtree(self, path):
        self.log.debug("Deleting path %s..." % str(path))

        if len(path) < 1:
            return None

        last_dict = self.documents

        for key in path[0 : -1]:
            last_dict = last_dict[key]

        value = last_dict[path[-1]]
        del last_dict[path[-1]]

        self.store_db()
        return value

    def store_db(self):
        with open(self.dbname, 'w') as outfile:
            outfile.write(json.dumps(self.documents))

    def load_db(self):
	try:
            with open(self.dbname, 'r') as infile:
                self.documents = json.load(infile)
        except IOError:
                pass

