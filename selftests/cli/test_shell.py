"""Shell class tests.
"""
import pytest
from lorem_text import lorem

from nsfarm.cli import Shell
from nsfarm.lxd import Container
from nsfarm.toolbox.tests import deterministic_random


class Common:
    """Common tests implementation for Shell."""

    @pytest.fixture(autouse=True)
    def shell(self, container):
        yield Shell(container.pexpect())

    def test_true(self, shell):
        """Simple command that has no effect just to test full process match."""
        shell.run("true")

    def test_false(self, shell):
        """Simple command that has no effect but fails with known exit code."""
        assert shell.run("false", check=False) == 1

    def test_long_command(self, shell):
        """The long commands are broken to multiple lines when it is echoed to terminal. This verifies that we can
        ignore the breakage and math it anyway.
        """
        shell.run(" && ".join(["true"] * 20) + " && echo Content")
        assert shell.output == "Content"

    def test_prompt_pattern(self, shell):
        """Verify that we break early for provided patterns in prompt method."""
        shell.command("echo 'Terminate me..' && sleep 120")
        assert shell.prompt(["Terminate me.."]) == 1
        shell.ctrl_c()
        assert shell.prompt(["Terminate me.."]) == 0
        assert shell.exit_code == 130  # 128+SIGINT is exit code for termination in shells such as ash or bash

    @pytest.fixture
    def test_file(self, shell):
        """This provides test file path that is removed after test finishes."""
        path = "/tmp/test-file"
        yield path
        shell.run(f"rm -f '{path}'")

    def test_txt(self, shell, test_file):
        """Check for simple use of txt_write and txt_read."""
        with deterministic_random() as _:
            txt = lorem.paragraph()
        shell.txt_write(test_file, txt)
        assert txt == shell.txt_read(test_file)

    def test_txt_multiline(self, shell, test_file):
        """Check for multiline use of txt_write and txt_read."""
        with deterministic_random() as _:
            txt = lorem.paragraphs(5)  # 5 paragraphs means five lines
        shell.txt_write(test_file, txt)
        assert txt == shell.txt_read(test_file)

    def test_txt_append(self, shell, test_file):
        """Check if txt_read append option works as expected."""
        txt1 = "First line"
        txt2 = "Second line"
        shell.txt_write(test_file, txt1)
        shell.txt_write(test_file, txt2, append=True)
        assert f"{txt1}\n{txt2}" == shell.txt_read(test_file)

    def test_bin(self, shell, test_file):
        """Check if txt_read append option works as expected."""
        data = b"\x01\x02\x03\x04\x05"
        shell.bin_write(test_file, data)
        assert data == shell.bin_read(test_file)


class TestOpenWrt(Common):
    """These are tests in OpenWrt (ash) shell."""

    @pytest.fixture(scope="class", autouse=True)
    def container(self, lxd_client):
        with Container(lxd_client, "openwrt") as container:
            yield container


class TestAlpine(Common):
    """These are tests in Alpine Linux (ash) shell."""

    @pytest.fixture(scope="class", autouse=True)
    def container(self, lxd_client):
        with Container(lxd_client, "base-alpine") as container:
            yield container
