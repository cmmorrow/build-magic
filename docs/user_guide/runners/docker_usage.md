# Using the Docker Command Runner

The *docker* Command Runner executes commands in a container. Build-magic will start a new container named `build-magic` using the image specified by **--environment**. The container will start detached from the build-magic sub-process, use a pseudo TTY, and override the container entrypoint to `/bin/sh`.

!!! Note
    Build-magic only supports Linux-based containers with the *docker* Command Runner. Windows-based container will fail to launch.

## Running Shell Commands

The *docker* Command Runner invokes `/bin/sh` to execute commands, allowing the use of redirection and piping.

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner docker \
      --environment alpine:latest \
      -c execute 'echo "hello world" > hello.txt' \
      -c execute 'cat hello.txt'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: alpine:latest
          commands:
            - execute: echo "hello world" > hello.txt
            - execute: cat hello.txt
    ```

Environment variables can be included in commands by wrapping the command in single quotes:

=== "Command-line"

    ```bash
    > build-magic --verbose \
      --runner docker \
      --environment alpine:latest \
      'echo $TERM'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: alpine:latest
          commands:
            - execute: 'echo $TERM'
    ```

## Setting the Working Directory

When using the *docker* Command Runner, the Working Directory option **--wd** refers to the Working Directory within the container. Build-magic mounts a local directory, referred to as the Host Working Directory, to a Bind Directory in the container. The Bind Directory in the container might or might not be the same as the Working Directory.

![Working Directory Diagram](https://mermaid.ink/img/eyJjb2RlIjoiZ3JhcGggTFJcbiAgICBzdWJncmFwaCBIb3N0XG4gICAgYShIb3N0IFdvcmtpbmcgRGlyZWN0b3J5KVxuICAgIGVuZFxuICAgIHN1YmdyYXBoIENvbnRhaW5lclxuICAgIGIoQmluZCBEaXJlY3RvcnkpXG4gICAgYyhXb3JraW5nIERpcmVjdG9yeSlcbiAgICBiIC0tPiBjXG4gICAgZW5kXG4gICAgYSAtLT4gYiIsIm1lcm1haWQiOnt9LCJ1cGRhdGVFZGl0b3IiOmZhbHNlfQ)

By default, the Host Working Directory is the current directory build-magic is executed from, but can be changed with **--parameter hostwd**.

=== "Command-line"

    ```bash
    > build-magic -r docker -e alpine --parameter hostwd /home/myproject make
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: alpine
          parameters:
            hostwd: /home/myproject
          commands:
            - execute: make
    ```

The Bind Directory and Working Directory both default to `/build-magic` in the container. The Bind Directory can be changed with **--parameter bind**.

=== "Command-line"

    ```text
    > build-magic -r docker -e alpine --parameter bind /app --wd /app make
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: alpine
          working directory: /app
          parameters:
            bind: /app
          commands:
            make
    ```

Just as with every other Command Runner, the Working Directory can be changed with the **--wd** option.

## Copying Files Into the Container

By establishing a mount, all files in Host Working Directory are available from Bind Directory in the container. While it's possible to work on files in the Bind Directory, it isn't recommended for I/O intensive operations like compiling code. Docker has some overhead associated with the mount, so in situations where performance is slow, it's a good idea to instead copy files from the Bind Directory to the Working Directory.

Individual files can be copied into the container from a directory specified with the **--copy** option. If using the **--copy** option, the files to copy should be specified as arguments.

=== "Command-line"

    ```bash
    > build-magic \
      --runner docker \
      --environment alpine:latest \
      --copy /home/myproject \
      --wd /app \
      --command install "apk add gcc" \
      --command build 'make' \
      main.cpp plugins.cpp audio.cpp
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: alpine:latest
          copy from directory: /home/myproject
          working directory: /app
          artifacts:
            - main.cpp
            - plugins.cpp
            - audio.cpp
          commands:
            - install: apk add gcc
            - build: make
    ```

Instead of copying individual files to the Working Directory, an entire directory can be used by the container by setting the Host Working Directory, Bind Directory, and Working Directory:

=== "Command-line"

    ```bash
    > build-magic \
      --runner docker \
      --environment alpine:latest \
      --parameter hostwd /home/myproject \
      --parameter bind /app \
      --wd /app \
      --command install "apk add gcc" \
      --command build 'make'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: alpine:latest
          parameters:
            hostwd: /home/myproject
            bind: /app
          working directory: /app
          commands:
            - install: apk add gcc
            - build: make
    ```

## Cleaning Up New Files

Compiling software into executables can often produce extra files that need to be manually deleted. Build-magic can clean up these newly created files with the *cleanup* Action.

The *cleanup* Action will take a snapshot of every file and directory in the Host Working Directory before the Stage runs. At the end of the Stage, any files or directories that don't exist in the snapshot are deleted.

If the Working Directory is different from the Bind Directory, all files will be lost when the build-magic container is destroyed when build-magic exits. However, if the Working Directory is also the Bind Directory, any newly created files in the Host Working Directory will be deleted.

The exception is for files that are copied to the Host Working Directory from a directory specified with the **--copy** option. Since these files are copied before the Stage starts executing Commands, they will not be cleaned up when the Stage ends.

If there are build artifacts that shouldn't be deleted, they should be moved or deployed before the Stage ends so that they aren't deleted. These build artifacts are typically binary executables, archives, or minified code and should be pushed to an artifactory, moved, or deployed before the Stage ends.

The *cleanup* Action can be executed with the **--action** option.

=== "Command-line"

    ```bash
    > build-magic --action cleanup \
      -r docker \
      -e alpine:latest \
      -c build 'python setup.py sdist bdist_wheel --universal' \
      -c release 'twine upload dist/*'
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: alpine:latest
          action: cleanup
          commands:
            - build: python setup.py sdist bdist_wheel --universal
            - release: twine upload dist/*
    ```

!!! Note
    There is a special exclusion to prevent deleting files and directories that are modified inside the .git directory in the working directory to prevent git from becoming corrupted.

## Debugging the build-magic Container

If a command fails in the container for an unknown reason, the *persist* Action can be used for troubleshooting. The *persist* Action will keep the container running in the background after build-magic has exited.

=== "Command-line"

    ```bash
    > build-magic --runner docker \
      --environment alpine:latest \
      --action persist \
      --command execute "cp"
    ```

=== "Config File"

    ```yaml
    build-magic:
      - stage:
          runner: docker
          environment: alpine:latest
          action: persist
          commands:
            - execute: cp
    ```

The command `cp` will fail because it doesn't have any arguments. The container will continue to run and can be seen with:

    > docker ps all
    CONTAINER ID   IMAGE          COMMAND     CREATED          STATUS        PORTS    NAMES
    7fa0295c9d93   alpine:latest  "sh"        36 seconds ago   Up 34 seconds          build-magic

The container can be inspected by running a shell on the container with:

    > docker exec -it build-magic /bin/sh

When finished, exit the container with `exit`. The container can then be stopped and destroyed with:

    > docker stop build-magic
    > docker rm build-magic

Until the `build-magic` container is stopped and destroyed, build-magic won't be able to start a new container.
