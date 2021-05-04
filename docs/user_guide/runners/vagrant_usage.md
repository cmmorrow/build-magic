# Using the Vagrant Command Runner

The *vagrant* Command Runner executes commands in a virtual machine. Vagrant is a command line utility for creating and managing virtual machines. A specialized Ruby scripted called a Vagrantfile is used to provision the virtual machine.

Build-magic will start a new virtual machine provisioned by a specified Vagrantfile. The path to the Vagrantfile can be provided by the **--environment** option. When the Stage ends, build-magic will destroy the virtual machine so that it doesn't continue to use resources on the host machine.

!!! Note
    Virtual machines are significantly slower to start up compared to containers. Depending on the Vagrant Box used, the VM Provider configured, and the host machine resources, the virtual machine can take 30+ seconds to start up.

## Using a Virtual Machine Compared to a Container

There are a few noteworthy differences between using the *vagrant* Command Runner to execute commands in a virtual machine vs using the *docker* Command Runner to execute commands in a container.

* Virtual machines are significantly slower to start up compared to a container.
* Virtual machines typically consume more resources (CPU, memory, disk space) on the host machine compared to containers.
* Virtual machines much more closely resemble a full operating system compared to a container. This can be useful when testing package installation for a target operating system/distribution/version. Containers are relatively minimal and won't have a lot of programs or libraries available by default.

## Running Shell Commands

The *vagrant* Command Runner invokes `/bin/sh` to execute commands, allowing the use of redirection and piping.

```text
> build-magic --verbose \
--runner vagrant \
--environment Vagrantfile \
-c execute 'echo "hello world" > hello.txt' \
-c execute 'cat hello.txt'
```

Environment variables can be included in commands by wrapping the command in single quotes:

```text
> build-magic --verbose \
--runner vagrant \
--environment Vagrantfile \
'echo $TERM'
```

## Setting the Working Directory

When using the *vagrant* Command Runner, the Working Directory option **--wd** refers to the Working Directory within the virtual machine. Build-magic mounts a local directory, referred to as the Host Working Directory, to a Bind Directory in the container. The Bind Directory in the container might or might not be the same as the Working Directory.

![diagram](https://mermaid.ink/img/eyJjb2RlIjoiZ3JhcGggTFJcbiAgICBzdWJncmFwaCBIb3N0XG4gICAgYShIb3N0IFdvcmtpbmcgRGlyZWN0b3J5KVxuICAgIGVuZFxuICAgIHN1YmdyYXBoIFZpcnR1YWwgTWFjaGluZVxuICAgIGIoQmluZCBEaXJlY3RvcnkpXG4gICAgYyhXb3JraW5nIERpcmVjdG9yeSlcbiAgICBiIC0tPiBjXG4gICAgZW5kXG4gICAgYSAtLT4gYiIsIm1lcm1haWQiOnt9LCJ1cGRhdGVFZGl0b3IiOmZhbHNlfQ)

By default, the Host Working Directory is the current directory build-magic is executed from, but can be changed with **--parameter hostwd**.

```text
> build-magic -r vagrant -e . --parameter hostwd /home/myproject make
```

Unlike the *docker* Command Runner, the Working Directory and Bind Directory for the *vagrant* Command Runner do not default to the same directory. The Working Directory defaults to `/home/vagrant` and the Bind Directory defaults to `/vagrant`. This means if you want the Working Directory to be set to the Bind Directory, the **--wd** option must be used to set the Working Directory to `/vagrant`.

```text
> build-magic -r vagrant -e . --wd /vagrant make
```

!!! Note
    The bind directory is set from the Vagrantfile with `config.vm.synced_folder`, and therefore cannot be controlled by build-magic.

## Copying Files Into the Virtual Machine

By establishing a mount, all files in Host Working Directory are available from Bind Directory in the virtual machine. While it's possible to work on files in the Bind Directory, it isn't recommended for I/O intensive operations like compiling code. Some of the shared folder implementations Vagrant uses have significant overhead associated with the mount, so in situations where performance is slow, it's a good idea to instead copy files from the Bind Directory to the Working Directory.

Individual files can be copied into the container from a directory specified with the **--copy** option. If using the **--copy** option, the files to copy should be specified as arguments.

```text
> build-magic \
--runner vagrant \
--environment Vagrantfile \
--copy /home/myproject \
--command install "apk add gcc" \
--command build 'make' \
main.cpp plugins.cpp audio.cpp
```

Instead of copying individual files to the Working Directory, an entire directory can be used by the virtual machine by setting the Host Working Directory and Working Directory:

```text
> build-magic \
--runner vagrant \
--environment Vagrantfile \
--parameter hostwd /home/myproject \
--wd /app \
--command install "apk add gcc" \
--command build 'make'
```

## Cleaning Up New Files

Compiling software into executables can often produce extra files that need to be manually deleted. Build-magic can clean up these newly created files with the *cleanup* Action.

The *cleanup* Action will take a snapshot of every file and directory in the Host Working Directory before the Stage runs. At the end of the Stage, any files or directories that don't exist in the snapshot are deleted.

If the Working Directory is different from the Bind Directory, all files will be lost when the virtual machine is destroyed when build-magic exits. However, if the Working Directory is the also the Bind Directory, any newly created files in the Host Working Directory will be deleted.

The exception is for files that are copied to the Host Working Directory from a directory specified with the **--copy** option. Since these files are copied before the Stage starts executing Commands, they will not be cleaned up when the Stage ends.

If there are build artifacts that shouldn't be deleted, they should be moved or deployed before the Stage ends so that they aren't deleted. These build artifacts are typically binary executables, archives, or minified code and should be pushed to an artifactory, moved, or deployed before the Stage ends.

The *cleanup* Action can be executed with the `--action` option.

```text
> build-magic --action cleanup \
-c build 'python setup.py sdist bdist_wheel --universal' \
-c release 'twine upload dist/*'
```

## Debugging the Virtual Machine

If a command fails in the container for an unknown reason, the *persist* Action can be used for troubleshooting. The *persist* Action will keep the container running in the background after build-magic has exited.

```text
> build-magic --runner vagrant \
--environment Vagrantfile \
--action persist \
--command execute "cp"
```

The command `cp` will fail because it doesn't have any arguments. The virtual machine will continue to run and can be accessed with:

```text
> vagrant ssh
```

When finished, exit the virtual machine with `exit`. The virtual machine can then be stopped and destroyed with:

```text
> vagrant destroy
```
