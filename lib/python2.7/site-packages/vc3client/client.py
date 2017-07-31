#!/bin/env python
__author__ = "John Hover"
__copyright__ = "2017 John Hover"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.1"
__maintainer__ = "John Hover"
__email__ = "jhover@bnl.gov"
__status__ = "Production"

import ast
import base64
import json
import logging
import os
import yaml

from entities import User, Project, Resource, Allocation, Request, Cluster, Environment
from vc3infoservice import infoclient
from vc3infoservice.infoclient import  InfoMissingPairingException, InfoConnectionFailure

class VC3ClientAPI(object):
    '''
    Client application programming interface. 
    
    -- DefineX() methods return object. CreateX() stores it to infoservice. The two steps will allow 
    some manipulation of the object by the client, or calling user. 
    
    -- Oriented toward exposing only valid operations to external
    user (portal, resource tool, or admin CLI client). 
    
    -- Direct manipulations of stored information in the infoservice is only done by Entity objects, not
    client user.
        
    -- Store method (inside of storeX methods) takes infoclient arg in order to allow multiple infoservice instances in the future. 
        
    '''
    
    def __init__(self, config):
        self.config = config
        self.ic = infoclient.InfoClient(self.config)
        self.log = logging.getLogger() 



    ################################################################################
    #                           User-related calls
    ################################################################################
    def defineUser(self,   
                   name,
                   first,
                   last,
                   email,
                   institution):           
        '''
       Defines a new User object for usage elsewhere in the API. 
              
       :param str name: The unique VC3 username of this user
       :param str first: User's first name
       :param str last: User's last name
       :param str email: User's email address
       :param str institution: User's intitutional affiliation or employer
       :return: User  A valid User object
       
       :rtype: User        
        '''
        u = User( name=name, 
                  state='new', 
                  acl=None, 
                  first=first, 
                  last=last, 
                  email=email, 
                  institution=institution)
        self.log.debug("Creating user object: %s " % u)
        return u
    
        
    def storeUser(self, user):
        '''
        Stores the provided user in the infoservice. 
        
        :param User u:  User to add. 
        :return: None
        '''
        user.store(self.ic)
          

    def listUsers(self):
        '''
        Returns list of all valid users as a list of User objects. 

        :return: return description
        :rtype: List of User objects. 
        
        '''
        docobj = self.ic.getdocumentobject('user')
        ulist = []
        try:
            for u in docobj['user'].keys():
                    s = "{ '%s' : %s }" % (u, docobj['user'][u] )
                    nd = {}
                    nd[u] = docobj['user'][u]
                    uo = User.objectFromDict(nd)
                    ulist.append(uo)
                    js = json.dumps(s)
                    ys = yaml.safe_load(js)
                    a = ast.literal_eval(js) 
                    #self.log.debug("dict= %s " % s)
                    #self.log.debug("obj= %s " % uo)
                    #self.log.debug("json = %s" % js)
                    #self.log.debug("yaml = %s" % ys)
                    #self.log.debug("ast = %s" % a)
                    #print(uo)
        except KeyError:
            pass
        return ulist

    def getUser(self, username):
        ulist = self.listUsers()
        for u in ulist:
            if u.name == username:
                return u
    
    ################################################################################
    #                           Project-related calls
    ################################################################################  
    def defineProject(self, name, owner, members):
        '''
        Defines a new Project object for usage elsewhere in the API. 
              
        :param str name: The unique VC3 name of this project
        :param str owner:  The VC3 user name of the owner of this project
        :param List str:  List of VC3 user names of members of this project.  
        :return: Project  A valid Project object
        :rtype: Project        
        '''
        p = Project( name=name, 
                     state='new', 
                     acl=None, 
                     owner=owner, 
                     members=members)
        self.log.debug("Creating project object: %s " % p)
        return p
    
    
    def storeProject(self, project):
        '''
        Stores the provided project in the infoservice. 
        
        :param Project project:  Project to add. 
        :return: None
        '''
        self.log.debug("Storing project %s" % project)
        project.store(self.ic)
        self.log.debug("Done.")
    
    
    def addUserToProject(self, project, user):
        '''
        :param str project
        :param str user
        
        
        '''
        self.log.debug("Looking up user %s project %s " % (user, project))
        pdocobj = self.ic.getdocumentobject('project')
        udocobj = self.ic.getdocumentobject('user')
        # confirm user exists...
        pd = pdocobj['project'][project]
        po = Project.objectFromDict(pd)
        self.log.debug("Adding user %s to project object %s " % (user, po))
        po.addUser(user)
        self.storeProject(po)        

    
    def listProjects(self):
        docobj = self.ic.getdocumentobject('project')
        plist = []
        try:
            for p in docobj['project'].keys():
                    s = "{ '%s' : %s }" % (p, docobj['project'][p] )
                    nd = {}
                    nd[p] = docobj['project'][p]
                    po = Project.objectFromDict(nd)
                    plist.append(po)
                    js = json.dumps(s)
                    ys = yaml.safe_load(js)
                    a = ast.literal_eval(js) 
                    #self.log.debug("dict= %s " % s)
                    #self.log.debug("obj= %s " % uo)
                    #self.log.debug("json = %s" % js)
                    #self.log.debug("yaml = %s" % ys)
                    #self.log.debug("ast = %s" % a)
                    #print(uo)
        except KeyError:
            pass
        
        return plist
    
    
    def getProject(self, projectname):
        plist = self.listProjects()
        for p in plist:
            if p.name == projectname:
                return p
    
        
    ################################################################################
    #                           Resource-related calls
    ################################################################################    
    def defineResource(self, name, 
                             owner, 
                             accesstype, 
                             accessmethod, 
                             accessflavor, 
                             gridresource, 
                             mfa):
        '''
        Defines a new Resource object for usage elsewhere in the API. 
              
        :param str name: The unique VC3 name of this resource
        :param str owner:  The VC3 user name of the owner of this project
        :param str resourcetype,  # grid remote-batch local-batch cloud
        :param str accessmethod,  # ssh, gsissh,  
        :param str accessflavor,  # htcondor-ce, slurm, sge, ec2, nova, gce
        :param gridresource,      # http://cldext02.usatlas.bnl.gov:8773/services/Cloud  | HTCondorCE hostname             
        :param Boolean mfa        # Does site need head-node factory?     
        :return: Resource          A valid Project object
        :rtype: Resource        
        
        '''
        r = Resource( name, 
                      state='new', 
                      acl=None, 
                      owner=owner, 
                      accesstype=accesstype, 
                      accessmethod=accessmethod, 
                      accessflavor=accessflavor, 
                      gridresource=gridresource, 
                      mfa=mfa )
        self.log.debug("Creating Resource object: %s " % r)
        return r
    
    
    def storeResource(self, resource):
        resource.store(self.ic)
    
    def listResources(self):
        docobj = self.ic.getdocumentobject('resource')
        rlist = []
        try:
            for r in docobj['resource'].keys():
                    s = "{ '%s' : %s }" % (r, docobj['resource'][r] )
                    nd = {}
                    nd[r] = docobj['resource'][r]
                    ro = Resource.objectFromDict(nd)
                    rlist.append(ro)
                    js = json.dumps(s)
                    ys = yaml.safe_load(js)
                    a = ast.literal_eval(js) 
        except KeyError:
            pass
       
        return rlist
    
    def getResource(self, resourcename):
        rlist = self.listResources()
        for r in rlist:
            if r.name == resourcename:
                return r

    ################################################################################
    #                           Allocation-related calls
    ################################################################################ 
    def defineAllocation(self, name,
                               owner, 
                               resource, 
                               accountname):
        '''
          
        '''
        ao = Allocation(name, state='new', acl=None, owner=owner, resource=resource, accountname=accountname)
        self.log.debug("Creating Allocation object: %s " % ao)
        return ao
    
    def storeAllocation(self, allocation):
        allocation.store(self.ic)
        

    def listAllocations(self):
        docobj = self.ic.getdocumentobject('allocation')
        alist = []
        try:
            for a in docobj['allocation'].keys():
                    s = "{ '%s' : %s }" % (a, docobj['allocation'][a] )
                    nd = {}
                    nd[a] = docobj['allocation'][a]
                    ao = Allocation.objectFromDict(nd)
                    alist.append(ao)
                    js = json.dumps(s)
                    ys = yaml.safe_load(js)
                    a = ast.literal_eval(js) 
        except KeyError:
            pass
        return alist
    
    def addAllocationToProject(self, allocation, projectname ):
        pass
    
    def removeAllocationFromProject(self, allocation, projectname):
        pass
        
    ################################################################################
    #                        Cluster-related calls
    ################################################################################ 
    def defineCluster(self, name, allocations = [], environments = [], policy = None, expiration = None):
        c = Cluster(name, state='new', acl=None, allocations = allocations, environments = environments, policy = policy, expiration = expiration)
        self.log.debug("Creating Cluster object: %s " % c)
        return c
    
    def storeCluster(self, cluster):
        cluster.store(self.ic)
    
    def listClusters(self):
        cluster.listClusters(self.ic)

    def listCluster(self, clustername):
        cluster.listCluster(self.ic, clustername)

    def defineNodeset(self, name, state, acl):
        pass
    
    def storeNodeset(self, nodeset):
        pass
    
    def addNodesToCluster(self, nodesetname, clustername):
        pass
    
    def removeNodesFromCluster(self, nodesetname):
        pass

    ################################################################################
    #                        Environment-related calls
    ################################################################################ 
    def defineEnvironment(self, name, owner, packagelist = [], files={}, envmap = []):
        e = Environment(name, 
                        state='new', 
                        acl=None, 
                        owner = owner, 
                        packagelist = packagelist, 
                        files = files, 
                        envmap = envmap)
        self.log.debug("Creating Environment object: %s " % e)
        return e
    
    def storeEnvironment(self, environment):
        environment.store(self.ic)
    
    def listEnvironments(self):
        docobj = self.ic.getdocumentobject('environment')
        elist = []
        try:
            for e in docobj['environment'].keys():
                    s = "{ '%s' : %s }" % (e, docobj['environment'][e] )
                    nd = {}
                    nd[e] = docobj['environment'][e]
                    eo = Environment.objectFromDict(nd)
                    elist.append(eo)
                    #js = json.dumps(s)
                    #ys = yaml.safe_load(js)
                    #a = ast.literal_eval(js) 
        except KeyError:
            pass

        return elist


    def getEnvironment(self, environmentname):
        elist = self.listEnvironments()
        for e in elist:
            if e.name == environmentname:
                return e

    ################################################################################
    #                        Request-related calls
    ################################################################################ 
    def defineRequest(self, name, state, acl, cluster, environment, allocations, policy ):
        '''
        
        :return Request
        
        '''
        pass
    
    def storeRequest(self):
        pass

    def listRequests(self):
        pass

    def saveRequestAsBlueprint(self, requestid, label):
        pass
    
    def listBlueprints(self, project):
        '''
        Lists blueprints that this project contains.
        '''
        pass

    def getBlueprint(self, name):
        '''
        :return Request
        '''
 
    
    ################################################################################
    #                        Infrastructural calls
    ################################################################################ 
    def getQueuesConf(self, requestname):
        '''
        
        '''
        pass

    def requestPairing(self, commonname):
        '''
        Create a request in the VC3 category to create a pairing setup protected by the supplied pairingcode.
        Master will see request, generate keypair, and place in infoservice w/ code. 
         
        '''
        code = self.ic.requestPairing(commonname)
        return code
        
    
    def getPairing(self, pairingcode):
        '''
        One-time only successful call. 
        Can be called unsuccessfully (i.e. during wait for request satisfaction) without harm. 
        Returns tuple of (pubsslkey, privsslkey)
         
        '''
        (cert, key) = self.ic.getPairing(pairingcode)
        return (cert, key)

    @classmethod
    def encode(self, string):
        return base64.b64encode(string)
    
    @classmethod
    def decode(self, string):
        return base64.b64decode(string)
        
    
class EntityExistsException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class MissingDependencyException(Exception):
    '''
    To be thrown when an API call includes a reference to an entity that doesn't exist. 
    '''
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

