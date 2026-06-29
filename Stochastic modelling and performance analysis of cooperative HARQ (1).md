Sådhanå (2021) 46:12 (cid:2)Indian Academyof Sciences
https://doi.org/10.1007/s12046-020-01534-8
Sadhana(0123456789().,-volV)FT3](0123647589().,-volV)
Stochastic modelling and performance analysis of cooperative HARQ
in multi-cluster underwater acoustic sensor networks
VEERAPU GOUTHAM* and V P HARIGOVINDAN
Department of Electronics and Communication Engineering, National Institute of Technology Puducherry,
Karaikal 609609, India
e-mail: gouthamveerapu@gmail.com
MS received 6 July 2020; revised 3 November 2020; accepted 6 November 2020
Abstract. Cooperative hybrid automatic repeat request (C-HARQ) scheme based on multi-hop relaying has
been adopted as an efficient strategy in underwater acoustic sensor networks (UASNs) to extend network
coverage and to enhance the performance by utilizing spatial diversity gain. In this letter, we develop a
stochastic model for multi-cluster transmissions in UASNs, considering the underwater-specific characteristics
such as frequency-dependent signal attenuation, acoustic spreading, multi-path fading and underwater noises.
From this generalized stochastic model, we derive accurate analytical expressions to analyse the end-to-end
packet error rate (PER) and energy efficiency. Analytical results demonstrate that the C-HARQ scheme can
significantly improve the performance of UASNs, especially with the increase in number of relay nodes.
Analytical results are corroborated with extensive simulation studies.
Keywords. Cooperative HARQ; multi-hop relaying; underwater acoustic sensor networks.
1. Introduction cooperative ARQ (C-ARQ), proposed for UASNs. In
C-ARQ, the destination node uses a feedback channel for
Underwater acoustic sensor networks (UASNs) have the packet retransmissions. In addition, the idea of com-
recentlyreceivedsignificantrecognitionfrombothindustry biningCCwithhybridautomaticrepeatrequest(C-HARQ)
and researchers due to its capability to support diverse protocol further improves the reliability and energy effi-
applications, such as ocean exploration, military surveil- ciency (EE) of UASNs [9, 10]. In C-HARQ, both forward
lance, environmental monitoring and much more [1, 2]. and backward error correction techniques are used in con-
UASNs have unique channel characteristics, namely fre- junctionwiththeCCschemetoimproveEEandreliability.
quency-dependentpathloss,time-varyingmulti-pathfading As an extension to the afore-mentioned research works on
and limited transmission bandwidth [1]. In addition, the multi-hop UASNs, we present a stochastic model for the
propagation characteristics of acoustic waves change with calculation of packet error rate (PER) and EE of the
the depth of the sensor nodes. All these factors have a C-HARQ-based multi-cluster UASNs.
significant impact on network connectivity and coverage. Major contributions of this letter are as follows: 1. We
As a result, transmission based on multi-hop relaying is develop a stochastic model for C-HARQ-based multi-clus-
preferred in UASNs to build a network with improved ter UASNs by considering the underwater channel charac-
coverage and connectivity [3]. Initially, the integration of teristics, namely frequency-dependent path loss, acoustic
cluster-based communication protocols using cooperative spreading and multi-path fading effects. 2. From this gen-
communication (CC) was proposed for ad-hoc networks eralized stochastic model, we derive accurate analytical
[4]. Subsequently, Lee and Hossain [5] presented a math- expressionsforPERandEE.3.Theresultsshowthatthere
ematical model for computing the end-to-end throughput existsathresholddistancebetweenthetransceivingnodesin
and delay for cluster-based CC in multi-hop wireless net- both shallow and deep water scenarios, which acts as a
works. In general, CC uses multiple relay nodes for user deciding factor for selection of the optimal transmission
cooperation in the case of packet retransmissions [6]. scheme.Itisalsoobservedfromtheresultsthatanincrease
Jamshidi [7] and Chen et al [8] combined the CC inthenumberofrelaynodesimprovesthePERperformance
schemewithautomaticrepeatrequest(ARQ),referredtoas ofC-HARQ in both shallow and deep water scenarios.
*For correspondence


![page_1_full](https://doc2markdown.com/images/20260608/74bcfaaf-d1d6-4f4d-8572-9aaa6c60d49e/page_1/page_1_full.png)


12 Page 2 of 5 Sådhanå (2021) 46:12
2. Physical layer modelling of UASNs 1 XX k(cid:3) X(cid:4)
SER(cid:4) ðSER(cid:3)Þkð1(cid:5)SER(cid:3)ÞX(cid:5)k; ð3Þ
X r
In this section, we present mathematical model of the k¼tþ1
underwater physical layer. The signal-to-noise ratio (SNR)
wherethesizeofdatapacketX ¼2K (cid:5)1andtistheerror-
of an underwater link depends on source level (SL),
correctingcapabilityofR-Scodes.ThedecodedPERofthe
transmission loss (TL), directivity index (DI) and ambient
XþCb
noise level (NL) [1, 2, 10]. Here, DI is considered to be 0 link is given by PER¼1(cid:5)ð1(cid:5)SERÞ m :
dB for an omnidirectional antenna. The source signal
strength related to the reference intensity is given by SL¼
3. Mathematical modelling of multi-cluster
Iref(cid:2)P at rea; where P t is transmit power, I ref ¼ qq2 c is the refer- transmission
enceintensity,qisthedensityandcisthespeedofacoustic
signalintheunderwatermedium.NLcomprisesturbulence, We consider a multi-cluster UASN model consisting of a
shipping, waves and thermal noises. NL is given by NL¼ source s, destination d and the relay nodes r 1, ..., r i;:::;r r
in each cluster as shown in figure 1. Let us define N as
105: TL consists of spreading and absorption losses. These i
f1:8 the cluster number in the multi-cluster transmission,
losses depend mainly on the geometry of acoustic signal
where i2f1;2;::::;ng, and R is the relay state variable
r
propagation, frequency and transmission distance. TL
that provides information on the status of relay nodes.
between two nodes can be calculated by TL¼dkaðfÞd; Relay nodes consider the binary value of 1 when decod-
where k is the spreading factor, d is the distance between ing a packet successfully, otherwise they consider 0. In
two nodes and a(f) is the absorption coefficient. In deep R , r denotes the decimal number of a vector
r
water, the geometry of acoustic signals exhibits spherical ½r r r (cid:6)(cid:6)(cid:6)r r (cid:7). L indicates the number of transmis-
r r(cid:5)1 r(cid:5)2 2 1 l
spreading. However, in shallow water, the geometry of sion rounds in a single cluster, where l2f1;2;::::;rþ1g.
acoustic signals exhibits cylindrical spreading due to the The maximum number of transmissions in a single cluster
signals being bounded by the floor and surface of the sea. is limited to rþ1 rounds due to the possibility that each
As a result, k is 1 for shallow water and 2 for deep water node will be given a chance of transmission, when other
scenarios. The SNR of an underwater link is given by [2] nodes fail to successfully transmit the data packet. The
description of the C-HARQ is as follows. Initially the
Pf1:8
SNR¼ t ; ð1Þ node s broadcasts the hello packets, whenever it has data
u(cid:2)105I refdkaðfÞd to send. The nodes that receive the hello packets will
provide the depth information along with the acknowl-
where u¼4p for deep water and u¼2pH for shallow
edgement (ACK). Upon receiving the ACK, node s will
water; H is the depth in m. We model the underwater
choose the node d and r number of relay nodes to form
channel as a Rayleigh fading channel due to multi-path
the ðNÞ cluster. Clustering can be done based on depth
signal propagation and also assume statistically i.i.d. i
information, propagation delay and angle of arrival. There
channels. We also consider the M-QAM modulation tech-
are different techniques proposed for clustering in
nique with a modulation level of m¼log M bits/symbol.
2 UASNs, but that is beyond the scope of this work. After
A closed-form approximation for finding the average
clustering, the node s transmits the data packets along
symbol error rate (SER) of a Rayleigh fading channel link
with the destination and relay nodes addresses in the first
is given by
sffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi!
3SNR
SER(cid:3) (cid:4)2ð1(cid:5)2(cid:5) 2m Þ 1(cid:5) : ð2Þ
2ð2m(cid:5)1Þþ3SNR
The PER of a link is given by PER(cid:3) ¼1(cid:5)ð1(cid:5)SER(cid:3)ÞmX ;
where X is the packet size consisting of message bits ðX Þ
b
and header bits ðH Þ. In the HARQ scheme, the receiver
b
can detect and correct a few errors present in the data
packetwiththehelpoftheredundancycheckbitsgenerated
byR-Scodes.Inthisscheme,thedatapacketconsistsofX ,
b
H and check bits (C ). The decoded average SER of the
b b
link is given by [11] Figure 1. Multi-cluster transmission.


Sådhanå (2021) 46:12 Page 3 of 5 12
transmission round L 1. In addition to the node d, the relay PrfðN i;R 0;L 1Þ!ðN i;R r;L 2Þg¼PERi
sd
nodes are also capable of receiving data packets. If the Y ðPERi Þ Y ð1(cid:5)PERi Þ; ð4Þ
node d decodes the data packet accurately, it sends a srk srg
positive ACK to the node s. Otherwise, it sends a negative rk2A1 rg2A2
ACK to the node r 1. If the node r 1 decodes the data where 1(cid:8)N i(cid:8)N n, R 0(cid:8)R r(cid:8)R 2r(cid:5)1, A 1 is the set of relay
packet correctly, then it transmits the data packet to the nodesthatunsuccessfullydecodedthedatapacketandA is
2
node d in the second transmission round L 2. Otherwise, it the set of relay nodes that successfully decoded the data
sends a negative ACK to the node d. As a result, the node packet.Weassumethattherelaynodestransmitdirectlyto
d can approach the remaining relay nodes in the next the d node at the instance of packet retransmission.
transmission rounds. If the node d cannot decode the Accordingly, the probability of transition from
packet, then it will drop the data packet. After the suc- ðN;R ;LÞ!(cid:7) N;R ;L (cid:8) is given by
i r l i r0 lþ1
cessful reception of data packet in Nth cluster, the node d
i
will act as a source node in N iþ1th cluster. The data packet PrfðN i;R r;L lÞ!(cid:7) N i;R r0;L lþ1(cid:8) g¼0; ð5Þ
is sent to the next successor cluster, forming a chain up to
where 1(cid:8)N i(cid:8)N n, R 0(cid:8)R r(cid:8)R 2r(cid:5)1, R 0(cid:8)R (cid:8)R and
the final destination node. r0 2r(cid:5)1
L (cid:8)L (cid:8)L . ðN;R ;LÞ! ðN ;R ;L Þ represents suc-
2 l r i r l iþ1 0 1
cessful packet reception at the destination node through
source or relay nodes in an N cluster. The probability of
i
3.1 End-to-end PER analysis in multi-cluster transitionfromðN i;R 0;L 1Þ!ðN iþ1;R 0;L 1Þthroughsource
node is given by
transmission
For the multi-cluster transmission in UASNs, we develop PrfðN;R ;L Þ!ðN ;R ;L Þg¼1(cid:5)PERi ;
i 0 1 iþ1 0 1 sd
an absorbing Markov chain model to calculate the end-to-
where 1(cid:8)N (cid:8)N . The probability of transition from
end PER. We define the absorbing Markov chain with the i n(cid:5)1
ðN;R ;LÞ!ðN ;R ;L Þthroughrelaynodeisgivenby
sample space given by X¼fðN;R ;LÞg[fsuccessg i r l iþ1 0 1
i r l
[ffailureg; where fsuccessg and ffailureg are the
PrfðN;R ;LÞ!ðN ;R ;L Þg¼1(cid:5)PERi ;
absorbingstatesandðN i;R r;L lÞarethetransientstates.The i r l iþ1 0 1 rgd
success state represents the successful reception of a data
where r 2A , 1(cid:8)N (cid:8)N , R (cid:8)R (cid:8)R and
g 2 i n(cid:5)1 1 r 2r(cid:5)1
packetatthenodedintheendcluster,andthefailurestate
L (cid:8)L (cid:8)L . The probability of transition from
2 l rþ1
representstheunsuccessfulreceptionofadatapacketatthe
ðN;R ;LÞ!ðN;R ;L Þ is given by
i r l i r lþ1
node d of any cluster along the transmission path after the
ðrþ1Þth retransmission round. The transition probability PrfðN;R ;LÞ!ðN;R ;L Þg¼PERi ;
i r l i r lþ1 rgd
matrix for the absorbing Markov chain can be written as
(cid:5) 0 I 2;2(cid:6) where r g 2A 1, 1(cid:8)N i(cid:8)N n(cid:5)1, R 1(cid:8)R r(cid:8)R 2r(cid:5)1 and
, where Q is the transition probability matrix
Q R L 2(cid:8)L l(cid:8)L rþ1. The probability of transition from
ðN i;R r;L rþ1Þ!ffailureg is given by
between transient states, R denotes the transition probabil-
ity matrix from transient to absorbing states, I , the
identitymatrix,denotesthetransitionprobabilitiesb2 e;2 PrfðN i;R 2r(cid:5)1;L rþ1Þ!ffailuregg¼PERi rgd; ð6Þ
tween
absorbing states and 0 is all-zero matrix and denotes the
where 1(cid:8)N (cid:8)N . The probability of transition from
i n
transition probabilities from absorbing to transient states.
ðN ;R ;L Þ!fsuccessg through source node in the N
(cid:7) (cid:8) n 0 1 n
Here, ðN;R ;LÞ! N ;R ;L represents the transition
i r l i0 r0 l0 cluster is given by
fromonetransientstateðN;R ;LÞtoanothertransientstate
i r l
(cid:7) N i0;R r0;L l0(cid:8) . ðN i;R r;L lÞ!fsuccessg and ðN i;R r;L lÞ! PrfðN n;R 0;L 1Þ!fsuccessgg¼1(cid:5)PERn sd: ð7Þ
ffailureg denote the transition from transient state to
TheprobabilityoftransitionfromðN ;R ;LÞ!fsuccessg
absorbing states. The transition probability from n 0 l
ðN;R ;LÞ!(cid:7) N ;R ;L (cid:8) is given by the Q matrix and through relay nodes in the N n cluster is given by
i r l i0 r0 l0
DðN ei fi; nR er; PL ElÞ R! ,f Pa Ebs Ro irb ,i Pn Egs Rta ite as sg ti hs egi Pv Een Rb oy f,th ree spR ecm tia vt er li yx ,. PrfðN n;R r;L lÞ!fsuccessgg¼1(cid:5)PERn rgd; ð8Þ
i
sd sr rd
the links s(cid:5)to(cid:5)d, s(cid:5)to(cid:5)r and r(cid:5)to(cid:5)d in the ith where R (cid:8)R (cid:8)R and L (cid:8)L (cid:8)L .
1 r 2r(cid:5)1 1 l rþ1
cluster. Now we see probabilities between the transient TheprobabilityvectorforthestatestowhichtheMarkov
(cid:7) (cid:8)
states: ðN i;R r;L lÞ! N i;R r0;L l0 are the unsuccessful model is absorbed can be obtained by v¼jðI(cid:5)QÞ(cid:5)1R,
packet reception at the node d of N cluster. The transition where j¼½100(cid:6)(cid:6)(cid:6)0(cid:7) represents the vector with which the
i
probability from ðN;R ;L Þ! ðN;R ;L Þ is given by Markov model begins. In fact we can write vector v as
i 0 1 i r 2


12 Page 4 of 5 Sådhanå (2021) 46:12
v¼½vð1Þvð2Þ(cid:7), where vð1Þ and vð2Þ are, respectively, the transmissionschemes.EEisgivenbyg¼Xpð1(cid:5)PERÞ;where
ETotal
end-to-end probability of success and failure.
X is the payload of data packet and PER can be obtained
p
usingtheabsorbingMarkovmodelpresentedinsection3.1.
The analytical expressions for calculating EE of existing
3.2 End-to-end energy consumption modelling
DC and CC schemes are given in [10].
The aggregate energy consumed in the multi-cluster
transmission is the sum of energy consumed in all the
¼PN 4. Results and discussion
individual clusters. It is given by E E ; where
Total i¼1 Ci
E is the average energy consumed in the ith cluster. The
Ci
aggregate energy consumed in an ith cluster is the average
In this section, we present analytical results validated
sum of energy consumed in all retransmissions. Mathe-
using ns3 simulations.We consideredthe transmission and
matically E ¼Pr Ej ; where Ej is the energy con-
Ci j¼0 Ci Ci energy consumption parameters of an underwater acoustic
sumed in the jth retransmission. The average energy modem developed by Evologics(cid:3) as shown in Table 1
consumed in the first transmission by the source node (i.e., [1, 12]. Figure 2 and Table 2 show the variation of EE
zeroth retransmission) is given by againstthedistancebetweenS–Dlinksinshallowanddeep
! water scenarios, respectively. Figure 2 and Table 2 also
E0 ¼ ð1(cid:5)PER ÞþPER Y PER UðXþC bÞ ; indicate thatthereisadecidingthreshold distancebetween
Ci sd sd rk2A1 srk R b the source and destination nodes in both shallow and deep
water scenarios. This threshold distance determines the
ð9Þ
schemethatcanbeusedtoimproveEE.Itisalsonotedthat
where U¼½P þðrþ1ÞP (cid:7), A is the set of r relay nodes the DC and HARQ-DC perform better than CC and
t r 1
that unsuccessfully decoded the data packet and P is the C-HARQ when the distance between S–D links is lower
r
receivepowerconsumption.Theaverageenergyconsumed
inthenthretransmissionbyarelaynodefromthesuccessful
set of relay nodes is given by
80
¼(cid:3) i¼r n(cid:3)r i(cid:4) srg(cid:8)(cid:4) R R= =0 1, ,N N= =4 ( (D CC C- -A QIN -A A))
E Cn PER sdX rY k2A1PER srk rY g2A2(cid:7) 1(cid:5)PER 67 00 R R = = 0 0 , , N N = = 4 4 ( ( D H C A - R S AQ M N- D C )- -A SIN MA ))
i R = 0 , N = 4 ( H A R D C
J/stib 4
(cid:7) PER (cid:8)n(cid:5)1 ½ðnþ1ÞP R=1, N=4 (CC-SIM)
rgd t R=1, N=4 (C-HARQ-ANA)
XþC ycneiciffe 50 R=1, N=4 (C-HARQ-SIM)
þðrþnþ1ÞP (cid:7) b;
r R b 40
ð10Þ
ygrenE 30
where A is the set of r(cid:5)i relay nodes that unsuccessfully
1 20 Increasing R
decoded the data packet and A is the set of i relay nodes
2
that successfully decoded the data packet. The retransmis- 10
sions are possible only when one or more relay nodes
0
decoded the packet successfully. Several combinations of 500 1000 1500 2000 2500 3000
relay nodes are possible out of r relay nodes, given by Distance between S-D in meters
(cid:3) (cid:4)
r
. We compare the EE performance of different Figure2. EEvsdistance betweenS–D links (shallow water).
i
Table 1. Parameters considered fornumericalanalysis.
Parameters Values Parameters Values
Bitrate usedinUASNs 13900bits/s Depth ofshallow water 50m
Absorptioncoefficient Thorp’sformula[2] Depth ofdeep water 1000m
X 41bits Noise model ns3::UanNoiseModelDefault
b
X 57bits Propagation model ns3::UanPropModelThorp
FrequencyðfÞ 26kHz Transmit mode ns3::UanTxMode
P 35W PER model ns3::UanPhyPerCommonModes
t
P 1.3W Energy model ns3::AcousticModemEnergyModelHelper
r
ðmÞ 2 bits/symbol Mobility model ns3::ConstantPositionMobilityModel


Sådhanå (2021) 46:12 Page 5 of 5 12
Table 2. EEvs distance between S–D links(deepwater). acoustic sensor networks. IEEE Trans. Ind. Inf. 15(2):
719–729
Energy efficiency(bits/J) [2] LiY,ZhangY,ZhouHandJiangT2018Torelayornotto
relay: open distance and optimal deployment for linear
Distance (km) 1 1.5 2
underwateracousticnetworks.IEEETrans.Commun.66(9):
DC 39.19 1.5 0.0001 3797–3808
HARQ-DC 62.63 10.2 4.9e–05 [3] YuW,ChenY,WanL,ZhangX,ZhuPandXuX2020An
CC 40.8 11.4 1.007 energy optimization clustering scheme for multi-hop under-
HARQ-CC 35.9 30.8 20.7 wateracousticcooperativesensornetworks.IEEEAccess8:
89171–89184
than the threshold distance. This is due to the extra energy [4] Scaglione A, Goeckel D L and Laneman J N 2006
consumed by the relay nodes in CC and C-HARQ. On the Cooperative communications in mobile ad hoc networks.
otherhand,CCandC-HARQoutperformtheotherDCand IEEE SignalProcess. Mag. 23(5):18–29
HARQ-DC when the distance between S–D links is higher [5] Le L and Hossain E 2008 An analytical model
than the threshold distance. It is also observed from the for ARQ cooperative diversity in multi-hop wireless net-
results that an increase in the number of relay nodes works. IEEE Trans. Wirel. Commun. 7(5): 1786–
1791
improvestheperformanceofC-HARQinbothshallowand
[6] Al-Dharrab S, Uysal M and Duman T M 2013 Cooperative
deep water scenarios.
underwater acoustic communications [accepted from open
call].IEEE Commun.Mag.51(7): 146–153
5. Conclusion [7] JamshidiA2019EfficientcooperativeARQprotocolsbased
on relay selection in underwater acoustic communication
sensornetworks. Wirel. Netw.25:4815–4827
In this letter, we have developed an accurate stochastic
[8] Chen Y, Jin X, Wan L, Zhang X and Xu X 2019 Selective
model for multi-cluster transmissions in UASNs by con-
dynamic coded cooperative communications for multi-hop
sideringdifferentpropagationcharacteristicsofunderwater
underwater acoustic sensor networks. IEEE Access 7:
channel such as frequency-dependent signal attenuation,
70552–70563
acoustic spreading, multi-path fading and aquatic noises.
[9] GhoshA,LeeJWandChoHS2013Throughputandenergy
Analytical and simulation results show that there exists a
efficiency of a cooperative hybrid ARQ protocol for
threshold distance between the transceiving nodes in both underwater acoustic sensor networks. Sensors 13(11):
shallowanddeepwaterscenarios,whichplaysanimportant 15385–15408
roleindecidingtheoptimalscheme.Itisalsoevidentfrom [10] Goutham V and Harigovindan V P 2020 Modeling and
the results that an increase in the number of relay nodes analysisofhybridARQschemeforincrementalcooperative
significantly improves the EE. communication in underwater acoustic sensor networks.
Iran. J. Sci. Technol. Trans. Electr. Eng. https://doi.org/
10.1007/s40998-020-00348-y
[11] Sklar B 1988 Digital communications: fundamentals
References
and applications. Upper Saddle River: Prentice-
Hall,Inc.
[1] Yildiz H U, Gungor V C and Tavli B 2019 Packet size [12] Evologics 2020 Underwater acoustic modem. Available at:
optimization for lifetime maximization in underwater https://evologics.de/acoustic-modem/18-34


