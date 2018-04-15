#!/bin/bash
cp ./controller.py ../../pox/ext
cp ./hosts.py ../../pox/ext

../../pox/pox.py controller
