NSFarm Hardware Wiring
======================
NSFarm is designed so that there is one PC running with various connections to
tested board. This is broad list of those connections. This file later continues
with exacting wiring for specific boards setups.

There are following expected connections:
* __serial__ which is USB-to-TTL connection to system console of board. This is
  expected to be not a minimal serial converter but it has to have RST and CST
  pins. RST pin is used to control reset pin of board and CST is used to
  optionally control power relay.
* __wan__ which is Ethernet connection for WAN port of board. Note that this port
  has to be configurable by U-Boot as it is used to load tested root file-system
  to device.
* __lan1__ is Ethernet connection between one of the board's LAN ports and PC. It
  is required to test LAN. It is optional and not all tests are run if not
  provided. Please see router specific section for exact port that is expected.
* __lan2__ is Ethernet connection between additional board's LAN port and PC. It
  is required to test switch configuration between two clients. It is optional
  and not all tests are run if not provided. Please see router specific section
  for exact port that is expected.

```
           ____serial_______
 __________|_             _|_________________
|            |            |                 |
|            |            |                 |
|            |----WAN-----|                 |
|            |            |                 |
|            |----LAN1----|                 |
|            |----LAN2----|                 |
|            |            |                 |
|     PC     |            |     Router      |
|____________|            |_________________|
```


Specific boards wiring
----------------------
This section documents how various boards are expected to be connected to testing
PC. This mirrors real configuration done in `nsfarm` framework so if you plan to
change interconnection then you should change it `nsfarm` as well as here.

Minimal information provided is how to hookup console, RST for reset and CST for
power. It also has to states what connectors WAN/LAN1/LAN2 refers to on real
device.

### Turris Omnia
This board is referred in targets configuration with keyword `omnia`.

#### Serial cable
UART is located at right front of the PCB. There are four pins. You should
connect, from left, ground (GND), transmitted data (RxD) and received data (RxD)
pins of you serial cable.

RST connection is little bit more complicated. There is no on board pin for reset
pin. The only easily accessible place is button at the back. You have to solder
wire to in on the bottom of the board. The correct pin is the one closer to WAN
port from two of the closest ones to edge of the PCB under button. You can see
[illustrative photo](resources/omnia-reboot.jpg) if you are not sure.


How to connect CST pin please see section about board power shutdown. Connection
of this pin is not required unless you want power shutdown feature.

### Ethernet connections
| NSFarm alias | Router port | ifname    |
|--------------|-------------|-----------|
| WAN          | WAN         | eth2      |
| LAN1         | LAN0        | lan0@eth1 |
| LAN2         | LAN4        | lan4@eth1 |


Power shutdown board
--------------------
None of the supported boards have ability to power them self completely off.
NSFarm is expected to be deployed in state where there is multiple boards
available for testing. This means that all such boards would be always running and
consuming energy no matter if tests are run on them or not. For that reason there
is optional feature that turns board off when no tests are running. This is done
by additional hardware with relay and CST port of serial cable.

Real board is still TBD!


Wiring routers to PC with single Ethernet card
----------------------------------------------
The setup expected by NSFarm is theoretically very demanding on PC Ethernet ports.
One board requires three ports and PC it self requires one port to access the
Internet. There is of course simple solution in form of tagged LANs and smart
switch.

The result should be that you have single link interface for every single
Ethernet connection to board. Such interface is then used in targets
configuration.

Setup is so we use default untagged interface as it is to connect to router and to
Internet and we add tagged 802.11q interfaces on top of that. This way on single
Ethernet port we have not only all ports to tested boards but also access to the
Internet.

### Switch/router configuration
The switch/router of our choosing is based on OpenWRT with DSA. This can be for
example Turris MOX. If you have different switch then please just extrapolate idea
of configuration and apply it on your specific switch.

You have to configure separate network bridges to bridge over always tagged
interface to PC and specific port to tested router. Let's expect that PC is
connected to `lan1`, WAN port of tested board to `lan2`, LAN1 port of tested
board to `lan3` and LAN2 of tested board to `lan4`.

First step is to remove `lan2`, `lan3` and `lan4` from any existing interface. If
you have router in somewhat default setup then those are going to be part of `lan`
interface. To do so you have to modify it either by UCI or manually by editing
`/etc/config/network`. To remove it with UCI you can run commands like this:
```sh
uci del_list network.lan.ifname=lan2
uci del_list network.lan.ifname=lan3
uci del_list network.lan.ifname=lan4
uci commit network.lan.ifname
```

Next you have to create new interfaces to bridge connection. To connect WAN, in
our example here, we have to create interface for example named `nsfarm_wan` with
no protocol with `ifname` `lan2` and `lan1.1`. This introduces new VLAN with ID 1
to `lan1`, that is port to our PC, that is in same network as WAN port of tested
board. There should be no other device on that network. To apply this
configuration you can either use UCI:
```
uci set network.nsfarm_wan=interface
uci set network.nsfram_wan.type=bridge
uci set network.nsfram_wan.proto=none
uci add_list network.nsfram_wan.ifname=lan1.1
uci add_list network.nsfram_wan.ifname=lan2
uci commit network
```
or you can add to file `/etc/config/network` section like this:
```
config interface 'nsfarm_wan'
	option type 'bridge'
	option proto 'none'
	list ifname 'lan1.1'
	list ifname 'lan2'
```
To configure LAN1 you have to do the same but change name of interface to
something else (for example `nsfarm_lan1`) and if course `ifname` should be rather
`lan1.2` and `lan3`. And for LAN2 that is once again same with different interface
name and with `ifname` of `lan1.3` and `lan4`.

To apply all this settings you have to reconfigure network on router with
`/etc/init.d/network restart`.

### PC configuration
At this time you should have configured router/switch and have VLANs on interface
connected to PC. Next step is to create interfaces for them on PC it self. That is
pretty easy, to do that for example introduced in switch/router configuration
section you can do this:
```
sudo ip link add link enp0s1f1 name nsfarm_wan type vlan id 1
sudo ip link add link enp0s1f1 name nsfarm_lan1 type vlan id 2
sudo ip link add link enp0s1f1 name nsfarm_lan2 type vlan id 3
```

To remove those interfaces later on you can just do:
```
sudo ip link delete nsfarm_wan
sudo ip link delete nsfarm_lan1
sudo ip link delete nsfarm_lan2
```

To test whole setup you can temporally disconnect WAN port from tested device and
to connect it to network with DHCP (best option is free port on router you just
used to configure all this) and to run `sudo dhclient nsfarm_wan` on PC to see if
bridge works as expected. You should get IP address from DHCP server of your
router on `nsfarm_wan` interface. Don't forget to return correct Ethernet cable to
WAN interface on tested device.
