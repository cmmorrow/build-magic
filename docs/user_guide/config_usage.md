# Defining build-magic config files

Build-magic supports executing multiple stages as static, repeatable jobs with a config file. A build-magic config file is a YAML file with the following structure:

```yaml
build-magic:
    - stage:
        name: Build Project
        working directory: /home/myproject
        commands:
            - build: make
    - stage:
        name: Run tests
        working directory: /home/myproject
        commands: 
            - execute: service start mydb
            - test: make test
            - execute: service stop mydb
    - stage:
        name: Package Fedora
        working directory: /home/myproject
        cleanup: true
        commands:
            - build: make rpm
            - release: jfrog rt upload "build/RPMS/x86_64/(*).rpm" my-artifactory
```

**build-magic** - Each build-magic config file must start with **build-magic** on the first line. The type of the **build-magic** property is an array of **stage** properties. The **build-magic** property must define at least one **stage**.

**stage** - Each **stage** is an object that defines the same properties as the CLI. The only property of **stage** that's required is **commands**.

**name** - Optional name to give the executing **stage**. If **name** isn't provided, the default stage name is 1, and each subsequent stage name is incremented by 1.

**runner** - The command runner to use for executing commands. The value must be one of *local*, *remote*, *vagrant* or *docker*. The default command runner is *local*.

**environment** - The environment to use for the specified command runner. If the **runner** property is defined and not equal to *local*, the **environment** property is required.

**action** The setup and teardown action to use. The value must be one of *default*, *cleanup*, or *persist*. The default action is *default*.

**continue on fail** - If *true*, build-magic will try to continue execution even if a command fails.

!!! Warning
    Depending on the commands being executed, using **continue** can lead to unstable behavior as failures can cascade to subsequent commands.

**copy from directory** - The path to copy artifacts from. If defined, build-magic will copy the array of items in **artifacts** to **working directory**.

**working directory** - The working directory the **stage** will operate from. If not specified, the default working directory is the current directory. In the case of the *local* and *remote* **runner**, the working directory is on the host machine. For the *vagrant* and *docker* **runner**, the working directory is on the guest machine, i.e. inside the virtual machine or running container.

**artifacts** - Files to be copied from the **copy from directory** to the **working directory**. Artifacts are ignored unless the **copy from directory** option is set. The artifacts must exist in **copy from directory** path to be copied to the working directory.

**parameters** - A list of key/value pairs of command runner specific configurations.

**commands** - A list of key/value pairs, where the key is a directive and the value is the command to execute.
