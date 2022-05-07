import deeplink
import os
import pathlib
import shutil
import pytest


@pytest.fixture
def setup_and_teardown():
    if pathlib.Path("./test-data").exists():
        shutil.rmtree("./test-data")

    os.mkdir("./test-data")
    os.mkdir("./test-data/in")
    pathlib.Path("./test-data/in/file-base").touch()
    os.mkdir("./test-data/in/dir-a")
    pathlib.Path("./test-data/in/dir-a/file-a").touch()
    pathlib.Path("./test-data/in/dir-a/ignore-file-a").touch()
    os.mkdir("./test-data/in/dir-b")
    os.symlink("./test-data/in/dir-b", "./test-data/in/symlink-to-dir-b")
    pathlib.Path("./test-data/in/dir-b/file-b-to-be-copied").touch()
    yield

    shutil.rmtree("./test-data")


@pytest.fixture
def setup_ignore_file_and_teardown():
    filename = "ignore-file-for-test"
    with open(filename, "w", encoding="utf-8") as fd:
        fd.write("#This is a comment\n.*ignore-file-a.*\n\n")
    yield

    os.unlink(filename)


@pytest.fixture
def setup_copy_file_and_teardown():
    filename = "copy-file-for-test"
    with open(filename, "w", encoding="utf-8") as fd:
        fd.write("#This is a comment\n.*ignore_.*\n\n")
    yield

    os.unlink(filename)


def test_input_directory(setup_and_teardown):
    if pathlib.Path("./test-data/out").exists():
        shutil.rmtree("./test-data/out")

    args = deeplink.get_args(["./test-data/in", "./test-data/out"])
    deeplink.prepare_destination(args.destination)

    assert pathlib.Path("./test-data/out").exists()


def test_basic_results(setup_and_teardown):
    args = deeplink.get_args(
        ["--ignore", ".*ignore.*", "./test-data/in", "./test-data/out"]
    )
    deeplink.prepare_destination(args.destination)
    deeplink.create_links(args)
    p = pathlib.Path("./test-data/out")

    assert p.exists()
    assert (p / "dir-a" / "file-a").exists()
    assert not (p / "dir-a" / "ignore-file-a").exists()
    assert (p / ".." / "in" / "symlink-to-dir-b").is_symlink()


def test_remove_front_dir_complex():
    assert deeplink.remove_front_dir(
        pathlib.PosixPath("a/b/c"), pathlib.PosixPath("a/b/c/d/e")
    ) == pathlib.PosixPath("d/e")


def test_remove_front_dir_from_dot():
    assert deeplink.remove_front_dir(
        pathlib.PosixPath("."), pathlib.PosixPath("a/b/c/d/e")
    ) == pathlib.PosixPath("a/b/c/d/e")


def test_relative_path_from_abs():
    expected_path = pathlib.PosixPath("../../../../..")
    rel_cwd_path = "/".join(pathlib.PosixPath().cwd().parts[1:])
    expected_path /= pathlib.PosixPath(rel_cwd_path) / "a" / "z"

    assert (
        deeplink.relative_path(
            pathlib.PosixPath("/a/b/c/d/e"), pathlib.PosixPath("./a/z")
        )
        == expected_path
    )


def test_ignore_from_file(setup_and_teardown, setup_ignore_file_and_teardown):
    args = deeplink.get_args(
        [
            "--ignore-list-file",
            "ignore-file-for-test",
            "./test-data/in",
            "./test-data/out",
        ]
    )
    deeplink.prepare_destination(args.destination)
    deeplink.create_links(args)
    p = pathlib.Path("./test-data/out")

    assert p.exists()
    assert (p / "dir-a" / "file-a").exists()
    assert not (p / "dir-a" / "ignore-file-a").exists()
    assert (p / ".." / "in" / "symlink-to-dir-b").is_symlink()
    assert (p / "dir-b" / "file-b-to-be-copied").is_symlink()


def test_copy_from_file(setup_and_teardown, setup_copy_file_and_teardown):
    args = deeplink.get_args(
        [
            "--copy-list-file",
            "copy-file-for-test",
            "./test-data/in",
            "./test-data/out",
        ]
    )
    deeplink.prepare_destination(args.destination)
    deeplink.create_links(args)
    p = pathlib.Path("./test-data/out")

    assert p.exists()
    assert (p / "dir-a" / "file-a").exists()
    assert not (p / "dir-a" / "ignore-file-a").exists()
    assert (p / ".." / "in" / "symlink-to-dir-b").is_symlink()
    assert (p / "dir-b" / "file-b-to-be-copied").is_symlink()


def test_relative_path_from_rel():
    assert deeplink.relative_path(
        pathlib.PosixPath("./a/b"), pathlib.PosixPath("./k/l")
    ) == pathlib.PosixPath("../../k/l")


def test_relative_path_to_abs():
    assert deeplink.relative_path(
        pathlib.PosixPath("/a/b/c/d/e"), pathlib.PosixPath("/k/h/i")
    ) == pathlib.PosixPath("/k/h/i")
