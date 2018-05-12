# Software Defined Networks Assignment 2

#### Make sure you first install
sudo pip install simplejson
sudo pip install networkx



Assuming this directory is located aside 'pox' directory you can just:

```bash
./run-mn.sh
./run-pox.sh
```

Otherwise:

    copy controller.py to pox/ext
    copy hosts.py to pox/ext

### To Run:

```
./run-mn.sh
./run-pox.sh


mininet > h1 ping 10.0.0.10
mininet > h2 ping 10.0.0.10
...

mininet> exit
```

If you want to copy and run on your own, you can add --ip=<LOAD_BALANCER_IP> switch

Make sure you exit properly to see the plot
