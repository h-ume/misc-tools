#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2016 Hajimu UMEMOTO <ume@mahoroba.org>.
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
# $Mahoroba: misc/trunk/mkpatch.py 686 2016-09-28 06:25:27Z ume $

version = "20151016"

try:
    import argparse
except ImportError:
    from optparse import OptionParser
import io
import os
import re
import subprocess
import sys


def warnx(message):
    sys.stderr.write('{0}: {1}\n'.format(os.path.basename(sys.argv[0]),
                                         message))


def errx(val, message):
    warnx(message)
    sys.exit(val)


def diff(oldfile, newfile, ignspcchg, diffopts, ports_format):
    dopts = ['-u'] + diffopts
    if ignspcchg:
        dopts.append('-b')
    if ports_format or re.search('.+\.(c|cpp|py)$', newfile):
        dopts.append('-p')
    if ports_format:
        dopts.append('-d')
    command = ['diff'] + dopts + [oldfile, newfile]
    env = None
    if ports_format:
        env = os.environ
        env['TZ'] = 'UTC'
    p = subprocess.Popen(command, universal_newlines=True, env=env,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, close_fds=True,
                         encoding=sys.getdefaultencoding())
    if not ports_format:
        print('Index: {0}'.format(newfile))
        print(' '.join(command))
    for line in p.stdout:
        if ports_format:
            if re.match(r'^---', line):
                line = re.sub(r'\.\d* \+0000$', ' UTC', line)
            elif re.match(r'^\+\+\+', line):
                line = re.sub(r'(\s+[-0-9:.+]+)+$', '', line)
        sys.stdout.write(line)
    p.wait()


def mkpatch(path, suffix, ignspcchg, diffopts, ports_format):
    path = path.rstrip('/')
    try:
        os.stat(path)
    except Exception as e:
        warnx(re.sub('^\[Errno \w+]\s+', '', str(e)))
        return(1)
    paths = []
    if os.path.isfile(path):
        if not re.search('{0}$'.format(suffix), path):
            path += suffix
        paths.append(path)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for oldfile in files:
                paths.append(os.path.join(root, oldfile))
    else:
        warnx("Not file nor directory: '{0}'".format(path))
        return(1)

    for oldfile in sorted(paths):
        oldfile = re.sub('^\./', '', oldfile)
        match_obj = re.search('(.+){0}$'.format(suffix), oldfile)
        if not match_obj:
            continue
        newfile = match_obj.group(1)
        removed = not os.path.exists(newfile)
        if removed:
            os.symlink('/dev/null', newfile)
        if os.path.getsize(oldfile) == 0:
            oldfile = '/dev/null'

        diff(oldfile, newfile, ignspcchg, diffopts, ports_format)

        if removed:
            os.unlink(newfile)

    return(0)


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--version', action='version', version=version)
        parser.add_argument('-b', '--ignore-space-change', action='store_true',
                            dest='ignspcchg',
                            help='ignore changes in the amount of white space')
        parser.add_argument('-o', '--diff-options', action='append',
                            default=[], help='additional diff options')
        parser.add_argument('-P', '--ports-format', action='store_true',
                            help='produce diff for FreeBSD ports')
        parser.add_argument('-r', '--read-file', action='store', dest='file',
                            help='read filenames from diff file')
        parser.add_argument('-s', '--suffix', action='store', dest='suffix',
                            default='.orig',
                            help='suffix of original file (default: %(default)s)')
        parser.add_argument('path', nargs='*', help='path to compare')
        args = parser.parse_args()
    except NameError:
        parser = OptionParser(usage='%prog [options] [path ...]',
                              version='%prog {0}'.format(version))
        parser.add_option('-b', '--ignore-space-change', action='store_true',
                          dest='ignspcchg',
                          help='ignore changes in the amount of white space')
        parser.add_option('-P', '--ports-format', action='store_true',
                          help='produce diff for FreeBSD ports')
        parser.add_option('-r', '--read-file', action='store', dest='file',
                          help='read filenames from diff file')
        parser.add_option('-s', '--suffix', action='store', dest='suffix',
                          default='.orig',
                          help='suffix of original file [default: %default]')
        parser.add_option('-o', '--diff-options', action='append',
                          default=[], help='additional diff options')
        args, args.path = parser.parse_args()
    if args.file:
        try:
            for line in open(args.file, 'r'):
                match_obj = re.search('^Index:\s(.+)$', line.rstrip())
                if match_obj:
                    args.path.append(match_obj.group(1))
        except Exception as e:
            errx(1, re.sub('^\[Errno \w+]\s+', '', str(e)))

    if len(args.path) == 0:
        args.path.append('.')

    ret = 0
    for path in args.path:
        ret |= mkpatch(path, args.suffix, args.ignspcchg, args.diff_options,
                       args.ports_format)
    sys.exit(ret)


if __name__ == '__main__':
    if os.name == 'nt':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, newline='\n')
    main()
