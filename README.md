NOTE: NOT FOR PRODUCTION USE

Please note these scripts are intended to allow experimentation with
Azure Container Service. They are not intended for production use.

A set of convenience scripts for creating and testing ACS
clusters. These scripts can also be helpful in working out how to use
the REST API interfaces for managing applicaitons on an ACS cluster.

# Usage

See the [documentation](http://rgardler.github.io/acs-cli).

# Development

## Prerequisites

  * Python 3
	* `apt-get install python`
  * [PIP](https://pip.pypa.io/en/stable/installing/)
  * Azure CLI installed and configured to access the test subscription
    * install Node and NPM
    * `sudo npm install azure-cli -g`

## Preparing

To install all libraries and development dependencies:

```
sudo pip install -e .
sudo pip install -e .[test]
```

## General Use

Copy `cluster.ini` and edit accordingly.

```
acs --help
```

## Create a Service

```
acs service create
```

Once you have created your service you will likely want to open a
connection to it:

```
acs service openTunnel
```

Now you can run commands against you Azure Container Service using any
tooling compatible with your chose orchestrator, such as the Docker
CLI for the Docker Swarm version of ACS and the DC/OS cli for the
DC/OS version.

# Developing

## Adding a command

To add a top level command representing a new feature follow the
these steps (in this example the new command is called `Foo`:

  * Add the command `foo` and its description to the "Commands" section of the docstring for acs/cli.py
  * Copy `acs/commands/command.tmpl` to `acs/commands/foo.py`
    * Add the subcommands and options to the docstring of the foo.py file
    * Implement each command in a method using the same name as the command
  * Add foo.py import to `acs/commands/__init__.py`
  * Copy `tests/command/test_command.tmpl` to `test/command/test_foo.py`
    * Implement the tests
  * Run the tests with `python setup.py test` and iterate as necessary
  * Install the package with `python setup.py install`
  
## Adding a subcommand

Subcommands are applied to commands, to add a subcommand do the following:

  * Add the subcommand to the docstring of the relevant command class (e.g. foo.bar)
  * Add a method with the same name as the subcommand
  * Add a test
  * Run the tests with `python setup.py test` and iterate as necessary
  * Install the package with `python setup.py install`
  
## Testing

Run tests using [py.test:](http://pytest.org/latest) and [coverage](https://pypi.python.org/pypi/pytest-cov):

```
python setup.py test
```

Note, by default this does not run the slow tests (like creating the
cluster and installing features. You must therefore first have run the full suite of tests at least once. You can do this with:

```
py.test --runslow
```

## Releasing

Cut a release and publish to the [Python Package
Index](https://pypi.python.org/pypi) install install
[twine](http://pypi.python.org/pypi/twine. and then run:

```
python setup.py sdist bdist_wheel
twine upload dist/*
```

This will build both a surce tarball and a wheel build, which will run
on all platforms.

### Updating Documentation

To build and pucblish the documentsation:

```
cd docs
make gh-pages
cd ..
```

