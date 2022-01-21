# Basic Usage

## Running a single command

You can run a single command from the command-line with:

    > build-magic --verbose echo hello world

![single command output](docs/../../static/single_command.svg)

The arguments to *build-magic* are executed as a single command and the **--verbose** option prints the output of the command.

## Changing the output format

Build-magic's output can be changed to a more log-like appearance with the **--plain** option.

```bash
> build-magic --verbose --plain echo hello world
```

![plain output](docs/../../static/plain_output.svg)

## Using command runners

Build-magic can run commands locally, remotely via SSH, in a Docker container, or in a VM via Vagrant. The following commands all print the same output, but are run in different environments:

```bash
> build-magic --verbose echo hello world
```

```bash
> build-magic --verbose --runner remote -e user@myhost echo hello world
```

```bash
> build-magic --verbose --runner docker -e alpine:latest echo hello world
```

```bash
> build-magic --verbose --runner vagrant -e Vagrantfile echo hello world
```

## Running multiple commands

Multiple commands can be run from the command-line using the **--command** or **-c** option which takes two values, a directive and a command wrapped in quotes. Multiple commands can similarly be run from a Config File:

=== "Command-line"

    ```bash
    > build-magic \
      --command execute "./configure CC=c99 CFLAGS=-O2 LIBS=-lposix" \
      --command build "make build" \
      --command test "make test" \
      --command execute "tar -czf myapp.tar.gz build/*" \
      --command release "jfrog rt upload myapp.tar.gz my-artifactory"
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          commands:
            - execute: ./configure CC=c99 CFLAGS=-O2 LIBS=-lposix
            - build: make build
            - test: make test
            - execute: tar -czf myapp.tar.gz build/*
            - release: jfrog rt upload myapp.tar.gz my-artifactory
    ```

## Running commands from a Config File

If you have a build-magic Config File named *myproject.yaml*, you can run the commands in the Config File with the **--config** or **-C** option:

    > build-magic -C myproject.yaml

![multi command output](docs/../../static/multi_command.svg)

## Running a Config File with multiple Stages

One of the advantages of running commands from a Config File compared to the command-line is being able to run multiple Stages. A Stage is a group of commands that are run together and executed in order. By default, if a command in a Stage fails, build-magic will move on to executing commands in the next Stage. Typically, you want to batch together commands related to a particular task into a Stage.

Consider the contrived example below:

```bash
> build-magic \
--runner docker \
--environment ubuntu:latest \
--verbose \
--command execute "echo hello > file1.txt" \
--command execute "echo world > file2.txt" \
--command build "tar -czf myfiles.tar.gz file1.txt file2.txt" \
--command execute "rm file1.txt file2.txt" \
--command install "tar -xzf myfiles.tar.gz" \
--command test "cat file1.txt file2.txt" \
--command execute "rm file1.txt file2.txt" \
--command execute "rm myfiles.tar.gz"
```

We can group related commands into Stages in a Config File:

```yaml
build-magic:
  - stage:
      name: Setup
      runner: docker
      environment: ubuntu:latest
      commands:
        - execute: echo hello > file1.txt
        - execute: echo world > file2.txt
  - stage:
      name: Archive
      runner: docker
      environment: ubuntu:latest
      commands:
        - build: tar -czf myfiles.tar.gz file1.txt file2.txt
          label: Archive the files as myfiles.tar.gz
        - execute: rm file1.txt file2.txt
          label: Delete the original files
  - stage:
      name: Un-Archive
      runner: docker
      environment: ubuntu:latest
      commands:
        - install: tar -xzf myfiles.tar.gz
          label: Extract the archive to the current directory
  - stage:
      name: Result
      runner: docker
      environment: ubuntu:latest
      commands:
        - test: cat file1.txt file2.txt
        - execute: rm file1.txt file2.txt
          label: Cleanup the files
        - execute: rm myfiles.tar.gz
          label: Cleanup the archive
```

Config Files are written in YAML, using a simple syntax. Commands are grouped together into Stages. Each **stage** can optionally have a **name**, **runner**, **description**, and **environment**. Commands are listed with a directive first, followed by a colon (*:*), followed by the command.

Directives don't have any special meaning in build-magic, but are simply descriptive. The available directives are:

* **execute**
* **build**
* **install**
* **test**
* **deploy**
* **release**

Each command can optionally define a **label** to be displayed in the output instead of the command being executed.

Naming this file *example.yaml*, you can run it with:

```bash
> build-magic -C example.yaml --verbose
```

![archive config output](docs/../../static/archive_config.svg)

A single Stage in a Config File can be run with:

```bash
> build-magic --config example.yaml --target Setup
```

![setup config output](docs/../../static/setup_config.svg)

Individual Stages can be executed using the **--target** or **-t** option. The Stages will be executed in the order listed on the command-line.

```bash
> build-magic --config example.yaml -t Setup -t Result --verbose
```

![archive error output](docs/../../static/archive_error.svg)

The last command fails because the archive file was never created.

## Continue on fail

You can tell build-magic to continue executing even if a command fails by adding **--continue** on the command-line to continue after fails in all Stages:

```bash
> build-magic -C example.yaml -t Setup -t Result --verbose --continue
```

![archive continue output](docs/../../static/archive_continue.svg)

## Code reuse with anchors

YAML anchors and aliases can be used to reuse repeated values. In the Config File above, the command `rm file1.txt file2.txt` is used more than once, and the same runner and environment is used for each Stage. These values can be replaced with anchors and called with aliases. YAML anchors can be defined in a **prepare** section of the Config File:

```yaml
prepare:
  - &delete_files
      rm file1.txt file2.txt
  - &runner
      docker
  - &environment
      ubuntu:latest
build-magic:
  - stage:
      name: Setup
      runner: *runner
      environment: *environment
      commands:
        - execute: echo hello > file1.txt
        - execute: echo world > file2.txt
  - stage:
      name: Archive
      runner: *runner
      environment: *environment
      commands:
        - build: tar -czf myfiles.tar.gz file1.txt file2.txt
          label: Archive the files as myfiles.tar.gz
        - execute: *delete_files
          label: Delete the original files
  - stage:
      name: Un-Archive
      runner: *runner
      environment: *environment
      commands:
        - install: tar -xzf myfiles.tar.gz
          label: Extract the archive to the current directory
  - stage:
      name: Result
      runner: *runner
      environment: *environment
      commands:
        - test: cat file1.txt file2.txt
        - execute: *delete_files
          label: Cleanup the files
        - execute: rm myfiles.tar.gz
          label: Cleanup the archive
```

The execution of this Config File is identical to the previous one.

## Cleanup action

Instead of using a command to manually delete files, you can use the cleanup action with **--action** *cleanup* on the command-line or **action:** *cleanup* in a Config File which will delete all new files that were created during a build-magic Stage.

=== "Command-line"

    ```yaml
    > build-magic \
    --name Setup \
    --runner docker \
    --environment ubuntu:latest \
    --action cleanup \
    --command execute 'echo hello > file1.txt' \
    --command execute 'echo world > file2.txt' \
    --command test 'cat file1.txt file2.txt'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          name: Setup
          runner: docker
          environment: ubuntu:latest
          action: cleanup
          commands:
            - execute: echo hello > file1.txt
            - execute: echo world > file2.txt
            - test: cat file1.txt file2.txt
    ```

After running this Config File, the files *file1.txt* and *file2.txt* will be automatically deleted without touching any other files in the directory.

## Using environment variables

Commands executed by build-magic can use environment variables as if the command was being executed from the shell, but they cannot set new environment variables. This is because each command is atomic and executed in it's own shell environment, so setting an environment variable in one command doesn't carry over to another.

If you want to provide new environment variables for a Stage, use the **environment variable** key in a **stage**, followed by key/value pairs where each key is the name of the environment variable. For example:

```yaml
build-magic:
  - stage:
      environment variables:
        FOO: hello
        BAR: world
      commands:
        - execute: echo $FOO $BAR
```

Running the Config File above named *example.yaml*:

```bash
> build-magic -C example.yaml --verbose
```

![envvars command output](docs/../../static/envvars_command.svg)

The equivalent command can be run solely from the command-line with:

```bash
> build-magic --env FOO hello --env BAR world --verbose echo '$FOO' '$BAR'
```

If you need to set multiple environment variables or use different environments for development vs production, you can use a dotenv file per **stage**:

```yaml
build-magic:
  - stage:
      dotenv: develop.env
      commands:
        - execute: echo $FOO $BAR
```

In this example, the content of *develop.env* is:

```cfg
FOO=hello
BAR=world
```

Dotenv files can also be used when running commands from the command-line:

```bash
> build-magic --dotenv develop.env --verbose echo '$FOO' '$BAR'
```

## Using runtime variables

Variables can be substituted into a Config File at runtime. A special syntax is used to mark runtime variables in a Config File and the values to use are specified by the user on the command-line with the **--variable** or **-v** option. Consider the following Config File:

```yaml
build-magic:
  - stage:
      commands:
        - execute: >
          curl -u {{ user }}:{{ password }} 
          https://myrepo/myproject/{{ version }}
```

The double braces `{{}}` indicate a runtime variable that should be substituted at runtime. The following will substitute values into the Config File and successfully run the command:

```bash
> build-magic -v user vision -v password wanda -v version 12 -C config.yaml
```

![cleartext command output](docs/../../static/cleartext_command.svg)

You can see in the output that the values were substituted into the command, however, it's a bad idea to supply passwords and other secrets in clear text. Instead, you can use the **--prompt** option which will interactively prompt the user for input and hide what is typed.

```bash
> build-magic -v user --prompt password -v version 12 -C config.yaml
> password:
```

![prompt command output](docs/../../static/prompt_command.svg)

You can see that the prompt for `password` doesn't print any text that is typed, and the prompted value isn't displayed in the output either.

## Changing the working directory

By default, build-magic runs in the current directory, but you can override the default by specify the working directory with **working directory** in a Config File or **--wd** from the command-line. For example, the following will set the working directory to *~/myprojects/app* regardless of the shell's current directory:

=== "Command-line"

    ```bash
    > build-magic \
      --wd ~/myprojects/app \
      --command execute "./configure CC=c99 CFLAGS=-O2 LIBS=-lposix" \
      --command build "make build" \
      --command test "make test" \
      --command execute "tar -czf myapp.tar.gz build/*" \
      --command release "jfrog rt upload myapp.tar.gz my-artifactory"
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          working directory: ~/myprojects/app
          commands:
            - execute: ./configure CC=c99 CFLAGS=-O2 LIBS=-lposix
            - build: make build
            - test: make test
            - execute: tar -czf myapp.tar.gz build/*
            - release: jfrog rt upload myapp.tar.gz my-artifactory
    ```

The **working directory** always refers to the directory where build-magic executes commands, regardless of which runner is used. For example if we execute the commands above in a Docker container, the working directory *~/myprojects/app* will refer to a path in the container.

=== "Command-line"

    ```bash
    > build-magic \
      --runner docker \
      --environment ubuntu:latest \
      --wd ~/myprojects/app \
      --command execute "./configure CC=c99 CFLAGS=-O2 LIBS=-lposix" \
      --command build "make build" \
      --command test "make test" \
      --command execute "tar -czf myapp.tar.gz build/*" \
      --command release "jfrog rt upload myapp.tar.gz my-artifactory"
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: ubuntu:latest
          working directory: ~/myprojects/app
          commands:
            - execute: ./configure CC=c99 CFLAGS=-O2 LIBS=-lposix
            - build: make build
            - test: make test
            - execute: tar -czf myapp.tar.gz build/*
            - release: jfrog rt upload myapp.tar.gz my-artifactory
    ```

## Including files

Files can be copied from another directory into the working directory using **copy from directory** in a Config File or the **--copy** option on the command-line:

=== "Command-line"

    ```bash
    > build-magic \
    --copy myproject/src \
    -c execute "go build main.go" \
    audio.go equalizer.go effects.go
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          copy from directory: myproject/src
          artifacts:
            - audio.go
            - equalizer.go
            - effects.go
        commands:
          - execute: go build main.go
    ```

## Adding metadata to Config Files

Config Files can contain additional info that isn't used directly by build-magic, but is useful for documenting Config Files. These metadata fields are:

* **author**
* **maintainer**
* **version**
* **created**
* **modified**
* **description**

Each of these fields are user definable, as build-magic doesn't enforce any constraints on their formatting.

```yaml
version: 0.1.0
author: The Vision
created: 2021-12-12
description: An example build-magic Config File.
build-magic:
  - stage:
      commands:
        - execute: echo hello world
```

## Viewing Config File metadata

You can get a high-level summary of a Config File by using the **--info** option to view the Stage names, runtime variables, and metadata. Consider the Config File below:

```yaml
maintainer: Hawkeye
version: 1.0.4
prepare:
  - &clone_repo
      git clone --depth 1 --branch v{{ version }} some/git/repo.git
  - &get_release_id >
      curl -s -u {{ user }}:{{ password }} api/some/git/repo/releases/v{{ version }} |
      jq .id > RELEASE_ID
build-magic:
  - stage:
      name: debian
      runner: docker
      environment: debian:latest
      working directory: /app
      commands:
        - execute: apt update
        - install: apt install -y gcc make curl jq git
        - execute: *clone_repo
        - build: make all
        - test: ./myapp --help
        - execute: mkdir -p $HOME/myapp/usr/local/bin
        - execute: mkdir -p $HOME/myapp/DEBIAN
        - execute: cp $HOME/control $HOME/myapp/DEBIAN
        - execute: cp /app/myapp /$HOME/myapp/usr/local/bin
        - build: dpkg-deb --build $HOME/myapp
        - execute: *get_release_id
        - release: >
            curl -u {{ user }}:{{ password }}
            --data-binary @"$HOME/myapp.deb"
            -H "Content-Type: application/octet-stream"
            uploads/some/git/repo/releases/$(cat RELEASE_ID)/assets?name=myapp.deb
  - stage:
      name: centos
      runner: docker
      environment: centos:latest
      working directory: /app
      commands:
        - install: yum install -y rpmdevtools git
        - install: yum install -y epel-release
        - install: yum install jq
        - execute: *clone_repo
        - build: make all
        - test: ./myapp --help
        - execute: rpmdev-setuptree
        - execute: mkdir -p $HOME/rpmbuild/RPMS/x86_64
        - execute: cp $HOME/myapp.spec $HOME/rpmbuild/SPECS
        - build: rpmbuild -bb --target x86_64 $HOME/rpmbuild/SPECS/myapp.spec
        - execute: *get_release_id
        - execute: ls $HOME/rpmbuild/RPMS/x86_64/* | xargs basename > NAME
        - release: >
            curl -u {{ user }}:{{ password }}
            --data-binary @$(ls $HOME/rpmbuild/RPMS/x86_64/*)
            -H "Content-Type: application/octet-stream"
            uploads/some/git/repo/releases/$(cat RELEASE_ID)/assets?name=$(cat NAME)
```

To get a high-level summary of this Config File named *myapp.yaml*, simply run:

```bash
> build-magic --info myapp.yaml
```

![single info output](docs/../../static/single_info.svg)

You can get a high-level summary of multiple Config Files by passing more than one Config File path as an argument to the **--info** option:

```bash
> build-magic --info myapp.yaml config.yaml
```

![multi info output](docs/../../static/multi_info.svg)

## Specifying a local environment

Optionally, when running a Stage locally, you can specify a local environment for the Stage to run in. You might want to do this to ensure a Stage with Debian Linux specific commands doesn't run on Red Hat Enterprise Linux, or Windows Powershell commands don't run on MacOS. If the operating system (or Linux distribution) doesn't match the current machine, build-magic will skip the Stage.

For example, if running CentOS Linux and specifying the local environment as *debian*, the Stage will be skipped:

```bash
> build-magic -r local -e debian --verbose echo hello world
```

![skip debian output](docs/../../static/skip_debian.svg)

If running MacOS and specifying *windows*:

```bash
> build-magic -r local -e windows --verbose echo hello world
```

![skip windows output](docs/../../static/skip_windows.svg)

However, if the the local machine matches the specified environment, the Stage will be executed. For example, if running MacOS and specifying the environment should be *macos*:

```bash
> build-magic -r local -e macos --verbose echo hello world
```

![single command output](docs/../../static/single_command.svg)

## Default Config File names and target arguments

If a Config File has a default name such as *build-magic.yaml*, you can provide a target name as an argument, similar to calling targets in a Makefile with *make*:

```bash
> build-magic Setup
```

You can run all Stages in a Config File using the special target *all*:

```bash
> build-magic all
```

The accepted default Config File names are:

* *build-magic.yaml*
* *build_magic.yaml*
* *build-magic.yml*
* *build_magic.yml*
