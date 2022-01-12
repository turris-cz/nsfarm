"""CLI communication helper classes based on pexpect.

This ensures systematic logging and access to terminals. We implement two special terminal types at the moment. We have
support for shell and u-boot.  They differ in a way how they handle prompt and methods they provide to user.
"""
# Notest on some of the hacks in this file:
#
# There are new line character matches in regular expressions. Correct one is \r\n but some serial controlles for some
# reason also use \n\r so we match both alternatives.
#
import abc
import base64
import fcntl
import io
import logging
import os
import pathlib
import re
import select
import socket
import threading
import typing

import pexpect

from . import mterm

CTRL_C = "\x03"
CTRL_D = "\x04"

_FLUSH_BUFFLEN = 2048


def pexpect_flush(pexpect_handle):
    """Flush all input on pexpect. This effectively reads everything."""
    # The read_nonblocking blocks when there is not at least one byte available for read (yeah you are reading it right
    # the nonblocking read is blocking). The solution here is to use timeout with zero value. This raises timeout
    # exception immediately once there is no input available.
    while True:
        try:
            pexpect_handle.read_nonblocking(io.DEFAULT_BUFFER_SIZE, 0)
        except pexpect.TIMEOUT:
            return


def run_exit_code_zero(exit_code):
    """Default handler for Cli.run exit_code parameter.
    This checks if exit code is zero and raises exception if it is not.
    """
    if exit_code != 0:
        raise Exception(f"Command exited with non-zero code: {exit_code}")
    return 0


class Cli(abc.ABC):
    """This is generic abstraction on top of pexpect for command line interface."""

    _NOCMD: str

    def __init__(self, pexpect_handle, flush=True):
        self._pe = pexpect_handle
        if flush:
            self.flush()

    def __getattr__(self, name):
        # Just propagate anything we do not implement to pexect handle
        return getattr(self._pe, name)

    @abc.abstractmethod
    def prompt(self, **kwargs) -> int:
        """Follow output until prompt is reached and parse it.  Exit code is returned.
        All keyword arguments are passed to pexpect's expect call.
        """

    @property
    @abc.abstractmethod
    def output(self) -> str:
        """All output before latest prompt.

        This is everything not matched till prompt is located.  Note that this is for some implementations same as
        pexpect before but in others it can differ so you should always use this property instead of before.
        """

    def command(self, cmd: str = "") -> None:
        """Calls pexpect sendline and expect cmd with trailing new line.

        This is handy when you are communicating with console that echoes input back. This effectively removes sent
        command from output.
        """
        self.sendline(cmd)
        # Note: We have to expect possible line break after every character because terminal breaks echoed characters
        # when there is more characters than columns. We could also simply disable echo but that is not always possible
        # in our case. In the end there should be no issue in matching random new lines in command we sent.
        for char in cmd:
            self.expect_exact([char, "\r", "\n"])
        self.expect_exact(["\r\n", "\n\r"])

    def run(
        self, cmd: str = "", exit_code: typing.Optional[typing.Callable[[int], None]] = run_exit_code_zero, **kwargs
    ) -> typing.Any:
        """Run given command and follow output until prompt is reached and return exit code with optional automatic
        check. This is same as if you would call cmd() and prompt() while checking exit_code.

        cmd: command to be executed
        exit_code: function verifying exit code or None to skip default check
        All other key-word arguments are passed to prompt call.

        Returns result of exit_code function or exit code of command if exit_code is None.
        """
        self.command(cmd)
        ecode = self.prompt(**kwargs)
        return ecode if exit_code is None else exit_code(ecode)

    def match(self, index: int) -> str:
        """Returns located match in previously matched output."""
        return self._pe.match.group(index).decode()

    def flush(self):
        """Flush all input.

        This is handy if you don't know the state of console and you don't want to read any old input. This is
        automatically called in init unless you specify otherwise.
        """
        pexpect_flush(self._pe)

    def mterm(self, new_prompt: bool = True):
        """Runs interactive terminal on this cli.

        new_prompt controls if new command with no effect should be automatically send to trigger print of new prompt in
        terminal. It is just something nice to have but it might not be desirable sometimes so it is possible to disable
        it.
        """
        if new_prompt:
            self._pe.sendline(self._NOCMD)
            os.read(self._pe.fileno(), len(self._NOCMD) + 1)  # Eat up no command and new line character
        mterm.mterm(self._pe.fileno())


class Shell(Cli):
    """Unix shell support class.

    This is tested to handle busybox's ash and bash.

    Warning: this changes the prompt and it won't revert it. In most use cases this should not be an issue but keep it
    on mind when using this.
    """

    _NOCMD = ":"
    _SET_NSF_PROMPT = "export PS1='nsfprompt:$(echo -n $?)\\$ '"
    _NSF_PROMPT = re.compile(b"(\r\n|\n\r)?nsfprompt:([0-9]+)($|#) ")
    _INITIAL_PROMPTS = [
        re.compile(b"root@[a-zA-Z0-9_-]*:.*($|#) "),  # Common prompt for root user on most Linux distributions
        re.compile(b"(\r\n|\n\r|^).+? ($|#) "),  # Bare Busybox prompt
        re.compile(b"bash-.+?($|#) "),  # Default Bash prompt
        _NSF_PROMPT,
    ]

    def __init__(self, pexpect_handle: pexpect.spawnbase, flush: bool = True):
        super().__init__(pexpect_handle, flush=flush)
        # Firt check if we are on some sort of shell prompt
        self.expect(self._INITIAL_PROMPTS)
        # Now sanitize prompt format
        self.run(self._SET_NSF_PROMPT)

    def prompt(self, **kwargs) -> int:
        self.expect(self._NSF_PROMPT, **kwargs)
        return int(self.match(2))

    def ctrl_c(self) -> None:
        """Sends ^C character."""
        self.send(CTRL_C)

    def ctrl_d(self) -> None:
        """Sends ^D character."""
        self.send(CTRL_D)

    def txt_read(
        self, path: typing.Union[str, pathlib.PurePosixPath], expect_exist: bool = True
    ) -> typing.Optional[str]:
        """Read text file via shell.

        path: path to text file to read
        expect_exist: raise exception if file can't be read

        Returns string containing text of the file or None if file can't be read in some cases.
        """
        if self.run(f"cat '{path}'", exit_code=None) != 0:
            if expect_exist:
                raise Exception(f"Can't get file: {path}")
            return None
        return self.output.replace("\r\n", "\n")

    def txt_write(self, path: typing.Union[str, pathlib.PurePosixPath], content: str, append: bool = False) -> None:
        """Write text file via shell.

        Note that parent directory has to exist and any file will be rewritten.

        path: path to be written to
        content: string with data to be written to text file.
        append: append instead of just write.
        """
        self.sendline(f"cat {'>>' if append else '>'} '{path}'")
        self.sendline(content)
        self.ctrl_d()
        exit_code = self.prompt()
        if exit_code != 0:
            raise Exception(f"Writing file failed with exit code: {exit_code}")

    def bin_read(
        self, path: typing.Union[str, pathlib.PurePosixPath], expect_exist: bool = True
    ) -> typing.Optional[bytes]:
        """Read binary file via shell encoded in base64.

        path: path to file to read
        expect_exist: raise exception if file can't be read

        Returns bytes with content of binary file from the path or None if file can't be read in some cases.
        """
        if self.run(f"base64 '{path}'", exit_code=None) != 0:
            if expect_exist:
                raise Exception(f"Can't get file: {path}")
            return None
        return base64.b64decode(self.output)

    def bin_write(self, path: typing.Union[str, pathlib.PurePosixPath], content: bytes) -> None:
        """Write given bytes to binary file in path.

        Note that parent directory has to exist and any file will be rewritten.

        path: path to file to be written.
        content: bytes to be written to binary file.
        """
        self.sendline(f"base64 -d > '{path}'")
        self.sendline(base64.b64encode(content))
        self.ctrl_d()
        exit_code = self.prompt()
        if exit_code != 0:
            raise Exception(f"Writing file failed with exit code: {exit_code}")

    @property
    def output(self) -> str:
        return self._pe.before.decode()


class Uboot(Cli):
    """U-boot prompt support class."""

    _NOCMD = ";"
    _PROMPT = "(\r\n|\n\r|^)=> "
    _EXIT_CODE_ECHO = "echo $?"

    def __init__(self, pexpect_handle, flush=True):
        super().__init__(pexpect_handle, flush=flush)
        self._output = ""
        self.run("true")  # Check if we are in U-boot prompt

    def prompt(self, **kwargs):
        self.expect(self._PROMPT, **kwargs)
        self._output = self._pe.before.decode()
        # Check exit code
        self.command(self._EXIT_CODE_ECHO)
        self.expect(self._PROMPT, **kwargs)
        return int(self._pe.before.decode())

    @property
    def output(self):
        return self._output


class LineBytesAggregate:
    """Aggregates bytes and dispatches them in lines instead.
    This is primarily used to split stream of communication in CLI session to distinct blocks that makes sense to send
    to logging system.
    """

    def __init__(self, callback: typing.Callable[[bytes], None]):
        self._callback = callback
        self.linebuf = b""
        self.newline = True

    def add(self, buf: bytes) -> None:
        """Add bytes to aggregate."""
        jbuf = self.linebuf + buf
        i = 0
        while i < len(jbuf):
            if jbuf[i] == b"\r"[0] or (not self.newline and jbuf[i] == b"\n"[0]):
                self.newline = self.newline or jbuf[i] == b"\n"[0]
                i += 1
                continue  # skip new line characters
            ri = jbuf.find(b"\r", i)  # cursor leftward
            ni = jbuf.find(b"\n", i)  # cursor to the new line
            eol = ri if ni == -1 else ni if ri == -1 else min(ri, ni)
            if eol == -1:  # No new line byte located, store for now
                self.linebuf = jbuf[i:]
                return
            self._callback(jbuf[i:eol])
            i = eol + 1
            self.newline = eol == ni
        self.linebuf = b""

    def flush(self):
        """Dispatch unfinished line."""
        if self.linebuf:
            self._callback(self.linebuf)


class FDLogging:
    """Live logging with data passtrough.

    This is stream logging that logs communication comming from and to file descript trough socket. The intended use is
    for direct output to be visible live in logs.

    This has one primary limitation and that is output only in lines. Log is created only when new line character is
    located not before that. The reason for this is readibility of logs.
    """

    _thread: typing.Optional[threading.Thread] = None
    _lock: threading.Lock = threading.Lock()
    _poll: select.poll = select.poll()
    _output: dict[int, int] = {}
    _propagation: dict[int, bool] = {}
    _aggregate: dict[int, LineBytesAggregate] = {}

    def __init__(self, fileno: int, logger: logging.Logger, in_level=logging.INFO, out_level=logging.DEBUG):
        self._logger = logger
        self._fileno = fileno
        self._our_sock, self._user_sock = socket.socketpair()

        self._orig_filestatus = fcntl.fcntl(self._fileno, fcntl.F_GETFL)
        fcntl.fcntl(self._fileno, fcntl.F_SETFL, self._orig_filestatus | os.O_NONBLOCK)
        self._our_sock.setblocking(False)

        self._add_socket(
            self._fileno,
            LineBytesAggregate(lambda line: self._log_line("> ", line, in_level)),
            self._our_sock.fileno(),
            LineBytesAggregate(lambda line: self._log_line("< ", line, out_level)),
        )

    @property
    def socket(self):
        """Returns socket for user to use to communicate trough this logged passtrough."""
        return self._user_sock

    def set_propagation(self, propagate: bool):
        """Configures if input should be propagated to socket or not. Output is still propagated to file but input read
        from file is simply logged and dropped.
        """
        self._set_propagation(self._fileno, propagate)

    @classmethod
    def _set_propagation(cls, fileno: int, propagate: bool):
        with cls._lock:
            cls._propagation[fileno] = propagate

    def close(self):
        """Close socket and stop logging."""
        if self._our_sock is None:
            return
        self._del_socket(self._fileno, self._our_sock.fileno())
        self._our_sock.close()
        self._our_sock = None
        fcntl.fcntl(self._fileno, fcntl.F_SETFL, self._orig_filestatus)

    def __del__(self):
        self.close()

    def _log_line(self, prefix, line, level):
        self._logger.log(level, prefix + repr(line.expandtabs())[2:-1])

    @classmethod
    def _add_socket(
        cls, fileno_in: int, aggregate_in: LineBytesAggregate, fileno_out: int, aggregate_out: LineBytesAggregate
    ):
        with cls._lock:
            cls._output.update({fileno_in: fileno_out, fileno_out: fileno_in})
            cls._propagation.update({fileno_in: True, fileno_out: True})
            cls._aggregate.update({fileno_in: aggregate_in, fileno_out: aggregate_out})
            cls._poll.register(fileno_in, select.POLLIN)
            cls._poll.register(fileno_out, select.POLLIN | select.POLLNVAL)
        if cls._thread is None:
            cls._thread = threading.Thread(target=cls._thread_func, daemon=True)
        if not cls._thread.is_alive():
            cls._thread.start()

    @classmethod
    def _del_socket(cls, fileno_in: int, fileno_out: int):
        with cls._lock:
            cls._poll.unregister(fileno_in)
            cls._poll.unregister(fileno_out)
            del cls._output[fileno_in]
            del cls._output[fileno_out]
            del cls._propagation[fileno_in]
            del cls._propagation[fileno_out]
            del cls._aggregate[fileno_in]
            del cls._aggregate[fileno_out]

    @classmethod
    def _thread_func(cls):
        while cls._output:  # We run until we have some output then we can terminate
            for poll_event in cls._poll.poll():
                fileno, event = poll_event
                if event == select.POLLNVAL:
                    continue
                data = os.read(fileno, io.DEFAULT_BUFFER_SIZE)
                with cls._lock:
                    if fileno not in cls._output:
                        # This covers race condition with _del_socket as it might win lock over us and remove fileno in
                        # the meantime we were waiting for the lock.
                        continue
                    if cls._propagation[fileno]:
                        os.write(cls._output[fileno], data)
                    cls._aggregate[fileno].add(data)


class PexpectLogging:
    """Logging for pexpect.

    This emulates file object and is intended to be used with pexpect handler as logger.
    """

    def __init__(self, logger: logging.Logger, prefix: str = ""):
        self._level = logging.INFO
        self.logger = logger
        self.aggregate = LineBytesAggregate(self._log)

    def __del__(self):
        self.aggregate.flush()

    def _log(self, line: bytes) -> None:
        self.logger.log(self._level, repr(line.expandtabs())[2:-1])

    def write(self, buf: bytes) -> None:
        """Standard-like file write function."""
        self.aggregate.add(buf)

    def flush(self) -> None:
        """Standard-like flush function."""
        # Just ignore flush as it is not what we want in general.
