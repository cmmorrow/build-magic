Name: build-magic
Version: 0.3.0rc0
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
/usr/local/bin/build-magic_0.3.0rc0/_cffi_backend.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/base_library.zip
/usr/local/bin/build-magic_0.3.0rc0/bcrypt/_bcrypt.abi3.so
/usr/local/bin/build-magic_0.3.0rc0/build-magic_0.3.0rc0
/usr/local/bin/build-magic_0.3.0rc0/build_magic/static/build-magic_template.yaml
/usr/local/bin/build-magic_0.3.0rc0/build_magic/static/config_schema.json
/usr/local/bin/build-magic_0.3.0rc0/certifi/cacert.pem
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/INSTALLER
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/LICENSE
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/LICENSE.APACHE
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/LICENSE.BSD
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/LICENSE.PSF
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/METADATA
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/RECORD
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/WHEEL
/usr/local/bin/build-magic_0.3.0rc0/cryptography-3.4.8.dist-info/top_level.txt
/usr/local/bin/build-magic_0.3.0rc0/cryptography/hazmat/bindings/_openssl.abi3.so
/usr/local/bin/build-magic_0.3.0rc0/importlib_metadata-4.8.1.dist-info/INSTALLER
/usr/local/bin/build-magic_0.3.0rc0/importlib_metadata-4.8.1.dist-info/LICENSE
/usr/local/bin/build-magic_0.3.0rc0/importlib_metadata-4.8.1.dist-info/METADATA
/usr/local/bin/build-magic_0.3.0rc0/importlib_metadata-4.8.1.dist-info/RECORD
/usr/local/bin/build-magic_0.3.0rc0/importlib_metadata-4.8.1.dist-info/WHEEL
/usr/local/bin/build-magic_0.3.0rc0/importlib_metadata-4.8.1.dist-info/top_level.txt
/usr/local/bin/build-magic_0.3.0rc0/jsonschema-3.2.0.dist-info/COPYING
/usr/local/bin/build-magic_0.3.0rc0/jsonschema-3.2.0.dist-info/INSTALLER
/usr/local/bin/build-magic_0.3.0rc0/jsonschema-3.2.0.dist-info/METADATA
/usr/local/bin/build-magic_0.3.0rc0/jsonschema-3.2.0.dist-info/RECORD
/usr/local/bin/build-magic_0.3.0rc0/jsonschema-3.2.0.dist-info/WHEEL
/usr/local/bin/build-magic_0.3.0rc0/jsonschema-3.2.0.dist-info/entry_points.txt
/usr/local/bin/build-magic_0.3.0rc0/jsonschema-3.2.0.dist-info/top_level.txt
/usr/local/bin/build-magic_0.3.0rc0/jsonschema/schemas/draft3.json
/usr/local/bin/build-magic_0.3.0rc0/jsonschema/schemas/draft4.json
/usr/local/bin/build-magic_0.3.0rc0/jsonschema/schemas/draft6.json
/usr/local/bin/build-magic_0.3.0rc0/jsonschema/schemas/draft7.json
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_bisect.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_blake2.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_bz2.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_codecs_cn.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_codecs_hk.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_codecs_iso2022.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_codecs_jp.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_codecs_kr.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_codecs_tw.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_csv.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_ctypes.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_datetime.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_hashlib.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_heapq.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_hmacopenssl.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_json.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_lzma.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_multibytecodec.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_opcode.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_pickle.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_posixsubprocess.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_random.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_sha3.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_socket.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_ssl.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/_struct.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/array.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/binascii.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/fcntl.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/grp.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/math.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/pyexpat.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/readline.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/resource.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/select.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/termios.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/unicodedata.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/lib-dynload/zlib.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/libbz2.so.1
/usr/local/bin/build-magic_0.3.0rc0/libcom_err.so.2
/usr/local/bin/build-magic_0.3.0rc0/libcrypto.so.10
/usr/local/bin/build-magic_0.3.0rc0/libexpat.so.1
/usr/local/bin/build-magic_0.3.0rc0/libffi-c643fa1a.so.6.0.4
/usr/local/bin/build-magic_0.3.0rc0/libffi.so.6
/usr/local/bin/build-magic_0.3.0rc0/libgssapi_krb5.so.2
/usr/local/bin/build-magic_0.3.0rc0/libk5crypto.so.3
/usr/local/bin/build-magic_0.3.0rc0/libkeyutils.so.1
/usr/local/bin/build-magic_0.3.0rc0/libkrb5.so.3
/usr/local/bin/build-magic_0.3.0rc0/libkrb5support.so.0
/usr/local/bin/build-magic_0.3.0rc0/liblzma.so.5
/usr/local/bin/build-magic_0.3.0rc0/libpcre.so.1
/usr/local/bin/build-magic_0.3.0rc0/libpython3.6m.so.1.0
/usr/local/bin/build-magic_0.3.0rc0/libreadline.so.6
/usr/local/bin/build-magic_0.3.0rc0/libselinux.so.1
/usr/local/bin/build-magic_0.3.0rc0/libssl.so.10
/usr/local/bin/build-magic_0.3.0rc0/libtinfo.so.5
/usr/local/bin/build-magic_0.3.0rc0/libz.so.1
/usr/local/bin/build-magic_0.3.0rc0/nacl/_sodium.abi3.so
/usr/local/bin/build-magic_0.3.0rc0/pvectorc.cpython-36m-x86_64-linux-gnu.so
/usr/local/bin/build-magic_0.3.0rc0/yaml/_yaml.cpython-36m-x86_64-linux-gnu.so

%clean
rm -rf $RPM_BUILD_ROOT/*

%post
ln -s /usr/local/bin/build-magic_%{version}/build-magic_%{version} /usr/local/bin/build-magic

