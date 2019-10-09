Image definitions for NSFarm
============================
This directory contains definitions of images used in NSFarm. Images define
content of container used during testing.

Image is defined by existence of file `NAME.sh` in `/imgs` directory where `NAME`
is name for image used in NSFarm. Note that this is not name used in LXD (only
part of it). This file definition suppose to be a bash script. It is run in
container to prepare image. There is also a second part of image definition and
that is directory named `NAME` here. Content of this directory is merged to
container as it is.

It is expected that `NAME.sh` file has on first line shebang and on second line
name of base image to be used. It is suggested to continue with comment block with
description of container use. This is an example of such header:
```sh
#!/bin/bash
#images:alpine/3.10/amd64
##################################################################################
# This is example image definition. Please describe here what this container does.
##################################################################################
```

Image naming limitations
------------------------
Because of LXD requirements it is needed that image is named only with characters,
numbers and `-` where first leter has to be a character not a number.

This is a limitation of image name having to be a valid hostname.

Base image
----------
The base idea of images is that we can stack images on top of each other and that
makes it easier to have common base and additional scripts that do only minimal
changes to it. This concept is base image. In definition file `NAME.sh` this is
sourced from second line. Leading hash is expected and stripped.

You can use either generic images from `linuximages.com` with prefix `images:` or
other NSFarm images with prefix `nsfarm:`.

It is suggested to base you image on some other NSFarm image or if you really need
then on Alpine Linux. The reason is to preserve minimal size and fast environment
execution/preparation.

Image preparation
-----------------
The image is prepared in following way:
* Container with base image is created
* `NAME.sh` script is copied to it to `/tmp/nsfarm-img.sh`
* Content of directory named same way as definition script is merged to container
* Script `/nsfarm-init.sh` is run inside container
* Image is created from container
