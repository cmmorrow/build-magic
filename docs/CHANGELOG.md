# What's New

## Version 0.3.1

* Updated dependency versions.

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