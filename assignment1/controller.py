import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr, EthAddr

from collections import defaultdict

import pox.misc
import csv
import os


policyFile = pox.misc.__file__.replace('__init__.pyc', 'firewall-policies.csv')
blockList = list()

with open(policyFile) as f:
    reader = csv.reader(f, delimiter=',')
    for row in reader:
        blockList.append(row[1:])

blockList.pop(0)

messages = []

for sublist in blockList:

    blockRule = of.ofp_match()
    blockRule.dl_src = EthAddr(sublist[0])
    blockRule.dl_dst = EthAddr(sublist[1])

    msg = of.ofp_flow_mod()
    msg.priority = 0
    msg.match = blockRule
    messages.append(msg)


hosts = {
    1: EthAddr('00:00:00:00:00:01'),
    2: EthAddr('00:00:00:00:00:02'),
    3: EthAddr('00:00:00:00:00:03'),
    4: EthAddr('00:00:00:00:00:04'),

}

switches = {
    1: '00-00-00-00-00-01',
    2: '00-00-00-00-00-02',
    3: '00-00-00-00-00-03',
    4: '00-00-00-00-00-04'
}

switch_hosts = {
    (switches[1], hosts[1]): 3,
    (switches[1], hosts[2]): 4,
    (switches[4], hosts[3]): 3,
    (switches[4], hosts[4]): 4,
	# Resolved connections:
	(switches[2], hosts[1]): 1,
    (switches[2], hosts[2]): 1,
    (switches[2], hosts[3]): 2,
    (switches[2], hosts[4]): 2,
	(switches[3], hosts[1]): 1,
    (switches[3], hosts[2]): 1,
    (switches[3], hosts[3]): 2,
    (switches[3], hosts[4]): 2
}

video_traffic = [
    (switches[1], hosts[1], hosts[3]),
    (switches[1], hosts[1], hosts[4]),
    (switches[1], hosts[2], hosts[3]),
    (switches[1], hosts[2], hosts[4]),
    (switches[4], hosts[3], hosts[1]),
    (switches[4], hosts[3], hosts[2]),
    (switches[4], hosts[4], hosts[1]),
    (switches[4], hosts[4], hosts[2])
]

lan_traffic = {
    (switches[1], hosts[1], hosts[2]): 4,
    (switches[1], hosts[2], hosts[1]): 3,
    (switches[4], hosts[3], hosts[4]): 4,
    (switches[4], hosts[4], hosts[3]): 3
}


class Controller (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        # Adjacency map.  [sw1][sw2] -> port from sw1 to sw2
        self.adjacency = defaultdict(lambda: defaultdict(lambda: None))

    def _handle_LinkEvent(self, event):
        l = event.link
        sw1 = dpid_to_str(l.dpid1)
        sw2 = dpid_to_str(l.dpid2)
        self.adjacency[sw1][sw2] = l.port1
        self.adjacency[sw2][sw1] = l.port2

    def _handle_ConnectionUp(self, event):
        for msg in messages:
            event.connection.send(msg)

    def _handle_PacketIn(self, event):
        packet = event.parsed

        def flood():
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            msg.data = event.ofp
            msg.in_port = event.port
            event.connection.send(msg)

        def install_fwdrule(event, packet, outport):
            msg = of.ofp_flow_mod()
            msg.priority = 1
            msg.idle_timeout = 10
            msg.hard_timeout = 30
            msg.match = of.ofp_match.from_packet(packet, event.port)
            msg.actions.append(of.ofp_action_output(port=outport))
            msg.data = event.ofp
            msg.in_port = event.port
            event.connection.send(msg)

        if packet.dst.is_multicast:
            flood()
        else:
            try:
                thisHop = dpid_to_str(event.dpid)
                traffic = (thisHop, packet.src, packet.dst)
                hop = (thisHop, packet.dst)

                if lan_traffic.get(traffic) is not None:
                    outPort = lan_traffic.get(traffic)

                elif traffic in video_traffic:
                    tcpp = event.parsed.find('tcp')
                    outPort = 2 if tcpp.srcport == 10000 or tcpp.dstport == 10000 else 1

                else:
					outPort = switch_hosts.get(hop)

                install_fwdrule(event, packet, outPort)

            except AttributeError:
                flood()


def launch():
    core.registerNew(Controller)
