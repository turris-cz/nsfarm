"""CLI comunication helper classes based on pexpect.

This ensures systematic logging and access to terminals. We implement two
special terminal types at the moment. We have support for shell and u-boot.
They differ in a way how they handle prompt and methods they provide to user.
"""
import sys
import pexpect


class Console():
    """Generic console interface handler helper class.
    """

    def __init__(self, pexpect_handle, flush=True):
        self._pe = pexpect_handle
        if flush:
            self.flush()

    def __getattr__(self, name):
        # Just propagate anything we do not implement to pexect handle
        return getattr(self._pe, name)

    def cmd(self, cmd=""):
        """Run given command.
        """
        self._pe.sendline(cmd)

    def output(self, pattern, **kwargs):
        """Follow output until one of patterns is reached.
        """
        try:
            self._pe.expect(pattern if isinstance(pattern, list) else [pattern, ], **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT) as exc:
            print("Command exc: {}".format(exc))  # TODO log error
            return False
        return True

    def output_exact(self, string, **kwargs):
        """Follow output until exact match with one of given strings is found.
        """
        try:
            self._pe.expect_exact(string if isinstance(string, list) else [string, ], **kwargs)
        except (pexpect.EOF, pexpect.TIMEOUT) as exc:
            print("Command exc: {}".format(exc))  # TODO log error
            return False
        return True

    def match(self, index):
        """Returns located match in previously matched output.
        """
        return self._pe.match.group(index).decode(sys.getdefaultencoding())

    def flush(self):
        """Flush all input.

        This is handy if you don't know the state of console and you don't want
        to read any old input. This is automatically called in init unless you
        specify otherwise.
        """
        bufflen = 2048
        while len(self._pe.read_nonblocking(bufflen)) == bufflen:
            pass


class Cli(Console):
    """This is generic abstraction on top of Console for command line
    interface.
    """

    def prompt(self, exit_code=0, **kwargs):
        """Follow output until prompt is reached and parse it.
        Exit code is verified against provided one.
        """
        raise NotImplementedError

    def run(self, cmd="", exit_code=0, **kwargs):
        """Run given command and follow output untill prompt is reached.
        This is same as if you would call cmd() and prompt().
        """
        self.cmd(cmd)
        return self.prompt(exit_code, **kwargs)

    def batch(self, batch, **kwargs):
        """Run multiple commands one after each other.
        Every command has to end with prompt and have to exit with exit code 0.
        This is same as running run() for every command in batch.
        """
        for cmd in batch:
            if not self.run(cmd, **kwargs):
                return False
        return True


class Shell(Cli):
    """Unix shell support class.

    This is tested to handle busybox and bash.
    """
    _SET_NSF_PROMPT = r"export PS1='nsfprompt:$(echo -n $?)\$ '"
    _NSF_PROMPT = r"\r\nnsfprompt:([0-9]+)($|#) "
    _INITIAL_PROMPTS = [
        r"\r\n\S+ ($|#) ",
        r"\r\nbash-.+($|#) ",
        r"\r\nroot@[a-zA-Z0-9_-]*:",
        _NSF_PROMPT,
    ]
    # TODO compile prompt regexp to increase performance

    def __init__(self, pexpect_handle, flush=True):
        super().__init__(pexpect_handle, flush=flush)
        # Firt check if we are on some sort of shell prompt
        self._pe.sendline()
        if not self.output(self._INITIAL_PROMPTS):
            # TODO better exception
            raise Exception("Initial shell prompt not found")
        # Now sanitize prompt format
        if not self.run(self._SET_NSF_PROMPT):
            # TODO better exception
            raise Exception("Unable to locate new prompt form")

    def prompt(self, exit_code=0, **kwargs):
        return \
            self.output(self._NSF_PROMPT, **kwargs) and \
            int(self.match(1)) == exit_code


class Uboot(Cli):
    """U-boot prompt support class.
    """
    _PROMPT = "\r\n=> "
    _EXIT_CODE_ECHO = "echo --$?--"
    _EXIT_CODE = "--([0-9]+)--"
    # TODO compile exit code regexp to increase performance

    def __init__(self, pexpect_handle, flush=True):
        super().__init__(pexpect_handle, flush=flush)
        # Check if we are in U-boot prompt
        if not self.run("true"):
            # TODO better exception
            raise Exception("Unable to locate Uboot prompt")

    def prompt(self, exit_code=0, **kwargs):
        if not self.output_exact(self._PROMPT, **kwargs):
            # TODO report error
            return False
        self.cmd(self._EXIT_CODE_ECHO)
        if not self.output(self._EXIT_CODE, **kwargs):
            # TODO better error
            raise Exception("Unable to parse our own exit code echo.")
        result = int(self.match(1)) == exit_code
        if not self.output_exact(self._PROMPT, **kwargs):
            # TODO report error
            return False
        return result
