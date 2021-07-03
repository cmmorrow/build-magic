# What's New

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
