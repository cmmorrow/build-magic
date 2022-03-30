Name: build-magic
Version: 0.5.1rc1
%{?el7:Release: 0%{?dist}.9}
%{?el8:Release: 0%{?dist}.4}
Summary: An un-opinionated build automation tool.
BuildArch: x86_64

License: MIT
URL: https://github.com/cmmorrow/build-magic
Packager: Chris Morrow

%description
A general purpose build/install/deploy tool.

%prep
mkdir -p $RPM_BUILD_ROOT/usr/local/bin/%{name}_%{version}
cp -r $HOME/%{name}_%{version}/* $RPM_BUILD_ROOT/usr/local/bin/%{name}_%{version}
exit

%files
%dir /usr/local/bin/%{name}_%{version}
/usr/local/bin/%{name}_%{version}/*

%clean
rm -rf $RPM_BUILD_ROOT/*

%post
ln -sf /usr/local/bin/%{name}_%{version}/%{name}_%{version} /usr/local/bin/%{name}

%postun
if [ ! -f /usr/local/bin/%{name}_* ]; then
    unlink /usr/local/bin/%{name}
fi
