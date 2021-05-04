# Getting Started

## Requirements

The build-magic project is written in Python and is cross-platform.

* Operating System: MacOS, Windows, or Linux
* Python 3.6+
* Docker (optional)
* Vagrant (optional)
* OpenSSH (optional)

## Installation

### Installing From PyPI

You can install build-magic using [pip](http://pip-installer.org/) with the following command:

```text
pip install build-magic
```

Alternatively, if you want build-magic to run from an isolated environment, you can use:

```text
pipx install build-magic
```

### Installing From Source

The build-magic project is written in Python. First, create a new virtual environment for development with:

```text
python3 -m venv /path/to/new/virtual/environment
```

Alternatively, you can create a virtual environment with `conda` or `virtualenv`. Be sure to activate your virtual environment with:

```text
source /path/to/new/virtual/environment/bin/activate
```

Next, navigate to the directory where you want to install build-magic and clone the [repository](https://github.com/cmmorrow/build-magic) using HTTPS with:

```text
git clone https://github.com/cmmorrow/build-magic.git
```

Or using SSH with:

```text
git clone git@github.com:cmmorrow/build-magic.git
```

Or using the GitHub CLI with:

```text
gh repo clone cmmorrow/build-magic
```

### Getting The Most Out of build-magic With Optional Command Runners

In addition to running commands on your machine, build-magic can also run commands in a virtual machine, a Docker container, or on a remote machine.

#### Using Docker

To use build-magic to run commands in a container, you will need to have [Docker](https://www.docker.com/) installed. Instructions on how to install Docker can be found [here](https://docs.docker.com/get-docker/).

#### Using A Virtual Machine

Build-magic can execute commands in a virtual machine via [Vagrant](https://www.vagrantup.com/). Vagrant is a command-line tool for controlling virtual machines. Instructions on how to install Vagrant can be found [here](https://www.vagrantup.com/docs/installation).

#### Using a Remote Machine

Build-magic can execute commands on a remote machine via [SSH](https://www.openssh.com/). To allow remote command execution, SSH client needs to be installed on the local machine and SSH server needs to be installed and running on the remote machine.

If you're using MacOS or Linux, both SSH client and SSH server should be installed. If you are using Windows 10, SSH client and SSH server are installable features. Instructions for installing SSH on Windows 10 or Windows Server 2019 can be found [here](https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse).

Currently, build-magic only supports SSH connections via public/private key pairs for password-less login. Password-less login needs to be working before build-magic can make use of remote command execution. You can read more about how to configure public/private key pairs on [SSH.com](https://www.ssh.com/ssh/key/).

## Basic Usage

You can verify build-magic is install by running the following command from a command prompt:

```text
build-magic --verbose 'echo Hello World!'
```

You should see build-magic run and output `Hello World!`
