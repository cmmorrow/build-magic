Name: build-magic
Version: 0.3.0rc3
Release: 0%{?dist}
Summary: An un-opinionated build automation tool.
BuildArch: x86_64

License: MIT
URL: https://github.com/cmmorrow/build-magic
Packager: Chris Morrow

%description
A general purpose build/install/deploy tool.

%prep
mkdir -p $RPM_BUILD_ROOT/usr/local/bin/build-magic_%{version}
cp -r $HOME/build-magic_%{version}/* $RPM_BUILD_ROOT/usr/local/bin/build-magic_%{version}
exit

%files
/usr/local/bin/build-magic_%{version}/*

%clean
rm -rf $RPM_BUILD_ROOT/*

%post
ln -s /usr/local/bin/build-magic_%{version}/build-magic_%{version} /usr/local/bin/build-magic

