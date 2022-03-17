# Using the build-magic Command-line Interface

## Synopsis

### Provide Commands

```text
build-magic [-r | --runner (local | remote | vagrant | docker)] 
    [-e | --environment <env>] [--name <stage>] [--wd <working-directory>] 
    [-p | --parameter <p-name p-value>]... 
    [--description] [--env <name value>]... [--dotenv <dotenv-file>]
    [--skip <stage>] [--action (default | cleanup | persist)] 
    [--fancy | --plain | --quiet] [--verbose] <command>

build-magic [-r | --runner (local | remote | vagrant | docker)] 
    [-e | --environment <env>] [--name <stage>] [--wd <working-directory>] 
    [-p | --parameter <p-name p-value>]... 
    [--description] [--env <name value>]... [--dotenv <dotenv-file>]
    [--skip <stage>] [--action (default | cleanup | persist)] 
    [--fancy | --plain | --quiet] [--verbose] [--copy <copy-from>] 
    [--continue | --stop] [-c | --command <directive command>]... 
    [<artifact>...]
```

### Provide Config Files

```text
build-magic [--fancy | --plain | --quiet] [--verbose] 
[--skip <stage name>] [-t | --target <stage name>]... 
[-v | --variable <var-name var-value>]... 
[--prompt <prompt-name>]... -C | --config <config-file>

build-magic [--fancy | --plain | --quiet] [--verbose] 
[-v | --variable <var-name var-value>]... 
[--prompt <prompt-name>]... 
all | <stage name>... | [-t | --target <stage name>]...
```

### Generate a Config File Template

```text
build-magic --template
```

### Check Config File Info

```text
build-magic --info <config-file>...
```

## Usage

There are two ways to use build-magic from the command-line.

### Specify commands to execute from the command line

Execute a single command where any arguments provided after valid options are interpreted as part of **<command\>**. For example:

```bash
> build-magic --verbose echo hello world
```

Alternatively, execute a single stage with multiple commands. This form must use one or more **[-c | --command <directive command\>]** options to specify the commands. For example:

```bash
> build-magic --verbose \
  --command execute 'echo "hello world" > hello.txt' \
  --command execute 'cat hello.txt'
```

In this form, any arguments provided after valid options are interpreted as one or more **<artifact\>**. Artifact arguments are ignored unless the **--copy** option is used. The artifacts must exist in **<copy-from\>** to be copied to the working directory. For example:

```bash
> build-magic --copy src --command build 'make' audio.c equalizer.c effects.c
```

#### Description

**--help** - Prints build-magic's help text.

**--version** - Prints the build-magic version.

**--description** - Provides a description of the executing stage.

**-r**, **--runner** - The command runner to use for executing commands. Must be one of *local*, *remote*, *vagrant* or *docker*. The default command runner is *local*.

**-e**, **--environment** - The environment to use for the specified command runner. The context of the environment depends on the command runner.

* *local* - The **environment** option is ignored.
* *remote* - The host machine to connect to in the form `user@host:port`. If port isn't provided, it will default to 22.
* *vagrant* - The path to the Vagrantfile to use for provisioning the Vagrant virtual machine.
* *docker* - The name of the container to use. Optionally, the container tag can be specified in the form `container:tag`.

If **--runner** is defined and not equal to *local*, **--environment** is required.

**--name** - Optional name **<stage\>** to give the executing stage. If **--name** isn't provided, the default stage name is 1.

**--skip** - Optional **<stage\>** name to skip.

**--env** - Key/value pairs **<name value\>** sets an environment variable to be used in the executing stage. Can be provided multiple times.

**--dotenv** - The path to a dotenv file of environment variables to set in the executing stage.

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

### Specify stages and commands to execute from a Config File

Execute multiple stages with multiple commands using a Config File. For example:

```bash
> build-magic --config my_config.yaml
```

Alternatively, **-C** (uppercase c) can be used instead of **--config**.

```bash
> build-magic -C my_config.yaml
```

A Config File in a different directory can also be used by providing the relative or absolute path to the Config File:

```bash
> build-magic --config my_project/config.yaml
```

Multiple Config Files can be specified and they will be executed in order.

```bash
> build-magic --config config1.yaml --config config2.yaml
```

Execute a specific stage in a Config File with the **--target** option. If for example, a Config File has three stages named *build*, *test*, and *deploy*, the *deploy* stage can be run on it's own with:

```bash
> build-magic --config my_config.yaml --target deploy
```

Multiple targets can be specified to change the stage execution order of a Config File. Running tests before building can be accomplished with:

```bash
> build-magic --config my_config.yaml --target test --target build
```

Alternatively, **-t** can be used instead of **--target**.

```bash
> build-magic -C my_config.yaml -t test -t build
```

Specifically named stages can be skipped with **--skip**. For example, to skip the *test* stage but still run the *build* stage use:

```bash
> build-magic -C my_config.yaml --skip test -t build
```

Named stages in a Config File can also be run similar to a Makefile by specifying the stage name:

```bash
> build-magic deploy
```

However, this usage will only work if the Config File is named one of the following default filenames:

* `build-magic.yaml`
* `build_magic.yaml`
* `build-magic.yml`
* `build_magic.yml`

To run all the stages in a default named Config File, use:

```bash
> build-magic all
```

!!! Note
    The `make` like usage is more limited than using the **--target** option. Only a single stage can be executed by name as an argument, or all stages can be executed in order with *all*. Stage names also need to be a single word. Also, a Config File must have one of the default filenames mentioned above, which also means multiple Config Files cannot be used. The Config File must also be in the directory build-magic is being executed from. If a directory has more than one of the above named files in the same directory, an error is returned when running build-magic. While convenient, it's recommended to use the **--target** option instead for these reasons.

It is also possible to use the **--target** option with a Config File that has a default filename without having to specify the Config File name with **--config**. For example:

```bash
> build-magic --target test --target build
```

!!! Note
    If running build-magic from a directory that has a Config File with a default filename and another Config File is specified with the **--config** option, both Config Files will be executed with the Config File with the default filename running first.

#### Description

**--help** - Prints build-magic's help text.

**--version** - Prints the build-magic version.

**--fancy** - This option is the default unless **--plain** or **--quiet** is used. If specified, build-magic will check to see if it's being executed in a TTY, and if so, use colored text, cursor repositioning, and format stdout to fit the terminal size. Otherwise, build-magic will assume an output width of 80 characters.

**--plain** - If specified, build-magic will write it's output to stdout in a log-like format ideal for non-interactive use.

**--quiet** - If specified, build-magic will suppress it's output to stdout.

**--verbose** - If specified, the stdout output of each command will be captured and printed after the execution of the corresponding command.

**-C**, **--config** - Executes the stages in **<config-file\>**.

**-t**, **--target** - Matches the name of a stage in the specified Config File or files to execute. If **<stage name\>** doesn't match a named stage in any of the Config Files, an error is returned. Multiple targets can be provided and each corresponding stage will be executed in the order the targets are specified.

**-v**, **--variable** - A name/value pair of **<var-name var-value\>** where the name matches a placeholder in a Config File using the syntax `{{ var-name }}` and the value is the value to substitute the placeholder with.

**--prompt** - Similar to **--variable** but only accepts a placeholder name **<prompt-name\>** and interactively prompts the user to input the value to be substituted. The input is hidden as to not be displayed in the shell history.
