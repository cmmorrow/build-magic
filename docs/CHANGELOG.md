# What's New

## Version 0.5.0

* Added the --skip switch to manually skip named stages.
* Added the current working directory to stdout.
* Fixed a regression bug that caused the bind and hostwd parameters to fail validation.

## Version 0.4.1 (Newest)

* Updated python packages.
* Fixed a cleanup action bug on Windows that prevented directories mis-identified as files from preventing cleanup.
* Fixed a cleanup action bug that prevented files in an empty working directory from being cleaned up.
* Fixed a cleanup action bug that prevented an empty directory from being deleted.
* Fixed a bug that would raise an unhandled exception if a Windows path was provided as a runtime variable.
* Fixed a cleanup action bug on Windows with the remote command runner.

## Version 0.4.0

* Added a prep section to config files.
* Added author, maintainer, version, created, and modified sections to config files.
* Added the --info option to the CLI for viewing config file meta data.
* Added dotenv file support.
* Added support for environment variables.
* Added support for command labels to optionally display instead of the command itself.
* Added support for job and stage descriptions.
* An environment can now be specified for the Local command runner and the stage will be skipped if the environment doesn't match the current OS or distribution.
* Build-magic creates and uses a custom Vagrantfile when using the Vagrant command runner and setting bind directory or envvars.
* Bugfixes

## Version 0.3.3

* Fixed a bug where an error when parsing a YAML file was not caught and handled.
* Code cleanup and style enforcement with Flake8.

## Version 0.3.2

* Updated dependencies to newer versions.

## Version 0.3.1

* Updated dependency versions.
* Improved the error message when Docker or Vagrant isn't installed.
* Fixed a bug that caused the spinner to continue running if the environment is a Docker container that cannot be found.
* Improved error handling in the case a Docker container cannot be found.
* Added a check for if a build-magic container is already running and raises an exception if so.
* Added a check to make sure the provided host working directory exists for the Docker and Vagrant runners.

## Version 0.3.0

* Added the `--template` option for generating an example Config File named build-magic_template.yaml.
* Added support for variable substitution in Config Files using the syntax `{{ VARIABLE }}` which can be substituted with **myhost** by using the command-line option `--variable VARIABLE myhost`.
* Added the `--prompt` option to interactively prompt the user for a value to substitute with `--prompt VARIABLE`.
* Fixed a bug in the cleanup action that caused directories to not be properly deleted on Windows.
* Fixed a bug where open default config files were not being properly closed on Windows.
* Fixed a bug affecting commands displayed that are too long for the terminal or end in a new line character.
* Fixed a bug where the spinner continued to run after a keyboard interrupt was received.
* Fixed a bug where using the cleanup action on Windows would cause a job to fail on startup if a file or directory raised a permission error.
* Fixed a bug that prevented stderr from a command executed in a Docker container from being displayed properly.

## Version 0.2.0

* Added the `--target` and `-t` options to execute specific config file stages by name.
* Added the ability to run specific config file stages by name passed as an argument if the config file has a default name of build-magic.yaml.
* Added a process spinner to long-running stage start up commands.
* Added the sequence number and total commands to the output for each command.
* Removed the newline character at the end of the output displayed when in verbose mode.
* Changed the stage end status from COMPLETE to DONE.

## Version 0.1.1

* Added the hammer and sparkles emoji to the terminal output.
* Suppressed the Vagrant not installed log warning.
* Updated requests to 2.25.1 in requirements.txt.
* Fixed a bug with the cleanup action that was corrupting git refs by ignoring modified files in the .git directory.
* Fixed a bug with terminal output that could cause a large empty gap of lines if build-magic is executed after running the `clear` command.

## Version 0.1.0

* Initial release. &#x1f389;
