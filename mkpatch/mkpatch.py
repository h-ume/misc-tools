#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2023 Hajimu UMEMOTO <ume@mahoroba.org>.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# mkpatch - Make patch

import argparse
import io
import os
import re
import subprocess
import sys
from typing import NoReturn, Optional

version = "20231007"


def warnx(message: str) -> None:
    sys.stderr.write(f'{os.path.basename(sys.argv[0])}: {message}\n')


def errx(val: int, message: str) -> NoReturn:
    warnx(message)
    sys.exit(val)


def diff(oldfile: str, newfile: str, ignspcchg: bool, diffopts: list[str],
         ports_format: bool) -> None:
    dopts: list[str] = ['-u'] + diffopts
    if ignspcchg:
        dopts.append('-b')
    if ports_format or re.search(r'.+\.(c|cpp|py)$', newfile):
        dopts.append('-p')
    if ports_format:
        dopts.append('-d')
    command: list[str] = ['diff'] + dopts + [oldfile, newfile]
    env: Optional[os._Environ[str]] = None
    if ports_format:
        env = os.environ
        env['TZ'] = 'UTC'
    response: subprocess.CompletedProcess = subprocess.run(
        command, env=env, text=True, capture_output=True)
    if not ports_format:
        print(f'Index: {newfile}')
        print(' '.join(command))
    lines: str = response.stdout
    if ports_format:
        lines = re.sub(r'^(---.+)\.[ +\d]+$', r'\1 UTC', lines,
                       flags=re.MULTILINE)
        lines = re.sub(r'^(\+\+\+.+?)(\s+[-+.:\d]+){3}$', r'\1', lines,
                       flags=re.MULTILINE)
    print(lines, end='')


def mkpatch(path: str, suffix: str, ignspcchg: bool, diffopts: list[str],
            ports_format: bool) -> int:
    path = path.rstrip('/')
    try:
        os.stat(path)
    except Exception as e:
        warnx(re.sub(r'^\[Errno \w+]\s+', '', str(e)))
        return 1
    paths: list[str] = []
    if os.path.isfile(path):
        if not re.search(f'{suffix}$', path):
            path += suffix
        paths.append(path)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for oldfile in files:
                paths.append(os.path.join(root, oldfile))
    else:
        warnx(f"Not file nor directory: '{path}'")
        return 1

    for oldfile in sorted(paths):
        oldfile = re.sub(r'^\./', '', oldfile)
        match_obj: Optional[re.Match] = re.search(f'(.+){suffix}$', oldfile)
        if not match_obj:
            continue
        newfile: str = match_obj.group(1)
        removed: bool = not os.path.exists(newfile)
        if removed:
            os.symlink('/dev/null', newfile)
        if os.path.getsize(oldfile) == 0:
            oldfile = '/dev/null'

        diff(oldfile, newfile, ignspcchg, diffopts, ports_format)

        if removed:
            os.unlink(newfile)

    return 0


def main() -> NoReturn:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version=version)
    parser.add_argument('-b', '--ignore-space-change', action='store_true',
                        dest='ignspcchg',
                        help='ignore changes in the amount of white space')
    parser.add_argument('-o', '--diff-options', action='append',
                        default=[], help='additional diff options')
    parser.add_argument('-P', '--ports-format', action='store_true',
                        help='produce diff for FreeBSD ports')
    parser.add_argument('-s', '--suffix', action='store', dest='suffix',
                        default='.orig',
                        help='suffix of original file (default: %(default)s)')
    parser.add_argument('path', nargs='*', help='path to compare')
    args: argparse.Namespace = parser.parse_args()

    if len(args.path) == 0:
        args.path.append('.')

    ret: int = 0
    for path in args.path:
        ret |= mkpatch(path, args.suffix, args.ignspcchg, args.diff_options,
                       args.ports_format)
    sys.exit(ret)


if __name__ == '__main__':
    if os.name == 'nt':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, newline='\n')
    main()
