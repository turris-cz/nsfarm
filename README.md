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
* Python3
* pexpect
* pyserial
* pylxd

You can install all Python libraries using `pip install -r requirements.txt`. It
is suggested to either install them to system or to use `virtualenv`.

You should also make sure that LXD is up and running on your system.

In terms of hardware you need target router board of course. It has to be
connected with appropriate USB-to-TTL converter and with at least one Ethernet
port for WAN. The USB-to-TTL convert has to have CST and RST signals. For more
info about hardware connection please see [hardware wiring](HARDWARE_WIRING.md).


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

You should read [tests writing guide](TESTS_WRITING.md) to see how you can write
more tests and/or to understand current ones.


How it works
------------
TBD
