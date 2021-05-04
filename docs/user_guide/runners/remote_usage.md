# Using the Remote Command Runner

The *remote* Command Runner executes commands on a remote machine. To execute commands remotely, SSH needs to be installed on the host machine and configured using a public/private key pair. This way, build-magic can execute commands without prompting the user for a password.

To connect to a remote machine, the **--environment** option should include the user and hostname of the machine to connect to, for example:

```text
build-magic --verbose \
--runner remote \
--environment user@myhost \
"echo hello world"
```

Optionally, the port can also be given. By default, the port SSH will use is 22.

```text
build-magic --verbose \
--runner remote \
--environment user@myhost:2222 \
"echo hello world"
```

## Running Shell Commands

The *remote* Command Runner invokes the default shell to execute commands, allowing the use of redirection and piping.

```text
> build-magic --verbose \
--runner remote \
--environment user@myhost \
-c execute 'echo "hello world" > hello.txt' \
-c execute 'cat hello.txt'
```

```text
> build-magic --verbose \
--runner remote \
--environment user@myhost \
'ps -ef | grep python'
```

Environment variables can be included in commands by wrapping the command in single quotes:

```text
> build-magic --verbose --runner remote --environment user@myhost 'echo $SHELL'
```

## Setting the Working Directory

The Working Directory is the path that build-magic operates from. By default, the Working Directory is the home directory of user used for logging into the remote machine.

The Working Directory can be changed to any path the user has permission to read from with the `--wd` option.

```text
> build-magic --runner remote --environment user@myhost --wd ~/myproject make
```

## Cleaning Up New Files

Compiling software into executables can often produce extra files that need to be manually deleted. Build-magic can clean up these newly created files with the *cleanup* Action.

The *cleanup* Action will take a snapshot of every file and directory in the working directory before the Stage runs. At the end of the Stage, any files or directories that don't exist in the snapshot are deleted.

If there are build artifacts that shouldn't be deleted, they should be moved or deployed before the Stage ends so that they aren't deleted. These build artifacts are typically binary executables, archives, or minified code and should be pushed to an artifactory, moved, or deployed before the Stage ends.

The *cleanup* Action can be executed with the `--action` option.

```text
> build-magic --action cleanup \
--runner remote \
--environment user@myhost \
-c build 'python setup.py sdist bdist_wheel --universal' \
-c release 'twine upload dist/*'
```

## Working with Public/Private Keypairs

The *remote* Command Runner uses SSH public/private keypairs to connect to remote machines and execute commands. By default, build-magic looks for the private key at `~/.ssh/id_rsa`. The path to the private key can be specified with **--parameter keypath**:

```text
> build-magic --verbose \
--runner remote \
--environment user@myhost \
--parameter keypath ~/ssh/keys/id_rsa \
--command execute 'echo hello world'
```

Build-magic supports several different SSH key types:

* *rsa*
* *dsa*
* *ecdsa*
* *ed25519*

The SSH key type can be specified with **--parameter keytype**:

```text
> build-magic --verbose \
--runner remote \
--environment user@myhost \
--parameter keytype ecdsa \
--parameter keypath ~/.ssh/id_ecdsa \
--command execute 'echo hello world'
```

To use a private key protected by a passphrase, use **--parameter keypass**:

```text
> build-magic --verbose \
--runner remote \
--environment user@myhost \
--parameter keytype ecdsa \
--parameter keypath ~/.ssh/id_ecdsa \
--parameter keypass secret \
--command execute 'echo hello world'
```