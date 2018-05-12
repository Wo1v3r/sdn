import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr, EthAddr
from TopologyReader import *
from TopologyBuilder import short_paths
import random

log = core.getLogger()
json_data = read_json('result.json')
hosts = parse_hosts(json_data)
switches = parse_switches(json_data)
links = parse_links(json_data)

switches_with_host = filter(lambda x: len(x.adjacent_hosts.keys()) != 0, switches)

hosts_mac = [host.mac for host in hosts]
hosts_id = [host.id for host in hosts]
hosts_ip = [host.ip for host in hosts]
ip_hosts = { host.ip: host.id for host in hosts }
host_switch = { switch.adjacent_hosts.keys()[0]: switch.id for switch in switches_with_host }

print(host_switch)
#print(short_paths)

class Controller (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)

    def _handle_PacketIn(self, event):
        def install_fwdrule(event, packet, inport, outport):
            msg = of.ofp_flow_mod()
            msg.idle_timeout = 10
            msg.hard_timeout = 30
            # msg.match = of.ofp_match.from_packet(packet)
            msg.actions.append(of.ofp_action_output(port=outport))
            msg.data = event.ofp
            msg.in_port = inport
            event.connection.send(msg)

        packet = event.parsed
        log.info('packet in: ' +  str(packet.src))
        if str(packet.src) in hosts_mac:
            log.info('my name is: ' +  str(packet.src))
            log.info('my dst is: ' +  str(packet.next.protodst))
            log.info('dest host: ' + ip_hosts[str(packet.next.protodst)])
            src = host_switch[ip_hosts[str(packet.next.protosrc)]]
            dst = host_switch[ip_hosts[str(packet.next.protodst)]]
            path = short_paths[src][dst]
            log.info('path:' + str(path))
            chosen_path = path[random.randint(0, len(path))]
            log.info('path: ' + str(path))

            for hop in range(len(chosen_path)):
                for link in links:
                    if hop == 0:
                        if link.node1 == chosen_path[hop] and link.node2 == ip_hosts[str(packet.next.protosrc)]:
                            outPort = link.port1
                            inPort = link.port2
                    elif hop == len(chosen_path) - 1:
                        if link.node1 == chosen_path[hop] and link.node2 == ip_hosts[str(packet.next.protosrc)]:
                            outPort = link.port1
                            inPort = link.port2
                    elif link.node1 == chosen_path[hop] and link.node2 == chosen_path[hop + 1]:
                        outPort = link.port1
                        inPort = link.port2
                    elif link.node2 == chosen_path[hop] and link.node1 == chosen_path[hop + 1]:
                        outPort = link.port2
                        inPort = link.port1
                hop_dpid = filter(lambda x: x.id != hop, switches)
                hop_dpid = hop_dpid.id
                install_fwdrule(event, packet, inPort, outPort)



def launch():
    core.registerNew(Controller)
