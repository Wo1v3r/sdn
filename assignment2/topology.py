#!/usr/bin/python
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.node import RemoteController

clients = [
 ('h1', '10.0.0.1', '00:00:00:00:00:01'),
 ('h2', '10.0.0.2', '00:00:00:00:00:02'),
 ('h3', '10.0.0.3', '00:00:00:00:00:03'),
 ('h4', '10.0.0.4', '00:00:00:00:00:04'),
]

servers = [
 ('h5', '10.0.0.5', '00:00:00:00:00:05'),
 ('h6', '10.0.0.6', '00:00:00:00:00:06'),
 ('h7', '10.0.0.7', '00:00:00:00:00:07'),
 ('h8', '10.0.0.8', '00:00:00:00:00:08'),
]

hosts = clients + servers

class Topology(Topo):
    def __init__(self):
        Topo.__init__(self)

    def build(self):
        hostNodes = list(map(lambda (name,ip,mac): self.addHost(name, ip=ip, mac=mac) ,hosts))
        loadBalancer = self.addSwitch('s1', dpid= "%016x" % 9 )
        links = list(map(lambda h: self.addLink(h, loadBalancer), hostNodes))


topo = Topology()

net = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip='127.0.0.1',port = 6633), link=TCLink)

net.start()
CLI(net)
net.stop()

