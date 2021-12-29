# Using the Remote Command Runner

The *remote* Command Runner executes commands on a remote machine. To execute commands remotely, SSH needs to be installed on the host machine and configured using a public/private key pair. This way, build-magic can execute commands without prompting the user for a password.

!!! Note
    To connect to or from a Windows 10 or 11 machine, OpenSSH needs to be installed on the Windows machine. Build-magic isn't compatible with other Windows SSH implementations or PuTTY **.ppk** files. You can find instructions on installing OpenSSH for Windows 10 [here](https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse).

To connect to a remote machine, the **--environment** option should include the user and hostname of the machine to connect to, for example:

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner remote \
      --environment user@myhost \
      "echo hello world"
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          commands:
            - execute: echo hello world
    ```

Optionally, the port can also be given. By default, the port SSH will use is 22.

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner remote \
      --environment user@myhost:2222 \
      "echo hello world"
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost:2222
          commands:
            - execute: echo hello world
    ```

## Running Shell Commands

The *remote* Command Runner invokes the default shell to execute commands, allowing the use of redirection and piping.

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner remote \
      --environment user@myhost \
      -c execute 'echo "hello world" > hello.txt' \
      -c execute 'cat hello.txt'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          commands:
            - execute: echo "hello world" > hello.txt
            - execute: cat hello.txt
    ```

---

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner remote \
      --environment user@myhost \
      'ps -ef | grep python'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          commands:
            - execute: ps -ef | grep python
    ```

Environment variables can be included in commands by wrapping the command in single quotes:

=== "Command-line"

    ```bash
    > build-magic --verbose -r remote -e user@myhost 'echo $SHELL'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          commands:
            - execute: 'echo $SHELL'
    ```

## Setting the Working Directory

The Working Directory is the path that build-magic operates from. By default, the Working Directory is the home directory of user used for logging into the remote machine.

The Working Directory can be changed to any path the user has permission to read from with the **--wd** option.

=== "Command-line"

    ```bash
    > build-magic --runner remote --environment user@myhost --wd ~/myproject make
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          working directory: ~/myproject
          commands:
            - execute: make
    ```

## Copying Files To The Remote Machine

Individual files can be copied to the remote machine from a directory specified with the **--copy** option. If using the **--copy** option, the files to copy should be specified as arguments.

=== "Command-line"

    ```bash
    > build-magic \
      --runner remote \
      --environment user@myhost \
      --copy /home/myproject \
      --command execute ./configure \
      --command build 'make' \
      main.cpp plugins.cpp audio.cpp
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          copy from directory: /home/myproject
          artifacts:
            - main.cpp
            - plugins.cpp
            - audio.cpp
          commands:
            - execute: ./configure
            - execute: make
    ```

## Cleaning Up New Files

Compiling software into executables can often produce extra files that need to be manually deleted. Build-magic can clean up these newly created files on the remote machine with the *cleanup* Action.

The *cleanup* Action will take a snapshot of every file and directory in the working directory on the remote machine before the Stage runs. At the end of the Stage, any files or directories that don't exist in the snapshot are deleted.

If there are build artifacts that shouldn't be deleted, they should be moved or deployed before the Stage ends so that they aren't deleted. These build artifacts are typically binary executables, archives, or minified code and should be pushed to an artifactory, moved, or deployed before the Stage ends.

The *cleanup* Action can be executed with the **--action** option.

=== "Command-line"

    ```bash
    > build-magic --action cleanup \
      --runner remote \
      --environment user@myhost \
      -c build 'python setup.py sdist bdist_wheel --universal' \
      -c release 'twine upload dist/*'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          action: cleanup
          commands:
            - build: python setup.py sdist bdist_wheel --universal
            - release: twine upload dist/*
    ```

!!! Note
    There is a special exclusion to prevent deleting files and directories that are modified inside the .git directory in the working directory to prevent git from becoming corrupted.

If using the **--copy** option to copy files to the working directory on the remote machine, these files are deleted along with any new files created during the Stage.

## Working with Public/Private Keypairs

The *remote* Command Runner uses SSH public/private keypairs to connect to remote machines and execute commands. By default, build-magic looks for the private key at `~/.ssh/id_rsa`. The path to the private key can be specified with **--parameter keypath**:

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner remote \
      --environment user@myhost \
      --parameter keypath ~/.ssh/keys/id_rsa \
      --command execute 'echo hello world'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          parameters:
            - keypath: ~/.ssh/keys/id_rsa
          commands:
            - execute: echo hello world
    ```

Build-magic supports several different SSH key types:

* *rsa*
* *dsa*
* *ecdsa*
* *ed25519*

The SSH key type can be specified with **--parameter keytype**:

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner remote \
      --environment user@myhost \
      --parameter keytype ecdsa \
      --parameter keypath ~/.ssh/id_ecdsa \
      --command execute 'echo hello world'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          parameters:
            - keytype: ecdsa
            - keypath: ~/.ssh/id_ecdsa
          commands:
            - execute: echo hello world
    ```

To use a private key protected by a passphrase, use **--parameter keypass**:

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner remote \
      --environment user@myhost \
      --parameter keytype ecdsa \
      --parameter keypath ~/.ssh/id_ecdsa \
      --parameter keypass secret \
      --command execute 'echo hello world'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: remote
          environment: user@myhost
          parameters:
            - keytype: ecdsa
            - keypath: ~/.ssh/id_ecdsa
            - keypass: secret
          commands:
            - execute: echo hello world
    ```

## A Note on Setting Environment Variables

By default, OpenSSH doesn't allow for environment variables to be set on a remote machine because it's a security risk. Unless sshd is explicitly configured to allow for setting environment variables on the remote machine, passing environment variables or a dotenv file through the command-line or a Config File will have no effect. More info on the process for configuring sshd to allow environment variables can be found [here](https://man.openbsd.org/sshd#LOGIN_PROCESS).
