import logging

class Memory(object):
    
    def __init__(self, parent, config, section ):
        self.log = logging.getLogger()
        self.parent = parent
        self.config = config
        self.section = section
        self.documents = {}
        self.log.debug("Memory persistence plugin initialized...")
        
    def storedocument(self, key, doc):
        self.log.debug("Storing doc for key %s..." % key)
        self.documents[key] = doc

    def deletesubtree(self, path):
        self.log.debug("Deleting path %s..." % str(path))

        if len(path) < 1:
            return None

        last_dict = self.documents

        for key in path[0 : -1]:
            last_dict = last_dict[key]

        value = last_dict[path[-1]]
        del last_dict[path[-1]]

        return value
        
    def getdocument(self, key):
        self.log.debug("Getting doc for key %s..." % key)
        try:
            s = self.documents[key]
        except KeyError, e:
            s = {}
        return s
        
        
        
