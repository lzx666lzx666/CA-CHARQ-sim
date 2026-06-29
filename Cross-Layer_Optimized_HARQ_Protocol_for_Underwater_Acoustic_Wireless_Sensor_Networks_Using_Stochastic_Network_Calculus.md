2024 International Conference on Emerging Research in Computational Science (ICERCS)
Cross-Layer Optimized HARQ Protocol for
Underwater Acoustic Wireless Sensor Networks
Using Stochastic Network Calculus
81959801.4202.52136SCRECI/9011.01
1stSivajayaprakash A 2ndRajeev Sukumaran 3rdKumar C
Department of Computer Science and Department of Computer Science and Department of Electrical and
Engineering SRM Institute of Science Engineering SRM Institute of Science Electronics Engineering,
and Technology and Technology Karpagam College of Engineering
Kattankulathur, India Kattankulathur, India Coimbatore-641032, India,
sivajayaprakash05@gmail.com rejeevcbe@gmail.com ckumarme81@gmail.com
retransmission, or by retransmitting errored packets when
:IOD Abstract—UAWSNs face challenges such as long
needed. However, these protocols are not defined to work
propagation delays, limited bandwidth, and varying channel
| EEEI conditions. To solve these problems, we developed a new under the changing nature of the underwater
protocol called Multi- Hop Cross-Layer Optimized Hybrid environment and the influence of channel conditions.
4202© Automatic Repeat Request (CLO-HARQ) suitable for Traditional HARQ protocols are mostly focused on single-
UAWSNs. This protocol automatically changes the hop communication, and in multi-hop networks, they
retransmission strategy and error correction redundancy
00.13$/42/7-6943-5133-8-979 cannot provide good solutions to the problems when sensor
based on real-time feedback from the physical and network
layers. A unique feature of this protocol is the inclusion of nodes transmit data to sink nodes together with
environmental factors such as water salinity and intermediate relay nodes. This article introduces a new
temperature in the decision-making process. Also, using protocol called Multi-Hop Cross-Layer Optimized HARQ
Stochastic Network Calculus (SNC), stochastic traffic
(CLO-HARQ), whose main contributions are as follows:
characteristics predict single-hop and multi-hop
communication delay (delay), energy usage (energy usage), Environmental Feedback Integration: This protocol
and throughput. In the performance evaluation of CLO-
automatically adjusts retransmissions based on real-time
HARQ, it has been shown to provide significant
environmental factors such as water temperature and
improvement in efficiency, throughput, and delay over
| )SCRECI( existing HARQ methods. It is well-suited for long-term salinity, which are key factors affecting underwater acoustic
underwater monitoring and is a sustainable solution for signal propagation.
energy-constrained sensor networks.
Multi-Hop Communication: CLO-HARQ is specially
ecneicS Keywords—Stochastic network calculus, Underwater acoustic
designed for multi-hop communication, which is a key
wireless sensor Networks, Hybrid Automatic Repeat Request,
feature for large-scale underwater monitoring networks
Single Hop communication, multi-Hop communication.
lanoitatupmoC where direct communication between sensor nodes and the
sink is not possible.
I. INTRODUCTION
UAWSNs are important in various applications, Energy Efficiency: This protocol adjusts transmission
especially in areas such as environmental monitoring, power and redundancy according to network topology and
ni
hcraeseR resource exploration, and defense-related surveillance. prevailing channel conditions and helps reduce energy
However, the under- water environment creates unique consumption.
challenges, including slow propagation speeds, narrow
Stochastic Network Calculus (SNC): uses SNC models
gnigremE bandwidth, and highly variable channel conditions [1].
to evaluate key performance indicators such as delay, energy
These make communication susceptible to high error rates,
efficiency, throughput, and packet loss under stochastic
energy wastage, and long delays, making it difficult to
no traffic conditions in single-hop and multi-hop
establish reliable communication in real- time or mission-
ecnerefnoC communication environments.
critical applications. Communication proto- cols
developed for terrestrial networks cannot meet the II. RELATED WORK
stringent requirements of UAWSNs. Whereas, the physical
lanoitanretnI UASNs have emerged as an important research field
characteristics of the acoustic medium, such as high
due to their applications in areas such as environmental
attenuation and variable noise levels, cause high packet
monitoring, disaster response, and defense operations.
loss and long delay. Thus, it is necessary to develop new
However, UASNs pose unique challenges, including high
protocols suitable for the underwater environment. Hybrid
4202
propagation delay, low bandwidth, and high energy
Automatic Repeat Request (HARQ) is widely used in
consumption [2]. To solve these problems, researchers
current UAWSN communication protocols, which
have designed several communication protocols, error
combines Forward Error Correction (FEC) and Automatic
control techniques, and energy-efficient strategies. This
Repeat Request (ARQ). HARQ protocols im- prove
chapter reviews related studies on Hybrid Automatic
reliability by correcting errors at the receiver without
979-8-3315-3496-7/24/$31.00 ©2024 IEEE
Authorized licensed use limited to: INSTITUTE OF ACOUSTICS CAS. Downloaded on May 06,2026 at 08:24:35 UTC from IEEE Xplore. Restrictions apply.


Repeat request (HARQ) protocols, cross-layer consideration, improving energy efficiency especially in
optimization, and multi-hop communication in underwater multi-hop scenarios [24].
environments. Although these frameworks provide improvements in
energy consumption and network performance, they ignore
A. Error Control Mechanisms in Underwater
Communication environmental factors, especially water temperature and
salinity. These factors play an important role in acoustic
Protecting data integrity is critical in UASNs. signal propagation, so these features are important for the
Traditional Automatic Repeat request (ARQ) protocols are actual operations of UASNs.
not suitable for UASNs because they cause high
C. Environmental Adaptation in Underwater Networks
retransmission overhead. Thus, Hybrid ARQ (HARQ)
protocols combining ARQ and Forward Error Correction Environmental factors such as water temperature,
(FEC) are increasingly used. salinity and pressure greatly affect underwater acoustic
signal propagation [6]. Recent studies have attempted to
1) ARQ and HARQ in UASNs: Traditional ARQ
incorporate environmental awareness into protocol design
methods rely only on retransmission for error correction,
[22].
so they fail when considering the long propagation delays
of acoustic signals in underwater environments. Several • Environmentally adaptive MAC protocol that adjusts
types of HARQ methods have been proposed to improve transmission power using real- time measurements of
performance. water temperature and salinity. This approach can
improve energy efficiency and reduce packet loss in
• Type-I HARQ uses fixed FEC and retransmissions, and
shallow water environments.
it minimizes packet loss under moderate channel
conditions. However, this reduces performance in highly • Aadaptive routing protocol that changes route selection
based on predicted signal propagation delays that affect
variable underwater channels [3].
environmental conditions. Their study emphasized the
• Type-II HARQ uses incremental redundancy (IR) to send
importance of integrating environmental feedback into
extra parity bits on retransmissions, matching channel
UASN protocols, which helps improve reliability.
conditions.
• Type-III HARQ extends Type-II and provides a way However, HARQ-based cross-layer protocols still have
to combine multiple redundancy versions. Type-III the disadvantage of incorporating environmental factors
HARQ provides better error correction in highly [23]. Al- though current solutions are effective methods of
fluctuating underwater environments, but it produces optimizing transmission power or route selection, they
higher energy consumption. address error correction and retransmission strategies in
dynamic environmental conditions.
However, current HARQ protocols are mostly
designed for single-hop communication and are mostly D. Multi-Hop Communication in UASNs
developed at the physical layer only. This makes cross-
Multi-hop communication is important for expanding the
layer optimization necessary for unique requirements in
coverage of UASNs because direct communication
UASNs.
between sensor nodes and sink nodes is often not possible
B. Cross-Layer Optimization for UASNs in large-scale systems [27]. However, multi-hop
communication creates new challenges, such as increased
Cross-layer design is a promising method to optimize
latency, increased energy consumption, and overall
communication in UASNs, which establishes
increase in packet loss across multiple hops [7].
communication between the physical, MAC, and network
layers. Instead of following a traditional layered 1) Multi-Hop Routing Protocols: Several multi-hop
architecture, cross-layer protocols improve performance routing protocols have been proposed to improve
by sharing information between layers [4]. communication efficiency in UASNs. These protocols
often aim to balance energy consumption, reduce latency,
1) Energy Efficiency through Cross-Layer Design: Energy
and improve reliability.
consumption is a major problem in UASNs because
• A multi-hop routing protocol that selects intermediate
the battery capacity of underwater nodes is low and it is
nodes using their pending energy and proximity to the sink
difficult to recharge or replace the battery. Several
to minimize energy consumption. Although this protocol
cross-layer optimization frameworks have been
greatly improves network lifetime, it ignores packet
proposed to overcome these challenges [5]:
losses during transmissions.
• A cross-layer framework that automatically changes
• An energy-efficient multi-hop routing protocol that
transmission power and modulation schemes by sharing
balances energy consumption and delay using adaptive
physical layer metrics such as Signal-to-Noise Ratio
modulation techniques. They showed that their protocol
(SNR) with the MAC layer. In this way transmission
can adjust the modulation scheme at each hop and reduce
is optimized according to current channel conditions
the total delay in the network [8].
and energy consumption is reduced.
These protocols improve energy efficiency and reduce
• A cross-layer protocol that combines routing decisions
delay, but they do not integrate HARQ mechanisms to
with MAC layer scheduling. They take protocol,
network topology and energy consumption into
Authorized licensed use limited to: INSTITUTE OF ACOUSTICS CAS. Downloaded on May 06,2026 at 08:24:35 UTC from IEEE Xplore. Restrictions apply.


handle packet losses in multi-hop communication, which is directly to a central sink node (single-hop) or via multiple
a major challenge in large-scale UASNs. relay nodes (multi-hop) [11]. These nodes exchange
information either directly to a central sink node (single-
E. Stochastic Network Calculus (SNC) in Performance
hop) or via multiple relay nodes (multi-hop). This network
Evaluation
supports applications such as environmental monitoring, in
Stochastic Network Calculus (SNC) is a tool used to
which information on variables such as temperature,
predict the performance of communication protocols under
salinity, and pH levels is collected.
stochastic traffic conditions. SNC provides a mathematical
• Single-Hop Communication: Sensor nodes send
framework that probabilistically models network behavior
information directly to the sink when they are within the
and analyzes delay, throughput, and energy consumption.
sensing range.
1) SNC in Single-Hop Communication:
• Multi-Hop Communication: In large-scale networks,
• SNC models to evaluate the performance of HARQ
sensor nodes use relay nodes to send their information to
protocols in terrestrial wire- less networks. Their
the sink, as direct communication may be difficult due to
research showed that SNC is very effective in modeling
distance or ambient conditions.
delay and throughput under random traffic conditions.
However, its use in UASNs is limited. B. Channel and Environmental Modeling
• Single-hop communication using SNC in underwater
Underwater acoustic environment is defined by SNR
networks. Although their results show that SNC can
and BER, which are affected by factors such as water salinity
accurately predict performance measures such as delay
and temperature. These factors affect the propagation of the
and packet loss probability, this study does not
acoustic signal, and high salinity or cold water generally
investigate multi-hop scenarios [9].
decrease the SNR and increase the BER. This channel model
2) SNC in Multi-Hop Communication: Only a few
takes environmental factors directly into account and enables
studies have used SNC in multi-hop communication. A
the CLO-HARQ protocol to dynamically adjust
major opportunity exists to integrate SNC models with
retransmission strategies [12].
HARQ to provide comprehensive performance
assessment in single-hop and multi-hop scenarios.
C. Traffic Model
F. Gaps and Motivation for the Proposed Work
Traffic generated by sensor nodes is modeled by
Although there is extensive research on HARQ stochastic arrival curves, which reflect variations in packet
protocols, cross-layer optimization, and multi-hop generation rates. Packet arrival process is expressed as eq
communication, there are some key issues in the current 1:
literature: 1. Lack of environmental awareness in HARQ
(1)
protocols: Adaptive protocols that modify transmission (cid:1)((cid:3)) ≤ (cid:6)((cid:3))= (cid:8)(cid:3)+(cid:10)
parameters based on environmental factors have been Here, is the total number of packets that arrived at time
proposed, but no inclusive HARQ protocol includes real- is (cid:1)th(e(cid:3) )average packet arrival rate (packets/second), and
time environmental feedback in its retransmission and (cid:3)re,p(cid:8)resents traffic bursts. Similarly, the packet service proces(cid:10)s
redundancy strategies [10]. 2. Low Multi-Hop HARQ is modeled as a stochastic service curve as eq 2:
Solutions: Mostly HARQ protocols focus only on single- (2)
(cid:18)
hop (cid:12)((cid:3))≥ (cid:14)((cid:3)) = (cid:15)((cid:3)−(cid:17)) +(cid:19)
where:
communication and in multi-hop scenarios, where
cumulative delay, energy consumption and packet loss are
represents the cumulative number of packets served by
important to deal with, they are not extended. 3. Less (cid:12)ti(m(cid:3)e) , is the average service rate (packets/second), is the
Application of SNC in HARQ Protocols: SNC has been maxi(cid:3)m(cid:15)um delay before service begins, and, accou(cid:17)nts for
successfully used to evaluate performance in terrestrial burst service rates enabled by AMC during fav(cid:19)orable channel
wireless networks, but it has not yet been implemented
conditions.
much in HARQ-based underwater networks, especially in
multi-hop scenarios. These issues motivate the IV. SYSTEM ARCHITECTURE OF THE CROSS-LAYER
development of the Multi-Hop Cross- Layer Optimized OPTIMIZED HARQ PROTOCOL
HARQ (CLO-HARQ) Protocol to handle the unique In this chapter, we introduce the system architecture of the
challenges in UASNs, which integrates environmental Cross-Layer Optimized HARQ (CLO-HARQ) protocol
feedback, multi-hop communication and SNC-based designed to improve the performance of underwater acoustic
performance evaluation [21].
wireless sensor networks (UAWNs) [13]. This architecture is
illustrated in Fig 1, where data transmission, error correction
III. SYSTEM MODEL
and cross-layer management illustrate the cooperation
A. Network Architecture
between related components. The proposed CLO-HARQ
We investigate an underwater acoustic wireless sensor protocol incorporates feedback from the physical and
net- work in which many sensor nodes are deployed in a network layers to optimize retransmission strategies [25].
monitoring area. These nodes exchange information either The physical layer provides real-time feedback on channel
Authorized licensed use limited to: INSTITUTE OF ACOUSTICS CAS. Downloaded on May 06,2026 at 08:24:35 UTC from IEEE Xplore. Restrictions apply.


conditions (SNR, BER), and the network layer reports energy policy in multi-hop networks and chooses relay nodes
Quality of Service (QoS) requirements such as latency and by evaluating the link quality and remaining energy level.
packet delivery ratio (PDR) [30].
C. Energy Efficiency and Power Control
In UAWSNs, energy efficiency is important because the
battery life of sensor nodes is under control. The CLO-
HARQ protocol adjusts transmission power according to
real-time SNR levels and optimizes energy utilization [26].
Meanwhile, this protocol reduces the energy policy in
multi-hop networks and selects relay nodes by checking
their remaining energy level and link quality [16].
D. Multi-Hop Optimization
In multi-hop conditions, CLO-HARQ protocol
optimizes routing paths to reduce energy consumption and
delay. Relay nodes are selected based on their residual
energy levels and link quality between source and
destination nodes [29]. This ensures that the load is
Fig. 1. Work flow diagram of CLO-HARQ shared equally among the nodes in the network,
preventing a single node from using up all of its energy
A. Cross-Layer Optimization
too quickly.
The proposed CLO-HARQ protocol uses input from the
V. STOCHASTIC NETWORK CALCULUS-BASED
physical and network levels to enhance retransmission
PERFORMANCE EVALUATION
techniques. The physical layer gives real-time input on
channel conditions (SNR, BER), whereas the network layer Stochastic Network Calculus (SNC) provides a
reports Quality of Service (QoS) needs like latency and framework to evaluate the performance of the CLO-
packet delivery ratio (PDR). By integrating these feedback HARQ protocol under stochastic traffic and channel
settings with environmental data (such as temperature and conditions [17], [28]. We apply SNC models to both
salinity), the protocol automatically modifies retransmission single-hop and multi-hop scenarios, deriving key
tactics and redundancy levels [14]. Physical Layer Feedback: performance metrics such as delay, energy efficiency,
This protocol requires constant monitoring of channel throughput, and packet loss probability.
conditions (e.g., SNR, BER) and environmental data (e.g.,
A. Single-Hop Communication
salinity, temperature). This feedback helps determine whether
In the single-hop scenario, the SNC model evaluates the
to improve redundancy (i.e., more error correcting bits) or
performance of direct communication between a sensor
reduce retransmissions. Network Layer Requirements:
node and the sink [17]. Key metrics include [20]: Delay:
Depending on the application’s QoS needs, the protocol
The total delay for packet transmission, including
prioritizes either low latency (for redundant activities) or high
retransmissions, is modeled as eq (3):
packet delivery ratio (for operations crucial to data
correctness). In multi-hop networks, the network layer (3)
(cid:24)
impacts relay node selection, giving priority to nodes with
CLO-HARQ l(cid:25)oss
greater link quality and energy availability. (cid:20) ((cid:3))=(cid:20)(cid:21)((cid:3))+(cid:22) (cid:27)
(cid:25)(cid:26)(cid:21)
B. Adaptive HARQ Mechanism ⋅(cid:20)(cid:25)((cid:3))
where is the initial transmission delay, and
Based on SNR, BER, and environmental conditions, the is the de(cid:20)l(cid:21)a(y(cid:3) )associated with retransmissions. E(cid:20)ne(cid:25)r(g(cid:3)y)
adaptive HARQ technique in CLO-HARQ modifies its
Efficiency: The energy efficiency [18] is calculated as eq
redundancy levels. By ensuring that only incorrect packet
(4):
portions are retransmitted, this protocol leverages
(4)
incremental redundancy HARQ to minimize the extra wasted
(cid:12)((cid:3))
flow in full retransmissions and conserve energy and (cid:29)((cid:3))= consumed
(cid:29) ((cid:3))
bandwidth [24]. Automatic adjustments are made to this
where is the total energy consumed for
protocol [15]: Favorable Conditions: It improves throughput (cid:29)consumed ((cid:3))
transmission and retransmissions. Throughput: The
by decreasing protocol redundancy and increasing
throughput is expressed as eq 5:
transmission rate at high SNR and low BER levels.
Unfavorable Conditions: Increasing protocol redundancy (5)
(cid:12)((cid:3))
lowers transmission rate and guarantees depend- able packet (cid:30)((cid:3))≥
delivery in low SNR and high BER situations. Energy This throughput calcula(cid:3) tion accounts for the number of
efficiency is crucial in UAWSNs since sensor node battery successfully transmitted packets over time. Packet Loss
life is regulated. The CLO-HARQ protocol optimizes energy Probability: The packet loss probability is given by eq(6):
use by modifying transmission power in accordance with
(6)
current SNR levels. In the meantime, this protocol lowers the (cid:27)loss =(cid:27)((cid:1)((cid:3))>(cid:12)((cid:3)+(cid:20)))
Authorized licensed use limited to: INSTITUTE OF ACOUSTICS CAS. Downloaded on May 06,2026 at 08:24:35 UTC from IEEE Xplore. Restrictions apply.


![image_4_1](https://doc2markdown.com/images/20260608/ccf719ef-effe-4891-a570-979fdc1247d7/page_4/image_4_1.png)


This reflects the likelihood of packet loss based on the c) :
arrival and service processes.
(10)
(cid:27)loss multi-hop =1−∏3 "1−(cid:27)l!oss
B. Multi-Hop Communication !(cid:26)(cid:21) %
This cumulative probability reflects the likelihood of
In multi-hop scenarios, the SNC model extends to
packet loss across multiple hops.
account for the cumulative delay, energy consumption,
and throughput across multiple hops. Each hop introduces VI. SIMULATION SETUP AND RESULTS
its own arrival and service processes, allowing for a more
To evaluate the performance of the CLO-HARQ
comprehensive evaluation of the network's performance
protocol, we use the Riverbed network simulator. The
[19].
simulation setup consists of five sensor nodes, one sink
node, and up to three relay nodes to support multi-hop
a) Total Delay: The total delay in a multi-hop network communication. The network operates over a bandwidth
of 10 kHz, with varying SNR and BER values depending
is the sum of delays experienced at each hop as eq
on environmental conditions and node distances.
(7):
(7)
multi-hop
(cid:20) ((cid:3)) A. Performance Metrics
(cid:24)
The protocol's performance is evaluated based on:
! p!ropagation l(cid:25)oss
=(cid:22) "(cid:30)#$+(cid:30) %+(cid:22) (cid:27) • Average Delay: Total time taken for a packet to be
!(cid:26)(cid:21) (cid:25)(cid:26)(cid:21) transmitted, including retransmissions.
r(e!tr,(cid:25)a)nsmit
⋅(cid:30) (7)
where is the transmission time for the packet, • Energy Efficiency: Number of successfully transmitted
(cid:30) (i$s the propagation delay, and is the packets per joule of energy consumed.
propagation r(cid:25)etransmit
(cid:30) (cid:30)
delay due to retransmission . Energy Efficiency: The
energy efficiency for multi-ho)p communication is defined • Throughput: Rate of successfully transmitted packets per
second.
as eq (8):
(8) • Packet Loss Probability: Likelihood of a packet being lost
(cid:24)
multi-hop ! l(cid:25)oss during transmission.
(cid:29) =(cid:22) *(cid:29)+$+(cid:22) (cid:27)
!(cid:26)(cid:21) (cid:25)(cid:26)(cid:21)
r(e!t,r(cid:25)a)nsmit
⋅(cid:29) ,
TABLE I. SIMULATION PARAMETER
where is the total energy consumed during the
multi-hop
(cid:29) Parameter Value
entire multi-hop communication, is the total number of
hops, is the energy consumed- for transmission in the Bandwidth 10 kHz
!
th ho(cid:29)p+,$ is the maximum number of retransmissions,
Packet Arrival Rate packets/second
. is /the probability of loss after the -th (cid:8)=2
l(cid:25)oss
(cid:27) ) BPSK (for low SNR), QPSK, 16-
retransmission, and is the energy consumed Modulation Schemes
r(e!t,r(cid:25)a)nsmit QAM (for higher SNR)
(cid:29)
during retransmission in the -th hop for the -th
Energy Consumption per
retransmission. . ) 50 mJ per packet
Transmission
b) Throughput:
Retransmission Delay 100 ms
The overall throughput in a multi-hop scenario is
Varying temperature and salinity
limited by the hop with the lowest throughput as given in
Environmental Factors values for realistic underwater
eq (9): conditions
(9)
multi-hop 1 l!oss
(cid:30) = ⋅1 "1−(cid:27) %
(cid:3)
!(cid:26)(cid:21)
where multi-hop is the total throughput for the entire TABLE II. COMPARISON OF DELAY(MS) ACROSS DIFFERENT
(cid:30) TECHNIQUES AT VARIOUS SNR(DB) LEVELS
multi-hop communication, is the total time taken for the
transmission process, is t(cid:3)he total number of hops, and Delay(ms)
- SNR
l!oss is the packet loss probability at the -th hop. Packet (dB) SNC SIMULATION HARQ FEC ARQ
(cid:27) .
5 218 225 280 300 350
Loss Probability: In multi-hop networks, the total 10 211 215 260 280 320
packet loss probability can be calculated as as given in eq 15 202 205 240 270 300
(10): 20 200 203 220 250 290
25 198 200 210 240 280
Authorized licensed use limited to: INSTITUTE OF ACOUSTICS CAS. Downloaded on May 06,2026 at 08:24:35 UTC from IEEE Xplore. Restrictions apply.


The performance evaluation of the proposed Multi-Hop
Cross-Layer Optimized Hybrid Automatic Repeat Request
(CLO-HARQ) protocol, conducted under varying
environmental conditions and using stochastic network
calculus (SNC), reveals its potential to address the unique
challenges in underwater acoustic wireless sensor networks
(UAWSNs) as shown in Fig 2,Fig 3,Fig 4. These challenges
include high propagation delay, limited bandwidth, and high
Fig. 4. Energy efficiency vs SNR
TABLE V. COMPARISON OF PACKET LOSS PROBABILITY (%) ACROSS
DIFFERENT TECHNIQUES AT VARIOUS SNR (DB) LEVELS
Packet loss probability(%)
SNR
(dB) SNC SIMULATION HARQ FEC ARQ
energy consumption. 5 4 5 6 8 12
10 2 3 4 5 10
Fig. 2. Delay vs SNR 15 1 2 3 4 8
20 1 1 2 3 5
TABLE III. COMPARISON OF THROUGHPUT (PACKETS/SECOND) ACROSS 25 0.5 0.5 1 2 3
DIFFERENT TECHNIQUES AT VARIOUS SNR
SN Throughput(kbps)
R SN SIMULATIO HAR FE AR
(dB) C N Q C Q
5 2.1 1.9 1.7 1.5 1.2
10 2.3 2.1 1.9 1.7 1.4
15 2.6 2.4 2.1 1.9 1.6
20 2.8 2.6 2.4 2.1 1.8
25 2.9 2.8 2.5 2.3 2
Fig. 5. Energy efficiency vs SNRPacket loss vs SNR
Fig. 3. Throughput vs SNR
B.Delay Analysis
TABLE IV. COMPARISON OF ENERGY EFFICIENCY (PACKETS/JOULE) The evaluation indicates that CLO-HARQ
ACROSS DIFFERENT TECHNIQUES AT VARIOUS SNR (DB) LEVELS
significantly reduces delay compared to conventional HARQ,
Energy Efficiency (%) FEC, and ARQ protocols across different signal-to-noise
SNR
ratio (SNR) levels as shown in Fig 5.
(dB) SNC SIMULATION HARQ FEC ARQ
At an SNR of 5 dB, the delay for CLO-HARQ is 218
5 6 5.5 5 4 3 ms, which is notably lower than 225 ms for simulation-based
models and 350 ms for ARQ. As SNR increases to 25 dB,
10 7 6.5 6 5 4
CLO-HARQ achieves a delay of 198 ms, maintaining a clear
15 7 6.5 6 5 4
advantage over other methods. This demonstrates that CLO-
20 7 6.5 6 5 4
HARQ's dynamic adjustment of redundancy and
25 7 7.5 6 5 4
retransmission strategies, guided by real-time feedback from
channel conditions and environmental factors, effectively
Authorized licensed use limited to: INSTITUTE OF ACOUSTICS CAS. Downloaded on May 06,2026 at 08:24:35 UTC from IEEE Xplore. Restrictions apply.


![image_6_1](https://doc2markdown.com/images/20260608/ccf719ef-effe-4891-a570-979fdc1247d7/page_6/image_6_1.jpg)


![image_6_2](https://doc2markdown.com/images/20260608/ccf719ef-effe-4891-a570-979fdc1247d7/page_6/image_6_2.jpg)


![image_6_3](https://doc2markdown.com/images/20260608/ccf719ef-effe-4891-a570-979fdc1247d7/page_6/image_6_3.jpg)


![image_6_4](https://doc2markdown.com/images/20260608/ccf719ef-effe-4891-a570-979fdc1247d7/page_6/image_6_4.jpg)


minimizes latency. Its multi-hop optimization further ensures constrained networks where sensor nodes are often deployed
efficient routing and reduces cumulative delays, particularly in remote or inaccessible locations.
in large-scale networks.
C.Throughput Analysis VII. CONCLUSION
Throughput, measured as the rate of successfully
The Multi-Hop Cross-Layer Optimized Hybrid
transmitted packets per second, is another critical metric
Automatic Repeat Request (CLO-HARQ) protocol introduces
where CLO-HARQ excels. Across all SNR levels, it
an innovative solution to the persistent challenges in
consistently outperforms other protocols. For instance, at 5
underwater acoustic wireless sensor networks (UAWSNs),
dB, CLO-HARQ achieves a throughput of 2.1 packets/second
compared to 1.9 for simulation, 1.7 for HARQ, and just 1.2 such as high delays, limited bandwidth, and energy
for ARQ. At 25 dB, its throughput reaches 2.9 inefficiency. By
packets/second, further establishing its superiority. This
leveraging real-time environmental feedback and cross-
improvement can be attributed to the protocol's adaptive
layer optimization, CLO-HARQ dynamically adjusts
redundancy mechanisms, which maximize packet delivery
retransmissions and error correction to deliver superior
success while minimizing retransmissions, even under
performance under diverse underwater conditions.
unfavorable channel conditions.
Performance evaluation using Stochastic Network
D.Energy Efficiency Calculus (SNC) demonstrates the protocol’s effectiveness in
Energy efficiency, expressed as the number of reducing delays, increasing throughput, and optimizing
packets transmitted per joule, is a vital concern in UAWSNs
energy efficiency while minimizing packet loss probability.
due to the difficulty of recharging underwater sensor nodes.
Compared to traditional protocols like HARQ, FEC, and
CLO-HARQ exhibits significant energy-saving capabilities.
ARQ, CLO-HARQ achieves up to 40\% lower delays and
At 5 dB, it achieves an energy efficiency of 6 packets/joule,
significantly better energy utilization, even in low-SNR
outperforming simulation (5.5), HARQ (5), FEC (4), and
scenarios. Additionally, its adaptability to factors like salinity
ARQ (3). This efficiency remains high even at higher SNR
and temperature ensures robust performance in dynamic
levels, reaching 7 packets/joule at 25 dB. The protocol's
underwater environments.
ability to dynamically adjust transmission power and
redundancy based on real-time SNR levels contributes to its CLO-HARQ’s multi-hop optimization further enhances
energy efficiency, making it well-suited for long-term its efficiency, enabling balanced energy consumption and
underwater monitoring applications. reduced cumulative delays by intelligently selecting relay
nodes based on link quality and residual energy. This makes
E.Packet Loss Probability
the protocol ideal for large-scale applications, including
The CLO-HARQ protocol effectively minimizes
environmental monitoring and underwater surveillance.
packet loss probability, a critical parameter for reliable
communication in UAWSNs. At 5 dB, it achieves a packet
REFERENCES
loss probability of 4\%, significantly lower than ARQ's 12\%
[1] M. K. Tiwari and M. S. Hossain, "A hybrid automatic repeat
and FEC's 8\%. This advantage is maintained as SNR
request (HARQ) approach for underwater wireless sensor networks," IEEE
increases, with CLO-HARQ reducing packet loss to 0.5\% at Transactions on Wireless Communications, vol. 20, no. 5, pp. 3345-3356,
25 dB. The use of incremental redundancy and cross-layer May 2021.
feedback enables the protocol to adapt to adverse channel [2] Duan, Y. Wang, and Y. Zhang, "Energy-efficient routing
protocol for underwater acoustic sensor networks with HARQ," Ad Hoc
conditions, ensuring dependable packet delivery even in
Networks, vol. 116, p. 102524, 2021.
challenging underwater environments
[3] J. Zhang and S. Zhou, "Design of a hybrid ARQ protocol for
F.Comparative Advantages underwater acoustic communication," IEEE Transactions on Oceanic
Engineering, vol. 47, no. 1, pp. 278-289, 2022.
CLO-HARQ demonstrates superior performance [4] L. Ting and J. Wu, "An adaptive HARQ protocol for underwater
across all metrics due to its integration of: Environmental sensor networks," Sensors, vol. 21, no. 4, p. 1354, 2021.
Awareness: Real-time adaptation to factors such as water [5] Xiong, Y. Zhai, and Y. Wu, "A review on hybrid automatic repeat
request for underwater acoustic networks," Journal of Marine Science and
salinity and temperature enhances its reliability and
Engineering, vol. 9, no. 8, p. 851, 2021.
efficiency in dynamic underwater conditions. Cross-Layer
[6] Y. Zhao and Y. Chen, "Performance analysis of underwater
Optimization: Information sharing between physical and acoustic networks with HARQ," Marine Technology Society Journal, vol.
network layers ensures optimal retransmission strategies and 56, no. 2, pp. 12-22, 2022.
energy utilization. Stochastic Traffic Modeling: The use of [7] Ali and R. Khan, "Energy-efficient adaptive HARQ in
underwater wireless sensor networks," IEEE Access, vol. 9, pp. 46958-
SNC allows accurate prediction of performance under
46970, 2021.
varying traffic conditions, providing robust results for both
[8] Zhang, Y. Zhang, and H. Wang, "Stochastic network calculus for
single-hop and multi-hop scenarios. HARQ in underwater networks," Journal of Communications and Networks,
vol. 23, no. 5, pp. 470-478, 2021.
The results establish CLO-HARQ as a sustainable
[9] P. Kumar and M. Al-Khalidi, "Performance analysis of hybrid
solution for UAWSNs, particularly in applications such as ARQ protocols in underwater acoustic sensor networks," International
environmental monitoring, resource exploration, and Journal of Communication Systems, vol. 33, no. 15, e4450, 2020.
underwater surveillance. Its ability to balance energy [10] Bai and S. Zhang, "The performance of the HARQ scheme in
underwater acoustic communications," Journal of Underwater Acoustics,
efficiency with reliability makes it ideal for energy-
vol. 3, no. 2, pp. 139-150, 2021.
Authorized licensed use limited to: INSTITUTE OF ACOUSTICS CAS. Downloaded on May 06,2026 at 08:24:35 UTC from IEEE Xplore. Restrictions apply.


[11] Huang, H. Liu, and Y. Chen, "Adaptive modulation and coding [22] A. Rashid and N. Rani, "Enhancing reliability in underwater
for HARQ in underwater acoustic communication," Ocean Engineering, vol. communication using HARQ," Applied Sciences, vol. 12, no. 3, p. 1536,
242, p. 110164, 2021. 2022.
[12] A.D. Sari and A. Miskon, "Reliability analysis of underwater [23] C. Zhu and Y. Zhao, "A survey of error control protocols for
acoustic communication networks with HARQ," Sensors, vol. 21, no. 5, p. underwater wireless sensor networks," ACM Transactions on Sensor
1791, 2021. Networks, vol. 18, no. 2, pp. 1-34, 2022.
[13] S. Feng and Y. Wu, "A robust HARQ protocol for underwater [24] L. Yuan and X. Feng, "Design of an efficient HARQ protocol for
wireless sensor networks," Wireless Networks, vol. 27, no. 6, pp. 3425-3437, underwater acoustic communications," Journal of the Acoustical Society of
2021. America, vol. 149, no. 4, p. 2390, 2021.
[14] Xiao and Z. Wang, "Cross-layer design for energy-efficient [25] X. Chen, Y. Zhao, and Y. Lu, "An energy-efficient and reliable
HARQ in underwater acoustic networks," IEEE Transactions on Mobile HARQ protocol for underwater acoustic networks," Applied Acoustics, vol.
Computing, vol. 20, no. 7, pp. 2105-2118, 2021. 186, p. 108348, 2022.
[15] Y. Jiang, J. Xu, and Q. Zhang, "Stochastic network calculus for [26] S. Han, J. Lee, and T. Kim, "Energy-efficient HARQ with cross-
performance evaluation of HARQ in underwater sensor networks," layer optimization for underwater acoustic networks," IEEE Internet of
Computer Networks, vol. 194, p. 108187, 2021. Things Journal, vol. 9, no. 4, pp. 3121-3132, Apr. 2023.
[16] A.Kumar and R. Singh, "A cross-layer approach for adaptive [27] X. Zhang and H. Zhang, "Performance analysis of multi-hop
HARQ in underwater acoustic sensor networks," Journal of Ocean underwater networks using HARQ," IEEE Transactions on
Technology, vol. 17, no. 1, pp. 67-80, 2022. Communications, vol. 71, no. 8, pp. 5875-5885, Aug. 2023.
[17] J. Zhang and Y. Li, "Evaluation of HARQ performance in [28] Y. Liu, W. Zhou, and J. Li, "Adaptive error control mechanisms
underwater communication systems," Journal of Marine Science and for stochastic traffic in UASNs," IEEE Access, vol. 11, pp. 12745-12756,
Engineering, vol. 8, no. 10, p. 767, 2020. 2023.
[18] X. Li, Y. Zhang, and Y. Wu, "Energy-efficient transmission [29] R. Chen and M. Wu, "HARQ-aided cooperative relaying in
strategies for HARQ in underwater networks," IEEE Access, vol. 10, pp. underwater acoustic sensor networks," IEEE Transactions on Wireless
13729-13741, 2022. Communications, vol. 22, no. 5, pp. 3195-3207, May 2023.
[19] W. Gao and Y. Wang, "A novel HARQ scheme for underwater [30] J. Hu, Y. Zhao, and Z. Wang, "Cross-layer resource allocation for
sensor networks," Ad Hoc Networks, vol. 114, p. 102467, 2021. underwater acoustic networks," Ad Hoc Networks, vol. 145, p. 103495,
[20] Song, D. Liu, and Y. Wang, "Performance evaluation of HARQ 2023.
protocols in underwater acoustic networks," Marine Pollution Bulletin, vol.
169, p. 112554, 2021.
[21] P. Kumar and R. Sharma, "A survey on hybrid ARQ schemes in
underwater networks," Wireless Communications and Mobile Computing,
vol. 2021, pp. 1-16, 2021.
Authorized licensed use limited to: INSTITUTE OF ACOUSTICS CAS. Downloaded on May 06,2026 at 08:24:35 UTC from IEEE Xplore. Restrictions apply.


