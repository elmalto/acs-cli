"""

Create an manage instances of Azure Container Service. The service
configuration is defined in the `cluster.ini` file (or the file
specified in `--config-file`.

Usage:
  service <command> [help] [options]

Commands:
  create                create an Azure Container Service
  delete                delete an Azure Container Service
  scale                 Scale the agent cluster up
  show                  display the current service configuration
  openTunnel            open an SSH tunnel to the management interface

Options:
  --agents=<number>            number of agents (currently scale only scale up is supported)
  --quiet                      don't ask the user for input
Examples:

Make the number of agents in the primary pool 5
  acs service scale --agents=5

Help:
  For help using the oms command please open an issue at 
  https://github.com/rgardler/acs-scripts

"""
from .base import Base

from docopt import docopt
from inspect import getmembers, ismethod
import json
import os
import subprocess
import sys  
from tempfile import mkstemp
import time
from shutil import move
from os import remove, close

class Service(Base):

  def run(self):
    args = docopt(__doc__, argv=self.options)
    print("Service args")
    print(args)
    self.args = args
    
    command = self.args["<command>"]
    result = None
    methods = getmembers(self, predicate = ismethod)
    for name, method in methods:
      if name == command:
        result = method()
        if result is None:
          result = command + " returned no results"
    if result:
      print(result)
    else:
      print("Unknown command: '" + command + "'")
      self.help()
   	  
  def help(self):
    print(__doc__)

  def exists(self):
    """ Tests whether the management endpoint is accessible, if it is we assume the service exists """
    exists = Base._hostnameResolves(self, Base.getManagementEndpoint(self))
    return exists

  def create(self):
    if self.exists():
      return "It appears that the cluster already exists:\n" + self.show()

    self.log.debug("Creating ACS Deployment")
    self.log.debug(json.dumps(self.config.getACSParams()))

    Base.createResourceGroup(self)
    
    self._deploy(self.config.get('ACS', 'dnsPrefix'))
    
    if self.exists():
      if self.config.get('ACS', 'orchestratorType') == 'DCOS':
        print("You may now want to run `acs service openTunnel && acs dcos install` to install the DCOS command line")
        
      return self.show()

  def _deploy(self, name):
    command = "azure group deployment create"
    command = command + " " + self.config.get('ACS', 'dnsPrefix')
    command = command + " " + name
    command = command + " --template-uri " + self.config.get('Template', 'templateUrl')
    command = command + " -p '" + json.dumps(self.config.getACSParams()) + "'"
    os.system(command)

  def delete(self, quiet = False):
    self.log.debug("Deleting ACS Deployment")
    self.log.debug(json.dumps(self.config.getACSParams()))
    
    if not quiet and not self.args["--quiet"]:
      dns = self.config.get("ACS", "dnsPrefix")
      group = self.config.get("Group", "name")
      responded = False
      while not responded:
        resp = input("Do you really want to delete the ACS cluster '" + dns + "' in resource group '" + group + "' ('y' or 'yes' to confirm, 'n' or 'no' to abort)?\n")
        if resp == "y" or resp == "yes":
          responded = True
        elif resp == "n" or resp == "no":
          self.log.debug("Aborting delete at users request")
          return "Delete aborted"
        
    command = "azure acs delete"
    command = command + " " + self.config.get('ACS', 'dnsPrefix')
    command = command + " containerservice-" + self.config.get('ACS', 'dnsPrefix')
    os.system(command)
    
    # FIXME: we shouldn't need to do the group delete, but currently container delete is not a deep delete
    print("'azure acs delete 'does not currently delete resources created within the container service. You can delete all resources by also deleting the associated resource group, however, be aware this will delete everything in the resource group.")
    command = "azure group delete " 
    if quiet or self.args["--quiet"]:
      command = command + " --quiet "
    command = command + self.config.get('Group', 'name')
    os.system(command)

  def scale(self):
    if not self.exists():
      return "It appears that the cluster does not exists (try running `acs service createo`)"

    desired_agents = self.args["--agents"]

    fh, abs_path = mkstemp()
    with open(abs_path,'w') as new_file:
      with open(self.config.filename) as old_file:
        for line in old_file:
          if line.startswith("agentCount:"):
            new_file.write("agentCount: " + str(desired_agents) + "\n")
          else:
            new_file.write(line)
    close(fh)
    try:
      remove(self.config.filename + ".bak")
    except OSError:
      pass
    move(self.config.filename, self.config.filename + ".bak")
    move(abs_path, self.config.filename)

    self._deploy("scale")
    
    return "Scaled to " + str(desired_agents)

  def show(self):
    """
    Output the configuration of this cluster in json format.
    """
    config = self.getClusterSetup()
    return json.dumps(config, sort_keys=True,
                      indent=4, separators=(',', ': '))

  def openTunnel(self):
    """
    Open an SSH tunnel to the management endpoint.
    """
    try:
      pid = os.fork()
      if pid > 0:
        # Exit parent process
        sys.exit(0)
    except OSError as e:
        print >> sys.stderr, "fork failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # Descouple from the parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    print("To stop the SSH tunnel run 'kill " + str(os.getpid()) + "'")

    Base.sshTunnel(self)
    return pid

  def closeTunnel(self, pid):
    """
    Close the SSH tunnel to the management endpoint with the supplied pid
    """
    self.log.info("Attempting to kill the process " + str(int))
    try:
      while 1:
        os.kill(pid, SIGTERM)
        time.sleep(1.0)
    except OSError as err:
      err = str(err)
      if err.find("No such process") > 0:
        self.log.error("Failed to kill the process\n " + str(err))
        sys.exit(1)

  def marathonCommand(self, command, method = 'GET', data = None):
    curl = 'curl -s -X ' + method 
    if data != None:
      curl = curl + " -d \"" + data + "\" -H \"Content-type:application/json\""
    cmd = curl + ' localhost/marathon/v2/' + command 
    self.log.debug('Command to execute: ' + cmd)
    return Base.sshTunnel(self, cmd)
