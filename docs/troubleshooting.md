# Troubleshooting Common Problems With build-magic

* [RuntimeError: Click will abort further execution because Python was configured to use ASCII](troubleshooting.md#runtimeerror-click-will-abort-further-execution-because-python-was-configured-to-use-ascii)
* [Upgrading build-magic on CentOS doesn't work](troubleshooting.md#upgrading-build-magic-on-centos-doesnt-work)
* [Installing build-magic from brew is really slow](troubleshooting.md#installing-build-magic-from-brew-is-really-slow)
* [ModuleNotFoundError: No module named 'setuptools_rust'](troubleshooting.md#modulenotfounderror-no-module-named-setuptools_rust)
* [Microsoft Edge blocks downloading the build-magic Windows installer](troubleshooting.md#microsoft-edge-blocks-downloading-the-build-magic-windows-installer)

## RuntimeError: Click will abort further execution because Python was configured to use ASCII

When running build-magic for the first time on CentOS, you might encounter the following error message:

    Traceback (most recent call last):
    File "build_magic/__main__.py", line 7, in <module>
    File "click/core.py", line 1128, in __call__
    File "click/core.py", line 1034, in main
    File "click/_unicodefun.py", line 100, in _verify_python_env
    RuntimeError: Click will abort further execution because Python was configured to use ASCII as encoding for the environment. Consult https://click.palletsprojects.com/unicode-support/ for mitigation steps.

    This system lists some UTF-8 supporting locales that you can pick from. The following suitable locales were discovered: en_AG.utf8, en_AU.utf8, en_BW.utf8, en_CA.utf8, en_DK.utf8, en_GB.utf8, en_HK.utf8, en_IE.utf8, en_IN.utf8, en_NG.utf8, en_NZ.utf8, en_PH.utf8, en_SG.utf8, en_US.utf8, en_ZA.utf8, en_ZM.utf8, en_ZW.utf8
    [65] Failed to execute script '__main__' due to unhandled exception!

This is a known issue with Click, a package build-magic uses for building the command-line interface. Essentially, Python3 thinks you are restricted to using ASCII on your machine. You can read about the issue [here](https://click.palletsprojects.com/en/8.1.x/unicode-support/#surrogate-handling). The solution is to set environment variables for the locale and langauge on your system. For example, on a machine in the US, you would use:

    export LC_ALL=C.UTF-8
    export LANG=C.UTF-8

## Upgrading build-magic on CentOS doesn't work

After upgrading build-magic on CentOS, you might see the following message:

    /usr/local/bin/build-magic: No such file or directory

This happens if you installed build-magic from the RPM package and attempt to upgrade to a newer version of build-magic. This is because there's a bug in the RPM package that deletes the old version and breaks the symlink to the build-magic executable. There are two ways to solve this problem:

1. Uninstall build-magic with `yum remove build-magic` and reinstall with `yum install build-magic*.rpm`.
2. Manually add the symlink. For example, if you have build-magic version 0.5.1 installed, you need to create the symlink with `ln -s /usr/local/bin/build-magic_0.5.1/build-magic_0.5.1 /usr/local/bin/build-magic`.

## Installing build-magic from brew is really slow

Currently, installing build-magic from **brew** can take 10+ minutes because every Python package is built from source. This is because there isn't a build-magic Cask (binary) available just yet. With some patience, build-magic should install successfully.

## ModuleNotFoundError: No module named 'setuptools_rust'

This error can appear when installing build-magic using **pip**. To resolve this error, upgrade **pip** to a newer version with `python3 -m pip install --upgrade pip`.

## Microsoft Edge blocks downloading the build-magic Windows installer

The Microsoft Edge browser might block downloading the build-magic Windows installer. This is because build-magic is a fairly new application and hasn't been recognized by Microsoft's security team yet. To allow the download, click on the download icon at the top right corner of the browser. In the pop up menu, click **Keep Anyway**. Another window might appear that says Microsoft doesn't recognize the file being downloaded. In this window, again click **Keep Anyway**.

The build-magic Windows installer is uploaded to VirusTotal and the Crowd Strike Hybrid Analysis sandbox with every new version. If you are still uncomfortable installing build-magic from the Windows installer, you can alternatively install build-magic using **pip** or **pipx**.
