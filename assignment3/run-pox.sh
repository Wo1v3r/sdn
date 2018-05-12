#!/bin/bash
cp ./controller.py ../../pox/ext
cp ./TopologyReader.py ../../pox/ext
cp ./TopologyBuilder.py ../../pox/ext
cp ./NetworkStructures.py ../../pox/ext

../../pox/pox.py controller
