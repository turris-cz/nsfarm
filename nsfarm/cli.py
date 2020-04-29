"""CLI communication helper classes based on pexpect.

This ensures systematic logging and access to terminals. We implement two special terminal types at the moment. We have
support for shell and u-boot.  They differ in a way how they handle prompt and methods they provide to user.
"""
# Notest on some of the hacks in this file:
#
# There are new line character matches in regular expressions. Correct one is \r\n but some serial controlles for some
# reason also use \n\r so we match both alternatives.
#
import logging
import base64

_FLUSH_BUFFLEN = 2048


def pexpect_flush(pexpect_handle):
    """Flush all input on pexpect. This effectively reads everything.
    """
    # TODO fix: this timeouts if there is nothing to flush
    while len(pexpect_handle.read_nonblocking(_FLUSH_BUFFLEN)) == _FLUSH_BUFFLEN:
        pass


class Cli:
    """This is generic abstraction on top of pexpect for command line interface.
    """

    def __init__(self, pexpect_handle, flush=True):
        self._pe = pexpect_handle
        if flush:
            self.flush()

    def __getattr__(self, name):
        # Just propagate anything we do not implement to pexect handle
        return getattr(self._pe, name)

    def prompt(self, **kwargs):
        """Follow output until prompt is reached and parse it.  Exit code is returned.
        """
        raise NotImplementedError

    @property
    def output(self):
        """All output before latest prompt.

        This is everything not matched till prompt is located.  Note that this is for some implementations same as
        pexpect before but in others it can differ so you should always use this property instead of before.
        """
        raise NotImplementedError

    def command(self, cmd=""):
        """Calls pexpect sendline and expect cmd with trailing new line.

        This is handy when you are communicating with console that echoes input back. This effectively removes sent
        command from output.
        """
        self.sendline(cmd)
        # WARNING: this has known problem with serial console. Shells on serial console breaks line at 80 characters and
        # that means that this expect won't match.
        self.expect_exact(cmd)
        self.expect_exact(["\r\n", "\n\r"])

    @staticmethod
    def _run_exit_code_zero(exit_code):
        if exit_code != 0:
            raise Exception("Command exited with non-zero code: {}".format(exit_code))

    def run(self, cmd="", exit_code=_run_exit_code_zero, **kwargs):
        """Run given command and follow output until prompt is reached and return exit code with optional automatic
        check. This is same as if you would call cmd() and prompt() while checking exit_code.

        cmd: command to be executed
        exit_code: lambda function verifying exit code or None to skip default check
        All other key-word arguments are passed to prompt call.

        Returns result of exit_code function or exit code of command if exit_code is None.
        """
        self.command(cmd)
        ecode = self.prompt(**kwargs)
        return ecode if exit_code is None else exit_code(ecode)

    def match(self, index):
        """Returns located match in previously matched output.
        """
        return self._pe.match.group(index).decode()

    def flush(self):
        """Flush all input.

        This is handy if you don't know the state of console and you don't want to read any old input. This is
        automatically called in init unless you specify otherwise.
        """
        pexpect_flush(self._pe)


class Shell(Cli):
    """Unix shell support class.

    This is tested to handle busybox and bash.
    """
    _SET_NSF_PROMPT = r"export PS1='nsfprompt:$(echo -n $?)\$ '"
    _NSF_PROMPT = r"(\r\n|\n\r|^)nsfprompt:([0-9]+)($|#) "
    _INITIAL_PROMPTS = [
        r"(\r\n|\n\r|^).+? ($|#) ",
        r"(\r\n|\n\r|^)bash-.+?($|#) ",
        r"(\r\n|\n\r|^)root@[a-zA-Z0-9_-]*:",
        r"(\r\n|\n\r|^).*root@turris.*#",  # TODO this is weird dual prompt from lxd ssh
        _NSF_PROMPT,
    ]
    # TODO compile prompt regexp to increase performance
    # TODO the width of terminal is limited and command function fails with long commands

    def __init__(self, pexpect_handle, flush=True):
        super().__init__(pexpect_handle, flush=flush)
        # Firt check if we are on some sort of shell prompt
        self.command()
        self.expect(self._INITIAL_PROMPTS)
        # Now sanitize prompt format
        self.run(self._SET_NSF_PROMPT)

    def prompt(self, **kwargs):
        self.expect(self._NSF_PROMPT, **kwargs)
        return int(self.match(2))

    def file_read(self, path):
        """Read file trough shell.

        path: path to file to read

        This returns bytes with content of file from path.
        """
        self._sh.run("base64 '{}'".format(path))
        return base64.b64decode(self._sh.output())

    def file_write(self, path, content):
        """Write given content to file on path. Note that parent directory has to exists.

        path: path to file to be written
        content: bytes to be written to it
        """
        self._sh.sendline("base64 --decode > '{}'".format(path))
        self._sh.sendline(base64.b64encode(content))
        self._sh.sendeof()
        if self._sh.prompt() != 0:
            raise Exception("Writing file failed with exit code: {}".format(self._sh.prompt()))

    @property
    def output(self):
        return self._pe.before.decode()


class Uboot(Cli):
    """U-boot prompt support class.
    """
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
        if lines[-1] or lines[-1][-1] not in self._EXPECTED_EOL:
            # The last line is not terminated (no new line character) so just preserve it
            self.linebuf = lines.pop()
        for line in lines:
            self._log(line)

    def flush(self):
        """Standard-like flush function.
        """
        # Just ignore flush
