NSFarm (Network System testing Farm)
====================================
NSFarm is system testing tool for routers. It is intended as external device
testing tool but it does not do exactly blackbox testing. Its target is to do
testing of complete software stack of router.


Requirements
------------
NSFarm utilizes tools present on standard Linux based PC. It is based on Python3,
pytest, pexpect and LXD.

You need following software and its dependencies:
* Python3 (>=3.9)
* pytest (>=5.0)
* pytest-html (>=2.0)
* pexpect
* pyserial
* pylxd

You can install all Python libraries using `pip3 install -r requirements.txt`. It
is suggested to either install them to system or to use `virtualenv`.

You should also make sure that LXD is up and running on your system and is
correctly configured. Please see [appropriate documentation](docs/lxd.md) on how
to configure it.

In terms of hardware you need target router board of course. It has to be
connected with appropriate USB-to-TTL converter and with at least one Ethernet
port for WAN. The USB-to-TTL convert has to have CST and RST signals. For more
info about hardware connection please see [hardware
wiring](docs/hardware_wiring.md).


Usage
-----
To run tests you have to have configuration file. That file defines available
target boards tests can be run on. It is in INI file format. Please see
[targets.example.ini](targets.example.ini) for available options.

To run full test sweat it is as easy as running pytest in root directory of
NSFarm. You have to provide configured target with `-T` switch.
```sh
pytest -T omnia
```

You should read [tests writing guide](docs/tests_writing.md) to see how you can
write more tests and/or to understand current ones.

### Print live logs
NSFarm logs during its execution everything it can. This can later be used to
diagnose test failures. It is also nice to see how your tests progress so you can
enable live logging on console when tests are running. That can be done as follow:
```sh
pytest -T omnia --log-cli-level=DEBUG
```
You can choose any Python logging compatible level.

In rule of thumb the levels used in NSFarm are as follow:
* __DEBUG__: reports of NSFarm state changes and in general reports to be used
  when NSFarm behavior is diagnosed.
* __INFO__: on this level all console communication is logged.
* __WARNING__: some non-standard behavior proceeds (like waiting for other
  instance and so on).
* __ERROR__: non-standard situation encountered (like concurrent instance is
  running).

Non-standard behavior and situations noted here are meant as something that is
outside of tests scope but affects testing. The common effect is that tests
execution can't proceed and NSFarm has to wait for something to complete.

### HTML report
Using _pytest-html_ it is possible to generate nice HTML report of test run.
```sh
pytest -T omnia --self-contained-html --html=report.html
```
You can change `report.html` to any other name or path.


NSFarm utility
--------------
`nsfarm` is not only library but serves at the same time as utility Python
program. It implements some common operations you might want to use.

To invoke NSFarm utility you can use script `tool.sh`. Use `./tool.sh -h` to see
documentation and abilities of this utility.


How it works
------------
TBD
