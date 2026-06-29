SN Computer Science (2021) 2:108
https://doi.org/10.1007/s42979-021-00470-6
ORIGINAL RESEARCH
Analytical Modelling and Performance Enhancement of Cooperative
HARQ Scheme for Underwater Acoustic Sensor Networks
Veerapu Goutham1 · V. P. Harigovindan1
Received: 3 December 2020 / Accepted: 13 January 2021 / Published online: 20 February 2021
© The Author(s), under exclusive licence to Springer Nature Singapore Pte Ltd. part of Springer Nature 2021
Abstract
Cooperative relaying technique has been adopted as an efficient method for underwater acoustic sensor networks to extend
network coverage and enhance spatial diversity. Recently, cooperative relaying with HARQ (C-HARQ) schemes are proposed
for underwater acoustic sensor networks to improve energy efficiency and reliability. In this work, we present an analytical
model for calculating the energy efficiency of the C-HARQ protocol in underwater acoustic sensor networks. We derive
mathematical expressions from the analytical model to calculate the end-to-end energy efficiency by considering the impacts
of frequency-dependent path loss, ambient noise, and acoustic spreading. Results show that the C-HARQ scheme outper-
forms conventional cooperative communication and direct communication schemes when the distance between transceiving
nodes is beyond the threshold distance. In addition, we apply the particle swarm optimization algorithm to optimize the
energy efficiency by choosing the optimal modulation level and optimal packet size in accordance with the distance between
transceiving nodes. Analytical results are corroborated with the extensive ns3 simulations.
Keywords Cooperative communications · Absorbing Markov chain · Energy efficiency
Introduction
UASNs have unique channel characteristics, including the
frequency-dependent path loss, time-varying multipath fad-
Underwater acoustic sensor networks (UASNs) have recently ing, Doppler spread, underwater noises, increased propa-
received significant recognition from both industry, and gation delays, and limited transmission bandwidth [7, 17,
research communities for its diverse applications, such as 24]. The path loss in UASNs depends on both the transmis-
ocean exploration, underwater multimedia, aided navigation, sion distance and operating signal frequency. In addition,
military surveillance, environmental monitoring, and much the spread of acoustic waves changes with the variations
more [1, 24]. Unlike in terrestrial wireless sensor networks, in the depth of the sensor nodes. All of these factors have a
significant effect on reliability and energy efficiency (EE).
As a result, cooperative communication is a commonly
This work is supported by Science Engineering Research Board,
used method in UASNs to improve the reliability and EE by
Department of Science and Technology, Government of India,
under Mathematical Research Impact Centric Support scheme exploiting space and time diversity links using multiple relay
with file number MTR/2019/001228. nodes [2, 4, 15]. Cooperative communications were initially
introduced in wireless sensor networks and later adapted to
This article is part of the topical collection “Cyber Security and
UASNs [3, 4, 15]. This scheme uses one or more relay nodes
Privacy in Communication Networks” guest edited by Rajiv Misra,
R K Shyamsunder, Alexiei Dingli, Natalie Denk, Omer Rana, for user cooperation at the instance of packet retransmission.
Alexander Pfeiffer, Ashok Patel and Nishtha Kesswani”. Generally, two different types of cooperative commu-
nication schemes are proposed for UASNs, namely under-
*
Veerapu Goutham
water amplify-and-forward, and underwater decode-and-
gouthamveerapu@gmail.com
forward [3, 5, 23]. Relay nodes transmit the data packets
V. P. Harigovindan
with a particular additional gain without the information
hari@nitpy.ac.in
being decoded in the first approach. Whereas in the second
1 Department of Electronics and Communication Engineering, approach, the relay nodes decode the data packet and then
National Institute of Technology Puducherry, Karaikal, transmits the decoded data packet to the destination node
Puducherry 609609, India
SN Computer Science
Vol.:(0123456789)

108 Page 2 of 7 SN Computer Science (2021) 2:108
whenever a negative acknowledgement is received from the Physical Layer Modeling
destination node. The demand for highly reliable and energy-
efficient protocols in UASNs has increased rapidly. In [12, The signal-to-noise ratio (SNR) of a channel link in UASNs
14], the cooperative communication scheme be combined mainly depends on source transmit power level (SL), trans-
with ARQ referred to as cooperative ARQ was proposed for mission power loss (TL), directivity index (DI) and ambi-
UASNs. In cooperative ARQ scheme, the destination node ent noise level (NL). The transmitted source signal strength
uses a feedback channel for the packet retransmissions. In related to the reference intensity is given by [6],
addition, the idea of combining cooperative communication
P
with the HARQ (C-HARQ) protocol further improves the SL = t ,
I ×area (1)
reliability and EE of UASNs [11, 21]. In this scheme, the ref
d me is tt ti hn eat ii no cn o n ro red ce t r pe aq ru t e os ft s t ha e c do ao tp ae pra at ci kv ee t r ie nla sty e an do d oe f t to h ere wtr ha on ls e- where P t is power of transmitted signal, I ref = 𝜌q ×2 c is refer-
ence intensity. TL comprises of spreading and absorption
packet, significantly improving the throughput performance.
losses, which varies with the geometry of acoustic signals
In C-HARQ, both forward and backward error correction
propagation and signal frequency, respectively. TL between
techniques are used along with the cooperative communica-
any two nodes can be calculated by [6],
tion scheme to improve EE and reliability. After investigat-
ing the performance of different HARQ schemes in coop- TL=r𝜅 a(f)r,
(2)
erative communications, the authors of [16] suggested that
Reed–Solomon codes with selective repeat ARQ techniques where 𝜅 is the spreading factor, r is the distance between
are mostly preferred for low complexity and low latency two nodes, a(f) is the absorption coefficient. 𝜅 is 1 for shal-
applications. Recently, the authors of [22] have proposed a low water and 2 for deep water scenario [20]. NL comprises
hybrid scheme that combines network coding with HARQ to turbulence, shipping, waves and thermal noise. The overall
achieve better data transfer performance in UASNs. Authors NL also depends on the transmitted frequency of acoustic
of [18] have proposed energy-efficient cooperative opportun- signals (f). It is given by [6]
istic routing protocol for UASNs. Here, the source node uses
105
the underwater devices’ depth information and their residual NL= f1.8. (3)
energy of the relay nodes as constraints to determine the
route to the destination node.
In deep water, the geometry of acoustic signals exhibits
Differently, we present an analytical model for calculating
spherical spreading, and cylindrical spreading in case of
the packet error rate (PER) and EE of C-HARQ scheme for
shallow water [6]. The SNR of an underwater link in shal-
UASNs. EE is one of the key parameters considered for the
low water is given by
design of UASN transmission protocols. Major contributions
of this article as follows: P t×f1.8
SNR= ,
(4)
2𝜋H×105×I ×r𝜅 ×a(f)r
ref
– We develop an analytical model to evaluate the PER and
EE of C-HARQ based UASNs. This model considers where H is the depth in m and r is distance between trans-
the specific underwater channel characteristics, namely ceiving nodes. The SNR of an channel link in deep water
frequency-dependent path loss, acoustic spreading, and is given by
multipath fading effects.
P ×f1.8
– We derive mathematical equations for end-to-end PER SNR= t . (5)
4𝜋×105×I ×r𝜅 ×a(f)r
and EE using this model. ref
– Results show that the C-HARQ scheme can outperforms
the direct communication (with or without HARQ) and
cooperative communication schemes in terms of EE PER Calculation
when the distance between transceiving nodes is beyond
the threshold distance.
In this work, we have considered the power consumption
– Further, we apply particle swarm optimization algorithm
characteristics of WHOI micro-modem, which has the capa-
to maximize the EE by choosing the optimal packet size
bility to perform coherent phase shift keying with a carrier
and modulation level.
frequency of 25 KHz. First, we have modeled the under-
water channel as a Rayleigh fading channel due to multi-
path propagation of signals [8] and the gains provided by
multiple paths are assumed to be statistically i.i.d during
SN Computer Science

SN Computer Science (2021) 2:108 Page 3 of 7 108
packet transmission. Second, we have considered M-PSK End‑to‑End PER Analysis
technique with modulation level m=log 2M bits/symbol,
assuming that the output signals from the sensor nodes are According to the C-HARQ protocol, we present an absorbing
in the digital form. The closed-form approximation to calcu- Markov chain model to calculate the overall probability of
late the average symbol error rate (SER) of a Rayleigh fading packet success and error rate as shown in Fig. 1. Here, Source
channel link is given by [9], is the state, which represents source node is ready to transmit
the data packet, r success and r failure are the states which repre-
sin2 𝜋 SNR sents the successful and unsuccessful decoding of the data
SER∗ ≈ ⎡ ⎢1−� � � � �1+sin� 2M � M𝜋 SNR⎤ ⎥. (6) p sta ac tek se t w b hy i cth he r ere pl ra ey s en no td s e th r e, d susu cc cc ees ss s a fn ud l a d nf dai l uur ne sa ur ce c t eh se s fa ub ls do erb coin dg -
⎢ � � � ⎥ ing of the data packet by the destination node d. Therefore, the
⎢ ⎥
The PER⎣ of a link is given by, PER⎦∗ =1−(1−SER∗) mX , transition probability matrix of absorbing Markov chain can
0 I
where X is the size of a data packet consists of message bits be written as 2,2 , where Q is the transition probability
[Q R ]
(1−SER∗) mX
and header bits. gives the probability of suc- matrix between transient states, R is the transition probability
X
cessful reception of m symbols at the receiving node. In the matrix from transient to absorbing states, I 2,2 is identity matrix
HARQ scheme, the receiver can check and correct few errors representing the transition probabilities among absorbing
present in the data packet with the help of redundant check states and 0 is all zero matrix representing the transition prob-
bits generated using R–S codes. Here, the data packet con- abilities from absorbing state to transient states. Here onwards,
sists of message bits, header bits and check bits (Cb). The {A→B} represents the transition from state A to state B. The
decoded average symbol error rate between ith transmitting probability of transition from {A→B} is denoted by
node and jth receiving node can be given by [19] P{A→B} .
2K−1 Let define PER sd , PER sr , PER rd are the PER of the links
1 2K −1
SER ≈ k from s-to-d, s-to-r and r-to-d. A complete analysis to calcu-
ij 2K −1 k∑=t+1 ( r ) (7) late the PER sd , PER sr , PER rd for UASNs has discussed in
SER∗k 1−SER ∗ 2K−1−k , Sect. 2.1. Now we see some possible transitions among tran-
ij ij sient states: {Source→ d success} is the successful packet recep-
( )
where size of a data packet X =2K −1 and t is the error cor- {ti So on u a rt c t ehe → de dst si un cca et si so }n i sn o gd ive e. nT bh ye p [1ro 3b ]ability of transition from
recting capability of R–S codes. The decoded PER of a link
X+Cb X+Cb
is given by, PER=1−(1−SER) m , where (1−SER) m P{Source→ d }=1−PER
success sd (8)
X+Cb
gives the probability of successful reception of symbols
at the receiver node. m {Source→ r success} is the successful packet recep-
tion at the relay node. The probability of transition from
{Source→ r success} is given by [13]
Analytical Modelling
We consider a simple UASN model consisting of a source
(s), destination (d) and relay (r) nodes. The description of
C-HARQ is as follows: initially, the source node broadcasts
the data packets along with the addresses of destination and
relay nodes. Due to the broadcasting, relay node is also able
to receive the data packets along with the destination node.
If the node d is decoded the data packet correctly, it sends a
positive acknowledgment (ACK) to the node s. Otherwise,
it sends a negative ACK to the node r. Data packet errors
occur due to the signal degradation caused by multi-path sig-
nal propagation, frequency-dependent path loss, and ambi-
ent noises such as turbulence, shipping, waves and thermal
noises. If the node r decoded the data packet correctly, it
transmits the data packet to the node d, else it sends a nega-
tive ACK back to the node d. Even if the node d is not able to
decode the packet precisely, then it will drop the data packet. Fig. 1 Absorbing Markov chain for C-HARQ
SN Computer Science

108 Page 4 of 7 SN Computer Science (2021) 2:108
P{Source→ r }=PER (1−PER ), packet transmission over s-to-d via relay node channel links.
success sd sr (9)
Accordingly, the total energy consumed for transmitting one
{Source→ r failure} is the unsuccessful packet recep- data packet in C-HARQ is written as
tion at the relay node. The probability of transition from E C-HARQ =P C-HARQ× RX. Energy efficiency can be defined
{Source→ r failure} is given by [13] numbb
as the ratio of total er of successfully transmitted mes-
P{Source→ r }=PER PER sage bits to the energy consumed. Mathematically, the EE
failure sd sr (10)
of cooperative communication is given by
, {r success → d success} is the successful packet reception at X (1−PER )
p C-HARQ
the destination node. The probability of transition from 𝜂 = ,
{r success → d success} is given by [13], C-HARQ E C-HARQ (16)
P{r success → d success}=1 −PER rd, (11) where X p is the payload of the data packet. The energy effi-
ciency of existing direct and cooperative communication
{r success → d failure} is the unsuccessful packet transmission schemes can be calculated from the results by [10].
to the destination node. The probability of transition from
{r success → d failure} is given by [13],
P{r → d }=PER . Analytical Results
success failure rd (12)
The probability of transition from {r failure → d failure} is given In this section, we present numerical results for energy effi-
by [13] ciency analysis using MATLAB® R2018b and validate them
P{r → d }=1. by ns-3 simulations. We assume that the distance between
failure failure (13)
r and d ( r rd ) channel links is r sr =0.5×r sd , where r sr and
Before computing the probability vector of absorbing states, r sd are the distances between the s and r and s and d chan-
we define the probability vector with which the Markov nel links. The parameters used for numerical and simulation
model begins. We assume Markov chain starts with the analyses are shown in Table 1 and these values took from
Source state. Therefore, the probability vector with which WHOI practical underwater acoustic modem [24]. Figure 2
a=[10000]
the Markov model begins can be written as . shows the variation of energy efficiency with respect to the
The absorbing probability vector of the Markov chain is distance between the s and d links. In particular, the energy
given by b=a(I−Q)−1R , where b is b=[b(1)b(2)] , where efficiencies of the C-HARQ, HARQ-DC, cooperative com-
b(1) is the packet success rate and b(2) is the PER. munication (CC) and direct communication (DC) schemes
decrease with the increase in the distances between the s and
d links. The reason for this is the decrease in SNRs with the
Energy Consumption and EE Analysis
increase in distance of the respective channel links. Another
important observation from Fig. 2 is that, because of the
Based on the absorbing Markov model, the PER in C-HARQ
additional energy consumed by the relay nodes in C-HARQ,
is given by
the C-HARQ scheme performs less than the HARQ-DC, CC
PER =PER ×PER and DC schemes for smaller distances between the s and d
C-HARQ sd sr
+ PER ×(1−PER )×PER . (14) links. Whereas for higher distances between the s and d links
sd sr rd
are concerned, the C-HARQ scheme significantly improves
( )
Equation (14) represents the unsuccessful packet transmis- the energy efficiency compared to the other existing scheme.
sion over s-to-d link or s-to-d via relay node. The total power Here, the SNR performance of the C-HARQ scheme is
consumed in C-HARQ is statistically given by improved significantly compared to the other schemes due
to the packet transmission over multiple spatially diverse
P =(P +2P)(1−PER )
C-HARQ t r sd links. It clearly shows the presence of a threshold distance
+(P t+2P r) PER sdPER sr (15) separation between the transceiving nodes, which is used as
+(2P +3P()(PER (1−P)ER ). a key factor in determining the optimal transmission regime
t r sd sr
with respect to the distance between the transceiving nodes.
The first term in Eq. (15) represents the power consumption Figure 2 also shows the variation of EE with respect
for successful packet transmission over s-to-d channel link, to the change in the position of the relay node. Here, the
the second term represents power consumption for the fail- relay node position is changed using r sr =0.1r sd(q=0.1)
ure of packet transmission over s-to-d and s-to-r channel (node R is placed near to the node S compared to D),
links, the third term represents power consumption for the r sr =0.5r sd(q=0.5) (node R is placed exactly at the
failure of packet transmission over s-to-d path and successful center in between S and D nodes) and r sr =0.9r sd(q=0.9)
SN Computer Science

SN Computer Science (2021) 2:108 Page 5 of 7 108
Table 1 Parameters used for
System parameter Value
performance analysis
Transmit power consumption (P tx) 48 W
Receive power consumption (P rx) 3 W
Bit rate 5000 b/s
L
Payload size p 41 bits
Packet size L 57 bits
Frequency f 6 KHz
𝜅 (Spreading factor) 1.5 for practical spreading
Wind speed (w) 6.67 m/s (average wind speed)
Shipping activity (s) 0.5 (average value)
mobility model ns3::ConstantPositionMobilityModel
Energy model ns3::AcousticModemEnergyModelHelper
Propagation model ns3::UanPropModelThorp
Noise model ns3::UanNoiseModelDefault
PER model ns3::UanPhyPerCommonModes
Fig. 2 Energy efficiency vs. the distance between source and destina- Fig. 3 Energy efficiency gain vs. the distance between source and
destination nodes (q is varied to change the position of relay node)
tion nodes (q is varied to change the position of relay node)
Energy Efficiency Optimization Using PSO
(node R is placed near to the node D compared to S). It is
observed from Fig. 2 that the EE of C-HARQ scheme is Data packet size and modulation level are essential con-
performing better, when the relay node exists exactly in straints in UASNs to improve energy efficiency performance.
the center in between the source and destination nodes. It is noted that the relatively large packets are easily prone
Efficiency gain is a good measure to calculate the improve- to packet inaccuracies compared to the small-sized packets.
ment achieved in the energy efficiency of different schemes At the same time, the small-sized packets are more resilient
(CC, HARQ-DC, C-HARQ) compared to DC. Efficiency to packet errors. In particular, sending small-sized packets
gain is defined as the ratio of energy efficiency achieved could be a better way to avoid packet inaccuracies. On the
by a specific scheme to the energy efficiency achieved by other hand, small packets result in more number of frames
the DC. Figure 3 shows the variation of energy efficiency after the packet fragmentation, which increases the packet
gain with respect to the distance between the s and d links. overhead and energy consumption. Similarly, scheme with
It is observed from Fig. 3 that the energy efficiency gain high modulation levels is more prone to receive errors but
is significantly improved for C-HARQ scheme compared result in an increase in the overall energy consumption.
to the other existing schemes. Whereas schemes with low modulation levels are less prone
SN Computer Science

108 Page 6 of 7 SN Computer Science (2021) 2:108
Table 2 Optimization results using PSO improves energy efficiency of C-HARQ scheme. The paper
concludes that C-HARQ with an optimization algorithm
Distance in m Energy efficiency Kbits/J Modula- Packet
tion level size significantly improves the energy efficiency of UASNs.
(Kb)
C-HARQ Optimized
C-HARQ Compliance with Ethical Standards
100 120.5 422.9 5 293
Competing interests The authors would like to state that the content
250 120.5 302.3 4 215
of this paper has not been submitted to any other journal. Further, we
500 118.8 205.8 3 151 would like to state that we do not have any conflicting interest related
750 91.1 146.5 2 112 to the journal policies.
1000 63.8 106 2 91
to receive errors, but may result in an inefficient use of the
References
channel. As a result, we apply the PSO technique to optimize
energy efficiency by jointly optimizing the packet size and
1. Akyildiz IF, Pompili D, Melodia T. Underwater acoustic sensor
modulation level over transmission distances. Here, packet
networks: research challenges. Ad Hoc Netw. 2005;3(3):257–
size and modulation level vary between [10 and 1024 Kb] 79. https: //doi.org/10.1016/j.adhoc. 2005.01.004.
and [2 and 8], respectively. Using the expressions of the 2. Bletsas A, Shin H, Win MZ. Cooperative communications
energy efficiency 𝜂 C-HARQ , the optimization problem can be with outage-optimal opportunistic relaying. IEEE Trans
Wirel Commun. 2007;6(9):3450–60. https: //doi.org/10.1109/
framed as
TWC.2007.060200 50.
3. Cao R, Qu F, Yang L. Asynchronous amplify-and-forward relay
maximize 𝜂
X,P C-HARQ (17a) communications for underwater acoustic networks. IET Com-
tx
mun. 2016;10(6):677–84.
4. Carbonelli C, Mitra U. Cooperative multihop communication for
SubjecttoX∈[10,1024Kb],
(17b) underwater acoustic networks. In: Proceedings of the 1st ACM
International Workshop on Underwater Networks, WUWNet
’06, pp. 97–100. ACM, New York, NY, USA 2006. https: //doi.
m∈[2,8].
(17c) org/10.1145/116103 9.116105 9.
5. Celik A, Saeed N, Al-Naffouri TY, Alouini M. Modeling and
performance analysis of multihop underwater optical wireless
Table 2 shows the optimum energy efficiency of C-HARQ sensor networks. In: 2018 IEEE Wireless Communications and
scheme along with respective optimal modulation level and Networking Conference (WCNC), 2018;pp. 1–6. https: //doi.
org/10.1109/WCNC.2018.837738 8.
packet size. C-HARQ scheme with joint optimal modulation
6. Domingo MC, Prior R. Energy analysis of routing proto-
level and packet size significantly improves the energy effi- cols for underwater wireless sensor networks. Comput Com-
ciency, as shown in Table 2. It is evident that PSO optimally mun. 2008;31(6):1227–388. https: //doi.org/10.1016/j.comco
allocates the modulation level from 2 to 8 and packet size m.2007.11.005.
( 𝜒 ) from 10 to 1024 Kb to optimize the energy efficiency. 7. Dou J, Zhang G, Guo Z, Cao J. PAS: probability and sub-opti-
mal distance-based lifetime prolonging strategy for underwa-
ter acoustic sensor networks. Wirel Commun Mob Comput.
2008;8(8):1061–73. https: //doi.org/10.1002/wcm.v8:8.
Conclusion 8. Geethu KS, Babu AV. A hybrid ARQ scheme combining erasure
codes and selective retransmissions for reliable data transfer in
underwater acoustic sensor networks. EURASIP J Wirel Com-
In this paper, we have presented an analytical model for mun Netw. 2017;2017(1):32. https: //doi.org/10.1186/s1363
computing the energy efficiency of C-HARQ scheme in 8-017-0823-5.
UASNs. The results confirm the presence of a threshold 9. Goldsmith A. Wireless communications. Cambridge: Cam-
bridge University Press; 2005.
distance separation between the transceiving nodes, which
10. Goutham V, Harigovindan VP. Improving energy efficiency
is used as a key factor in determining the optimal trans- of hybrid ARQ scheme for cooperative communication in
mission regime over transmission distance.The results UASNs Using PSO. In: Intelligent Communication. Control
also show that C-HARQ can perform much better than and Devices. Singapore: Springer Singapore; 2020; p. 609–17.
11. Goutham V, Harigovindan VP. Modeling and analysis of hybrid
the other existing schemes in terms of the energy effi-
ARQ scheme for incremental cooperative communication in
ciency, when the distance between the transceiving nodes underwater acoustic sensor networks. Iran J Sci Technol Trans
is greater than the threshold distance. We also framed an Electric Eng. 2020. https: //doi.org/10.1007/s40998 -020-00348
optimization problem to optimize C-HARQ’s energy effi- -y.
12. Jamshidi A. Efficient cooperative ARQ protocols based on relay
ciency by jointly optimizing the packet size and the modu-
selection in underwater acoustic communication sensor networks.
lation level. The results show that this algorithm further
SN Computer Science

SN Computer Science (2021) 2:108 Page 7 of 7 108
Wirel Netw. 2019;25:4815–27. https: //doi.org/10.1007/s1127 20. Stojanovic M. On the relationship between capacity and distance
6-018-1773-5. in an underwater acoustic communication channel. ACM SIG-
13. Le L, Hossain E. An analytical model for ARQ cooperative diver- MOBILE Mob Comput Commun Rev. 2007;11(4):34. https: //doi.
sity in multi-hop wireless networks. IEEE Trans Wirel Commun. org/10.1145/134736 4.134737 3.
2008;7(5):1786–91. https: //doi.org/10.1109/TWC.2008.060798 . 21. Tan DD, Kim DS. Cooperative transmission scheme for multi-
14. Lee JW, Jin Yong Cheon, Cho H. A cooperative ARQ scheme hop underwater acoustic sensor networks. Int J Commun Netw
in underwater acoustic sensor networks. In: OCEANS’10 IEEE Distrib Syst. 2015;14(1):1–18. https: //doi.org/10.1504/IJCND
SYDNEY, 2010; pp. 1–5. https: //doi.org/10.1109/OCEAN S.2015.065998 .
SSYD.2010.560382 1. 22. Wang H, Wang S, Zhang E, Zou J. A network coding based hybrid
15. Liang X, Chen M, Balasingham I, Leung VC. Cooperative ARQ protocol for underwater acoustic sensor networks. Sensors.
communications with relay selection for wireless networks: 2016. https: //doi.org/10.3390/s16091 444.
design issues and applications. Wirel Commun Mob Comput. 23. Wang P, Zhang L, Li VOK. Asynchronous cooperative trans-
2013;13(8):745–59. https: //doi.org/10.1002/wcm.1138. mission for three-dimensional underwater acoustic networks.
16. Ngo HA, Hanzo L. Hybrid automatic-repeat-reQuest sys- IET Commun. 2013;7(4):286–94. https: //doi.org/10.1049/
tems for cooperative wireless communications. IEEE Com- iet-com.2012.0314.
mun Surveys Tutor. 2014;16(1):25–45. https: //doi.org/10.1109/ 24. Yildiz HU, Gungor VC, Tavli B. Packet size optimization for life-
SURV.2013.071913 .00073. time maximization in underwater acoustic sensor networks. IEEE
17. Patil A, Stojanovic M. A node discovery protocol for ad hoc Trans Ind Inf. 2018. https: //doi.org/10.1109/TII.2018.284183 0.
underwater acoustic networks. Wirel Commun Mob Comput.
2013;13(3):277–95. https: //doi.org/10.1002/wcm.2206. Publisher’s Note Springer Nature remains neutral with regard to
18. Rahman MA, Lee Y, Koo I. EECOR: an energy-efficient coopera- jurisdictional claims in published maps and institutional affiliations.
tive opportunistic routing protocol for underwater acoustic sensor
networks. IEEE Access. 2017;5:14119–32.
19. Sklar B. Digital communications: fundamentals and applications.
Upper Saddle River: Prentice-Hall Inc; 1988.
SN Computer Science

