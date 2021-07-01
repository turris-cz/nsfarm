"""CLI communication helper classes based on pexpect.

This ensures systematic logging and access to terminals. We implement two special terminal types at the moment. We have
support for shell and u-boot.  They differ in a way how they handle prompt and methods they provide to user.
"""
# Notest on some of the hacks in this file:
#
# There are new line character matches in regular expressions. Correct one is \r\n but some serial controlles for some
# reason also use \n\r so we match both alternatives.
#
import os
import io
import abc
import logging
import base64
import fcntl
import select
import socket
import threading
import typing
import pexpect
from . import mterm

CTRL_C = '\x03'
CTRL_D = '\x04'

_FLUSH_BUFFLEN = 2048


def pexpect_flush(pexpect_handle):
    """Flush all input on pexpect. This effectively reads everything.
    """
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
    """This is generic abstraction on top of pexpect for command line interface.
    """

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

    def command(self, cmd: str = ""):
        """Calls pexpect sendline and expect cmd with trailing new line.

        This is handy when you are communicating with console that echoes input back. This effectively removes sent
        command from output.
        """
        self.sendline(cmd)
        # WARNING: this has known problem with serial console. Shells on serial console breaks line at 80 characters and
        # that means that this expect won't match.
        self.expect_exact(cmd)
        self.expect_exact(["\r\n", "\n\r"])

    def run(self, cmd: str = "",
            exit_code: typing.Optional[typing.Callable[[int], None]] = run_exit_code_zero,
            **kwargs) -> typing.Any:
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
        """Returns located match in previously matched output.
        """
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

    This is tested to handle busybox and bash.
    """
    _COLUMNS_NUM = 800
    _NOCMD = ":"
    _SET_NSF_PROMPT = r"export PS1='nsfprompt:$(echo -n $?)\$ '"
    _NSF_PROMPT = r"(\r\n|\n\r|^)nsfprompt:([0-9]+)($|#) "
    _INITIAL_PROMPTS = [
        r"(\r\n|\n\r|^).+? ($|#) ",
        r"(\r\n|\n\r|^)bash-.+?($|#) ",
        r"(\r\n|\n\r|^)root@[a-zA-Z0-9_-]*:",
        r"(\r\n|\n\r|^).*root@turris.*#",  # Note: this is weird dual prompt from lxd ssh
        _NSF_PROMPT,
    ]
    # TODO compile prompt regexp to increase performance

    def __init__(self, pexpect_handle, flush=True):
        super().__init__(pexpect_handle, flush=flush)
        # Firt check if we are on some sort of shell prompt
        self.command()
        self.expect(self._INITIAL_PROMPTS)
        # Now sanitize prompt format
        self.run(self._SET_NSF_PROMPT)
        # And set huge number of columns to fix any command we throw at it
        self.run(f"stty columns {self._COLUMNS_NUM}")

    def prompt(self, **kwargs) -> int:
        self.expect(self._NSF_PROMPT, **kwargs)
        return int(self.match(2))

    def command(self, cmd: str = ""):
        # 20 characters are removed as those are approximately for prompt
        if len(cmd) >= (self._COLUMNS_NUM - 20):
            raise Exception("Command probably won't fit to terminal. Split it or increase number of columns.")
        return super().command(cmd)

    def ctrl_c(self):
        """Sends ^C character.
        """
        self.send(CTRL_C)

    def ctrl_d(self):
        """Sends ^D character.
        """
        self.send(CTRL_D)

    def txt_read(self, path):
        """Read text file via shell.

        path: path to text file to read

        Returns string containing text of the file
        """
        self.run(f"cat '{path}'")
        return self.output

    def txt_write(self, path, content):
        """Write text file via shell.

        Note that parent directory has to exist and any file will be rewritten.

        path: path to be written to
        content: string with data to be written to text file.
        """
        self.sendline(f"cat > '{path}'")
        self.sendline(content)
        self.sendeof()
        if self.prompt() != 0:
            raise Exception(f"Writing file failed with exit code: {self.prompt()}")

    def bin_read(self, path):
        """Read binary file via shell encoded in base64.

        path: path to file to read

        Returns bytes with content of binary file from the path.
        """
        self.run(f"base64 '{path}'")
        return base64.b64decode(self.output)

    def bin_write(self, path, content):
        """Write given bytes to binary file in path.

        Note that parent directory has to exist and any file will be rewritten.

        path: path to file to be written.
        content: bytes to be written to binary file.
        """
        self.sendline(f"base64 -d > '{path}'")
        self.sendline(base64.b64encode(content))
        self.sendeof()
        if self.prompt() != 0:
            raise Exception(f"Writing file failed with exit code: {self.prompt()}")

    @property
    def output(self):
        return self._pe.before.decode()


class Uboot(Cli):
    """U-boot prompt support class.
    """
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


class FDLogging:
    """Live logging with data passtrough.

    This is stream logging that logs communication comming from and to file descript trough socket. This intended use is
    for direct output to be visible live in logs.

    This has one primary limitation and that is output only in lines. Log is created only when new line character is
    located not before that.
    """
    _EXPECTED_EOL = b'\n\r'

    def __init__(self, fileno, logger, in_level=logging.INFO, out_level=logging.DEBUG):
        self._logger = logger
        self._in_level = in_level
        self._out_level = out_level
        self._fileno = fileno if isinstance(fileno, int) else fileno.fileno()
        self._our_sock, self._user_sock = socket.socketpair()
        self._propagate = True

        self._orig_filestatus = fcntl.fcntl(self._fileno, fcntl.F_GETFL)
        fcntl.fcntl(self._fileno, fcntl.F_SETFL, self._orig_filestatus | os.O_NONBLOCK)
        self._our_sock.setblocking(False)

        self._thread = threading.Thread(target=self._thread_func, daemon=True)
        self._thread.start()

    @property
    def socket(self):
        """Returns socket for user to use to communicate trough this logged passtrough.
        """
        return self._user_sock

    def set_propagation(self, propagate: bool):
        """Configures if input should be propagated to socket or not. Output is still propagated to file but input read
        from file is simply logged and dropped.
        """
        self._propagate = propagate

    def close(self):
        """Close socket and stop logging.
        """
        if self._our_sock is None:
            return
        self._our_sock.close()
        self._our_sock = None
        self._thread.join()
        fcntl.fcntl(self._fileno, fcntl.F_SETFL, self._orig_filestatus)

    def __del__(self):
        self.close()

    def _log_line(self, prefix, line, level):
        self._logger.log(level, prefix + repr(line.rstrip(self._EXPECTED_EOL).expandtabs())[2:-1])

    def _log(self, prev_data, new_data, level, prefix):
        data = prev_data + new_data
        lines = data.splitlines(keepends=True)
        if not lines:
            return data
        # The last line does not have to be terminated (no new line character) so just preserve it
        reminder = lines.pop() if lines[-1] and lines[-1][-1] not in self._EXPECTED_EOL else b''
        for line in lines:
            self._log_line(prefix, line, level)
        return reminder

    def _thread_func(self):
        data = {
            self._fileno: b'',
            self._our_sock.fileno(): b'',
        }
        level = {
            self._fileno: self._in_level,
            self._our_sock.fileno(): self._out_level,
        }
        output = {
            self._fileno: self._our_sock.fileno(),
            self._our_sock.fileno(): self._fileno,
        }
        prefix = {
            self._fileno: '< ',
            self._our_sock.fileno(): '> '
        }

        poll = select.poll()
        poll.register(self._fileno, select.POLLIN)
        poll.register(self._our_sock.fileno(), select.POLLIN | select.POLLNVAL)
        while True:
            for poll_event in poll.poll():
                fileno, event = poll_event
                if event == select.POLLNVAL:
                    return
                new_data = os.read(fileno, io.DEFAULT_BUFFER_SIZE)
                if fileno != self._fileno or self._propagate:
                    os.write(output[fileno], new_data)
                data[fileno] = self._log(data[fileno], new_data, level[fileno], prefix[fileno])


class PexpectLogging:
    """Logging for pexpect.

    This emulates file object and is intended to be used with pexpect handler as logger.
    """
    _EXPECTED_EOL = b'\n\r'

    def __init__(self, logger):
        self._level = logging.INFO
        self.logger = logger
        self.linebuf = b''

    def __del__(self):
        if self.linebuf:
            self._log(self.linebuf)

    def _log(self, line):
        self.logger.log(self._level, repr(line.rstrip(self._EXPECTED_EOL).expandtabs())[2:-1])

    def write(self, buf):
        """Standard-like file write function.
        """
        jbuf = self.linebuf + buf
        lines = jbuf.splitlines(keepends=True)
        # If the last line is not terminated (no new line character) so just preserve it
        self.linebuf = lines.pop() if lines[-1] and lines[-1][-1] not in self._EXPECTED_EOL else b''
        for line in lines:
            self._log(line)

    def flush(self):
        """Standard-like flush function.
        """
        # Just ignore flush
