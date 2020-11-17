#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import OVSController
from mininet.cli import CLI
import time
import os

myBandwidth = 50    # bandwidth of link ink Mbps
myDelay = ['10ms', '10ms']    # latency of each bottleneck link
myQueueSize = 50  # buffer size in packets
myLossPercentage = 0   # random loss on bottleneck links

#
#           h2      h4       h6
#           |       |        |
#           |       |        |
#           |       |        |
#   h1 ---- S1 ---- S2 ----- S3 ---- h8
#           |   0ms |   5ms  |
#           |       |        |
#           |       |        |
#           h3      h5       h7
#
#

class ParkingLotTopo( Topo ):
    "Three switches connected to hosts. n is number of hosts connected to switch 1 and 3"
    def build( self, n=3 ):
        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')
        switch3 = self.addSwitch('s3')

        # Setting the bottleneck link parameters (htb -> Hierarchical token bucket rate limiting)
        self.addLink( switch1, switch2,
            bw=myBandwidth,
            delay=myDelay[0],
            loss=myLossPercentage,
            use_htb=True,
            max_queue_size=myQueueSize,
            )
        self.addLink( switch2, switch3,
            bw=myBandwidth,
            delay=myDelay[1],
            loss=myLossPercentage,
            use_htb=True,
            max_queue_size=myQueueSize,
            )

        for h in range(3*n - 1):
            host = self.addHost('h%s' % (h + 1))
            if h < n:
                self.addLink(host, switch1) # one host to switch 1 (h1, h2, h3)
            elif h < 2*n - 1:
                self.addLink(host, switch2) # n hosts to switch 2 (h4, h5)
            else:
                self.addLink(host, switch3) # n hosts to switch 3 (h6, h7, h8)


def perfTest():
    "Create network and run simple performance test"
    topo = ParkingLotTopo(n=3)
    net = Mininet( topo=topo,
                   host=CPULimitedHost, link=TCLink, controller = OVSController)
    net.start()
    print("Dumping host connections")
    dumpNodeConnections( net.hosts )
    print("Testing network connectivity")
    net.pingAll()
    # CLI( net )

    TCP_TYPE_first = 'bbr' # bbr or cubic
    TCP_TYPE_second = 'bbr' # bbr or cubic
    run_time_tot = 200 # total iperf3 runtime, in seconds. I recommend more than 300 sec.

    h1, h2, h3, h4, h5, h6, h7, h8 = net.get('h1','h2','h3','h4','h5','h6','h7','h8')


    # ### To indirectly measure RTT delay
    # print("--- ping h6 to h2 ---") # to measure the bottleneck level at link S1-S2 and S2-S3
    # h5.cmd('ping 10.0.0.8 -i 1 -c %d > h5_ping_result_%s &' % (run_time_tot, TCP_TYPE_first))
    # print("--- ping h7 to h5 ---") # to measure the bottleneck level at link S2-S3
    # h2.cmd('ping 10.0.0.8 -i 1 -c %d > h2_ping_result_%s &' % (run_time_tot, TCP_TYPE_second))


    # Receiver of flow 1 = h1
    h6.cmd('iperf3 -s -i 1 > h6_logs_4_%s &' % (myQueueSize))
    # Receiver of flow 2 = h4
    h7.cmd('iperf3 -s -i 1 > h7_logs_4_%s &' % (myQueueSize))

    # First, start to send the flow 1 : h8 --> h1
    #print("--- h8 sends to h1 with 1 TCP (%s) flow during %d sec ---" % (TCP_TYPE_first, run_time_tot))
    h1.cmd('iperf3 -c 10.0.0.6 -t %d -C cubic > h1_logs_4_cubic_%s &' % (run_time_tot, myQueueSize))

    # wait 10 seconds
    #time.sleep(10)

    # Secondly, start to send the flow 2 : h8 --> h4
    #print("--- h8 sends to h4 with 1 TCP (%s) flow during %d sec ---" % (TCP_TYPE_second, run_time_tot - 10))
    h1.cmd('iperf3 -c 10.0.0.7 -t %d -C bbr > h1_logs_4_bbr_%s &' % (run_time_tot, myQueueSize))

    # wait enough until all processes are done.

    h3.cmd('ping 10.0.0.8 -i 1 -c 200 > ping_4_%s &'%(myQueueSize))

    time.sleep(240)
    # CLI(net)
    net.stop() # exit mininet



if __name__ == '__main__':
    os.system("sudo mn -c")
    os.system("killall /usr/bin/ovs-testcontroller")
    setLogLevel( 'info' )
    print("\n\n\n ------Start Mininet ----- \n\n")
    perfTest()
    print("\n\n\n ------End Mininet ----- \n\n")
