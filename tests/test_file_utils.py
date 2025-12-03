import os
import tempfile

from semantic_tester.utils.file_utils import FileUtils


def test_ensure_directory_exists_creates_and_reports_true():
    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = os.path.join(tmpdir, "subdir")
        assert not os.path.exists(target_dir)

        ok = FileUtils.ensure_directory_exists(target_dir)

        assert ok is True
        assert os.path.isdir(target_dir)


def test_ensure_directory_exists_invalid_dir_returns_false():
    assert FileUtils.ensure_directory_exists("") is False


def test_find_markdown_files_recursive_and_non_recursive():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory structure
        root_md = os.path.join(tmpdir, "root.md")
        subdir = os.path.join(tmpdir, "sub")
        os.makedirs(subdir)
        sub_md = os.path.join(subdir, "sub.md")
        other = os.path.join(subdir, "file.txt")

        for path in (root_md, sub_md, other):
            with open(path, "w", encoding="utf-8") as f:
                f.write("x")

        recursive = FileUtils.find_markdown_files(tmpdir, recursive=True)
        non_recursive = FileUtils.find_markdown_files(tmpdir, recursive=False)

        assert set(map(os.path.basename, recursive)) == {"root.md", "sub.md"}
        assert set(map(os.path.basename, non_recursive)) == {"root.md"}


def test_find_markdown_files_on_missing_dir_returns_empty():
    files = FileUtils.find_markdown_files("/path/that/does/not/exist", recursive=True)
    assert files == []


def test_read_file_content_success_and_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "a.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("hello")

        assert FileUtils.read_file_content(path) == "hello"
        assert FileUtils.read_file_content(os.path.join(tmpdir, "missing.txt")) is None


def test_read_file_content_decoding_error_returns_none(tmp_path):
    # 写入无效的 UTF-8 字节，触发解码错误分支
    path = tmp_path / "bad.bin"
    path.write_bytes(b"\xff\xff")

    assert FileUtils.read_file_content(str(path)) is None


def test_find_file_by_name_direct_and_recursive():
    with tempfile.TemporaryDirectory() as tmpdir:
        subdir = os.path.join(tmpdir, "sub")
        os.makedirs(subdir)
        target = os.path.join(subdir, "target.md")
        with open(target, "w", encoding="utf-8"):
            pass

        # Direct path must match exact filename in root
        assert FileUtils.find_file_by_name(tmpdir, "target.md", recursive=False) is None

        found = FileUtils.find_file_by_name(tmpdir, "target.md", recursive=True)
        assert os.path.abspath(found) == os.path.abspath(target)


def test_find_file_by_name_missing_directory_returns_none():
    assert FileUtils.find_file_by_name("/no/such/dir", "a.txt", recursive=True) is None


def test_get_and_format_file_size(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "a.bin")
        data = b"1234567890"  # 10 bytes
        with open(path, "wb") as f:
            f.write(data)

        size = FileUtils.get_file_size(path)
        assert size == len(data)
        assert FileUtils.get_file_size(os.path.join(tmpdir, "none")) == 0

        # Just ensure formatting returns a non-empty human readable string
        formatted = FileUtils.format_file_size(size)
        assert formatted.endswith("B")

        # get_file_size 在底层 os.path.getsize 抛异常时应返回 0
        def bad_getsize(_path):  # type: ignore[unused-argument]
            raise OSError("boom")

        monkeypatch.setattr(
            "semantic_tester.utils.file_utils.os.path.getsize",
            bad_getsize,
        )
        assert FileUtils.get_file_size(path) == 0


def test_format_file_size_zero():
    assert FileUtils.format_file_size(0) == "0 B"


def test_backup_file_and_safe_filename_and_relative_path(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "a.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("data")

        assert FileUtils.backup_file(path) is True

        # 备份不存在的文件返回 False
        missing = os.path.join(tmpdir, "missing.txt")
        assert FileUtils.backup_file(missing) is False

        safe = FileUtils.safe_filename("a<>:/\\|?* .txt")
        # Illegal characters should be removed/replaced and name should be non-empty
        assert "<" not in safe and ">" not in safe
        assert "?" not in safe and "*" not in safe
        assert safe  # non-empty

        rel = FileUtils.get_relative_path(path, tmpdir)
        assert rel == os.path.basename(path)

        # get_relative_path 在 os.path.relpath 抛出 ValueError 时应回退为原路径
        def bad_relpath(_path, _base):  # type: ignore[unused-argument]
            raise ValueError("nope")

        monkeypatch.setattr(
            "semantic_tester.utils.file_utils.os.path.relpath",
            bad_relpath,
        )
        assert FileUtils.get_relative_path(path, tmpdir) == path
