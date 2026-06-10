
import datetime
import hashlib
import os
import platform
import re
import shutil
import socket
import subprocess
import sys


class File:
    def __init__(self, name, cmd, version=None, md5=None, svn_rev=None):
        self.name     = name
        self.cmd      = cmd
        self.expected = {k: v for k, v in
                         [('version', version), ('md5', md5), ('svn_rev', svn_rev)]
                         if v is not None}


filelist = [
    File('make', ['make', '--version'], md5='98a6341042ce824386bd6f3711ae8d83',
         version='GNU Make 4.4.1'),
    File('SVN',  ['svn', '--version']),
    File('Git',  ['"%DEMO%"\\git.exe', '--version']),
    File('Tig',  ['C:\\Users\\fgrando\\Downloads\\myproject\\tig.exe', '--version']),
]

# Expected environment variable values; leave empty to skip env checks.
expected_env = {}  # e.g. {'DEMO': r'C:\tools', 'CC': 'gcc'}

_IS_WINDOWS = sys.platform == 'win32'
_IS_CYGWIN  = sys.platform == 'cygwin'

# Cygwin root candidates used when Windows Python can't find tools via PATH
_CYGWIN_ROOTS = [r'C:\cygwin64', r'C:\cygwin']


def _cygpath(flag, path):
    """Run cygpath and return the converted path, or the original on failure."""
    try:
        r = subprocess.run(['cygpath', flag, path], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
    except FileNotFoundError:
        pass
    return path


def to_native_path(path):
    """Return a path that Python's open() can use on the current platform."""
    if _IS_WINDOWS and path.startswith('/'):
        return _cygpath('-w', path)           # POSIX → Windows for Windows Python
    if _IS_CYGWIN and not path.startswith('/') and ':' in path:
        return _cygpath('-u', path)           # Windows → POSIX for Cygwin Python
    return path


def to_windows_path(path):
    """Return the Windows-format path for display."""
    if path.startswith('/'):
        return _cygpath('-w', path)           # works on both Cygwin and Windows Python
    return os.path.normpath(path)


def expand_cmd(cmd):
    """Expand env vars (both $VAR and %VAR% styles) and strip shell quoting."""
    result = []
    for part in cmd:
        part = os.path.expandvars(part)
        if not _IS_WINDOWS:
            # os.path.expandvars only handles $VAR on non-Windows; expand %VAR% too
            part = re.sub(r'%([^%]+)%', lambda m: os.environ.get(m.group(1), m.group(0)), part)
        result.append(part.replace('"', ''))
    return result


def find_executable(name):
    """Locate an executable, handling both POSIX and Windows-style paths."""
    if os.sep in name or (os.altsep and os.altsep in name) or '/' in name or '\\' in name:
        native = to_native_path(name)
        return native if os.path.isfile(native) else None
    path = shutil.which(name)
    if path:
        return path
    if _IS_WINDOWS:
        for root in _CYGWIN_ROOTS:
            for sub in ('usr\\bin', 'bin'):
                for ext in ('', '.exe'):
                    candidate = os.path.join(root, sub, name + ext)
                    if os.path.isfile(candidate):
                        return candidate
    return None


def md5sum(path):
    h = hashlib.md5()
    with open(to_native_path(path), 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def get_svn_revision(path):
    try:
        r = subprocess.run(
            ['svn', 'info', to_windows_path(path)],
            capture_output=True, text=True, timeout=5
        )
        for line in r.stdout.splitlines():
            if line.startswith('Last Changed Rev:'):
                return line.split(':', 1)[1].strip()
        return 'N/A'
    except Exception:
        return 'N/A'


def which_path(name):
    """Resolve the bare executable name via PATH only, ignoring any directory prefix."""
    # Replace backslashes before basename so it works on Cygwin (os.sep is '/')
    basename = os.path.basename(name.replace('\\', '/'))
    # Cygwin's shutil.which looks for 'git', not 'git.exe'
    if not _IS_WINDOWS:
        basename = re.sub(r'\.exe$', '', basename, flags=re.IGNORECASE)
    p = shutil.which(basename)
    return to_windows_path(p) if p else None


def get_version(cmd):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5
        )
        output = (result.stdout or result.stderr).strip()
        return output.splitlines()[0] if output else 'N/A'
    except Exception as e:
        return f'ERROR: {e}'


def _check(checks, label, expected, actual):
    """Record a check result and return 'PASS' or 'FAIL: expected X got Y'."""
    if expected == actual:
        checks.append((label, True, expected, actual))
        return 'PASS'
    checks.append((label, False, expected, actual))
    return f'FAIL: expected {expected!r} got {actual!r}'


def run():
    checks = []
    rows   = []

    for f in filelist:
        cmd  = expand_cmd(f.cmd)
        exe  = cmd[0]
        path = find_executable(exe)
        if path is None:
            row_check = _check(checks, f'{f.name} found', 'yes', 'no') if f.expected else '-'
            rows.append((f.name, 'NOT FOUND', 'N/A', 'N/A', 'N/A', 'N/A', row_check))
            continue

        win_path = to_windows_path(path)
        in_path  = which_path(exe)
        if in_path is None:
            path_check = 'Not in PATH'
        elif in_path.lower() == win_path.lower():
            path_check = 'OK'
        else:
            path_check = in_path

        try:
            digest = md5sum(path)
        except Exception as e:
            digest = f'ERROR: {e}'

        version = get_version([path] + cmd[1:])
        svn_rev = get_svn_revision(path)

        row_fails = []
        if 'md5'     in f.expected: row_fails.append(_check(checks, f'{f.name} md5',     f.expected['md5'],     digest))
        if 'version' in f.expected: row_fails.append(_check(checks, f'{f.name} version', f.expected['version'], version))
        if 'svn_rev' in f.expected: row_fails.append(_check(checks, f'{f.name} svn_rev', f.expected['svn_rev'], svn_rev))

        if not f.expected:
            row_check = '-'
        elif all(r == 'PASS' for r in row_fails):
            row_check = 'PASS'
        else:
            row_check = 'FAIL'

        rows.append((f.name, win_path, path_check, digest, version, svn_rev, row_check))

    for var, expected_val in expected_env.items():
        actual_val = os.environ.get(var, '(not set)')
        _check(checks, f'env:{var}', expected_val, actual_val)

    headers = ('Name', 'Path', 'PATH Check', 'MD5', 'Version', 'SVN Rev', 'Check')
    col_w = [
        max(len(h), max(len(r[i]) for r in rows))
        for i, h in enumerate(headers)
    ]
    sep = '+' + '+'.join('-' * (w + 2) for w in col_w) + '+'
    fmt = '| ' + ' | '.join(f'{{:<{w}}}' for w in col_w) + ' |'

    print(sep)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*row))
    print(sep)

    print_inventory()
    return print_checks(checks)


def print_checks(checks):
    if not checks:
        return 0

    failures = [c for c in checks if not c[1]]
    passed   = len(checks) - len(failures)

    rows = [
        (label, expected, actual, 'PASS' if ok else 'FAIL')
        for label, ok, expected, actual in checks
    ]
    headers = ('Check', 'Expected', 'Actual', 'Result')
    col_w = [
        max(len(h), max(len(r[i]) for r in rows))
        for i, h in enumerate(headers)
    ]
    sep = '+' + '+'.join('-' * (w + 2) for w in col_w) + '+'
    fmt = '| ' + ' | '.join(f'{{:<{w}}}' for w in col_w) + ' |'

    print(f'\n=== Checks ({passed} passed, {len(failures)} failed) ===')
    print(sep)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*row))
    print(sep)

    print(f'\n{"FAILED" if failures else "OK"}: {passed}/{len(checks)} checks passed.')
    return len(failures)


def _windows_os_str():
    """Return OS in Windows Python format regardless of whether Cygwin Python is running."""
    if not _IS_CYGWIN:
        return f'{platform.system()} {platform.release()} {platform.version()}'
    try:
        r = subprocess.run(['cmd.exe', '/c', 'ver'], capture_output=True, text=True)
        m = re.search(r'Version (10\.0\.(\d+))', r.stdout)
        if m:
            name = 'Windows 11' if int(m.group(2)) >= 22000 else 'Windows 10'
            return f'{name} {m.group(1)}'
    except Exception:
        pass
    # Fallback: extract from CYGWIN_NT-10.0-26200
    m = re.match(r'CYGWIN_NT-(\d+\.\d+)-(\d+)', platform.uname().system)
    return f'Windows NT {m.group(1)}.{m.group(2)}' if m else platform.uname().system


def print_inventory():
    def section(title):
        print(f'\n=== {title} ===')

    # --- System ---
    section('System')
    print(f'  Timestamp : {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  Hostname  : {socket.gethostname()}')
    print(f'  User      : {os.environ.get("USERNAME") or os.environ.get("USER", "N/A")}')
    print(f'  OS        : {_windows_os_str()}')
    print(f'  Machine   : {platform.machine()}')
    print(f'  Python    : {platform.python_version()} ({sys.platform})')
    print(f'  CWD       : {to_windows_path(os.getcwd())}')

    # --- PATH entries ---
    section('PATH')
    path_sep = ';' if _IS_WINDOWS else ':'
    for entry in os.environ.get('PATH', '').split(path_sep):
        if entry:
            print(f'  {entry}')

    # --- Referenced env vars ---
    referenced = set()
    for f in filelist:
        for part in f.cmd:
            referenced.update(re.findall(r'%([^%]+)%', part))
            referenced.update(re.findall(r'\$\{?(\w+)\}?', part))

    if referenced:
        section('Referenced Variables')
        for var in sorted(referenced):
            print(f'  {var} = {os.environ.get(var, "(not set)")}')

    # --- All environment variables ---
    section('Environment Variables')
    for key in sorted(os.environ):
        if key != 'PATH':
            print(f'  {key} = {os.environ[key]}')


if __name__ == '__main__':
    sys.exit(run())
