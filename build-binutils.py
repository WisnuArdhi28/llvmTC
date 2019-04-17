#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2019 The ClangBuiltLinux Authors
# Description: Builds a standalone copy of binutils

import argparse
import multiprocessing
import os
import pathlib
import platform
import shutil
import subprocess
import utils


def x86_64_target():
    if platform.machine() == "x86_64":
        return "host"
    else:
        return "x86_64-linux-gnu"


def parse_parameters(root):
    parser = argparse.ArgumentParser()
    parser.add_argument("-I",
                        "--install-folder",
                        help="""
                        By default, the script will create a "usr" folder in the same folder as this script
                        and install binutils there. If you'd like to have it installed somewhere else, pass
                        it to this parameter. This can either be an absolute or relative path.

                        Example: ~/binutils
                        """,
                        type=str,
                        default=os.path.join(root.as_posix(), "usr"))
    parser.add_argument("-t",
                        "--targets",
                        help="""
                        The script can build binutils targeting arm-linux-gnueabi, aarch64-linux-gnu,
                        powerpc-linux-gnu, powerpc64le-linux-gnu, and x86_64-linux-gnu (host if on x86_64).

                        You can either pass the full target or just the first part (arm, aarch64, etc) or all
                        if you want to build all targets (which is the default).

                        Example: all, aarch64, arm-linux-gnueabi
                        """,
                        default="all",
                        nargs="+")
    return parser.parse_args()


def create_targets(targets):
    targets_dict = {
        "arm": "arm-linux-gnueabi",
        "aarch64": "aarch64-linux-gnu",
        "powerpc64le": "powerpc64le-linux-gnu",
        "powerpc": "powerpc-linux-gnu",
        "x86": x86_64_target()
    }
    targets_list = []

    if ''.join(targets) == "all":
        for key in targets_dict:
            targets_list.append(targets_dict[key])
    else:
        for target in targets:
            targets_list.append(targets_dict[target.split("-")[0]])

    return targets_list


def cleanup(build_folder):
    if build_folder.is_dir():
        shutil.rmtree(build_folder.as_posix())
    build_folder.mkdir(parents=True, exist_ok=True)


def invoke_configure(build_folder, install_folder, root, target):
    configure = [
        root.joinpath(utils.current_binutils(), "configure").as_posix(),
        '--prefix=' + install_folder.as_posix(),
        '--enable-deterministic-archives', '--enable-gold',
        '--enable-ld=default', '--enable-plugins', '--quiet',
        'CFLAGS=-O2 -march=native -mtune=native',
        'CXXFLAGS=-O2 -march=native -mtune=native'
    ]
    if "arm-" in target or "aarch64-" in target:
        configure += [
            '--disable-multilib', '--disable-nls',
            '--program-prefix=' + target + '-', '--target=' + target,
            '--with-gnu-as', '--with-gnu-ld',
            '--with-sysroot=' + install_folder.joinpath(target).as_posix()
        ]
    elif "powerpc" in target:
        configure += [
            '--enable-lto', '--enable-relro', '--enable-shared',
            '--enable-threads', '--disable-gdb', '--disable-sim',
            '--disable-werror', '--program-prefix=' + target + '-',
            '--target=' + target, '--with-pic', '--with-system-zlib'
        ]
    elif "x86" in target or "host" in target:
        configure += [
            '--enable-lto', '--enable-relro', '--enable-shared',
            '--enable-targets=x86_64-pep', '--enable-threads', '--disable-gdb',
            '--disable-werror', '--with-pic', '--with-system-zlib'
        ]
        if platform.machine() != "x86_64":
            configure += [
                '--program-prefix=' + target + '-', '--target=' + target
            ]
    utils.header("Building " + target + " binutils")
    subprocess.run(configure, check=True, cwd=build_folder.as_posix())


def invoke_make(build_folder, install_folder, target):
    if target == "host":
        subprocess.run(['make', '-s', 'configure-host', 'V=0'],
                       check=True,
                       cwd=build_folder.as_posix())
    subprocess.run(
        ['make', '-s', '-j' + str(multiprocessing.cpu_count()), 'V=0'],
        check=True,
        cwd=build_folder.as_posix())
    subprocess.run(
        ['make', '-s', 'prefix=' + install_folder.as_posix(), 'install', 'V=0'],
        check=True,
        cwd=build_folder.as_posix())
    with install_folder.joinpath(".gitignore").open("w") as gitignore:
        gitignore.write("*")


def for_all_targets(build, install_folder, root, targets):
    for target in targets:
        build_folder = build.joinpath(target)
        cleanup(build_folder)
        invoke_configure(build_folder, install_folder, root, target)
        invoke_make(build_folder, install_folder, target)


def main():
    root = pathlib.Path(__file__).resolve().parent

    args = parse_parameters(root)

    install_folder = pathlib.Path(args.install_folder)
    if not install_folder.is_absolute():
        install_folder = root.joinpath(install_folder)

    utils.download_binutils(root)

    for_all_targets(root.joinpath("build", "binutils"), install_folder, root,
                    create_targets(args.targets))


if __name__ == '__main__':
    main()
