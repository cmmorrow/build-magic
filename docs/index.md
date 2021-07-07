# Welcome to build-magic &#x1F528;&#x2728;

An un-opinionated, general purpose automation tool.

Build-magic is a command-line application for automating build, test, install, and deploy tasks. It's designed to be easy to use by both developers and DevOps engineers.

---

![build-magic](build-magic.gif)

Using build-magic is as simple as:

```text
> build-magic "echo hello world!"
```

But can support complex build automation with multiple steps such as:

```text
> build-magic \
--runner docker \
--environment ubuntu:latest \
--verbose \
--cleanup \
--command execute "./configure CC=c99 CFLAGS=-O2 LIBS=-lposix" \
--command build "make" \
--command test "make test" \
--command execute "tar -czf myapp.tar.gz build/*" \
--command release "jfrog rt upload myapp.tar.gz my-artifactory"
```

Build-magic can also execute a batch of commands in a config file such as:

```text
> build-magic -C release.yaml
```

Or, if the config file is named `build-magic.yaml`, can be run similar to the `make` command with:

```text
> build-magic all
```

---

Build-magic lets you work the way you want to work.

* Build and test your Linux application on a Windows laptop.
* Install and test your application in a VM.
* Automate your build, test, and deploy pipeline on your laptop or in the cloud.

Build-magic can execute commands on your local machine, on a remote server, in a Docker container, or in a virtual machine.

## What build-magic "Is"

A command-line automation tool for running commands locally, remotely, in a container, or in a VM. The complexity of what build-magic can do is limited primarily by your imagination. Build-magic strives to enable developers to simplifier their application builds in a portable, user-friendly way.

## What build-magic "Is Not"

A CI/CD tool replacement. There are plenty of great CI/CD tools out there. Build-magic isn't a replacement for Jenkins, GitLab CI, or GitHub Actions. In addition to build automation, these tools bake in notifications, post webhooks for source control events, and are generally cloud based. Build-magic is instead focused on build automation you can control locally.

CI/CD tools are extremely useful, and Jenkins, GitLab CI, and GitHub Actions can use build-magic to minimize differences between production builds in the cloud and development builds on your laptop.
