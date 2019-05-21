Note: to add/remove/move interface between lxd containers using pylxd you have to
configure `c.containers.all()[0].devices` to something like:
```
{'eth': {'name': 'nsfeth', 'nictype': 'physical', 'parent': 'enp0s1', 'type': 'nic'}}
```
