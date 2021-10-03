import os, sys, importlib, subprocess, platform, glob, json
from konsoru import CLI
from konsoru.decorators import parameter

OPTION_CONFIG_EXAMPLE = '''
{
    "data": [
        {
            "module_name": "tkfilebrowser",
            "system": "Windows",
            "data": [
                {
                    "src": "{tkfilebrowser.__path__[0]}\\images\\*.png",
                    "dst": "tkfilebrowser\\images"
                }
            ]
        }
    ],
    "binary": [
        {
            "module_name": "python-magic-bin",
            "import_name": "magic",
            "system": "Windows",
            "args": [
                {
                    "src": "{os.path.dirname(sys.executable)}\\Lib\\site-packages\\magic\\libmagic\\libmagic.dll",
                    "dst": "magic\\libmagic"
                },
                {
                    "src": "{os.path.dirname(sys.executable)}\\Lib\\site-packages\\magic\\libmagic\\magic.mgc",
                    "dst": "magic\\libmagic"
                }
            ]
        },

        {
            "system": "Windows",
            "system_version": "7",
            "args": [
                {
                    "src": "C:\\Program Files (x86)\\Windows Kits\\10\\Redist\\ucrt\\DLLs\\x64\\*.dll",
                    "dst": "."
                }
            ]
        }
    ],
    "hidden_import": [
        {
            "system": "Windows",
            "name": "win32api"
        }
    ]
}
'''

sysname2shortname = {
    'Windows': 'win',
    'Darwin': 'macos',
    'Linux': 'linux',
}
sysname = platform.platform()
if sysname.startswith('Windows-'):
    sysname = 'Windows'
sysver, _, _, _ = platform.win32_ver()    # returns empty string on other OS so it's okay

cli = CLI()


def find_python3_command():
    proc = subprocess.run('python --version', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        out = proc.stdout.decode()
        if out.startswith('Python 3.'):
            return 'python'
    proc = subprocess.run('python3 --version', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        out = proc.stdout.decode()
        if out.startswith('Python 3.'):
            return 'python3'
    raise RuntimeError('Cannot find python 3 command for some reason...')


def format_literal(s, globals=None, locals=None):
    s = s.replace("'", "\\'")
    return eval("f'%s'" % s, globals, locals)


def pip_install(module, python3_cmd=None, update=False):
    if python3_cmd is None:
        python3_cmd = find_python3_command()
    cmd = [python3_cmd, '-m', 'pip', 'install'] + (['-U'] if update else []) + [module]
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise RuntimeError('Failed to install %s!' % module)


def meets_target_system_requirement(system_name=None, system_version=None):
    if system_name is None:
        return True

    if system_name == sysname:
        if system_version is None:
            return True
        return sysver == '' or system_version == sysver

    return False


def remove_rf(path):
    path = glob.glob(path)
    if len(path) == 1:
        path = path[0]
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            for child in os.listdir(path):
                remove_rf(os.path.join(path, child))
            os.rmdir(path)
    else:
        for realpath in path:
            remove_rf(realpath)


@cli.subroutine()
# @parameter('software_name', help='Default is the name of the current working directory')
# @parameter('main_file', help='Default is main.py')
# @parameter('filename_format',
#            help='Default is "%(software_name)s-%(distro)s-%(version)s", that includes all configurable stuff')
# @parameter('version', help='Default is 0.0.1')
# @parameter('debug_window', help='Disables --noconsole option in pyinstaller')
# @parameter('extra_options', help='JSON config file for extra options related to pyinstaller')
def install(software_name=None, main_file='main.py', filename_format='%(software_name)s-%(distro)s-%(version)s',
            version='0.0.1', debug_window=False, extra_options=''):
    clean()

    python3_cmd = find_python3_command()

    # naming preparations
    if software_name is None:
        software_name = os.path.basename(os.getcwd())

    distro = '%s%s' % (sysname2shortname.get(sysname, sysname), sysver)

    filename = filename_format % {
        'software_name': software_name,
        'distro': distro,
        'version': version,
    }

    # install pyinstaller if it's not installed
    proc = subprocess.run(['pyinstaller', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        pip_install('pyinstaller', python3_cmd=python3_cmd, update=True)
        proc = subprocess.run('pyinstaller --version', shell=True)
        if proc.returncode != 0:
            raise RuntimeError('Unable to invoke PyInstaller after installation! Return code: %d' % proc.returncode)

    # install requirements
    proc = subprocess.run([python3_cmd, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    if proc.returncode != 0:
        raise RuntimeError('Requirement installation exited with non-zero code: %d' % proc.returncode)

    # compose command
    cmd = ['pyinstaller', '--onefile', '--name', filename]
    if not debug_window:
        cmd.append('--noconsole')

    # add data and binary
    if extra_options != '':
        with open(extra_options, 'r') as f:
            extra_options = json.load(f)

        syssep = ';' if sysname == 'Windows' else ':'
        for category, configurations in extra_options.items():
            if category in ('data', 'binary'):
                for config in configurations:
                    if 'module_name' in config:
                        module = config['module_name']
                        pip_install(module, python3_cmd=python3_cmd)  # in case these are not in requirements.txt
                        import_name = config.get('import_name', module)
                        locals()[import_name] = importlib.import_module(import_name)

                    target_sys = config.get('system')
                    target_sys_ver = config.get('system_version')

                    for item in config.get('args', []):
                        srclist = glob.glob(format_literal(item['src']))
                        dst = format_literal(item['dst'], locals=locals())
                        if meets_target_system_requirement(target_sys, target_sys_ver):
                            for src in srclist:
                                cmd += ['--add-%s' % category, '%s%s%s' % (src, syssep, dst)]
            elif category == 'hidden_import':
                for config in configurations:
                    target_sys = config.get('system')
                    target_sys_ver = config.get('system_version')
                    if meets_target_system_requirement(target_sys, target_sys_ver):
                        cmd += ['--hidden-import', config['name']]

    # compose command's final components and print for debug
    cmd.append(main_file)

    print('To execute command:')
    print(' '.join("'%s'" % item if ' ' in item else item for item in cmd))

    # execute installation
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print('Installation failed!', file=sys.stderr)
        raise SystemExit(1)


@cli.subroutine()
def clean():
    for path in ('build', 'dist', '*.spec'):
        remove_rf(path)


@cli.subroutine(name='help')
def get_help(command):
    cli.print_help(command)


# main program
# ----------------

if platform.system() not in ('Windows', 'Darwin', 'Linux'):
    raise RuntimeError('Unsupported OS: %s' % platform.system())

python_version = sys.version.split(' ')[0]
pvx, pvy, _ = python_version.split('.', maxsplit=2)
pvx, pvy = int(pvx), int(pvy)
if pvx < 3 or (pvx == 3 and pvy < 5):
    raise RuntimeError('Please use Python 3.5 or above to run this script!')

cli.run()
