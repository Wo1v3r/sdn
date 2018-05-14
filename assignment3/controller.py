import random
import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.arp import arp
from pox.lib.addresses import EthAddr


from TopologyReader import *


log = core.getLogger()

topology = read_json('result.json')
short_paths = read_json('short-paths.json')

hosts = parse_hosts(topology)
switches = parse_switches(topology)
links = parse_links(topology)

switches_with_host = filter(lambda x: len(x.adjacent_hosts.keys()) != 0, switches)

hosts_mac = [host.mac for host in hosts]
hosts_id = [host.id for host in hosts]
hosts_ip = [host.ip for host in hosts]
ip_hosts = { host.ip: host.id for host in hosts }
ip_mac = { host.ip: host.mac for host in hosts }
host_switch = { switch.adjacent_hosts.keys()[0]: switch.id for switch in switches_with_host }

log.info('Hosts: ' + str(hosts_id))

class Controller (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)

    def _handle_PacketIn(self, event):

        def install_fwdrule(dpid, packet, inport, outport, switch_name):
            msg = of.ofp_flow_mod()
            msg.idle_timeout = 10
            msg.hard_timeout = 30
            msg.match = of.ofp_match.from_packet(packet)
            msg.buffer_id = None
            msg.in_port = inport
            msg.actions.append(of.ofp_action_output(port=outport))

            for connection in core.openflow.connections:
                if dpid_to_str(connection.dpid) == dpid:
                    log.info('Installing on Switch: ' + switch_name + '\t Port: '+ str(inport) + ' => Port: ' + str(outport))
                    connection.send(msg)

        def arp_reply(arp_request):
            src_ip = arp_request.protosrc
            dst_ip = arp_request.protodst
            dst_mac = EthAddr(ip_mac[str(dst_ip)])

            log.info("Faking ARP Reply")
            log.info('from ' + str(dst_ip) + ' to ' + str(src_ip))

            reply = arp()
            reply.opcode = arp.REPLY
            reply.hwtype = arp_request.hwtype
            reply.prototype = arp_request.prototype
            reply.hwlen = arp_request.hwlen
            reply.protolen = arp_request.protolen
            reply.hwsrc = dst_mac
            reply.hwdst = arp_request.hwsrc    
            reply.protosrc = dst_ip
            reply.protodst = src_ip

            ether = ethernet()
            ether.type = ethernet.ARP_TYPE
            ether.dst = packet.src
            ether.src = dst_mac
            ether.set_payload(reply)

            msg = of.ofp_packet_out()
            msg.data = ether.pack()
            msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
            msg.in_port = event.port
            
            event.connection.send(msg)
                            

        packet = event.parsed
        src_mac = packet.src
                
        if str(src_mac) in hosts_mac:
            if packet.type == packet.ARP_TYPE:
                if packet.payload.opcode == arp.REQUEST:
                    arp_reply(packet.payload)
                return

            if str(packet.payload.dstip) in ip_hosts:

                src_host_ip = packet.payload.srcip
                dst_host_ip = packet.payload.dstip
                
                src_hostname = ip_hosts[str(src_host_ip)]
                dst_hostname = ip_hosts[str(dst_host_ip)]

                log.info("Setting up path")
                log.info('From | Host:' + src_hostname + ' IP: ' + str(src_host_ip))
                log.info('To   | Host:' + dst_hostname + ' IP: ' +  str(dst_host_ip))
                
                src_switch = host_switch[src_hostname]
                dst_switch = host_switch[dst_hostname]

                paths = short_paths[src_switch][dst_switch]
                path = paths[random.randint(0, len(paths) - 1)]
                
                log.info('Selected Path: ' + str(path))

                first_switch = filter(lambda x: x.id == path[0], switches)[0]
                first_switch_dpid = first_switch.dpidstr
                
                install_fwdrule(first_switch_dpid, packet, 1, 1, src_switch)

                for hop in range(len(path)):
                    for link in links:
                        if hop == len(path) - 1 and link.node1 == path[hop] and link.node2 == dst_hostname:
                            outPort = link.port1
                            inPort = link.port2
                            break
                        if link.node1 == path[hop] and link.node2 == path[hop + 1]:
                            outPort = link.port1
                            inPort = link.port2
                            break
                        if link.node2 == path[hop] and link.node1 == path[hop + 1]:
                            outPort = link.port2
                            inPort = link.port1
                            break

                    hop_switch = filter(lambda x: x.id == path[hop], switches)[0]
                    hop_dpid = hop_switch.dpidstr

                    install_fwdrule(hop_dpid, packet, inPort, outPort, hop_switch.id)

def launch():
    core.registerNew(Controller)
