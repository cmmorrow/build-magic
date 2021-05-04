# Using the build-magic Command-line Interface

## Synopsis

```text
build-magic [--help | --version]

build-magic [-r | --runner (local | remote | vagrant | docker)] 
    [-e | --environment <env>] [--name <stage>] [--wd <working-directory>] 
    [-p | --parameter <p-name p-value>]... 
    [--action (default | cleanup | persist)] 
    [--fancy | --plain | --quiet] [--verbose] <command>

build-magic [-r | --runner (local | remote | vagrant | docker)] 
    [-e | --environment <env>] [--name <stage>] [--wd <working-directory>] 
    [-p | --parameter <p-name p-value>]... 
    [--action (default | cleanup | persist)] 
    [--fancy | --plain | --quiet] [--verbose] [--copy <copy-from>] 
    [--continue | --stop] [-c | --command <directive command>]... 
    [<artifact>...]

build-magic [--fancy | --plain | --quiet] [--verbose] 
[-C | --config <config-file>]
```

## Usage

There are three ways to use build-magic from the command-line.

1. Execute a single command where any arguments provided after valid options are interpreted as part of **<command\>**. For example: `build-magic --verbose echo hello world`.
2. Execute a single stage with multiple commands. This form must use one or more **[-c | --command <directive command\>]** options to specify the commands. In this form, any arguments provided after valid options are interpreted as one or more **<artifact\>**. Artifact arguments are ignored unless the **--copy** option is used. The artifacts must exist in **<copy-from\>** to be copied to the working directory.
3. Execute multiple stages with multiple commands using a config file.

## Description

**--help** - Prints build-magic's help text.

**--version** - Prints the build-magic version.

**-r**, **--runner** - The command runner to use for executing commands. Must be one of *local*, *remote*, *vagrant* or *docker*. The default command runner is *local*.

**-e**, **--environment** - The environment to use for the specified command runner. The context of the environment depends on the command runner.

* *local* - The **environment** option is ignored.
* *remote* - The host machine to connect to in the form `user@host:port`. If port isn't provided, it will default to 22.
* *vagrant* - The path to the Vagrantfile to use for provisioning the Vagrant virtual machine.
* *docker* - The name of the container to use. Optionally, the container tag can be specified in the form `container:tag`.

If **--runner** is defined and not equal to *local*, **--environment** is required.

**--name** - Optional name **<stage\>** to give the executing stage. If **--name** isn't provided, the default stage name is 1.

**--wd** - The working directory build-magic will operate from. If not specified, the default working directory is the current directory. In the case of the *local* and *remote* command runners, the working directory is on the host machine. For *vagrant* and *docker* command runners, the working directory is on the guest machine, i.e. inside the virtual machine or running container. If the **copy** option is provided along with **<artifacts\>**, the **<artifacts\>** are copied from **<copy-from\>** to **<working-directory\>**.

**-p**, **--parameter** - Key/value pairs **<p-name p-value\>** of optional command runner specific configurations. Can be provided multiple times.

**--action** - Runs the specified setup and teardown action.

* *default* - Performs container and vm setup and teardown for the *docker* and *vagrant* command runners.
* *cleanup* - Deletes any new files or newly created copies of existing files after the last command is executed and before build-magic exits.
* *persist* - Only used by the *vagrant* and *docker* command runners. If specified, the virtual machine or container won't be destroyed after build-magic exits.

The *default* action is set by default.

**--fancy** - This option is the default unless **--plain** or **--quiet** is used. If specified, build-magic will check to see if it's being executed in a TTY, and if so, use colored text, cursor repositioning, and format stdout to fit the terminal size. Otherwise, build-magic will assume an output width of 80 characters.

**--plain** - If specified, build-magic will write it's output to stdout in a log-like format ideal for non-interactive use.

**--quiet** - If specified, build-magic will suppress it's output to stdout.

**--verbose** - If specified, the stdout output of each command will be captured and printed after the execution of the corresponding command.

**--copy** - Copy **<artifacts\>** from **<copy-from\>** to **<working-directory\>**.

**--continue**, **--stop** - Default setting is **--stop**. If **--stop** is set, build-magic will exit if a command fails (returns a non-zero exit code). If **--continue** is set, build-magic will try to continue execution even if a command fails.

!!! Warning
    Depending on the commands being executed, using **--continue** can lead to unstable behavior as failures can cascade to subsequent commands.

**-c**, **--command** - A **<directive command\>** pair to execute. The command must be wrapped in quotes for build-magic to parse it correctly. For example: `--command execute "echo 'hello world'"`. Can be provided multiple times.

**-C**, **--config** - Executes the stages in **<config-file\>**.