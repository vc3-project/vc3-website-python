#! /usr/bin/env python
__author__ = "John Hover, Jose Caballero"
__copyright__ = "2017 John Hover"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.1"
__maintainer__ = "John Hover"
__email__ = "jhover@bnl.gov"
__status__ = "Production"

import base64
import json
import logging
import logging.handlers
import requests
import urllib
import os
import platform
import sys
import time
import traceback

from random import choice
from string import ascii_uppercase
from optparse import OptionParser
from ConfigParser import ConfigParser


import requests
requests.packages.urllib3.disable_warnings()
try:
    logging.captureWarnings(True)
except AttributeError:
    # Some versions don't have this. 
    pass

from vc3infoservice.core import InfoEntity

TESTKEY='testkey'
TESTDOC='''{ 
                {"jhoverproject": 
                    { "blueprints": null, 
                      "name": "jhoverproject", 
                      "acl": null, 
                      "members": ["jhover", "angus"], 
                      "state": "new", 
                      "allocations": null, 
                      "owner": "jhover"}
                }
           }'''

class InfoConnectionFailure(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)   

class InfoMissingPairingException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)  


class InfoClient(object):
    
    def __init__(self, config):
        self.log = logging.getLogger()
        self.log.debug('InfoClient class init...')
        self.config = config
        self.certfile = os.path.expanduser(config.get('netcomm','certfile'))
        self.keyfile = os.path.expanduser(config.get('netcomm', 'keyfile'))
        self.chainfile = os.path.expanduser(config.get('netcomm','chainfile'))
        self.httpport = int(config.get('netcomm','httpport'))
        self.httpsport = int(config.get('netcomm','httpsport'))
        self.infohost = os.path.expanduser(config.get('netcomm','infohost'))
      
        self.log.debug("Client initialized.")

    def storedocument(self, key, doc):
        '''
        Store JSON string <doc> in infoservice under key <key>.
        
        '''
        
        u = "https://%s:%s/info?key=%s" % (self.infohost, 
                            self.httpsport,
                            key
                            )
        self.log.debug("Trying to store document %s at %s" % (doc, u))
        try:
            r = requests.put(u, verify=self.chainfile, cert=(self.certfile, self.keyfile), params={'data' : doc})
            self.log.debug(r.status_code)
        
        except requests.exceptions.ConnectionError, ce:
            self.log.error('Connection failure. %s' % ce)

    def getdocument(self, key):
        '''
        Get and return JSON string for document with key <key>
                
        '''
        u = "https://%s:%s/info?key=%s" % (self.infohost, 
                            self.httpsport,
                            key
                            )
        try:
            r = requests.get(u, verify=self.chainfile, cert=(self.certfile, self.keyfile))
            out = self.stripquotes(r.text)
            parsed = json.loads(out)
            pretty = json.dumps(parsed, indent=4, sort_keys=True)
            #self.log.debug(pretty)
            #self.log.debug(r.status_code)
            return r.text
        
        except requests.exceptions.ConnectionError, ce:
            self.log.error('Connection failure. %s' % ce)
    
    def getdocumentobject(self, key):
        '''
        Get JSON doc and convert to Python and return. 
        
        '''
        u = "https://%s:%s/info?key=%s" % (self.infohost, 
                            self.httpsport,
                            key
                            )
        try:
            r = requests.get(u, verify=self.chainfile, cert=(self.certfile, self.keyfile))
            out = self.stripquotes(r.text)
            parsed = json.loads(out)
            pretty = json.dumps(parsed, indent=4, sort_keys=True)
            return parsed
        
        except requests.exceptions.ConnectionError, ce:
            self.log.error('Connection failure. %s' % ce)       
    
    def storedocumentobject(self, dict, key):
        '''
        Directly store Python dictionary as JSON ...
        
        '''
        if key not in dict.keys():
            td = {}
            td[key] = dict
            dict = td
            
        jstr = json.dumps(dict)
        self.log.debug("JSON string: %s" % jstr)
        self.storedocument(key, jstr)
        
    
    def mergedocument(self, key, doc):
                
        u = "https://%s:%s/info?key=%s" % (self.infohost, 
                            self.httpsport,
                            key
                            )
        self.log.debug("Trying to merge document %s at %s" % (doc, u))
        try:
            r = requests.put(u, verify=self.chainfile, cert=(self.certfile, self.keyfile), params={'data' : doc})
            self.log.debug(r.status_code)
        
        except requests.exceptions.ConnectionError, ce:
            self.log.error('Connection failure. %s' % ce)

    def getbranch(self, *keys):
        doc = self.getdocument(key = keys[0])
        if not doc:
            return None
        ds = json.loads(doc)
        good_keys = []
        for k in keys:
            if k in ds:
                ds = ds[k]
            else:
                raise Exception('Successful keys: ' + str(good_keys))
        return ds
    
    def getsubtree(self, path):
        pass
    
    def deletesubtree(self, path):
        '''
        Delete the leaf given by path.
        
        '''

        try:
            keys = path.split('.')
            key  = keys[0]
        
            u = "https://%s:%s/info?key=%s" % (self.infohost, 
                                self.httpsport,
                                key
                                )
            self.log.debug("Trying to delete document at %s" % (path,))

            r = requests.delete(u, verify=self.chainfile, cert=(self.certfile, self.keyfile), params={'name' : path})
            self.log.debug(r.status_code)
        
        except IndexError, e:
            self.log.error('Path should contain at least one key')
            raise e
        except requests.exceptions.ConnectionError, ce:
            self.log.error('Connection failure. %s' % ce)
        
    def testquery(self):
        self.log.info("Testing storedocument. Doc = %s" % TESTDOC)
        self.storedocument(key=TESTKEY,doc=TESTDOC)
        
        self.log.info("Testing getdocument...")
        self.getdocument(key=TESTKEY)
        self.log.info("Done.")


    def stripquotes(self,s):
        rs = s.replace("'","")
        return rs

    def encode(self, string):
        return base64.b64encode(string)
    
    def decode(self, string):
        return base64.b64decode(string)

    def requestPairing(self, cnsubject):
        '''
        Establish a pairing entry
        '''
        self.log.debug("Infoclient requestPairing for %s " % cnsubject)
        pairingcode = self.generateCode(cnsubject)
        self.log.debug("Generated code: %s " % pairingcode)
        po = Pairing(name=cnsubject, 
                     state='new', 
                     acl=None, 
                     cn=cnsubject, 
                     pairingcode=pairingcode
                     )
        self.log.debug("Made pairing request: %s" % po)
        po.store(self)
        self.log.debug("Stored in /info/pairing..")
        return pairingcode

    def getPairing(self, pairingcode):
        '''
            Special call because it sends pairing code as data, along with URL
        
            :param str pairingcode    Code to be paired with. 
            :return
            :rtype (str, str)         Cert and key
        '''
        u = "https://%s:%s/info?key=pairing&pairingcode=%s" % (self.infohost, 
                            self.httpsport,
                            pairingcode
                            )
        self.log.debug("Attempting to get pairing via URL %s" % u)
        try:
            r = requests.get(u, verify=self.chainfile)     
            pe = json.loads(r.text)
            ecert = pe['cert']
            ekey = pe['key']
            cert = self.decode(ecert)
            key = self.decode(ekey)
            return (cert, key)
       
        except requests.exceptions.ConnectionError, ce:
            self.log.error('Connection failure. %s' % ce)
            raise InfoConnectionFailure("Connection Error.")
        
        except Exception, e:
            self.log.debug('Other failure. Probably missing pairing. %s ' % e)
            raise InfoMissingPairingException("Missing pairing.")
            
            
    def generateCode(self, name ):       
        cs= ''.join(choice(ascii_uppercase) for i in range(6))
        return("%s-%s" % (name, cs))
      

class Pairing(InfoEntity):
    '''
    Represents a request and completed entry for a pairing.
    Stored in /pairing/<code>
    
    '''    
    infokey = 'pairing'
    infoattributes = ['name', 
                      'state',
                      'acl',
                      'cn',   # common name for pair.  
                      'pairingcode',
                      'cert',
                      'key',
                      'encoding'
                     ]
    def __init__(self, name, state, acl, cn, pairingcode, cert=None, key=None, encoding='base64'):
        self.name = name
        self.log = logging.getLogger()
        self.state = state
        self.acl = acl
        self.cn = cn
        self.pairingcode = pairingcode
        self.cert = cert
        self.key = key
        self.encoding = encoding
        

class InfoClientCLI(object):
    """class to handle the command line invocation of APF. 
       parse the input options,
       setup everything, and run Factory class
    """
    def __init__(self):
        self.options = None 
        self.args = None
        self.log = None
        self.config = None

        self.__presetups()
        self.__parseopts()
        self.__setuplogging()
        self.__platforminfo()
        self.__createconfig()
        
    def __presetups(self):
        '''
        we put here some preliminary steps that 
        for one reason or another 
        must be done before anything else
        '''
    
    def __parseopts(self):
        parser = OptionParser(usage='''%prog [OPTIONS]
vc3-info-client is a client for the information store for VC3

This program is licenced under the GPL, as set out in LICENSE file.

Author(s):
John Hover <jhover@bnl.gov>
''', version="%prog $Id: infoclient.py 1-31-17 23:58:06Z jhover $" )

        parser.add_option("-d", "--debug", 
                          dest="logLevel", 
                          default=logging.WARNING,
                          action="store_const", 
                          const=logging.DEBUG, 
                          help="Set logging level to DEBUG [default WARNING]")
        parser.add_option("-v", "--info", 
                          dest="logLevel", 
                          default=logging.WARNING,
                          action="store_const", 
                          const=logging.INFO, 
                          help="Set logging level to INFO [default WARNING]")
        parser.add_option("--quiet", dest="logLevel", 
                          default=logging.WARNING,
                          action="store_const", 
                          const=logging.WARNING, 
                          help="Set logging level to WARNING [default]")

        default_conf = "~/etc/vc3/vc3-infoclient.conf"
        if 'VC3_SERVICES_HOME' in os.environ:
            default_conf = os.path.join(os.environ['VC3_SERVICES_HOME'], 'etc', 'vc3-infoclient.conf') + ',' + default_conf

        parser.add_option("-c","--config", dest="confFiles", 
                          default=default_conf,
                          action="store", 
                          metavar="FILE1[,FILE2,FILE3]", 
                          help="Load configuration from FILEs (comma separated list)")

        parser.add_option("--log", dest="logfile", 
                          default="stdout", 
                          metavar="LOGFILE", 
                          action="store", 
                          help="Send logging output to LOGFILE or SYSLOG or stdout [default <syslog>]")
        parser.add_option("--add", dest="addfiles", 
                          action="store", 
                          metavar="FILE1[,FILE2,FILE3]", 
                          help="Merge info into store from JSON files with key as top-level tag.")        
        parser.add_option("--getkey", dest="getkey", 
                          action="store", 
                          metavar="[resource|account|cluster|...]", 
                          help="Get info from store with provided key.")        
        parser.add_option("--deletesubtree", dest="deletesubtree", 
                          action="store", 
                          metavar="[resource|account|cluster|...]", 
                          help="Delete the leaf given by keys path. Path given in the form of a.b.c.d... ")        

        parser.add_option("--requestpairing",
                          dest = "requestpairing",
                          action="store",
                          metavar="SUBJECT/CN",
                          help="Request a cert/key creation for supplied HOST/CN/SUBJECT"
                          )
        
        parser.add_option("--getpairing",
                          dest = "pairingcode",
                          action = "store",
                          metavar="PAIRINGCODE",
                          help="Retrieve cert/key pair for supplied pairing code."
                          )
                        
        (self.options, self.args) = parser.parse_args()
        self.options.confFiles = self.options.confFiles.split(',')

    def __setuplogging(self):
        """ 
        Setup logging 
        """
        self.log = logging.getLogger()
        if self.options.logfile == "stdout":
            logStream = logging.StreamHandler()
        else:
            lf = self.options.logfile
            logdir = os.path.dirname(lf)
            if not os.path.exists(logdir):
                os.makedirs(logdir)
            logStream = logging.FileHandler(filename=lf)    

        # Check python version 
        major, minor, release, st, num = sys.version_info
        if major == 2 and minor == 4:
            FORMAT='%(asctime)s (UTC) [ %(levelname)s ] %(name)s %(filename)s:%(lineno)d : %(message)s'
        else:
            FORMAT='%(asctime)s (UTC) [ %(levelname)s ] %(name)s %(filename)s:%(lineno)d %(funcName)s(): %(message)s'
        formatter = logging.Formatter(FORMAT)
        formatter.converter = time.gmtime  # to convert timestamps to UTC
        logStream.setFormatter(formatter)
        self.log.addHandler(logStream)

        self.log.setLevel(self.options.logLevel)
        self.log.info('Logging initialized.')


    def _printenv(self):

        envmsg = ''        
        for k in sorted(os.environ.keys()):
            envmsg += '\n%s=%s' %(k, os.environ[k])
        self.log.debug('Environment : %s' %envmsg)


    def __platforminfo(self):
        '''
        display basic info about the platform, for debugging purposes 
        '''
        self.log.info('platform: uname = %s %s %s %s %s %s' %platform.uname())
        self.log.info('platform: platform = %s' %platform.platform())
        self.log.info('platform: python version = %s' %platform.python_version())
        self._printenv()

    
    def __createconfig(self):
        """Create config, add in options...
        """
        if self.options.confFiles != None:
            try:
                self.config = ConfigParser()
                self.config.read(self.options.confFiles)
            except Exception, e:
                self.log.error('Config failure')
                sys.exit(1)
        
        #self.config.add_section('cli')
        #self.config.set("cli", "addfiles", self.options.confFiles)

    def doquery(self):
        self.ic = InfoClient(self.config)
        if self.options.addfiles:
            flist = self.options.addfiles.split(',')
            for fn in flist:
                fname = fn.strip()
                self.log.debug("Adding contents of file %s" % fname)
                jdoc = open(fname).read()
                data = json.loads(jdoc)
                pretty = json.dumps(data, indent=4, sort_keys=True)
                self.log.debug(pretty)
                k = data.keys()[0]
                self.log.debug("key is %s" % k)
                self.ic.mergedocument(k,jdoc)
        
        if self.options.getkey:
            qkey = self.options.getkey.lower().strip()
            self.log.debug("Getkey is %s, doing query" % qkey )
            out = self.ic.getdocument(qkey)
            print(out)

        if self.options.deletesubtree:
            dpath = self.options.deletesubtree.lower().strip()
            self.log.debug("Deletesubtree is %s, doing query" % dpath )
            out = self.ic.deletesubtree(dpath)
            print(out)
            
        if self.options.requestpairing:
            self.log.debug("Setting up pairing for CN: %s"% self.options.requestpairing )
            code = self.ic.requestPairing(self.options.requestpairing)
            print("%s" % code)
        
        if self.options.pairingcode:
            try:
                #out = self.ic.getPairing(self.options.pairingcode)
                #print("out is %s" % out)
                (cert, key) = self.ic.getPairing(self.options.pairingcode)
                print("%s" % cert)
                print("")
                print("%s" % key)
            except Exception, e:
                self.log.error("Exception %s" % e)
                print("No response. Invalid pairing or not setup yet. Try in 30 seconds.")

    def testquery(self):
        self.ic = InfoClient(self.config)
        self.ic.testquery()
        

    def run(self):
        self.doquery()


if __name__ == '__main__':
    logging.info("Running from .py file...")
    iccli = InfoClientCLI()
    iccli.run()

