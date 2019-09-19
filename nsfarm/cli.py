"""CLI comunication helper classes based on pexpect.

This ensures systematic logging and access to terminals. We implement two special terminal types at the moment. We have
support for shell and u-boot.  They differ in a way how they handle prompt and methods they provide to user.
"""
import pexpect


class Console:
    """Extension for pexpect based handles.

    It is designed to allow better usage in assert based statements.
    """

    def __init__(self, pexpect_handle):
        self._pe = pexpect_handle

    def __getattr__(self, name):
        # Just propagate anything we do not implement to pexect handle
        return getattr(self._pe, name)

    def sexpect(self, pattern, **kwargs):
        """Safe variant of pexpect expect method.

        pattern can be single string or list of patterns to match. Note that this is extension to pexpect expect.

        It returns matched pattern index + 1. When timeout or end of input was reach then it returns 0. This allows it
        to be directly used in assert.
        """
        patterns = [pexpect.TIMEOUT, ]
        if isinstance(pattern, str):
            patterns.append(pattern)
        else:
            patterns += pattern
        try:
            return self.expect(patterns, **kwargs)
        except pexpect.EOF:
            return 0

    def sexpect_exact(self, string, **kwargs):
        """Safe variant of pexpect expect_exact method.

        string can be one string or list of string to match. Note that this is extension compared to pexpect
        implementation.

        It returns matched string index + 1. When timeout or end of input was reach then it returns 0. This allows it to
        be directly used in assert.
        """
        strings = [pexpect.TIMEOUT, ]
        if isinstance(string, str):
            strings.append(string)
        else:
            strings += string
        try:
            return self.expect_exact(strings, **kwargs)
        except pexpect.EOF:
            return 0

    def match(self, index):
        """Returns located match in previously matched output.
        """
        return self._pe.match.group(index).decode()

    def cmd(self, cmd=""):
        """Calls pexpect sendline and expect cmd.

        This is handy when you are comunicating with console that echoes input back. This effectively removes sent
        command from output.
        """
        self.sendline(cmd)
        if not self.sexpect_exact(cmd) or not self.sexpect("(\r\n|\n\r)"):
            # TODO better exception
            raise Exception("cmd used but terminal probably does not echoes.")

    def flush(self):
        """Flush all input.

        This is handy if you don't know the state of console and you don't want to read any old input. This is
        automatically called in init unless you specify otherwise.
        """
        bufflen = 2048
        while len(self.read_nonblocking(bufflen)) == bufflen:
            pass


class Cli(Console):
    """This is generic abstraction on top of pexpect for command line interface.
    """

    def __init__(self, pexpect_handle, flush=True):
        super().__init__(pexpect_handle)
        if flush:
            self.flush()

    def prompt(self, exit_code=0, **kwargs):
        """Follow output until prompt is reached and parse it.  Exit code is verified against provided one.
        """
        raise NotImplementedError

    @property
    def output(self):
        """All output before latest prompt.

        This is everything not matched till prompt is located.  Note that this is for some implementations same as
        pexpect before but in others it can differ so you should always use this property instead of before.
        """
        raise NotImplementedError

    def run(self, cmd="", exit_code=0, **kwargs):
        """Run given command and follow output untill prompt is reached.  This is same as if you would call cmd() and
        prompt().
        """
        self.cmd(cmd)
        return self.prompt(exit_code, **kwargs)

    def batch(self, batch, **kwargs):
        """Run multiple commands one after each other.  Every command has to end with prompt and have to exit with exit
        code 0.  This is same as running run() for every command in batch.
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
    _NSF_PROMPT = r"(\r\n|\n\r|^)nsfprompt:([0-9]+)($|#) "
    _INITIAL_PROMPTS = [
        r"(\r\n|\n\r|^).+? ($|#) ",
        r"(\r\n|\n\r|^)bash-.+?($|#) ",
        r"(\r\n|\n\r|^)root@[a-zA-Z0-9_-]*:",
        _NSF_PROMPT,
    ]
    # TODO compile prompt regexp to increase performance

    def __init__(self, pexpect_handle, flush=True):
        super().__init__(pexpect_handle, flush=flush)
        # Firt check if we are on some sort of shell prompt
        self.cmd()
        if not self.sexpect(self._INITIAL_PROMPTS):
            # TODO better exception
            raise Exception("Initial shell prompt not found")
        # Now sanitize prompt format
        if not self.run(self._SET_NSF_PROMPT):
            # TODO better exception
            raise Exception("Unable to locate new prompt form")

    def prompt(self, exit_code=0, **kwargs):
        return \
            self.sexpect(self._NSF_PROMPT, **kwargs) and \
            int(self.match(2)) == exit_code

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
        # Check if we are in U-boot prompt
        if not self.run("true"):
            # TODO better exception
            raise Exception("Unable to locate Uboot prompt")

    def prompt(self, exit_code=0, **kwargs):
        if not self.sexpect(self._PROMPT, **kwargs):
            # TODO report error
            return False
        self._output = self.before.decode()
        # Check exit code
        self.cmd(self._EXIT_CODE_ECHO)
        if not self.sexpect(self._PROMPT, **kwargs):
            # TODO report error
            raise Exception("Unable to parse our own exit code echo.")
        return int(self.before.decode()) == exit_code

    @property
    def output(self):
        return self._output


# Notest on some of the hacks in this file
#
# There are new line character matches in regular expressions. Correct one is \r\n but some serial controlles for some
# reason also use \n\r so we match both alternatives.
