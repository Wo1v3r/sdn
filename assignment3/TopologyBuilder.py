import networkx as nx
import matplotlib.pyplot as plt
from textwrap import wrap
import json
import random

GRAPH_SIZE = 30
graph = nx.erdos_renyi_graph(GRAPH_SIZE, 0.3)
while not nx.is_connected(graph):
    graph = nx.erdos_renyi_graph(GRAPH_SIZE, 0.3)
plt.subplot(111)
nx.draw(graph, with_labels=True, font_weight='bold')
plt.savefig("graph_print.png")

#shortest paths
short_paths = {}
for s_node in range(GRAPH_SIZE):
    short_paths['s' + str(s_node+1)] = {}
    for t_node in range(GRAPH_SIZE):
        paths = [path for path in nx.all_shortest_paths(graph,s_node,t_node)]
        short_paths['s' + str(s_node+1)]['s' + str(t_node+1)] = map(lambda x: map(lambda y: 's' + str(y+1),x),paths)

ids = map(lambda x: 's' + str(x+1), range(GRAPH_SIZE))
dpids = map(lambda x: ':'.join(wrap('%016x' % (x+1), 2)), range(GRAPH_SIZE))
switches = map(
    lambda x: {
        "id":ids[x],
        "dpid":dpids[x],
        "adjacent_switches":{},
        "next_port":1,
        "adjacent_hosts":{}
    }, 
    range(GRAPH_SIZE)
)
links = []
hosts = []

host_num = 1
for switch in switches:
    if random.random() < .5:
        host = {
            "id": "h" + str(host_num),
            "ip": "10.0.0." + str(host_num),
            "mac": ':'.join(wrap('%012x' % host_num, 2))
        }
        hosts.append(host)
        host_num = host_num + 1
        switch['adjacent_hosts'][host['id']] = switch['next_port']
        links.append(
            {
                "node1": switch['id'],
                "node2": host['id'],
                "port1": switch['next_port'],
                "port2": 1
            }
        )
        switch['next_port'] = switch['next_port'] + 1


data2 = nx.json_graph.node_link_data(graph, {'link': 'links', 'source': 'node1', 'target': 'node2'})
for link in data2['links']:
    port1 = switches[link['node1']]['next_port']
    port2 = switches[link['node2']]['next_port']
    switches[link['node1']]['adjacent_switches'][ids[link['node2']]] = port1
    switches[link['node2']]['adjacent_switches'][ids[link['node1']]] = port2
    switches[link['node1']]['next_port'] = port1 + 1
    switches[link['node2']]['next_port'] = port2 + 1
    links.append(
        {
            "node1": switches[link['node1']]['id'],
            "node2": switches[link['node2']]['id'],
            "port1": port1,
            "port2": port2
        }
    )

with open('result.json', 'w') as fp:
    json.dump({'hosts': hosts, 'switches': switches, 'links': links}, fp)

with open('short-paths.json', 'w') as sp:
    json.dump(short_paths, sp)
