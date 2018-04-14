# Software Defined Networks

Assuming this directory is located aside 'pox' directory you can just:

```bash
./run-mn.sh
./run-pox.sh
```

Otherwise:

    copy controller.py to pox/ext
    copy firewall-policies.csv to pox/pox/misc


Then to open a port connection on host(mininet terminal):
Opening port 10000 and 22 on h4

```bash 
mininet > 
    h4 iperf -s -p 10000 &
    h4 iperf -s -p 22 &
    h3 iperf -s -p 666 &
```

Then, you are able to send into h4 using these ports.

```bash
mininet> 
    h1 iperf -c h4 -p 10000 -t 2 -i 1 
    h1 iperf -c h4 -p 22 -t 2 -i 1 
```


The following example will be blocked per the Firewall rules:

```bash
mininet>
    h1 iperf -c h3 -p 666 -t 2 -i 1
```    

Where,
-c hostname, -t number of times, -i time interval(in seconds)
