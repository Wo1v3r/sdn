import pox.openflow.libopenflow_01 as of
from pox.lib.packet.ipv4 import ipv4
from pox.core import core
from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.util import dpidToStr
from pox.lib.packet.ethernet import ethernet
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.packet.arp import arp
from TopologyReader import *
import random

log = core.getLogger()

topology = read_json('result.json')
hosts = parse_hosts(topology)
switches = parse_switches(topology)
links = parse_links(topology)

short_paths = read_json('short-paths.json')


switches_with_host = filter(lambda x: len(x.adjacent_hosts.keys()) != 0, switches)

hosts_mac = [host.mac for host in hosts]
hosts_id = [host.id for host in hosts]
hosts_ip = [host.ip for host in hosts]
ip_hosts = { host.ip: host.id for host in hosts }
ip_mac = { host.ip: host.mac for host in hosts }
host_switch = { switch.adjacent_hosts.keys()[0]: switch.id for switch in switches_with_host }

# print(host_switch)
#print(short_paths)

print(hosts_id)

class Controller (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)

    def _handle_PacketIn(self, event):

        def install_fwdrule(dpid, packet, inport, outport):
            msg = of.ofp_flow_mod()
            # msg.idle_timeout = 10
            # msg.hard_timeout = 30
            msg.in_port = inport
            msg.actions.append(of.ofp_action_output(port=outport))

            for connection in core.openflow.connections:
                if dpid_to_str(connection.dpid) == dpid:
                    log.info('installing on ' + dpid + 'rule from: '+ str(inport) + ' to ' + str(outport))
                    connection.send(msg)


        packet = event.parsed
                
        #To filter out ether packets ; and isinstance(packet.payload, ipv4)

        if str(packet.src) in hosts_mac:
            log.info('from host: ')
            log.info('my name is: ' +  str(packet.src))
            log.info('my dst is: ' +  str(packet.payload.protodst))
            log.info('dest host: ' + ip_hosts[str(packet.payload.protodst)])
            src = host_switch[ip_hosts[str(packet.payload.protosrc)]]
            dst = host_switch[ip_hosts[str(packet.payload.protodst)]]
            path = short_paths[src][dst]
            chosen_path = path[random.randint(0, len(path) - 1)]
            log.info('chosen:' + str(chosen_path))

            for hop in range(len(chosen_path)):
                for link in links:
                    if hop == 0:
                        if link.node1 == chosen_path[hop] and link.node2 == ip_hosts[str(packet.payload.protosrc)]:
                            outPort = link.port1
                            inPort = link.port2
                    elif hop == len(chosen_path) - 1:
                        if link.node1 == chosen_path[hop] and link.node2 == ip_hosts[str(packet.payload.protosrc)]:
                            outPort = link.port1
                            inPort = link.port2
                    elif link.node1 == chosen_path[hop] and link.node2 == chosen_path[hop + 1]:
                        outPort = link.port1
                        inPort = link.port2
                    elif link.node2 == chosen_path[hop] and link.node1 == chosen_path[hop + 1]:
                        outPort = link.port2
                        inPort = link.port1

                hop_switch = filter(lambda x: x.id == chosen_path[hop], switches)[0]
                log.info(str(hop_switch))
                hop_dpid = hop_switch.dpidstr
                install_fwdrule(hop_dpid, packet, inPort, outPort)



def launch():
    core.registerNew(Controller)
