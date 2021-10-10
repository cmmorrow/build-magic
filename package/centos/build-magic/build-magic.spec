Name: build-magic
Version: 0.3.0
Release: 0%{?dist}.9
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
%dir /usr/local/bin/build-magic_%{version}
/usr/local/bin/build-magic_%{version}/*

%clean
rm -rf $RPM_BUILD_ROOT/*

%post
ln -s /usr/local/bin/build-magic_%{version}/build-magic_%{version} /usr/local/bin/build-magic

%preun
unlink /usr/local/bin/build-magic

