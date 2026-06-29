IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
https://doi.org/10.1007/s40998-020-00348-y
(0123456789().,-vol(V0)123456789().,-volV)
RESEARCH PAPER
Modeling and Analysis of Hybrid ARQ Scheme for Incremental
Cooperative Communication in Underwater Acoustic Sensor Networks
Veerapu Goutham1 • V. P. Harigovindan1
Received:27January2019/Accepted:5May2020/Publishedonline:2June2020
(cid:2)ShirazUniversity2020
Abstract
Underwateracousticsensornetwork(UASN)isavastnetwork,inwhichtheneighborhoodofatransmittingnodeconsists
of many operating sensor nodes. By considering this as an advantage, we propose a hybrid automatic repeat request
scheme for incremental cooperative communication (HARQ-INCC) in UASNs. The proposed scheme utilizes neighbor-
hoodsensornodesduringtheinstanceofpacketretransmission.ItcombinesHARQschemewithincrementalcooperative
communication;toenhancereliabilityandtooptimizetheenergyefficiency.Inthisarticle,wepresentananalyticalmodel
tocalculatetheenergyefficiencyinUASNsfordeepandshallowwaterscenarios,byexaminingtheinfluenceofacoustic
fading,ambientnoisesandunderwaterchannelcharacteristics.TheanalyticalresultsshowthatHARQ-INCCoutperforms
the existing techniques for considerable distances between the source and destination nodes. We further propose an
optimizationalgorithmtomaximizetheenergyefficiency,byadjustingthemodulationlevelandpacketsizeasafunction
of the distance between source and destination nodes. The proposed optimization algorithm significantly enhances the
energy efficiency of HARQ-INCC scheme. Finally, we analyze the energy efficiency of UASNs with respect to the
variation in environmental parameters like waves and shipping noises. We validate the analytical results using ns-3
simulations.
Keywords Incremental cooperative communication (cid:2) HARQ (cid:2) Reed–Solomon codes (cid:2) Energy efficiency
1 Introduction topologyduetothemobilityofsensornodesalongwiththe
ocean currents. Although radio frequency signals have a
Nowadays, underwater acoustic sensor network (UASN) considerable bandwidth, they are extremely prone to
plays a significant role in dealing with many practical absorption losses in UASN (Coutinho et al. 2018b;
issues like an indication of an intruder to the ocean Kaushal and Kaddoum 2016; Yan et al. 2008; Dareh-
surveillance system, prior notification during an emer- shoorzadeh and Boukerche 2015). Hence, acoustic signals
gency, detection of oil reserves and many more. In these are most commonly preferred for UASN, which leads to
applications,sensornodesgatherdatafromtheoceanfloor flatterbandwidthsandhigherpropagationdelaysrelatedto
and send tothe buoy locatedover the ocean surface. Buoy theterrestrialnetworks.Basically,UASNisavastnetwork
transmits the data to terrestrial networks through satellite consisting of many sensor nodes and autonomous under-
channels (Coutinho et al. 2018b). In recent times, UASN water vehicles linked by acoustic signals.
drawsattentionfromresearchersbecauseofitschallenging It is worthy to point out that energy efficiency and
characteristics.Mainly,UASNpossessesdynamicnetwork reliability are crucial constraints in UASNs. Mostly, the
sensor nodes depend entirely on batteries. It is tough to
regenerateorrestore thesensornodebatterieswhenitgets
& VeerapuGoutham
discharged due to the energy consumption by the trans-
gouthamveerapu@gmail.com
ceiver circuitry (Abughalieh et al. 2014). So, reducing the
V.P.Harigovindan
number of transmissions by a node is the one possible
hari@nitpy.ac.in
alternative to enhance the energy efficiency. Accordingly,
1 NationalInstituteofTechnologyPuducherry,Karaikal, incremental cooperative communication (INCC) is a
Puducherry,India
123


![image_1_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_1/image_1_1.jpg)


280 IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
probable scheme which reduces the number of transmis- for reliable data transmission (Tomasi et al. 2015). Cur-
sions by the same sensor node. This scheme utilizes rently, Reed–Solomon (RS) codes are most widely used
neighboring sensor nodes at the instance of packet FEC technique (Proakis and Salehi 2014). In Lott et al.
retransmission. In addition, UASN consists of a poor (2007), authors provided a survey of HARQ schemes and
underwater channel which leads to receiving erroneous also suggested some possible improvements by taking
data packets at the receiver. Forward error correction practical considerations into account. The authors in Tsai
(FEC)andautomaticrepeatrequest(ARQ)aretheprimary et al. (2011) proposed an adaptive FEC mechanism, in
approaches to improve the reliability. In FEC schemes, which the extra check bits in packets are adjusted accord-
extra check bits are carried along with the data packets to ing to the packet loss rate. In Maaz et al. (2016), authors
rectifyerroneousbits.FECschemesarerestrictedtorectify investigated energy efficiency of various hybrid ARQ
errors up to error correcting ability. Likewise in ARQ schemes(i.e.,HARQchasecombining,HARQincremental
schemes, the receiver requests source node to retransmit redundancy schemes) for relay-assisted communications
the erroneous data packets. In this scheme, an adequate (amplify & forward and decode & forward schemes).
sum of transmission rate is sacrificed to achieve the relia- Incremental cooperative communication is utilized to
bility.Hence,hybridARQschemesareadoptedtoimprove achieve higher energy efficiency by exploiting the spatial
reliability and achieve optimum transmission rate. diverse links. The authors in Ikki and Ahmed (2011) pre-
Since the underwater channel exhibits unique charac- sented the closed-form expressions for bit error rate, the
teristics,whichbringsanumberofchallengesindesigning outage probability and average channel capacity for an
the reliable, energy efficient, topology independent proto- incremental relaying scheme over Rayleigh fading chan-
cols useful for UASNs. Several protocols like depth-based nelswithbestrelayselection.InNasiret al.(2016),authors
routing (DBR), energy-efficient depth-based routing analyzed theperformanceofoutageanderrorprobabilities
(EEDBR), energy-balanced and depth-controlled routing of incremental cooperative communication in underwater
(EBDCR), depth-based clustering are proposed earlier for acoustic sensor networks. Differently in this work, we
UASNs (Yan et al. 2008; Wahid et al. 2011; Qin et al. present an analytical model to evaluate the energy effi-
2017; Shah et al. 2018). These protocols mainly use the ciency in the UASNs. We also propose a hybrid ARQ
depth information of neighboring nodes. But they are scheme for incremental cooperative communication
ineffective in utilizing the relay nodes from the collected (HARQ-INCC) to improve the reliability and energy effi-
node depth information. On the other side, some authors ciency. It combines conventional Reed–Solomon (R–S)
proposed vector-based forwarding (VBR), efficient vector- codes with selective retransmission. The proposed
based forwarding (EVBF) for UASNs (Xie et al. scheme does not require the network topology. Instead, it
2006, 2010). These protocols mainly depend on the full needs precise depth information of available neighboring
dimensional localization of the network. nodes at the instance of data transmission. Hence, sensor
On the alternative part, several cooperative communi- nodes are provided with low-power depth sensors to
cation approaches exist in the literature for terrestrial measure the depth of nodes (vertical distance from the
wireless sensor networks (WSNs) and UASNs. Mainly, ocean surface). In this scheme, the optimal relay nodes
cooperative communication divided into two approaches, (nodes which are located near to the centermost region
fixedcooperativecommunicationandincrementalrelaying. between source and destination nodes) are selected for
In the first approach, the received signals are decoded, re- cooperation using depth of the sensor nodes to further
encoded and re-transmitted at the specified intermediate improve the energy efficiency. The major contributions of
nodetothenexthop(WangandNie2010).Whereasinthe this paper are summarized as follows:
second approach, relay nodes are exploited incrementally
1. We present an analytical model to evaluate the energy
to retransmit the packets at the instance of a negative
efficiency in the UASNs. The analytical model is
acknowledgment from the receiver. Few authors proposed
developed by examining the influence of acoustic
amplify-forward and decode-forward approaches to the
fading, ambient noises and underwater channel char-
incremental cooperative communication (Cao et al. 2016;
acteristics.Theproposedmodelcanbeusedforenergy
Liau et al. 2018; Celik et al. 2018; Wang et al. 2017).
efficiency analysis in the cases of direct communica-
Theseprotocolsaresuboptimalinselectionofrelaynodes.
tion (DC) and INCC for both shallow and deep water
So, authors in Liu et al. (2017) proposed an algorithm for
scenarios.
selecting the optimal relay node to decrease the energy
2. WethenproposeanHARQschemeforINCC(HARQ-
consumption.
INCC) in UASNs. The proposed scheme combines
Recent works show that HARQ technique combined
FEC using conventional R–S codes and selective
with the incremental relaying improves the energy effi-
ciency.HARQisacombinationofFECandARQschemes
123


![image_2_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_2/image_2_1.jpg)


IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294 281
retransmission, which is implemented in INCC relay nodes based on the depth information. The lowest
scheme to optimize energy efficiency. depthnode(orfarthestnodeinthedirectionofbuoywithin
3. The analytical model presented is then extended to the coverage area of the source node) is selected as a
evaluate the performance of the proposed HARQ- destination node for the first hop, because it will be the
INCCandHARQwithDC(HARQ-DC)schemes.The closest node to the buoy which is placed over the ocean
resultsshowthattheHARQ-INCCschemeoutperforms surface. The nodes which are closer to the centermost
the DC, INCC and HARQ-DC schemes in terms of regionareselectedasrelaynodes.Thisisbecause,optimal
energy efficiency when the distance between commu- energy efficiency for cooperative communication is
nicating nodes are higher. achievedwhentherelaynodeisexactlyatthecenterofthe
4. We also propose an optimization algorithm to maxi- sourceanddestinationnodes(WangandNie2010;Geethu
mize the energy efficiency in UASNs by jointly andBabu2015).Subsequently, thesourcenodebroadcasts
optimizing thepacketsizeandmodulationlevel. From the data packets along with the specified addresses of
the analytical results, it is evident that the energy destination and relay nodes. By virtue of broadcasting, the
efficiency for HARQ-INCC can be improved further relaynodescanalsoreceivethedatapacketsinadditionto
using the proposed algorithm, which leads to a high thedestinationnodeinthephase-1asdepictedinFig. 1.If
energy efficient HARQ-INCC scheme for UASNs. thedestinationnodedecodesthedatapacketcorrectly,then
5. Finally, we analyze the energy efficiency of UASNs itsendsapositiveacknowledgmenttothenodeSasshown
with respect to the variation in environmental param- in Fig. 1a. On the other hand, if the destination node
eters, namely shipping noise, waves and depth. receives the erroneous packet in the phase-1, then desti-
nation will send a negative acknowledgment (NACK) to
Rest of the paper is organized as follows: Sect. 2 pre-
R , and R will transmit the data packet in the phase-2. In
sents simple UASN model with the proposed INCC 1 1
case, if this transmission also received with errors, then in
scheme. In Sect. 3, an analytical model is presented to
phase-3 destination node will send NACK to R for the
evaluate energy efficiency in UASNs. Section 4 discusses 2
transmissionofthepacketasshowninFig. 1b.Finally,the
protocol description for implementing the HARQ
destination node drops the data packet when all the
scheme in INCC. In Sect. 5, we present an optimization
attempts are unsuccessful. Here, positive acknowledgment
algorithm. Section 6 provides a description of analytical
(ACK) will be sent to source by the destination after the
and simulation results. The conclusion is presented in
successful reception of the data packet from any of the
Sect. 7.
relaynodes.Otherwise,thesourcenodewillnotreceivethe
ACK in case of link failure between the source and desti-
nation nodes due to deep fade and this will result in the
2 System Model
timerexpiryatthesourcenode.Inthissituation,thesource
node itself prompts the relay nodes to retransmit the data
We consider a linear system model (vertical) with trans-
packet as shown in Fig. 1c. Hence, this scheme is advan-
mitter sensor node at the seabed and receiver node (the
tageous in the instance of link failures between the source
buoy) on the ocean surface. Here, we model a single-hop
and destination nodes. The proposed scheme is imple-
scenario in this work, by considering an intermediate
mentedforsingle-hopscenario,thatcanbeeasilyextended
source and destination node of this multi-hop sensor net-
for multi-hop UASNs as well.
work as shown in Fig. 1, where the nodes S, D, R and R
1 2
represent the source, destination and relay nodes, respec-
tively. In this paper, we considered two different trans-
3 Analytical Model to Evaluate Energy
mission schemes, namely direct communication (DC) and
Efficiency in UASNs
INCC. Inthefirstscheme,onlythesourcenodeisallowed
to transmit and retransmit the data packets to the destina-
In this section, we present an analytical analysis to calcu-
tion node. It is simple, but not efficient at the instance of
late the signal-to-noise ratio (c), symbol error rate (P ),
link failures due to deep fading between the source and s
packet error rate (PER) and energy efficiency (g) for both
destination nodes. In these situations, adopting forward
direct and INCC schemes. The underwater channel link
errorcorrectionandARQmethodswillbecomeineffective.
between two nodes is characterized by Rayleigh fading
TheprotocoldescriptionofINCCisasfollows:initially,
channel due to the multi-path signal propagation (Geethu
the source node broadcasts the hello packets, whenever it
and Babu 2017; Domingo 2008; Xiang-ping et al. 2011).
hasdatatosend.Thenodeswhichreceivethehellopackets
The path gain provided by multiple paths is assumed as
will provide the depth information as an acknowledgment.
statisticallyi.i.dduringthedatapackettransmission(Wang
Accordingly, the source node selects the destination and
andNie2010).WeconsideredM-QAMdigitalmodulation
123


![image_3_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_3/image_3_1.jpg)


282 IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
(a) (b)
(c)
Fig.1 Incrementalcooperativecommunication
technique with modulation level m¼log M bits/symbol transmitting node and jth receiving node. A detailed pro-
2
for succeeding symbol error rate, PER and energy effi- cedure to compute the signal-to-noise ratio in UASNs is
ciency analysis. The closed-form approximation to calcu- presented in Sect. 3.1. The sensor node splits the overall
latethesymbolerrorrate(P )ofaRayleighfadingchannel collecteddataintoseveralnumbersofdatapackets,eachof
s
linkbetweenithtransmittingnodeandjthreceivingnodeis size X bits. The data packet mainly consists of header,
given by (Goldsmith 2005). payload and trailer bits. Therefore, the PER of a link
sffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi! between ith and jth nodes is given by,
3c
P Sij (cid:3)2ð1(cid:4)2(cid:4) 2m Þ 1(cid:4) 2ð2m(cid:4)1i Þj þ3c ij ; ð1Þ PER ij ¼1(cid:4)ð1(cid:4)P SijÞmX ; ð2Þ
where c is the signal-to-noise ratio between ith
ij
123


![image_4_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_4/image_4_1.jpg)


IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294 283
X transmission power loss depends on distance r and signal
where ð1(cid:4)P SijÞm is the probability of successfully trans-
frequencyf,givenby(LuJin2013;Coutinhoet al.2018a),
mittingXsymbolsfromithnodetothejthnodeandmisthe
m
modulation level. TL ¼k(cid:5)10logrþr(cid:5)10(cid:4)3(cid:5)10logaðfÞ; ð7Þ
dB
where k is spreading factor and a(f) is absorption coeffi-
3.1 Signal-to-Noise Ratio of an Underwater cientasafunctionoffrequencyfkHz.Thefirstandsecond
Acoustic Link terms in (7) represent the spreading and absorption losses
occurred in the channel during signal transmission,
The signal-to-noise ratio (c) of an underwater channel respectively. The geometry of propagation decides the
link is mainly governed by passive SONAR equation. It spreadingfactor(k).Typically,k¼2istakenforspherical
relates the received signal strength at the detector ðS RSSÞ and k¼1 for cylindrical spreading (Stojanovic 2007;
to the noise signal level ðS NLÞ. As the acoustic signals Geethu and Babu 2017). Thorp’s formula provides the
travel through the water, few signals are attenuated absorption coefficient (dB/km) for the frequencies greater
because of spreading and absorption losses. So, the than 400 Hz. It is given by (Domingo and Prior 2008;
received signal strength at the detector is the difference Geethu and Babu 2015; Thorp 1967),
between the signal strength transmitted by the source
f2 f2
node and the signal strength lost due to the transmission 10logaðfÞ¼0:11 þ44
in underwater channel. The equation to calculate S 1þf2 4100þf2 ð8Þ
RSS
can be given by, þ 2:75(cid:5)10(cid:4)3(cid:5)f2þ0:003:
S RSS ¼ðSL(cid:4)TLÞ dB; ð3Þ The total noise level S NL is the difference between direc-
tivity index (DI) and the ambientnoise level(NL).So, the
where SL is the source level, TL is the transmission loss.
total noise level provided by the underwater channel is
The input signal transmitted at the source to reference
given by,
intensityisgivenby(DomingoandPrior2008;Geethuand
Babu 2017), S ¼ðDI(cid:4)NLÞ ; ð9Þ
NL dB
I
SL¼10log t ; ð4Þ where the directivity index is the ratio of the noise level
I ref detected by the directional antenna to the omnidirectional
antenna. DI is precisely 0 dB for the omnidirectional
q2
where I is the reference intensity given by , q is
ref q(cid:5)c antenna and 3 dB for the directional antenna.The ambient
effectiveacousticpressure(q¼1lParms),cisspeedofan
noise present in the ocean is a combination of turbulence
acoustic wave in underwater (c¼1500m=s), q is the
ðNðfÞÞ, shipping ðN ðfÞÞ, waves ðN ðfÞÞ and thermal
t s w
density of the sea water (q¼1000kg=m3). In general, the
ðN ðfÞÞ noises. The power spectral densities of these four
th
transmitted signal intensity (I) is the power flow per unit
t different noisecomponents are givenby(Stojanovic2007;
area. The propagation of acoustic waves encounters the
Geethu and Babu 2017),
spherical spreading in deep water, and cylindrical spread-
10log 10N tðfÞ¼17(cid:4)30log 10f;
ing in case of shallow water due to the signals being
bounded by the floor and surface ofthe sea. So, the power 10log N ðfÞ¼40þ20ðs(cid:4)0:5Þþ26log f
10 s 10
transmitted (P tr) from the source with respect to the dis- (cid:4) 60log 10ðf þ0:03Þ;
tance in deep water is given by (Domingo and Prior 2008; ð10Þ
10log N ðfÞ¼50þ7:5w0:5þ20log f
Geethu and Babu 2015), 10 w 10
(cid:4) 40log ðf þ0:4Þ;
10
P ¼4pr2I; ð5Þ
tr t 10log N ðfÞ¼(cid:4)15þ20log f;
10 th 10
where r is the distance (in m). Similarly, the power trans-
where s and w denote shipping activity factor and wind
mitted (P )from the source with respect to the distance in
tr speed (in m/s), respectively. The overall power spectral
shallow water is given by (Geethu and Babu 2015; Dom-
density of an ambient noise is given by,
ingo and Prior 2008),
NL¼NðfÞþN ðfÞþN ðfÞþN ðfÞ: ð11Þ
t s w th
P ¼2prHI; ð6Þ
tr t
Finally, the signal-to-noise ratio (c) of an underwater
where H is the depth in meters. The transmission power
acoustic link is the difference of (3) and (9),
loss that occurs in an underwater acoustic channel is a
combination of spreading and absorption losses. So, the c¼S RSS(cid:4)S NL ¼ðSL(cid:4)TL(cid:4)NLþDIÞ dB: ð12Þ
123


![image_5_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_5/image_5_1.jpg)


284 IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
3.2 Calculation of Energy Efficiency in UASNs E ¼f½P þ3P (cid:6)ð1(cid:4)PER Þþ½2P þ4P (cid:6)
INCC t r sd t r
PER ð1(cid:4)PER Þð1(cid:4)PER Þ: þ½2P
sd sr1 r1d t
Energy efficiency defines the amount of energy consumed
þ5P (cid:6)PER PER :
bytransmittingthemessagebitssuccessfully.Ingeneral,it r sd sr1
is the ratio of successfully transmitted message bits to the ð1(cid:4)PER sr2Þð1(cid:4)PER r2dÞ ð16Þ
total energy consumption. In this subsection, we presented þ½3P þ6P (cid:6)PER ð1(cid:4)PER ÞPER
t r sd sr1 r1d
ananalysistocomputetheenergyefficiencyforbothdirect ð1(cid:4)PER Þð1(cid:4)PER Þ
sr2 r2d
and INCC schemes.
X
þ½P þ3P (cid:6)PER PER PER g(cid:5) :
t r sd sr1 sr2 R
b
3.2.1 Direct Communication
The first term in (16) is the energy consumption for suc-
cessful packet transmission over the source to destination
The amount of energy consumed in the direct communi-
(S–D)path.Thesecondtermistheenergyconsumptionfor
cation is the sum of energy consumed by the source and
failure packet transmission over (S–D) and successful
destination nodes for transmitting and receiving the data
transmissionoverthesourcetodestinationviarelay(S–R –
1
packet. Mathematically,
D) path. The third and fourth terms represent energy con-
X sumption for a failure of packet transmission over (S–D),
E ¼ðP þPÞ ; ð13Þ
DC t r R b (S–R 1–D) paths and successful packet transmission over
(S–R –D)path,thefifthtermistheenergyconsumptionfor
whereP,P arethetransmittingandreceivingnodepower 2
t r
afailureofpackettransmissionover(S–D),(S–R Þ,(S–R Þ
consumption,XisthepacketlengthandR isthedatarate. 1 2
b
paths. Similar to the direct communication, the energy
From the definition, the energy efficiency of the direct
efficiency of INCC scheme can be given by,
communication is given by,
X ð1(cid:4)PER Þ
¼X pð1(cid:4) EPER DCÞ g ¼ p INCC ; ð17Þ
g DC ; ð14Þ INCC E INCC
DC
where the total PER for the INCC scheme (PER ) is
whereX ispayloadofthedatapacketandthetotalpacket INCC
p
given by,
errorrate(PER)ofthedirectcommunication(DC)isgiven
by PER ¼PER PER PER þPER
INCC sd sr1 sr2 sd
PER ¼1(cid:4)ð1(cid:4)P SsdÞmX ; ð15Þ ð1(cid:4)PER sr1ÞPER r1dPER sr2 þPER sdPER sr1
DC
ð1(cid:4)PER ÞPER þPER
X sr2 r2d sd
w trah ne sr með it1 ti(cid:4) ngP XsdÞm sr ye mpr be os le snts frt oh mepro nb oa db eilit Syo tf osu tc hc eess nfu ol dly
S ð1(cid:4)PER sr1ÞPER r1dð1(cid:4)PER sr2ÞPER r2d:
e
m ð18Þ
X
D. 1(cid:4)ð1(cid:4)P SsdÞm gives unsuccessful probability of trans-
mitting a data packet from nodes S to D. The first term in (18) is the unsuccessful packet transmis-
sionover(S–D),(S–R Þand(S–R Þpaths.Thesecondterm
1 2
istheunsuccessfulpackettransmissionover(S–D),(S–R –
1
3.2.2 Incremental Cooperative Communication
D) and (S–R Þ. The third term is the unsuccessful packet
2
transmissionover(S–D),(S–R Þand(S–R –D).Thefourth
1 2
We have considered a single-hop UASN scenario with
termistheunsuccessfulofpackettransmissionover(S–D),
source (S), destination (D) and relay nodes (R ; R ) as
1 2 (S–R –D), (S–R –D) path. Efficiency gain is a good mea-
2 2
presented in Sect. 2. The total energy consumed in the
sure to calculate improvement achieved in the energy
INCC scheme is the sum of energy consumed by the
efficiency of INCC scheme in comparison with the direct
source, destination and relay nodes for transmitting and
communication. Efficiency gain achieved in INCC
receivingthedatapacket.So,thetotalenergyconsumedin
scheme compared to direct communication is given by,
the INCC is given by,
g
G INCC ¼ gINCC: ð19Þ
DC
123


![image_6_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_6/image_6_1.jpg)


IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294 285
4 Protocol Description of HARQ-INCC the data packet size (XþC). The energy efficiency and
Scheme in UASNs efficiency gain achieved in HARQ-INCC are given by,
X ð1(cid:4)PER Þ
HARQ-INCC scheme combines the HARQ with INCC. In g HARQ(cid:4)INCC ¼ p E HARQ(cid:4)INCC ; ð24Þ
HARQ(cid:4)INCC
this scheme, the data packets are added with extra redun-
g
dantbitsgeneratedbyconventionalR–Scodesforforward G HARQ(cid:4)CC ¼ HA gRQ(cid:4)CC: ð25Þ
error correction. Here the data packet is a combination of DC
header, payload, trailer and redundant bits. So, the length Similarly, the energy efficiency and efficiency gain in
of the data packet increases to N ¼XþC ¼2K (cid:4)1, HARQ-DC are given by,
whereXrepresentsthelengthoftheoriginaldatapacket,C
X ð1(cid:4)PER Þ
is number of extra redundant check bits, and K is any g ¼ p HARQ(cid:4)DC ; ð26Þ
HARQ(cid:4)DC E
positive integer. The value of X can be represented as HARQ(cid:4)DC
X the¼ R2 –K S(cid:4) co1 de(cid:4) s,2 et x, pw reh se sr ee dt ai ss be dr mr 2no (cid:4)r 1cc :o Trr he ect rin emg ac ia np inab gil bi it ty so inf G HARQ(cid:4)DC ¼g HA gR DQ C(cid:4)DC; ð27Þ
i
the data packet are considered as redundant bits C ¼
where X is the payload of the data packet. The energy
p
N(cid:4)X: These bits are particularly used for correcting the
efficiency gain achieved in HARQ-INCC and HARQ-DC
errorbitspresentinthedatapacketatthedestinationnode.
in comparison with direct communication is provided in
Here, we considered K ¼6 and t¼3. Accordingly, the
(25) and (27), respectively.
total number of bits in the data packet are 63, in which 6
redundant bits are used for error correction and remaining
57 bits include header, payload and trailer bits. The R–S 5 Optimization Algorithm for Improving
decoded symbol error rate (P(cid:7) Sij) in terms of uncoded P Sij Energy Efficiency in UASNs
can be expressed as (Sklar 1988),
1 2 XK(cid:4)1 r(cid:3) 2K (cid:4)1(cid:4) I on ptt ih mis izs eec et nio ern g, yw ee ffip cre ies nen cyte .d Ta hn eo ep nt eim rgi yza et fio fin ciea nlg co yri mth am inlto
P(cid:7) (cid:3) Pr ð1(cid:4)P Þ2K(cid:4)1(cid:4)r: ð20Þ y
Sij 2K (cid:4)1 r Sij Sij
r¼tþ1 depends on two important parameters, namely packet size
Xandmodulationlevelm.Duringdatatransmission,small
The PER of a link between ith transmitting node and jth
size packets are less susceptible to errors at the cost of
receiving node in HARQ-INCC and HARQ-DC schemes,
more overhead bits, whereas large size packets are more
PER(cid:7) can be calculated by,
ij susceptible to errors, which may decrease the energy effi-
PER(cid:7) ¼1(cid:4)ð1(cid:4)P(cid:7) ÞXþ mC : ð21Þ ciency. Similarly, a scheme with low modulation level is
ij Sij
more robust but may result in an inefficient use of the
TheoverallPERofHARQ-INCCschemecanbefoundby channel,whereashighmodulationlevelismoresensitiveto
substituting(21)in(18)withtheirrespectivepathswhichis get errors but carries more information per symbol.
given by, Therefore,jointoptimalXandmarerequiredtomaximize
energy efficiency. Accordingly,we presented analgorithm
PER ¼PER(cid:7) PER(cid:7) PER(cid:7) þPER(cid:7)
HARQ(cid:4)INCC sd sr1 sr2 sd tofindtheoptimumenergyefficiencyfortheHARQ-INCC
(cid:5) (cid:6)
1(cid:4)PER(cid:7) PER(cid:7) PER(cid:7) þPER(cid:7) PER(cid:7) and HARQ-DC systems by selecting the optimum values
sr1 r1d sr2 sd sr1
(cid:5) (cid:6) for X and m jointly. The procedure for selecting the opti-
1(cid:4)PER(cid:7) PER(cid:7) þPER(cid:7)
sr2 r2d sd mum values of X and m is illustrated in Fig. 2. In which,
(cid:5) (cid:6) (cid:5) (cid:6) gðX;mÞ represents energy efficiency of a scheme having
1(cid:4)PER(cid:7) PER(cid:7) 1(cid:4)PER(cid:7) PER(cid:7) :
sr1 r1d sr2 r2d packetlengthXbits,modulationlevelmbits/symbolandg(cid:7)
ð22Þ represents the optimum energy efficiency. Initially, we
assumed X ¼32 bits and m¼2 bits/symbol. The modu-
Similarly, the overall PER of HARQ-DC scheme can be
lationleveliskeptasconstantandthepacketsizeisvaried
found by substituting the (21) in (15) given by,
with an incremental step value of 8 bits ðX ¼Xþ8Þ to
pt
PER ¼1(cid:4)ð1(cid:4)P(cid:7) SsdÞXþ mC ð23Þ findthelocaloptimumenergyefficiencyg k.Theprocessis
HARQ(cid:4)DC
repeated several times by increasing the modulation level
The energy consumed in HARQ-INCC (E ) and
HARQ(cid:4)INCC andtheobtainedvalueiscomparedwiththepreviouslocal
HARQ-DC (E ) is similar to INCC and direct
HARQ(cid:4)DC optimumenergyefficiency.Iftheenergyefficiencyismore
communication,respectively,withthesignificantchangein
than the previous value, then the same steps are repeated
123


![image_7_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_7/image_7_1.jpg)


286 IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
Fig.2 Optimizationalgorithm
for succeeding pairs. The process gets terminated when 6.1 NumericalandSimulationAnalysisofEnergy
energy efficiency begins to fall. Efficiency
6.1.1 In Shallow Water
6 Results and Discussion
Firstly, we present a comparative analysis between energy
In this section, we presented analytical results using efficiencies of direct communication (DC), direct com-
MATLAB(cid:3)R2018aandtheseresultsarevalidatedthrough munication with HARQ (HARQ-DC), incremental coop-
ns-3simulations.ThedistancebetweenRandDnodes(r ) erative communication (INCC) and incremental
rd
isq(cid:7)r ,whereqisanarbitraryconstantrangingfrom0to cooperative communication with HARQ (HARQ-INCC)
sd
1 and r is the distance between S and D nodes. The using Eqs. (14), (17), (26), (24), respectively.
sd
parameter used for numerical and simulation analysis is It is evident from Fig. 3 that the average energy effi-
listed in Table 1 and these values took from Evologics(cid:4)d ciency of HARQ-INCC under performs the HARQ-DC
practical underwater acoustic modem (Samad et al. 2011; because of additional energy consumed by the relay nodes
Uysal et al. 2016; Evologics 2018). in HARQ-INCC for shorter distances between S–D nodes.
123


![image_8_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_8/image_8_1.jpg)


IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294 287
Table1 Systemparameters
Parameters Values
usedfornumericaland
simulationanalysis
TransmitterpowerconsumptionðPÞ 5W
t
ReceiverpowerconsumptionðPÞ 0.768W
r
BitrateusedinUASNs 13,900b/s
PayloadsizeL 41bits
p
PacketsizeL 57bits
Frequencyf 26kHz
Depthofshallowwater 50m
Depthofdeepwater 1000m
Modulationlevelm 2bits/symbol
Noisemodel ns3::UanNoiseModelDefault
Propagationmodel ns3::UanPropModelThorp
PERmodel ns3::UanPhyPerCommonModes
Energymodel ns3::AcousticModemEnergyModelHelper
Mobilitymodel ns3::ConstantPositionMobilityModel
3500
DC-ANA
DC-SIM
HARQ-DC-ANA
3000 HARQ-DC-SIM
INCC-ANA
INCC-SIM
HARQ-INCC-ANA
2500 HARQ-INCC-SIM
J/stib
ycneiciffe
2000
ygrenE 1500
1000
500
0
100 150 200 250 300 350 400 450 500
Distance between S-D in meters
Fig.3 EnergyefficiencyversusthedistanceseparationbetweenS–Dlinkforallschemesinshallowwater
In contrast, the proposed HARQ-INCC outperforms 6.1.2 In Deep Water
HARQ-DC for longer distances between S–D nodes. This
is because of the reduction in signal-to-noise ratio, which Inthissubsectionsimilartotheshallowwaterscenario,we
introducespacketerrors,resultinginlow-energyefficiency present a comparative analysis of DC, HARQ-DC, INCC
in HARQ-DC scheme. Figure 4 depicts efficiency gain and HARQ-INCC schemes implemented in deep water. A
achieved by the HARQ-DC, INCC and HARQ-INCC with similar kind of response as seen in the shallow water sce-
respect to the direct communication. These gains are cal- nario is obtained in deep water. Figure 5 depicts that the
culated by using Eqs. (27), (19), (25), respectively. It is transmission range of available schemes in deep water is
found that the energy efficiency gain of HARQ-INCC is restricted to smaller distances when compared to shallow
greater than other schemes when the distance between the water scenario. This is because of spherical spreading
source and destination nodes is longer. (K ¼2) of acoustic signals in deep water which increases
the transmission power loss. In Fig. 5, it is observed that
the average energy efficiency of HARQ-DC outperforms
123


![image_9_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_9/image_9_1.jpg)


288 IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
4.5
HARQ-DC-ANA
HARQ-DC-SIM
INCC-ANA
4
INCC-SIM
HARQ-INCC-ANA
HARQ-INCC-SIM
3.5
niag
3
ycneiciffe
2.5
ygrenEJ/stib
2
1.5
1
0.5
100 150 200 250 300 350 400 450 500
Distance between S-D in meters
Fig.4 EfficiencygainversusthedistanceseparationbetweenS–Dlinksforallschemesinshallowwater
2000
1800
1600
1400
ycneiciffe 1200
DC-ANA
DC-SIM
1000 HARQ-DC-ANA
HARQ-DC-SIM
ygrenE INCC-ANA
800 INCC-SIM
HARQ-INCC-ANA
HARQ-INCC-SIM
600
400
200
0
100 110 120 130 140 150 160 170 180 190 200
Distance between S-D in meters
Fig.5 EnergyefficiencyversusthedistanceseparationbetweenS–Dlinksforallschemesindeepwater
HARQ-INCC for smaller distances between S–D nodes 6.2 Numerical and Simulation Analysis
and HARQ-INCC outperforms the HARQ-DC for longer of Optimization Algorithm
distances between S–D nodes. Figure 6 shows the energy
efficiency gain achieved by the individual scheme with InSect. 5,wehaveproposedanoptimizationalgorithmfor
respect to direct communication in deep water. It is improving energy efficiency in UASNs. This algorithm is
observedthattheenergyefficiencygainofHARQ-INCCis applied to different schemes such as HARQ-DC and
much higher than that of other schemes in the deep water. HARQ-INCC.Wealsocomparedtheperformanceofthese
schemes (HARQ-DC & HARQ-INCC) with and without
theinclusionofthisoptimizationalgorithmtoevaluatethe
improvement achieved by using this optimization
123


![image_10_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_10/image_10_1.jpg)


IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294 289
104
18
HARQ-DC-ANA
HARQ-DC-SIM
16 INCC-ANA
INCC-SIM
HARQ-INCC-ANA
14 HARQ-INCC-SIM
12000
niag 12
10000
ycneiciffe
10 8000
6000
8
ygrenE)J/stib(
4000
6 2000
160 165 170 175 180 185 190
4
2
0
100 110 120 130 140 150 160 170 180 190 200
Distance between S-D in meters
Fig.6 EfficiencygainversusthedistanceseparationbetweenS–Dlinksforallschemesindeepwater
9000
8000 OPT-HARQ-DC-ANA
OPT-HARQ-DC-SIM
OPT-HARQ-INCC-ANA
OPT-HARQ-INCC-SIM
7000
HARQ-DC-ANA
HARQ-DC-SIM
HARQ-INCC-ANA
6000 HARQ-INCC-SIM
ycneiciffE
5000
4000
ygrenE
3000
2000
1000
0
100 150 200 250 300 350 400 450 500
The Distance of S-D link in meters
Fig.7 EnergyefficiencyversusthedistanceseparationbetweenS–Dlinksforoptimalandnon-optimalschemesinshallowwater
algorithm.HereHARQ-DCandHARQ-INCCschemesare 6.2.1 In Shallow Water
evaluated using fixed packet size (X ¼63 bits) and mod-
ulation level (m¼2). For the optimized schemes, packet The energy efficiency for HARQ-DC, HARQ-INCC
size and modulation level are obtained by using the opti- schemes has been optimized by adaptively adjusting the
mization algorithm. packet size and modulation level. Figure 7 provides the
comparativeanalysisofoptimizedHARQ-DCandHARQ-
INCCwiththeirrespectivetraditionalschemes.Ithasbeen
observed from Fig. 7 that the energy efficiency of HARQ
schemes can be further improved by applying the
123


![image_11_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_11/image_11_1.jpg)


290 IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
600
OPT-HARQ-DC
OPT-HARQ-INCC
500
400
ezis
tekcaPlevel 300
200
100
0
100 150 200 250 300 350 400 450 500
The Distance of S-D link in meters
Fig.8 PacketsizeversusthedistanceseparationbetweenS–Dlinkforoptimizedschemesinshallowwater
7
6.5 OPT-HARQ-DC
OPT-HARQ-INCC
6
5.5
5
noitaludoM
4.5
4
3.5
3
2.5
2
100 150 200 250 300 350 400 450 500
The Distance of S-D link in meters
Fig.9 ModulationlevelversusthedistanceseparationbetweenS–Dlinkforoptimizedschemesinshallowwater
optimizationalgorithm.Themaximumenergyefficiencyis 6.2.2 In Deep Water
observedfor HARQ-INCCwiththeproposedoptimization
algorithm. We have also found the optimum modulation Similar to the shallow water scenario, we have also found
level and packet size by using the optimization algorithm. optimized energy efficiency for the HARQ-DC and
Figures 8 and 9 depict the variation of optimum packet HARQ-INCCschemesusingtheoptimizationalgorithmin
size and modulation level with respect to the distance deep water. Figure 10 gives the optimized energy effi-
between the source and destination nodes. ciency for a corresponding pair of packet size and modu-
lationlevelwithrespecttothedistancebetweenthesource
and destination nodes. We have also found the optimum
123


![image_12_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_12/image_12_1.jpg)


IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294 291
5000
OPT-HARQ-DC-ANA
OPT-HARQ-DC-SIM
4500 OPT-HARQ-INCC-ANA
OPT-HARQ-INCC-SIM
HARQ-DC-ANA
4000 HARQ-DC-SIM
)J/stib( HARQ-INCC-ANA
HARQ-INCC-SIM
3500
ycneiciffE
3000
2500
ygrenElevel
2000
1500
1000
500
0
100 110 120 130 140 150 160 170 180 190 200
The Distance of S-D link in meters
Fig.10 EnergyefficiencyversusthedistanceseparationbetweenS–Dlinksforoptimalandnon-optimalschemesindeepwater
5
OPT-HARQ-DC
OPT-HARQ-INCC
4.5
4
noitaludoM
3.5
3
2.5
2
100 110 120 130 140 150 160 170 180 190 200
The Distance of S-D link in meters
Fig.11 ModulationlevelversusthedistanceseparationbetweenS–Dlinkforoptimizedindeepwater
modulation level and packet size to improve energy effi- longer distance between the source and destination nodes
ciency in deep water scenario. in both shallow and deep water scenarios.
Figures 11 and 12 depict the variation of optimum
modulation level and packet size with respect to the dis- 6.3 NumericalandSimulationAnalysisofEnergy
tancebetweenthesourceanddestinationnodes.Lastly,the Efficiency Considering the Effects
optimized HARQ-DC and HARQ-INCC use larger packet of Environmental Parameters
size and higher modulation level for the shorter distance
betweenthesourceanddestinationnodes.Italsoadjuststo In this subsection, we discussed the performance analysis
smaller packet sizes and lower modulation level for the of energy efficiency considering the effects of environ-
mental parameters, namely shipping noises, waves and
123


![image_13_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_13/image_13_1.jpg)


292 IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
200
OPT-HARQ-DC
OPT-HARQ-INCC
180
160
140
ezis
120
tekcaPJ/stib
100
80
60
40
20
100 110 120 130 140 150 160 170 180 190 200
The Distance of S-D link in meters
Fig.12 PacketsizeversusthedistanceseparationbetweenS–Dlinksforoptimizedschemesindeepwater
2600
2400
2200
2000
1800
ycneiciffe
1600
ygrenE 1400
1200
S=0.2, W=10 m/s-ANA
1000 S=0.2, W=10 m/s-SIM
S=0.4, W=15 m/s-ANA
S=0.4, W=15 m/s-SIM
800
S=0.6, W=20 m/s-ANA
S=0.6, W=20 m/s-SIM
600
100 150 200 250 300 350 400 450 500
Distance between S-D in meters
Fig.13 EnergyefficiencyversusthedistanceseparationbetweenS–Dlinksforallschemesinshallowwater
depth. The waves noise mainly depends on wind velocity severely degrade the performance of energy efficiency in
(w) on ocean, which varies approximately in the range of both shallow and deep water scenarios.
1–50 m/s (Molland 2008). The shipping noise depends on
shipping activity factor (s), which varies in the range of
[0, 1], where 0 and 1 represent low and high shipping 7 Conclusion
activities,respectively(Stojanovic2007).Weformedthree
different pairs of wind velocitiesand shipping activities as In this paper, we have presented an analytical model to
shown in Figs. 13 and 14. From the results, it is clearly compute energy efficiency and efficiency gain of DC,
observedthathigh-velocitywindsandhighshippingnoises HARQ-DC, INCC, HARQ-INCC schemes in UASNs. An
123


![image_14_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_14/image_14_1.jpg)


IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294 293
2500
S=0.2, W=10 m/s-ANA
S=0.2, W=10 m/s-SIM
S=0.4, W=15 m/s-ANA
S=0.4, W=15 m/s-SIM
S=0.6, W=20 m/s-ANA
2000 S=0.6, W=20 m/s-SIM
J/stib
ycneiciffe 1500
ygrenE
1000
500
0
100 110 120 130 140 150 160 170 180 190 200
Distance between S-D in meters
Fig.14 EnergyefficiencyversusthedistanceseparationbetweenS–Dlinksforallschemesindeepwater
extensive numerical and simulation analysis has per- Coutinho RWL, Boukerche A, Loureiro AAF (2018a) Modeling
formed, and it clearly shows that HARQ-INCC can powercontrolandanypathroutinginunderwaterwirelesssensor
networks.In:2018IEEEwirelesscommunicationsandnetwork-
improve the energy efficiency compared to existing
ing conference (WCNC), pp 1–6. https://doi.org/10.1109/
schemes in UASNs. It also reveals the existence of a WCNC.2018.8377329
threshold distance separation between the source and des- Coutinho RWL, Boukerche A, Vieira LFM, Loureiro AAF (2018b)
tination nodes, which serves as a deciding factor in per- Underwater wireless sensor networks: a new challenge for
topology control-based systems. ACM Comput Surv
formance calculation. We have also proposed an
51(1):19:1–19:36.https://doi.org/10.1145/3154834
optimization algorithm for HARQ-DC and HARQ-INCC Darehshoorzadeh A, Boukerche A (2015) Underwater sensor net-
to increase the energy efficiency in UASNs by jointly works:anewchallengeforopportunisticroutingprotocols.IEEE
optimizing the packet size and modulation level. It is evi- Commun Mag 53(11):98–107. https://doi.org/10.1109/MCOM.
2015.7321977
dent from the results that this algorithm further improves
Domingo MC (2008) Overview of channel models for underwater
the energy efficiency. Finally, the paper concludes that wirelesscommunicationnetworks.PhysCommun1(3):163–182.
HARQ-INCC with optimization algorithm (optimized https://doi.org/10.1016/j.phycom.2008.09.001
HARQ-INCC)significantlyimprovestheenergyefficiency DomingoMC,PriorR(2008)Energyanalysisofroutingprotocolsfor
underwater wireless sensor networks. Comput Commun
of UASNs.
31(6):1227–1238. https://doi.org/10.1016/j.comcom.2007.11.
005
Evologics(2018)Underwateracousticmodem.http://www.evologics.
de/en/products/acoustics/s2cm_hs.html.Accessed27Jan2020
References GeethuKS,BabuAV(2015)Minimizingthetotalenergyconsump-
tion in multi-hop UWASNs. Wirel Pers Commun
83(4):2693–2709.https://doi.org/10.1007/s11277-015-2564-2
Abughalieh N, Steenhaut K, Nowe´ A, Anpalagan A (2014) Turbo
Geethu KS, Babu AV (2017) A hybrid ARQ scheme combining
codesformulti-hop wireless sensornetworks withdecode-and-
erasure codes and selective retransmissions for reliable data
forward mechanism. EURASIP J Wirel Commun Netw
transfer in underwater acoustic sensor networks. EURASIP J
2014(1):204.https://doi.org/10.1186/1687-1499-2014-204
Wirel Commun Netw 2017(1):32. https://doi.org/10.1186/
Cao R, Qu F, Yang L (2016) Asynchronous amplify-and-forward
s13638-017-0823-5
relay communications for underwater acoustic networks. IET
GoldsmithA(2005)Wirelesscommunications.CambridgeUniversity
Commun 10(6):677–684. https://doi.org/10.1049/iet-com.2014.
Press,Cambridge
1233
Ikki SS, Ahmed MH (2011) Performance analysis of cooperative
CelikA,SaeedN,Al-NaffouriTY,AlouiniM(2018)Modelingand
diversity with incremental-best-relay technique over Rayleigh
performance analysis of multihop underwater optical wireless
fadingchannels.IEEETransCommun59(8):2152–2161.https://
sensor networks. In: 2018 IEEE wireless communications and
doi.org/10.1109/TCOMM.2011.053111.080672
networking conference (WCNC), pp 1–6. https://doi.org/10.
KaushalH,KaddoumG(2016)Underwateropticalwirelesscommu-
1109/WCNC.2018.8377388
nication. IEEE Access 4:1518–1547. https://doi.org/10.1109/
ACCESS.2016.2552538
123


![image_15_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_15/image_15_1.jpg)


294 IranianJournalofScienceandTechnology,TransactionsofElectricalEngineering(2021)45:279–294
LiauQY,LeowCY,DingZ(2018)Amplify-and-forwardvirtualfull- Stojanovic M (2007) On the relationship between capacity and
duplexrelaying-based cooperative noma.IEEE Wirel Commun distance in an underwater acoustic communication channel.
Lett7(3):464–467.https://doi.org/10.1109/LWC.2017.2785303 ACM SIGMOBILE Mobile Comput Commun Rev 11(4):34.
LiuL,MaM,LiuC,ShuY(2017)Optimalrelaynodeplacementand https://doi.org/10.1145/1347364.1347373
flow allocation in underwater acoustic sensor networks. IEEE Thorp WH (1967) Analytic description of the low-frequency atten-
Trans Commun 65(5):2141–2152. https://doi.org/10.1109/ uationcoefficient.JAcoustSocAm42(1):270–270.https://doi.
TCOMM.2017.2677448 org/10.1121/1.1910566
LottC,MilenkovicO,SoljaninE(2007)Hybridarq:theory,stateof TomasiB,CasariP,BadiaL,ZorziM(2015)Cross-layeranalysisvia
theart andfuture directions.In:2007 IEEE informationtheory Markov models of incremental redundancy hybrid ARQ over
workshoponinformationtheoryforwirelessnetworks,pp1–5. underwater acoustic channels. Ad Hoc Netw 34:62–74. https://
https://doi.org/10.1109/ITWITWN.2007.4318035 doi.org/10.1016/j.adhoc.2014.07.013
Lu Jin DH (2013) A slotted CSMA based reinforcement learning Tsai MF, Chilamkurti N, Shieh CK, Vinel A (2011) Mac-level
approach for extending the lifetime of underwater acoustic forwarderrorcorrectionmechanismforminimumerrorrecovery
wireless sensor networks. Comput Commun 36(9):1094–1099. overhead and retransmission. Math Comput Model
https://doi.org/10.1016/j.comcom.2012.10.007 53(11):2067–2077.https://doi.org/10.1016/j.mcm.2010.05.019
MaazM,LorandelJ,MaryP,Pre´votetJC,He´lardM(2016)Energy Uysal M, Panayirci E, Nouri H (2016) Information theoretical
efficiencyanalysisofhybrid-arqrelay-assistedschemesinLTE- performanceanalysisandoptimisationofcooperativeunderwa-
based systems. EURASIP J Wirel Commun Netw 2016(1):22. ter acoustic communication systems. IET Commun
https://doi.org/10.1186/s13638-016-0520-9 10(7):812–823.https://doi.org/10.1049/iet-com.2015.0640
Molland AF (2008) Chapter 1—the marine environment. In: The WahidA,LeeS,JeongHJ,KimD(2011)EEDBR:energy-efficient
Maritime Engineering Reference Book. Butterworth-Heine- depth-based routing protocol for underwater wireless sensor
mann, Oxford, pp 1–42. https://doi.org/10.1016/B978-0-7506- networks.Springer,Berlin,pp223–234.https://doi.org/10.1007/
8987-8.00001-9 978-3-642-24267-0_27
NasirH,JavaidN,SherM,QasimU,KhanZA,AlrajehN,NiazIA WangS,NieJ(2010)Energyefficiencyoptimizationofcooperative
(2016) Exploiting outage and error probability of cooperative communication in wireless sensor networks. EURASIP J Wirel
incremental relaying in underwater wireless sensor networks. CommunNetw.https://doi.org/10.1155/2010/162326
Sensors.https://doi.org/10.3390/s16071076 Wang C, Cho T, Tsai T, Jan M (2017) A cooperative multihop
Proakis JG, Salehi M (2014) Digital communications. McGraw Hill transmission scheme for two-way amplify-and-forward relay
Education,NewYork networks. IEEE Trans Veh Technol 66(9):8569–8574. https://
QinH,ZhangZ,WangR,CaiX,JiaZ(2017)Energy-balancedand doi.org/10.1109/TVT.2017.2687622
depth-controlledroutingprotocolforunderwaterwirelesssensor Xiang-ping G, Yyan Y, Rong-lin H (2011) Analyzing the perfor-
networks.Springer,Cham,pp115–131.https://doi.org/10.1007/ mance of channel in underwater wireless sensor networks
978-3-319-65482-9_8 (UWSN). Proc Eng 15:95–99. https://doi.org/10.1016/j.proeng.
Samad SA, Shenoy SK, Kumar GS (2011) Improving energy 2011.08.020
efficiency of underwater acoustic sensor networks using trans- XieP,CuiJH,LaoL(2006)VBF:vector-basedforwardingprotocol
mission power control: a cross-layer approach. Adv Comput forunderwatersensornetworks.Springer,Berlin,pp1216–1221.
Commun192:93–101 https://doi.org/10.1007/11753810_111
Shah SBH, Zhe C, Ahmed SH, Fuliang Y, Faheem M, Begum S Xie P, Zhou Z, Nicolaou N, See A, Cui JH, Shi Z (2010) Efficient
(2018)Depthbasedroutingprotocolusingsmartclusteredsensor vector-basedforwardingforunderwatersensornetworks.EUR-
nodes in underwater WSN. In: Proceedings of the 2nd interna- ASIP J Wirel Commun Netw 2010(1):195,910. https://doi.org/
tional conference on future networks and distributed systems, 10.1155/2010/195910
ICFNDS’18.ACM,NewYork,pp53:1–53:7.https://doi.org/10. Yan H, Shi ZJ, Cui JH (2008) DBR: depth-based routing for
1145/3231053.3231119 underwatersensornetworks.Springer,Berlin,pp72–86.https://
Sklar B (1988) Digital communications: fundamentals and applica- doi.org/10.1007/978-3-540-79549-0_7
tions.Prentice-Hall,Inc.,UpperSaddleRiver
123


![image_16_1](https://doc2markdown.com/images/20260608/0281ff37-70f5-4e02-8a71-8f46a40deb43/page_16/image_16_1.jpg)


