# Using the build-magic Command-line Interface

## Synopsis

### Provide Commands

```text
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
```

### Provide Config Files

```text
build-magic [--fancy | --plain | --quiet] [--verbose] 
[-C | --config <config-file>] [-t | --target <stage name>]...

build-magic [--fancy | --plain | --quiet] [--verbose]
[all | <stage name> | [-t | --target <stage name>]...]
```

## Usage

There are two ways to use build-magic from the command-line.

### Specify commands to execute from the command line

Execute a single command where any arguments provided after valid options are interpreted as part of **<command\>**. For example:

```sh
build-magic --verbose echo hello world
```

Alternatively, execute a single stage with multiple commands. This form must use one or more **[-c | --command <directive command\>]** options to specify the commands. For example:

```sh
build-magic --verbose \
--command execute 'echo "hello world" > hello.txt' \
--command execute 'cat hello.txt'
```

In this form, any arguments provided after valid options are interpreted as one or more **<artifact\>**. Artifact arguments are ignored unless the **--copy** option is used. The artifacts must exist in **<copy-from\>** to be copied to the working directory. For example:

```sh
build-magic --copy src --command build 'make' audio.c equalizer.c effects.c
```

### Specify stages and commands to execute from a config file

Execute multiple stages with multiple commands using a config file. For example:

```sh
build-magic --config my_config.yaml
```

A config file in a different directory can also be used by providing the relative or absolute path to the config file:

```sh
build-magic --config my_project/config.yaml
```

Multiple config files can be specified and they will be executed in order.

```sh
build-magic --config config1.yaml --config config2.yaml
```

Execute a specific stage in a config file with the `--target` option. If for example, a config file has three stages named build, test, and deploy, the deploy stage can be run on it's own with:

```sh
build-magic --config my_config.yaml --target deploy
```

Multiple targets can be specified to change the stage execution order of a config file. Running tests before building can be accomplished with:

```sh
build-magic --config my_config.yaml --target test --target build
```

Named stages in a config file can also be run similar to a Makefile by specifying the stage name:

```sh
build-magic deploy
```

However, this usage will only work if the config file is named one of the following default filenames:

* `build-magic.yaml`
* `build_magic.yaml`
* `build-magic.yml`
* `build_magic.yml`

To run all the stages in a default named config file, use:

```sh
build-magic all
```

!!! Note
    The `make` like usage is more limited than using the `--target` option. Only a single stage can be executed by name as an argument, or all stages can be executed in order with `all`. Also, a config file must have one of the default filenames mentioned above, which also means multiple config files cannot be used. The config file must also be in the directory build-magic is being executed from. If a directory has more than one of the above named files in the same directory, an error is returned when running build-magic. While convenient, it's recommended for these reasons to use the `--target` option instead.

It is also possible to use the `--target` option with a config file that has a default filename without having to specify the config filename with `--config`. For example:

```sh
build-magic --target test --target build
```

!!! Note
    If running build-magic from a directory that has a config file with a default filename and another config file is specified with the `--config` option, both config files will be executed with the config file with the default filename running first.

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

**-t**, **--target** - Matches the name of a stage in the specified config file or files to execute. If **<stage name\>** doesn't match a named stage in any of the config files, an error is returned. Multiple targets can be provided and each corresponding stage will be executed in the order the targets are specified.
