from typing import Dict
import platform
import pathlib
import os
import subprocess

# vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if platform.system() == 'Windows':
    VSWHERE = pathlib.Path(os.environ['ProgramFiles(x86)']) / \
        'Microsoft Visual Studio/Installer/vswhere.exe'
    VS = pathlib.Path(subprocess.run(
        [VSWHERE, '-latest', '-products', '*', '-requires',
            'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'],
        shell=True, check=False, capture_output=True).stdout.decode('utf-8').strip())
    VCBARS64 = VS / 'VC/Auxiliary/Build/vcvars64.bat'
    print(VCBARS64)


def decode(b: bytes) -> str:
    if platform.system() == 'Windows':
        try:
            return b.decode('cp932')
        except:
            return b.decode('utf8')
    else:
        return b.decode('utf-8')


def vcvars64() -> Dict[str, str]:
    # %comspec% /k cmd
    comspec = os.environ['comspec']
    process = subprocess.Popen(
        [comspec, '/k', VCBARS64, '&', 'set', '&', 'exit'],
        stdout=subprocess.PIPE)

    stdout = process.stdout
    if not stdout:
        raise Exception()

    # old = {k: v for k, v in os.environ.items()}

    new = {}
    while True:
        rc = process.poll()
        if rc is not None:
            break
        output = stdout.readline()
        line = decode(output)

        if '=' in line:
            k, v = line.strip().split('=', 1)
            # print(k, v)
            new[k.upper()] = v

    # diff(new, old)

    if rc != 0:
        raise Exception(rc)

    return new


if platform.system() == 'Windows':
    # for luarocks detect vc
    vc_map = vcvars64()
    os.environ['VCINSTALLDIR'] = vc_map['VCINSTALLDIR']
    os.environ['PATH'] = vc_map['PATH']
    os.environ['INCLUDE'] = vc_map['INCLUDE']
    os.environ['LIB'] = vc_map['LIB']
