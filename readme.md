A set of convenience scripts for creating and testing ACS
clusters. These scripts can also be helpful in working out how to use
the REST API interfaces for managing applicaitons on an ACS cluster.

# Pre-requisites

  * Azure CLI installed and configured to access the test subscription
    * install Node and NPM
    * `sudo npm install azure-cli -g'
  * Install jq
    * `apt-get install jq`
  * Install Python
    * `apt-get install python`
  * Install required Python libraries
    * `pip install -r requirements.txt`
  * Whitelisted for ACS preview

# Preparation

Create a config.ini by copying config.ini.tmpl and editing accoringly.

You will need to edit (at least) the value of `dnsPrefix` as this needs
to be world unique.

# Command Line

```
$ ./acs.py --help
Usage: acs.py [options] command

Options:
  -h, --help            show this help message and exit
  -c CONFIG_FILE, --config_file=CONFIG_FILE
                        define the configuration file to use. Default is
                        'cluster.ini'
```

There are a number of accepted commands, as follows

## deploy: Create or update a cluster

The `deploy` command will create or update a deployment. 

### Create

In order to create a new cluster ensure that the `dns_prefix` in
CONFIG_FILE does not already exist.

### Update

In order to update a new cluster you will run the deployment using a
`dns_prefix` in CONFIG_FILE that already exists. The cluster will be
modified to match any updated parameters. For example, you can
increase the agent count.

## addFeature

Adds a feature to the ACS cluster. Possible features are described
below. Features can be added at deployment time by specifiying them in
a comma separated list in the cluster ini file.

```bash
./acs.py addFeature FEATURE_LIST
```

Where FEATURE_LIST is a comma separated list of features required.

### Azure File Service

Azure File Service is a storage driver that enables multiple Docker
containers to read and write to a shared folder. To add this feature
simply run:

```bash
./acs.py addFeature afs
```

This will create a Storage Account on Azure, crate a share and mount
that share on each of the agents in your cluster.

#### Known Issues

If an agent is added to the cluster it will not have the Azure File
Service feature added by default.

## delete: Delete a cluster

`delete` will delete the cluster and all associated resource.

## test: Running Tests in Clusters

`test` will deploy some test applications and ensure they are started
correctly on the cluster. The tests will be run against a cluster
defined in the cluster.ini file (or the file specified with -c).

Each script performs various actions, such as deploying a
multi-container application and verifying it is working correctly.

The log outputs of these test scripts detail the commands being run
and can therefore be useful as a learning excercise.