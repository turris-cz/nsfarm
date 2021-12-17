"""NSFarm configuration classes.
"""
import collections.abc
import configparser
import pathlib
import typing

TARGET_CONFS = (
    "/etc/nsfarm_targets.ini",
    "~/.nsfarm_targets.ini",
    "./targets.ini",
)

BOARDS = (
    "mox",
    "omnia",
    "turris1x",
)


class Target:
    """Target configuration handler."""

    def __init__(self, name, conf):
        self._name = name
        self._conf = conf

    def check(self) -> bool:
        """Verify if target is correctly configured."""
        return bool(
            self.board
            and self.board in BOARDS
            and self.serial_number
            and len(self.serial_number) == 16
            and self.serial
            and self.wan
        )

    def is_available(self) -> bool:
        """Verify if target is present on system. This means if resources it specifies are all available."""
        return bool(
            (not self.serial or pathlib.Path(self.serial).exists())
            and self._netlink_present(self.wan)
            and self._netlink_present(self.lan1)
            and self._netlink_present(self.lan2)
        )

    @staticmethod
    def _netlink_present(value):
        return not value or (pathlib.Path("/sys/class/net") / value).exists()

    @property
    def name(self) -> str:
        """Name of target."""
        return self._name

    @property
    def board(self) -> str:
        """Target board. It can be one of: omnia"""
        return self._conf.get("board")

    @property
    def serial_number(self) -> str:
        """Serial number of target board."""
        return self._conf.get("serial_number")

    @property
    def serial(self) -> str:
        """Serial interface connected to target board."""
        return self._conf.get("serial")

    @property
    def reset_inverted(self) -> bool:
        """If reset pin is inverted or not. This is required due to some of the boards being connected trough level
        inverting transistor for power boost.
        """
        return self._conf.getboolean("reset_inverted", fallback=False)

    @property
    def legacyboot(self) -> str:
        """If does not support FIT image boot."""
        return self._conf.get("legacyboot", fallback=False)

    @property
    def wan(self) -> str:
        """Interface connected to WAN port of target board."""
        return self._conf.get("wan")

    @property
    def lan1(self) -> str:
        """Interface connected to one of LAN ports of target board."""
        return self._conf.get("lan1")

    @property
    def lan2(self) -> str:
        """Interface connected to one of LAN ports of target board."""
        return self._conf.get("lan2")

    def is_configured(self, name) -> bool:
        """Check if given field is configured."""
        return name in self._conf

    def device_map(self):
        """Provides full device map for all devices for LXD containers."""
        return {
            "net:wan": self.wan,
            "net:lan1": self.lan1,
            "net:lan2": self.lan2,
        }

    def __str__(self):
        representation = {"name": self._name}
        for attr in ("board", "serial_number", "serial", "wan", "lan1", "lan2"):
            if attr in self._conf:
                representation[attr] = self._conf[attr]
        return str(representation)


class Targets(collections.abc.Mapping):
    """All available NSFarm targets."""

    def __init__(self, additional: typing.Iterable[str] = frozenset(), rootdir: str = "."):
        self._rootdir = pathlib.Path(rootdir)
        self._conf = configparser.ConfigParser()
        # Load predefined ones
        for file in TARGET_CONFS:
            self.__read_file(file)
        # Load additional ones
        for file in additional:
            self.__read_file(file)

    def filter(self, board=None):
        """Method for selection of available and valid target with given parameters.
        Returns generator of available targets.
        """
        for target in self:
            trg = self[target]
            if not trg.check() or not trg.is_available():
                continue
            if board is not None and board != trg.board:
                continue
            yield target

    def __read_file(self, file):
        path = pathlib.Path(file).expanduser()
        if not path.is_absolute():
            path = self._rootdir / path
        self._conf.read(path)

    def __getitem__(self, key) -> Target:
        return Target(key, self._conf[key])

    def __iter__(self):
        for target in self._conf:
            if target == "DEFAULT":
                continue
            yield target

    def __len__(self):
        return len(self._conf)
