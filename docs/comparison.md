# Comparison with Similar Tools

There are already several great automation tools out there, so why use build-magic? First of all, build-magic is primarily focused on the problem of automating build tasks. That's why it's in the name. Here's how build-magic stacks up against similar tools.

## Make

Makefiles are tried and true. There's a reason they're still in use after 40+ years. Make allows a user to specify rules, targets, and commands to execute in a Makefile, in a very similar way to build-magic. Although it is primarily used for compiling files in C and C++ projects, Makefiles have found their way into command automation. While build-magic can certainly be used for compiling C and C++ projects, it isn't as focused on this as make is.

Make is often a popular choice in DevOps for its ubiquity and ease of integration into pipelines. This works fine so long as Make is always executing in a Unix-like operating system, because it doesn't run on Windows. Microsoft provides nmake for Windows, which has a slightly different syntax and isn't 100% compatible with Make. Build-magic has no problem executing on Windows, MacOS, or Linux. Also, Makefiles use their own specific syntax (requiring tabs), while build-magic uses YAML, which should be familiar to anyone who's used Docker, Ansible, or most CI/CD tools.

Build-magic also makes executing targets in a Docker container or virtual machine much easier compared to Make. For example, to execute several commands inside a Docker container using a Make target would involve starting a detached container, calling `docker exec` for each command, and finally `docker stop && docker rm` to stop and delete the container. Build-magic abstracts away the container management and allows the user to just worry about which commands to execute.

When using Make from the command-line, only a single target can be specified. This can often lead to a situation where rules need to be created to run multiple targets in order. The syntax for this can often be confusing for newcomers. Build-magic takes the approach of running stages in the order they're defined. If more fine-grained control is needed, the order of stages can be changed at runtime, and multiple Config Files can be specified to expand the pool of available stages to specify at runtime.

Makefile variables are a useful feature, considering Make executes each command in it's own shell. Build-magic makes use of YAML aliases and anchors for hard-coding variables, with the advantage that anchors can also be commands instead of just strings. Build-magic also allows for specifying variables at runtime and specifying new environment variables in addition to hard-coded variables.

Make does have a few advantages over build-magic. Make can implicitly skip execution on files that haven't been modified since Make last ran. Makefiles can define rules that apply to file suffixes and patterns. Gnu Make also has some imperative programming constructs like conditional statements and the foreach loop.

## Shell/Batch Scripts

Shell scripts have been used for building software for over 45 years. In fact, sometimes the fastest way to write a simple command-line tool is to knock out a quick shell script. But as the decades have rolled by, new shells have come and gone. This means old csh and ksh scripts might not run on a user's new machine.

For this reason, developers and DevOps engineers often default to writing scripts with `/bin/sh`, forgoing modern features of newer shells in the name of compatibility. Build-magic doesn't break backwards compatibility, so older Config Files will still work with newer versions of build-magic.

Shell scripts are written in an imperative programming style, compared to build-magic's declarative style. The obvious advantage shell scripts have is being able to execute conditional statements. However, this can also be a weakness as shell scripts often have to use conditional statements to check the current state of the file system before executing a command. Build-magic strives to make jobs idempotent, so that the job is executed the same way every time without side effects. If conditional statements and loops are needed for execution, a shell script can always be executed by build-magic.

## Ansible

Ansible is an automation tool that simplifies configuration management. It can be used to automate most tasks that can be performed on the command-line, but it really excels at installing software.

Ansible uses YAML files called Playbooks that describe what state a system should be in after running the Playbook. If the system is already in the desired state, no action is needed. This methodology works great for installing software but breaks down with building software. Often software needs to be built for a particular OS and architecture, which Ansible tries to abstract away. This forces a user to execute shell commands within Ansible, giving up it's biggest advantage.

With build-magic primarily focused on build automation, a user describes exactly what commands to run, without regard to the current state of the system. Build-magic runs precisely the commands you tell it to. Ansible also is very focused on managing remote systems. This is where Ansible scales really well, as build-magic cannot run a set of commands on multiple remote machines in parallel. However, build-magic can run commands in containers and virtual machines with easy; something Ansible struggles with.
