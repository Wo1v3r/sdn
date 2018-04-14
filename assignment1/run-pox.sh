#!/bin/bash

cp ./firewall-policies.csv ../pox/pox/misc
cp ./controller.py ../pox/ext

../pox/pox.py controller
