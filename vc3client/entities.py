#!/bin/env python
__author__ = "John Hover"
__copyright__ = "2017 John Hover"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.1"
__maintainer__ = "John Hover"
__email__ = "jhover@bnl.gov"
__status__ = "Production"

import logging

from vc3infoservice.core import InfoEntity


class User(InfoEntity):
    '''
    Represents a VC3 instance user account.
    As policy, name, email, and institution must be set.

    JSON representation:
    {
        "user" : {
            "johnrhover": {
                "name"  : "johnrhover",
                "first" : "John",
                "last"  : "Hover",
                "email" : "jhover@bnl.gov",
                "institution" : "Brookhaven National Laboratory",
            },
        }
    }
    '''
    infoattributes = ['name',
                      'state',
                      'acl',
                      'first',
                      'last',
                      'email',
                      'institution']
    infokey = 'user'

    def __init__(self,
                 name,
                 state,
                 acl,
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
        :return: User:  A valid User object
        :rtype: User
        '''
        self.log = logging.getLogger()
        self.state = state
        self.acl = acl
        self.name = name
        self.first = first
        self.last = last
        self.email = email
        self.institution = institution
        self.log.debug("User object created: %s" % self)


class Project(InfoEntity):
    '''
    Represents a VC3 Project.
    '''
    infokey = 'project'
    infoattributes = ['name',
                      'state',
                      'acl',
                      'owner',
                      'members',
                      'allocations',
                      'blueprints']

    def __init__(self,
                 name,
                 state,
                 acl,
                 owner,
                 members,   # list
                 allocations=None,
                 blueprints=None):
        '''
        Defines a new Project object for usage elsewhere in the API.

        :param str name: The unique VC3 name of this project
        :param str owner: VC3 username of project owner.
        :param
        :return: User:  A valid Project objext.

        :rtype: Project
        '''
        self.log = logging.getLogger()
        self.name = name
        self.state = state
        self.acl = acl
        self.owner = owner
        self.members = []
        for m in members:
            if m not in self.members:
                self.members.append(m)
        # self.members.append(owner)
        # if members is not None:
        #    for m in members:
        #        if m not in self.members:
        #            self.members.append(m)
        self.allocations = allocations
        self.blueprints = blueprints
        self.log.debug("Project object created: %s" % self)

    def addUser(self, user):
        '''
            Adds provided user (string label) to this project.
        '''
        self.log.debug("Adding user %s to project" % user)
        if user not in self.members:
            self.members.append(user)
        self.log.debug("Members now %s" % self.members)


class Resource(InfoEntity):
    '''
    Represents a VC3 target resource.

    "resource" : {
            "uchicago_rcc": {
                "resourcetype" : "remote-batch",  # grid remote-batch local-batch cloud
                "accessmode" : "MFA" # ssh, gsissh,
                "submithost" : <hostname>,
                "submitport" : <port>,
                "type": "<batch-type>",
                "version": "14.11.11",
                },
            }

    intrinsic time limits/preemption flag to distinguish platforms we could run static components on.
    network access is also critical for this.
    '''
    infokey = 'resource'
    infoattributes = ['name',
                      'state',
                      'acl',
                      'owner',
                      'accesstype',
                      'accessmethod',
                      'accessflavor',
                      'gridresource',
                      ]

    def __init__(self,
                 name,
                 state,
                 acl,
                 owner,
                 accesstype,   # grid, batch, cloud
                 accessmethod,  # ssh, gsissh
                 accessflavor,  # condor-ce, slurm, sge, ec2, nova, gce
                 # http://cldext02.usatlas.bnl.gov:8773/services/Cloud , HTCodnor CE hostname[:port]
                 gridresource,
                 mfa=False,
                 ):
        self.log = logging.getLogger()
        self.state = state
        self.acl = acl
        self.name = name
        self.owner = owner
        self.accesstype = accesstype
        self.accessmethod = accessmethod
        self.accessflavor = accessflavor
        self.gridresource = gridresource
        self.log.debug("Project object created: %s" % self)


class Allocation(InfoEntity):
    '''
    Represents the access granted a VC3 User and a VC3 target Resource.
    Defined by (resource, vc3user, unix_account) triple.

    May or may not contain sub-Allocations.

    (Top-level) Allocation names are in the form <vc3username>.<vc3resourcename>.
    Sub-allocation names are in the form <vc3username>.<vc3resourcename>.<suballocationlabel>

    "johnrhover.sdcc-ic." : {
        "acl" : "rw:vc3adminjhover, r:vc3jhover",
        "username": "jhover",
            "security-token" : {
            "type" : "ssh-keypair",
            "ssh-type" : "ssh-rsa",
            "ssh-pubkey" : "AAAAB3NzaC1...",
            "ssh-privkey" : "XXXXXXXXXXXX...",
            },
        },
        "johnrhover.amazon-ec2" : {
            "user" : "johnrhover",
            "resource" : "amazon-ec2"
            "acl" : "rw:vc3adminjhover, r:vc3jhover",
            "accountname" : "racf-cloud@rcf.rhic.bnl.gov",
            "security-token" :  {
                "type" : "cloud-tokens",
                "accesskey" : "AAAAB3NzaC1...",
                "privatekey" : "XXXXXXXXXXXX...",
                }
            }
        },
        "johnrhover.bnl-cluster1" : {
            "username": "jhover",
            "security-token" : {
                "type" : "ssh-keypair",
                "ssh-type" : "ssh-rsa",
                "ssh-pubkey" : "AAAAB3NzaC1...",
                "ssh-privkey" : "XXXXXXXXXXXX...",
                }
            }
        }
    '''
    infokey = 'allocation'
    infoattributes = ['name',
                      'state',
                      'acl',
                      'owner',
                      'resource',
                      'type',
                      'accountname',
                      'quantity',
                      'units',
                      'sectype',     # ssh-rsa, ssh-dsa, pki, x509
                      'pubtoken',    # ssh pubkey, cloud access key
                      'privtoken',   # ssh privkey, cloud secret key, VOMS proxy
                      ]

    def __init__(self, name, state, acl, owner, resource, accountname,
                 type='unlimited',
                 quantity=None,
                 units=None,
                 sectype=None,
                 pubtoken=None,
                 privtoken=None,
                 ):
        '''
        :param str owner:         vc3username of owner of allocation
        :param str resource:      vc3 resource name
        :param str type:          what sort of allocation (unlimited, limited, quota)

        '''
        self.log = logging.getLogger()
        self.name = name
        self.state = state
        self.acl = acl
        self.owner = owner
        self.resource = resource
        self.accountname = accountname     # unix username, or cloud tenant,
        self.type = type           # quota | unlimited | limited
        self.quantity = quantity   #
        self.units = units         #
        self.sectype = sectype
        self.pubtoken = pubtoken
        self.privtoken = privtoken


class Policy(InfoEntity):
    '''
    Describes the desired resource utilization policy when a Request
    includes multiple Allocations.

    '''
    infokey = 'policy'
    infoattributes = ['name',
                      'state',
                      'acl',
                      'pluginname'
                      ]

    def __init__(self, name, owner, acl, pluginname):
        '''
        "static-balanced" : {
                "pluginname" : "StaticBalanced",
            },

        "weighted-balanced" : {
                "pluginname" : "WeightedBalanced",
                "weightmap" : "sdcc-ic.johnrhover,.80,bnl-cluster1.johnrhover,.20"
            },

        "ordered-fill" : {
                "pluginname" : "OrderedFill",
                "fillorder: "sdcc-ic.johnrhover, bnl-cluster1.johnrhover,amazon-ec2.johnrhover"
        }

        '''
        self.name = name
        self.owner = owner
        self.acl = acl
        self.pluginname = pluginname


class Cluster(InfoEntity):
    '''
    Represents a supported VC3 middleware cluster application, node layout, and all relevant configuration
    and dependencies to instantiate it. It is focussed on building the virtual *cluster* not the task/job
    Environment needed to run a particular user's domain application.

    Cluster descriptions should be generic and shareable across Users/Projects.

    e.g. htcondor-managed-cm-schedd
         htcondor-managed-cm-ext-schedd
         workqueue-managed-catalog
         workqueue-ext-catalog
         ?

        }
    '''
    infokey = 'cluster'
    infoattributes = ['name',
                      'state',
                      'acl',
                      'nodesets',
                      'environments',
                      ]

    def __init__(self, name, state, acl):
        '''
        :param str name:   Label for this cluster definition.

        '''
        self.name = name

    def addNodeset(self, ):
        pass

    def removeNodeset(self, nodesetname):
        pass


class Nodeset(InfoEntity):
    '''

    Represents a set of equivalently provisioned nodes that are part of a Cluster definition.


        "nodes" : {
            "headnode1" : {
                "node_number" : "1",
                "node_memory_mb" : "4000",
                "node_cores_minimum" : "4",
                "node_storage_minimum_mb" : "50000",
                "app_type" : "htcondor",
                "app_role" : "head-node",
                "app_port" : "9618"
                "app_password" : "XXXXXXX",
            },
            "workers1" : {
                "app_depends" : "headnode1",
                "node_number" : "10",
                "node_cores_minimum" : "8",
                "node_memory_mb" : "4000",
                "node_storage_minimum_mb" : "20000",
                "app_type" : "htcondor",
                "app_role" : "execute",
                "app_host" : "${HEADNODE1}.hostname",
                "app_port" : "9618"
                "app_password" : "XXXXXXX",
            },
        }
    '''
    infokey = 'nodes'
    infoattributes = ['name',
                      'state',
                      'acl',
                      ]

    def __init__(self, name, state, acl, number, cores, memory_mb, storage_mb, app_type, app_role):
        pass


class Environment(InfoEntity):
    '''
    Represents the node/job-level environment needed to run a given user task.
    Consists of task requirements like job runtime, disk space, cpucount, gpu
    Consists of job requirements like application software, network access, http cache, CVMFS, etc.

    '''
    infokey = 'environment'
    infoattributes = ['name',
                      'state',
                      'acl',
                      'owner',
                      'packagelist',
                      'envmap',
                      ]

    def __init__(self, name, owner,  packagelist=None, envmap=None):
        '''
        Defines a new Environment object.

        :param str name: The unique VC3 label for this environment.
        :param str owner:
        :param List str packagelist:
        :param Dict str envmap:

        :return: User:  A valid Environment object
        :rtype: Environment
        '''
        self.log = logging.getLogger()

        self.name = name
        self.owner = owner
        self.packagelist = packagelist
        self.envmap = envmap


class Request(InfoEntity):
    '''
    Represents and contains all information relevant to a concrete virtual cluster.
    Contains sub-elements that reflect information from other Entities.
    expiration:  Date or None   Time at which cluster should unconditionally do teardown if
                                not actively terminated.


        "johnrhover-req00001" : {
            "cluster" : "clustername",
            "expiration" : "2017-07-07:1730",
            "environment" : {
                        <Environment json>
                    },
            "allocations" : {
                        <Allocations>
                        },
            "policy" :  {
                    <policy>
                }

        }

    '''
    infokey = 'request'
    infoattributes = ['name',
                      'state',
                      'acl',
                      ]

    def __init__(self, name, state, acl
                 ):
        pass

    def getQueuesConf(self):
        pass


def runtest():
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    log = logging.getLogger()
    u = User(name='vc3jhover',
             first='John',
             last='Hover',
             email='jhover@bnl.gov',
             institution='BNL')
    log.info("User made %s" % u)
    du = u.makeDictObject()
    log.info("Dict made %s" % du)
    # u.store()


if __name__ == '__main__':
    runtest()
