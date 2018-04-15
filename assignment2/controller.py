import pox.openflow.libopenflow_01 as of
from pox.core import core
from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.packet import arp, ethernet
from pox.lib.addresses import EthAddr
from hosts import clients

log = core.getLogger()

clients_mac = list(map(lambda (_,__,mac): mac,clients))



class Controller (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        self.installed_clients = {}
        self.arpTable = {}
        self.macToPort = {}

    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.info("Connection up event for: " + dpid)

    

    def _handle_PacketIn(self, event):

        def install_client(client):
            #create flow match rule #for each packet from h1 to h2 forward via port 3
            self.installed_clients[client] = True
            match = of.ofp_match()
            match.dl_dst = client
            fm = of.ofp_flow_mod()
            fm.match = match
            # fm.hard_timeout = 300
            # fm.idle_timeout = 100
            fm.actions.append(of.ofp_action_output(port=event.port))
            event.connection.send(fm)

        packet = event.parsed
        
        # if str(packet.src) in clients_mac and packet.src not in self.installed_clients:            
        #     log.info("Installing client")
            # install_client(packet.src)

        # If Request, check if we can reply
        # dont handle arp replies
        # otherwise flood


        if packet.type != packet.ARP_TYPE:
            log.info("Sending non ARP packet")

            #if destination is load-balancer, choose random server and forward packet
            #if destination is client, forward packet
            #if source is server, rewrite as loadbalancer
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            msg.actions.append( of.ofp_action_output( port = self.macToPort[packet.dst]) )

            event.connection.send( msg )
        else:            
            log.info("ARP Packet type")

            self.arpTable [packet.payload.hwsrc] = packet.payload.protosrc
            self.macToPort [packet.payload.hwsrc] = event.port
            log.info(self.arpTable)
            log.info(self.macToPort)

            if packet.payload.opcode == arp.REPLY:
                log.info( str(packet.payload.protosrc) + ' wants to reply')

                #if that someone is a server, rewrite its packet src to loadbalancer's
                #if that someone is a client, dont touch

                msg = of.ofp_packet_out()
                msg.data = event.ofp
                log.info(str(self.macToPort[packet.dst]))
                msg.actions.append( of.ofp_action_output( port = self.macToPort[packet.dst]) )

                event.connection.send( msg )
                
            if packet.payload.opcode == arp.REQUEST:
                log.info('Flooding')
                msg = of.ofp_packet_out()
                msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
                msg.data = event.ofp
                event.connection.send(msg)




def launch():
    core.registerNew(Controller)
