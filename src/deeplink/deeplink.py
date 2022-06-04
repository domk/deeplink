#!/usr/bin/env python3
#
# https://github.com/domk/deeplink
__version__ = "0.2"
__author__ = "Dominik Madon <dominik@acm.org>"


import abc
import argparse
import os
import pathlib
import re
import shutil
import sys
import typing

cache: typing.Dict[str, typing.Any] = {}


def get_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a simulated directory with linked files and directories."
        )
    )

    def directory_exists(directory: str) -> pathlib.PosixPath:
        if os.path.exists(directory) and os.path.isdir(directory):
            return pathlib.PosixPath(directory)
        print(f"ERROR: {directory} is not a directory.")
        sys.exit(1)

    def file_as_list(filename: str) -> typing.List[str]:
        if not os.path.exists(filename) or not os.path.isfile(filename):
            print(f"ERROR: {filename} is not a readable.")
            sys.exit(1)

        result: typing.List[str] = []
        with open(filename, "r", encoding="utf-8") as fn:
            re_comment = re.compile(r"^#.*$")
            re_empty = re.compile(r"^\s*$")
            line = fn.readline().rstrip('\n')
            while line:
                if not re_comment.match(line) and not re_empty.match(line):
                    result += [line]
                line = fn.readline().rstrip('\n')

        return result

    parser.add_argument(
        "source", type=directory_exists, help="Source directory"
    )
    parser.add_argument(
        "destination",
        type=pathlib.PosixPath,
        help="Destination directory",
    )
    parser.add_argument(
        "-l",
        "--hard-links",
        action="store_true",
        default=False,
        help="Use hard links",
    )
    parser.add_argument(
        "-c",
        "--copy",
        nargs=1,
        type=str,
        default=[],
        action="append",
        help=(
            "Copy files corresponding to the regexp pattern instead of "
            "creating links. The regexp patterns are applied to the "
            "source path including its directory."
        ),
    )
    parser.add_argument(
        "-C",
        "--copy-list-file",
        type=file_as_list,
        action="store",
        default=[],
        help=(
            "Copy files corresponding to the regexp patterns found in "
            "the given file instead of creating links. The regexp "
            "patterns are applied to the source path including its directory."
        ),
    )
    parser.add_argument(
        "-i",
        "--ignore",
        nargs=1,
        type=str,
        default=[],
        action="append",
        help=(
            "Ignore corresponding regexp pattern files or directories "
        ),
    )
    parser.add_argument(
        "-I",
        "--ignore-list-file",
        type=file_as_list,
        default=[],
        action="store",
        help=(
            "Ignore corresponding regexp pattern files or directories "
            "found in the given file"
        ),
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        default=False,
        action="store_true",
        help="Don't change filesystem and just print what will happen",
    )

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Print version and exit",
    )

    return parser.parse_args(args)


class FileReplacementError(Exception):
    """Raised whenever we need to have a directory whereas a file
    already exists with the same name.
    """


class DirectoryReplacementError(Exception):
    """Raised whenever we need to have a link whereas a directory
    already exists with the same name.
    """


def remove_front_dir(
    head_path: pathlib.Path, item: pathlib.Path
) -> pathlib.Path:
    """Given a head_path, remove this front path from item and return
    the results.

    >>> remove_front_dir(pathlib.Path('a/b/c'), pathlib.Path('a/b/c/d/e'))
    PosixPath('d/e')
    """

    head = list(head_path.parts)
    result = list(item.parts)

    while (len(head) > 0) and (len(result) > 0) and (head[0] == result[0]):
        del head[0], result[0]

    if result[0] == "/":
        return pathlib.Path("/" + "/".join(result))

    return pathlib.Path("/".join(result))


def relative_path(src: pathlib.Path, dest: pathlib.Path) -> pathlib.Path:
    """Given a `src` directory and a `dest` directory, returns the
    path to go from src to dest. If the dest path is absolute, returns
    the absolute path instead.

    >>> relative_path(pathlib.Path('a/b/c/m'), pathlib.Path('a/b/c/d/e'))
    PosixPath('../d/e')
    >>> relative_path(pathlib.Path('/a/b/c/m'), pathlib.Path('/a/b/c/d/e'))
    PosixPath('/a/b/c/d/e')

    """
    slist = list(src.absolute().parts)
    dlist = list(dest.absolute().parts)

    if dest.parts[0] == "/":
        return dest

    while (len(slist) > 0) and (len(dlist) > 0) and (slist[0] == dlist[0]):
        del slist[0], dlist[0]

    result = pathlib.Path("/".join([".."] * len(slist)))
    result = result / pathlib.Path("/".join(dlist))

    return result


class Executor(abc.ABC):
    def __init__(self, hard: bool = False):
        self.hard = hard

    @abc.abstractmethod
    def mkdir(self, path: pathlib.Path):
        pass

    @abc.abstractmethod
    def link(self, src: pathlib.Path, target: pathlib.Path):
        pass

    @abc.abstractmethod
    def copy(self, src: pathlib.Path, target: pathlib.Path):
        pass


class DryRunExecutor(Executor):
    def mkdir(self, path: pathlib.Path):
        if path.exists():
            if not path.is_dir():
                print(f"ERROR(mkdir) {path.as_posix()} exists")
                raise FileReplacementError(path.as_posix())
        else:
            print(f"mkdir {path.as_posix()}")

    def link(self, src: pathlib.Path, target: pathlib.Path):
        if target.exists() or target.is_symlink():
            print(f"ERROR(link): file {target.as_posix()} exists.")
            raise FileReplacementError(target.as_posix())

        print(f"link {src.as_posix()} {target.as_posix()}")

    def copy(self, src: pathlib.Path, target: pathlib.Path):
        if target.exists() and target.is_dir():
            print(f"ERROR(copy): diretory {target.as_posix()} exists.")
            raise DirectoryReplacementError(target.as_posix())

        print(f"copy {src.as_posix()} {target.as_posix()}")


class LinkExecutor(Executor):
    def mkdir(self, path: pathlib.Path):
        if path.exists():
            if not path.is_dir():
                print(f"ERROR(mkdir) {path.as_posix()} exists")
                raise FileReplacementError(path.as_posix())
        else:
            path.mkdir()

    def link(self, src: pathlib.Path, target: pathlib.Path):
        if target.exists() or target.is_symlink():
            print(f"ERROR(link): file {target.as_posix()} exists.")
            raise FileReplacementError(target.as_posix())
        else:
            src = relative_path(target.parent, src)
            if self.hard:
                target.link_to(src)
            else:
                target.symlink_to(src)

    def copy(self, src: pathlib.Path, target: pathlib.Path):
        if target.exists() and target.is_dir():
            print(f"ERROR(copy): diretory {target.as_posix()} exists.")
            raise DirectoryReplacementError(target.as_posix())

        shutil.copyfile(src, target)


def prepare_destination(dest: pathlib.Path):
    """Create the base directory if it doesn't exist yet"""

    if not dest.exists():
        dest.mkdir()
    elif not dest.is_dir():
        print(f"ERROR: {dest} exists already and is not a directory")
        raise FileReplacementError(dest.as_posix())


def create_links(
    args: argparse.Namespace, path: typing.Optional[pathlib.Path] = None
):
    global cache

    executor: Executor = (
        DryRunExecutor() if args.dry_run else LinkExecutor(args.hard_links)
    )

    if "cl.cp" not in cache:
        copy_files = [item for sublist in args.copy for item in sublist]
        copy_files += args.copy_list_file
        copy_files_re = [re.compile(regexp) for regexp in copy_files]
        cache["cl.cp_re"] = copy_files_re
    else:
        copy_files_re = cache.get("cl.cp_re", [])

    if "cl.ignore" not in cache:
        ignore_files = [item for sublist in args.ignore for item in sublist]
        ignore_files += args.ignore_list_file
        ignore_files_re = [re.compile(regexp) for regexp in ignore_files]
        cache["cl.ignore_re"] = ignore_files_re
    else:
        ignore_files_re = cache.get("cl.ignore_re", [])

    if path is None:
        path = args.source

    for item in path.iterdir():
        target = args.destination / remove_front_dir(args.source, item)

        skip_item = False
        for ignore in ignore_files_re:
            if ignore.match(item.as_posix()):
                skip_item = True
                break

        if skip_item:
            continue

        copy_required = False
        for copy in copy_files_re:
            if copy.match(item.as_posix()):
                copy_required = True
                break

        if item.is_dir():
            if item != args.destination:
                executor.mkdir(target)
                create_links(args, item)
        else:
            if copy_required:
                executor.copy(item, target)
            else:
                executor.link(item, target)


def main():
    args = get_args()

    try:
        prepare_destination(args.destination)
        create_links(args)
    except FileReplacementError as e:
        print(f"Remove the '{e}' file.")
    except DirectoryReplacementError as e:
        print(f"Remove the '{e}' directory.")


if __name__ == "__main__":
    main()
