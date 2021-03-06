"""The base command class. All implemented commands should extend this class."""
from ..AgentPool import AgentPool

from sshtunnel import SSHTunnelForwarder
import json
import os.path
import paramiko
from paramiko import SSHClient
from paramiko.agent import AgentRequestHandler
from time import sleep
import socket
import subprocess

class Base(object):

  def __init__(self, config, options, *args, **kwargs):
    self.log = ACSLog("Base")
    self.config = config
    self.options = options
    self.args = args
    self.kwargs = kwargs

  def _hostnameResolves(self, hostname):
    try:
      socket.gethostbyname(hostname)
      return True
    except socket.error:
      return False

  def getManagementEndpoint(self):
    return self.config.get('ACS', 'dnsPrefix') + 'mgmt.' + self.config.get('Group', 'region').replace(" ", "").replace('"', '') + '.cloudapp.azure.com'

  def getAgentEndpoint(self):
    return self.config.get('ACS', 'dnsPrefix') + 'agents.' + self.config.get('Group', 'region').replace(" ", "").replace('"', '') + '.cloudapp.azure.com'

  def createResourceGroup(self):
    self.log.debug("Creating Resource Group")

    command = "azure group create " + self.config.get('Group', 'name')  + " " + self.config.get('Group', 'region')
    os.system(command)

  def run(self):
    raise NotImplementedError("You must implement the run() method in your commands")

  def help(self):
    raise NotImplementedError("You must implement the help method. In most cases you will simply do 'print(__doc__)'")

  def getAgentIPs(self):
    # return a list of Agent IPs in this cluster
    
    agentPool = AgentPool(self.config)
    nics = agentPool.getNICs()
    
    ips = []
    for nic in nics:
      self.log.debug("Extracting IP from: " + json.dumps(nic, indent=True))
      ip = nic["properties"]["ipConfigurations"][0]["properties"]["privateIPAddress"]
      self.log.debug("IP is: " + str(ip))
      ips.append(ip)

    return ips

  def executeOnAgent(self, cmd, ip):
    """
    Execute command on an agent identified by agent_name
    """
    sshAgentConnection = "ssh -o StrictHostKeyChecking=no " + self.config.get('ACS', 'username') + '@' + ip
    self.log.debug("SSH Connection to agent: " + sshAgentConnection)
    
    self.log.debug("Command to run on agent: " + cmd)
    
    cmd = cmd.replace("\"", "\\\"")
    sshCmd = sshAgentConnection + ' \'' + cmd + '\''
    return self.executeOnMaster(sshCmd)

  def executeOnMaster(self, cmd):
    """
    Execute command on the current master leader
    """
    self.log.debug("Executing on master: " + cmd)

    if self._hostnameResolves(self.getManagementEndpoint()):
      ssh = SSHClient()
      ssh.load_system_host_keys()
      ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      ssh.connect(
        self.getManagementEndpoint(),
        username = self.config.get('ACS', "username"),
        port = 2200,
        key_filename = os.path.expanduser(self.config.get('SSH', "privatekey")))
      session = ssh.get_transport().open_session()
      AgentRequestHandler(session)
      stdin, sterr, stdout = ssh.exec_command(cmd)
      stdin.close()
      
      result = ""
      for line in stdout.read().splitlines():
        self.log.debug(line)
        result = result + line
    else:
      self.log.error("Endpoint " + self.getManagementEndpoint() + " does not exist, cannot SSH into it.")
      result = "Exception: No test cluster is available"
    return result

  def sshTunnel(self, command = None):
    """
    Either open an SSH tunnel and keep it open (if command = None) 
    or open the tunnel, execute the command and exit.
    """
    with SSHTunnelForwarder(
      (self.getManagementEndpoint(), 2200),
      remote_bind_address = ('localhost', 80),
      local_bind_address = ('', 80),
      ssh_username = self.config.get('ACS', 'username'),
      ssh_pkey = os.path.expanduser(self.config.get('SSH', "privatekey"))
    ) as server:
      if command:
        return subprocess.check_output(command, shell=True)
      else:
        while True:
          sleep(1)

  def getClusterSetup(self):
    """
    Get all the data about how this cluster is configured.
    """
    data = {}
    data["parameters"] = self.config.getACSParams()
    
    fqdn = {}
    fqdn["master"] = self.getManagementEndpoint()
    fqdn["agent"] = self.getAgentEndpoint()
    data["domains"] = fqdn
    
    data["sshTunnel"] = "ssh -o StrictHostKeyChecking=no -L 80:localhost:80 -N " + self.config.get('ACS', 'username') + "@" + self.getManagementEndpoint() + " -p 2200"

    azure = {}
    azure['resourceGroup'] = self.config.get('Group', 'name')
    data["azure"] = azure

    return data





"""The cofiguration for an ACS cluster to work with"""
from acs.ACSLogs import ACSLog

import configparser
import os 

class Config(object):

  def __init__(self, filename):
    print("Create base object")
    self.log = ACSLog("Config")

    if not filename:
      filename = "~/.acs/default.ini"

    self.filename = os.path.expanduser(filename)
    self.log.debug("Using config file at " + self.filename)

    if not os.path.isfile(self.filename):
      self.log.debug("Config file does not exist. Creating a new one.")
      dns = input("What is the DNS prefix for this cluster?\n")
      group = input("What is the name of the resource group you want to use/create?\n")
      region = input("In which region do you want to deploy the resource group (default: westus)?\n") or 'westus'
      username = input("What is your username (default: azureuser)?\n") or 'azureuser'
      orchestrator = input("Which orchestrator do you want to use (Swarm or DCOS, default: DCOS)?\n") or 'DCOS'
      masterCount = input("How many masters do you want in your cluster (1, 3 or 5, default: 3)?\n") or '3'
      agentCount = input("How many agents do you want in your cluster (default: 3)?\n") or '3'
      agentSize = input("Agent size required (default: Standard_D2_v2)?\n") or 'Standard_D2_v2'
      
      tmpl = open("config/cluster.ini.tmpl")
      output = open(self.filename, 'w')
      for s in tmpl:
        s = s.replace("MY-DNS-PREFIX", dns)
        s = s.replace("MY-RESOURCE-REGION", region)
        s = s.replace("MY-RESOURCE-GROUP-NAME", group)
        s = s.replace("MY-USERNAME", username)
        s = s.replace("MY-ORCHESTRATOR", orchestrator)
        s = s.replace("MY-MASTER-COUNT", masterCount)
        s = s.replace("MY-AGENT-COUNT", agentCount)
        s = s.replace("MY-AGENT-SIZE", agentSize)
        output.write(s)
        self.log.debug("Writing config line: " + s)

      tmpl.close()
      output.close()

    defaults = {"orchestratorType": "DCOS"}
    config = configparser.ConfigParser(defaults)
    config.read(self.filename)
    config.set('Group', 'name', config.get('Group', 'name'))
    self.config_parser = config
      
  def get(self, section, name):
    value = self.config_parser.get(section, name)

    if section == "SSH": 
      public_filepath = os.path.expanduser(self.config_parser.get('SSH', 'publicKey'))
      private_filepath = os.path.expanduser(self.config_parser.get('SSH', 'privatekey'))

      if name == "privateKey":
        self.log.debug("Checking if private SSH key exists: " + private_filepath)
        if not os.path.isfile(private_filepath):
          self.log.debug("Key does not exist")
          self._generateSSHKey(private_filepath, public_filepath)
        with open(private_filepath, 'r') as sshfile: 
          self.log.debug("Key does not exist")
          value = sshfile.read().replace('\n', '') 
      elif name == "publickey":
        self.log.debug("Checking if public SSH key exists: " + public_filepath)
        if not os.path.isfile(public_filepath):
          self._generateSSHKey(private_filepath, public_filepath)
        with open(public_filepath, 'r') as sshfile: 
          value = sshfile.read().replace('\n', '') 
        
    return value

  def getint(self, section, name):
    return self.config_parser.getint(section, name)

  def value(self, set_to):
    value = {}
    value["value"] = set_to
    return value
    
  def getACSParams(self):
    """
    Get a dictionary of all ACS parameters. Note that 
    this is not all the parameters provided in the config 
    file, only the ones needed by the ACS Resource Provider'
    """
    params = {}
    params["dnsNamePrefix"] = self.value(self.get('ACS', 'dnsPrefix'))
    params["orchestratorType"] = self.value(self.get('ACS', 'orchestratorType'))
    params["agentCount"] = self.value(self.getint('ACS', 'agentCount'))
    params["agentVMSize"] = self.value(self.get('ACS', 'agentVMSize'))
    params["masterCount"] = self.value(self.getint('ACS', 'masterCount'))
    params["linuxAdminUsername"] = self.value(self.get('ACS', 'username'))
    params["sshRSAPublicKey"] = self.value(self.get('SSH', 'publickey'))
  
    return params

  def _generateSSHKey(self, private_filepath, public_filepath):
    """
    Generate public and private keys. The filepath parameters 
    are the paths top the respective publoic and private key files.
    """
    self.log.debug("Writing SSH keys to: " + private_filepath + " and " + public_filepath)

    (ssh_dir, filename) = os.path.split(os.path.expanduser(private_filepath))
    if not os.path.exists(ssh_dir):
      self.log.debug("SSH Directory doesn't exist, creating " + ssh_dir)
      os.makedirs(ssh_dir)

    key = paramiko.RSAKey.generate(1024)
    key.write_private_key_file(os.path.expanduser(private_filepath))
    
    with open(os.path.expanduser(public_filepath),"w") as public:
      public.write("%s %s"  % (key.get_name(), key.get_base64()))

    public.close()
