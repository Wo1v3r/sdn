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
            msg.idle_timeout = 10
            msg.hard_timeout = 30
            msg.match = of.ofp_match.from_packet(packet)
            #msg.buffer_id = None
            msg.in_port = inport
            msg.actions.append(of.ofp_action_output(port=outport))

            for connection in core.openflow.connections:
                if dpid_to_str(connection.dpid) == dpid:
                    log.info('installing on ' + dpid + ' rule from: '+ str(inport) + ' to ' + str(outport))
                    connection.send(msg)

        def send_packet(dpid, outport, data):
            msg = of.ofp_packet_out(in_port=1, data = data)
            msg.actions.append(of.ofp_action_output(port = outport))
            for connection in core.openflow.connections:
                if dpid_to_str(connection.dpid) == dpid:
                    log.info('sending msg from: ' + dpid + ' port from: '+ str(1) + ' to ' + str(outport))
                    connection.send(msg)


        def flood(event):
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            msg.data = event.ofp
            msg.in_port = event.port
            event.connection.send(msg)
                            
        packet = event.parsed
                
        #To filter out ether packets ; and isinstance(packet.payload, ipv4)

        if str(packet.src) in hosts_mac:
            log.info('from host: ')
            log.info('my name is: ' +  str(packet.src))

            if packet.type == packet.ARP_TYPE:
                log.info("ARP Packet type")
                log.info('from ' + str(packet.next.protosrc) + ' to ' + str(packet.next.protodst)) 
                # Get the ARP request from packet
                arp_req = packet.next

                # Create ARP reply
                arp_rep = arp()
                arp_rep.opcode = arp.REPLY
                arp_rep.hwsrc = EthAddr(ip_mac[str(arp_req.protodst)])
                arp_rep.hwdst = arp_req.hwsrc    
                arp_rep.protosrc = arp_req.protodst
                arp_rep.protodst = arp_req.protosrc

                # Create the Ethernet packet
                ether = ethernet()
                ether.type = ethernet.ARP_TYPE
                ether.dst = packet.src
                ether.src = EthAddr(ip_mac[str(arp_req.protodst)])
                ether.set_payload(arp_rep)

                # Send the ARP reply to client
                msg = of.ofp_packet_out()
                #msg.data = ether.pack()
                msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
                msg.in_port = event.port
                event.connection.send(msg)     
            else:
                log.info("Non ARP packet")
                log.info('my dst is: ' +  str(packet.next.protodst))
                log.info('dest host: ' + ip_hosts[str(packet.next.protodst)])
                src = host_switch[ip_hosts[str(packet.next.protosrc)]]
                dst = host_switch[ip_hosts[str(packet.next.protodst)]]
                path = short_paths[src][dst]
                chosen_path = path[random.randint(0, len(path) - 1)]
                log.info('chosen:' + str(chosen_path))

                for hop in range(len(chosen_path)):
                    for link in links:
                        if hop == len(chosen_path) - 1:
                            if link.node1 == chosen_path[hop] and link.node2 == ip_hosts[str(packet.next.protodst)]:
                                outPort = link.port1
                                inPort = link.port2
                                log.info(link)
                        elif link.node1 == chosen_path[hop] and link.node2 == chosen_path[hop + 1]:
                            outPort = link.port1
                            inPort = link.port2
                            log.info(link)
                        elif link.node2 == chosen_path[hop] and link.node1 == chosen_path[hop + 1]:
                            outPort = link.port2
                            inPort = link.port1
                            log.info(link)

                    hop_switch = filter(lambda x: x.id == chosen_path[hop], switches)[0]
                    log.info(str(hop_switch))
                    hop_dpid = hop_switch.dpidstr
                    install_fwdrule(hop_dpid, packet, inPort, outPort)
                
                # installing rule for source host to his switch
                hop_switch = filter(lambda x: x.id == chosen_path[0], switches)[0]
                hop_dpid = hop_switch.dpidstr
                install_fwdrule(hop_dpid, packet, 1, 1)
                # send_packet(hop_dpid, 1, event.ofp)


def launch():
    core.registerNew(Controller)
