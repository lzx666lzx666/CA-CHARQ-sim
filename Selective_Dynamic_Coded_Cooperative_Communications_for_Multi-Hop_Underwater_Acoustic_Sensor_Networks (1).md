ReceivedMarch28,2019,acceptedApril19,2019,dateofpublicationApril23,2019,dateofcurrentversionJune11,2019.
DigitalObjectIdentifier10.1109/ACCESS.2019.2912917
Selective Dynamic Coded Cooperative
Communications for Multi-Hop Underwater
Acoustic Sensor Networks
YOUGANCHEN 1,2,(Member,IEEE),XIAOTINGJIN1,2,LEIWAN3,(Member,IEEE),
XIAOKANGZHANG1,2,ANDXIAOMEIXU1,2
1KeyLaboratoryofUnderwaterAcousticCommunicationandMarineInformationTechnology(XiamenUniversity),MinistryofEducation,Xiamen361005,
China
2ShenzhenResearchInstituteofXiamenUniversity,Shenzhen518000,China
3CollegeofUnderwaterAcousticEngineering,HarbinEngineeringUniversity,Harbin150001,China
Correspondingauthor:XiaomeiXu(xmxu@xmu.edu.cn)
ThisworkwassupportedinpartbytheBasicResearchProgramofScienceandTechnologyofShenzhen,China,underGrant
JCYJ20170818141735140,inpartbytheNationalKeyResearchandDevelopmentProgramofChinaunderGrant2016YFC1400200,
inpartbytheNationalNaturalScienceFoundationofChinaunderGrant41476026,Grant41676024,andGrant61801139,inpartbythe
FundamentalResearchFundsfortheCentralUniversitiesofChinaunderGrant20720180078andGrant20720180105,andinpartbythe
NaturalScienceFoundationofFujianProvinceofChinaunderGrant2018J05071.
ABSTRACT Duetothelimitationofacousticvelocityinunderwaterenvironments,propagationdelayisa
horribleprobleminmulti-hopunderwateracousticsensornetworks(UW-ASNs).Inthispaper,weproposed
an improved scheme of dynamic coded cooperation called selective dynamic coded cooperation (S-DCC)
for the multi-hop UW-ASNs, aiming at reducing the end-to-end delay and improving the transmission
efficiency.InS-DCCscheme,thecooperativenodeactivelytransmitsblockswithlimitedredundancy;yet
thereceiveronlyselectivelyreceivesthosecooperativeblocksdependingonitsowndecodingconditions.
TheS-DCCschemecanutilizetheretransmissionmechanismadequatelytoeliminatethewaitingtimeand
drastically shorten the overall transmission time, the gain of which increases linearly with the number of
hops.Concerningthetransmissiondelayandenergyconsumption,weevaluatedtheperformanceswiththe
differentmaximumnumberofretransmissionsanddifferentdataburstsizesfortheproposedS-DCCscheme
andothercomparedschemes.ThesimulationresultsshowedthattheproposedS-DCCschemecouldachieve
decentoutageperformanceandreducetheend-to-enddelayeffectivelywithoutextraenergyconsumption
comparedwithotherexistingschemes,especiallyforthecaseswithlowtransmissionsignaltonoiseratio.
Seatestdatawerealsoadoptedtofurtherverifytheconclusions.
INDEXTERMS Energyconsumption,multi-hopnetworks,end-to-enddelay,underwateracousticcommu-
nications.
I. INTRODUCTION distance-dependentbandwidth,highpropagationdelay,high
With the development of the exploration of the oceans, biterrorratesandtemporarylossofconnectivity.
the traditional node-to-node underwater acoustic commu- In underwater acoustic environments, much more trans-
nication has been transformed into networks. Underwater mission power is required for direct long distance commu-
Acoustic Sensor Networks (UW-ASNs) have been exten- nication. Hence the long link is usually divided into several
sively used in marine research, commercial and military short links in multi-hop transmissions where the data can
applications [1], [2]. However, the design of UW-ASNs be transmitted at a higher rate in each hop. This is because
is a challenging task due to the harsh characteristics of multi-hopsystemcandecreasesignalattenuationandprovide
underwater acoustic channels, such as limited frequency, moreavailablebandwidth[3],whichisespeciallyappealing
to underwater acoustic channels. On the other hand, most
sensornodesinmulti-hopUW-ASNsarebatterypoweredand
aredifficulttorechargeorreplace,whichcallsforattentionto
The associate editor coordinating the review of this manuscript and
approvingitforpublicationwasCunhuaPan. thetransmissionefficiencyduringthedesignofUW-ASNs.
2169-3536 2019IEEE.Translationsandcontentminingarepermittedforacademicresearchonly.
70552 Personaluseisalsopermitted,butrepublication/redistributionrequiresIEEEpermission. VOLUME7,2019
Seehttp://www.ieee.org/publications_standards/publications/rights/index.htmlformoreinformation.


![image_1_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_1/image_1_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
Generally,theend-to-enddelayandenergyefficiencyare according to its instant decoding results. Hence the waiting
thekeymetricsconsideredinthedesignofUW-ASNs.There timeoffeedbacksignalsentbythereceivertothecooperative
have been several research articles [4]–[6] about the end- node can be used for the redundant blocks’ transmission,
to-enddelayandenergy-efficiencyinlinearUW-ASNswith although they might not be adopted for dynamic decoding
differentfocuses.In[4],itproposesanenergy-efficiencygrid eventually.Inotherwords,sincetherequesttimeforretrans-
routing based on 3D cubes for UW-ASNs, considering the mission is eliminated, S-DCC can drastically shorten the
3Dchangingtopology,highpropagationdelay,nodemobil- overalltransmissiontimeforthemulti-hopUW-ASNssystem
ity and density. The literature in [5] shows the bandwidth- comparedwiththeexistingDCCprotocols.
distance, power-distance and delay-distance relationships, In addition, the main idea of Cooperative Hybrid Auto-
respectively, for energy-efficient design in UW-ASNs. Fur- matic Repeat reQuest (C-HARQ) protocol for UW-ASNs
thermore, in [6], the tradeoffs between energy consump- in [15] is to retransmit the erroneous part instead of entire
tionandnetworkconnectivityinUW-ASNsareinvestigated. packettoreducethedelayfromthecooperativenode,which
Although the aforementioned papers provide some closed- essentiallymergesCooperativeARQ(C-ARQ)withaHybrid
form approximate models, it is still difficult to draw a con- ARQ (HARQ) technique. Yet it does not concern the DCC
clusionfortherelationshipbetweenenergyconsumptionand protocol or S-DCC protocol. Instead of retransmitting the
multi-hop network design in the string UW-ASNs. More- erroneouspartpacket,thecooperativenodetransmitspartof
over,mostofthereferencesdonotconsiderthecooperative thepartial coded packet in DCC or S-DCC protocol, where
transmission. the partial coded packet can be arbitrarily added to the
Tocombatunderwaterchannelunreliabilityandlargepath received data as a whole codeword for decoding, so as to
losses, cooperative transmission has been applied in under- utilize the benefits of both the broadcasting listening and
water acoustic communications as an ideal solution. In [7], cooperationphases.MoredetailsaboutthedesignofC-ARQ,
it demonstrates the superiority of cooperative underwater HARQandC-HARQinunderwateracousticchannelscanbe
acousticcommunicationsystemsoverthepoint-to-pointsys- foundin[15].
tems, and they meet the requirements of UW-ASNs. For 2)Investigatingthedelay-energyrelationshipinmulti-hop
the cooperative communications, the design of relay strat- UW-ASNs for both S-DCC and DCC protocols. We com-
egy is crucial, and lots of schemes have been studied, such pare the outage probability, end-to-end delay and energy
asamplify-and-forward(AF),decode-and-forward(DF)and consumption of the S-DCC, DCC, C-ARQ protocols and
compression-and-forward(CF)[8],[9].Especially,dynamic the conventional stop and wait ARQ (S&W ARQ) proto-
coded cooperation (DCC) [10]–[12] has been proposed by col in the multi-hop UW-ASNs. Simulation results show
investigating the combination of coding and relay cooper- that,theproposedS-DCCschemecanachievedecentoutage
ation. In [13], we proposed orthogonal-frequency-division performance and reduce end-to-end delay effectively with-
multiplexing(OFDM)modulatedDCCforthree-nodeunder- outextraenergyconsumption,comparedwithotherexisting
water acoustic cooperative networks, where the relay node schemes. The proposed S-DCC scheme is a feasible coop-
can randomly access the point-to-point transmission proce- erative strategy for low transmission Signal to Noise Ratio
dureandenhancethecommunicationsbyexploitingtheben- (SNR). The sea test data are adopted to further verify the
efitofrate-compatiblecoding.Asshownin[13],significant conclusions.
gainwasachievedbyDCCinunderwateracousticchannels, 3) Given the target performance, e.g., the outage prob-
and therefore it is a promising technique in the design of ability of the multi-hop UW-ASNs system Pout ≤ 10−2,
future UW-ASNs. However, in adverse channel conditions, westudytheperformanceswithdifferentmaximumnumbers
the existing DCC protocols require the cooperative node to of retransmissions and block sizes of data burst for both
retransmitthedatawithfeedbacksignalineachhop.Oncein S-DCC and DCC protocols, which will help the design and
the multi-hop scenario of UW-ASNs, this will result in an applicationoftheproposedschemeinpractice.
accumulative effect of end-to-end delay due to the request Therestofthispaperisorganizedasfollows.InSectionII,
time for retransmission in each hop. Hence there still exists the network topology of multi-hop UW-ASNs, underwater
seriousend-to-enddelayproblemsintheDCCprotocol[14] acoustic channels and energy consumption for underwater
whenfurtherappliedtothemulti-hopUW-ASNs.Inorderto acoustic transmission are introduced. Section III presents
reducetheend-to-enddelayandmakeDCCmoresuitablefor theproposedS-DCCprotocolindetail,includingitsend-to-
themulti-hopscenario,inthispaperweproposeanimproved enddelayandenergyconsumptionformulti-hopUW-ASNs
schemebasedontheDCCprotocol,calledSelectiveDynamic system.Simulationandexperimentalresultsarepresentedin
CodedCooperation(S-DCC)protocolastherelaystrategyfor SectionIVandV,respectively.Finally,SectionVIconcludes
multi-hopUW-ASNs. thispaper.
Themaincontributionsofthispaperareasbellow:
1)PresentinganimprovedschemenamedS-DCCbasedon II. SYSTEMMODEL
theDCCprotocol.Intheproposedprotocol,thecooperative In this section, we present the networktopology and under-
nodes retransmit blocks actively and redundantly, and the water energy consumption model. Table 1 summarizes key
receivernodesselectivelyreceiveanddealwiththeseblocks symbolsusedthroughoutthepaper.
VOLUME7,2019 70553


![image_2_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_2/image_2_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
TABLE1. Listofkeysymbols.
FIGURE1. ANh-hopcooperativenetworkadoptingthecoded
cooperationscheme.
the transmission of the cooperative node C can only be
i
heardbytheneighboringrelaynodesR i−1 andR i.Withthis
assumption,thedatatransmissioninonehopwillnotaffect
thenexthop;
3)Thetransmissionpathispredeterminedbytheoptimal
routing algorithm for a given S-D pair, and in each hop,
thebestnodecanbeselectedasthecooperativenodeinthe
candidate nodes. The designs of optimal routing algorithm,
includingtheselectionofrelaynodesR (i=1,2,...,N −
i h
1)andcooperativenodesC i(i=1,2,...,N h−1),arebeyond
thescopeofthispaper.
Accordingtotheaboveassumptions,sinceeachhopcon-
sisting of source-relay-destination 3 nodes is predetermined
in the multi-hop network, and the transmission in each hop
willnotbereceivedbythenexthop,thedatatransmissionis
indeedcarriedoutstrictlyhopbyhop.Inthiscase,thereisno
impact between the transmission inside different hops, and
the performance analysis of the energy consumption, delay,
andoutageprobabilityforthewholenetworkcanbedivided
into independent hops. The energy consumption and end-
to-end delay of the multi-hop network are the summation
of the energy consumption and transmission delay inside
each hop, while the outage probability is calculated based
onthefactthatthenetworkwillbeoutageifanyonehopis
outage.
Fortheconvenienceofillustration,alinearuniformmulti-
hopnetwork[3]isshowninFig.1,inwhichthedistanceof
eachhopisd/N ,whered isthedistancebetweenSandD.
A. NETWORKTOPOLOGY h
However, the following discussions in this paper, including
As shown in Fig. 1, we consider a cooperative N -hop
h
the analysis on energy consumption, end-to-end delay and
UW-ASN consisting of the source node S, N -1 relay
h
outage probability performances are still valid for network
nodes, and the destination node D, with several coopera-
topologies other than linear, or for the case of different dis-
tive nodes among them. The relay can be expressed as R
i
(i = 1,2,N − 1), and the cooperative node is written as tances between the hops, as long as the above assumptions
h
C (i=1,2,N ). aresatisfied.
i h
Wehaveadoptedthefollowingassumptionsforeachhop
B. UNDERWATERENERGYCONSUMPTIONMODEL
transmissioninthenetwork:
Usually, underwater acoustic data transmission can be
1) Nodes are in half-duplex where nodes cannot transmit
describedbythepassivesonarequation.ThentheSNRatthe
andreceivedataatthesametime;
receivercanbepresentedasfollows[3],
2) As the focuses are primarily on the ARQ issues,
we assume that all the medium access control issues SNR = SL−TL−NL+DI, (1)
have been resolved. Therefore, the so-called source-relay-
destinationthreenodesineachhopareactuallyupgradedas whereSL,TL,NL andDI are,indB,thesourcelevel,trans-
R i−1-C i-R iinthemulti-hopUW-ASNsscenario.Further,it’s mission loss, noise level and directivity index respectively.
assumedthat,thetransmissionofR i−1 canonlybereceived Whenadoptingomnidirectionalhydrophones,thedirectivity
by the two neighboring relay nodes, i.e., R and R i−2; and indexissetas0.
i
70554 VOLUME7,2019


![image_3_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_3/image_3_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
Foratransmissiondistanced inmeterandfrequencyf in According to (1), (2), (6), (7) and (8), with the optimal
kHz,thetransmissionlossTLisgivenby[16] frequency f for a given d, the power P can be expressed
0 t
as
TL = k ·10log (d) +α (f) d ·10−3, (2)
th1 e0 ref10TL+NL 10+SNR0|
P =2πz 0I f=f0, (9)
where the first term is spreading loss with k represents t
thethespreadingfactor,andthesecondtermistheabsorption where SNR and z are the corresponding SNR and z in
0 0
losswithα(f)representstheabsorptioncoefficientindB/km.
practicaldesignwhenoperatingontheoptimalfrequencyf .
0
Commonly,thespreadingfactork canbesetas1.5inpracti- For the commercial hydrophone [18], it consumes about
calspreadingforunderwateracoustictransmission.Follow- onefifthofthetransmittedenergyatthereceiverforapacket.
ingThorp’sformula[17],theabsorptioncoefficientis:
Then, the energy consumed at the transmitter E and the
t
0.11f2 44f2 receiverE r canbewrittenas
α(f)= + +2.75×10−4f2+0.003. (3)
1+f2 4100+f2 l
E = P × =P ×T , (10)
t t t l
The ocean ambient noise is modeled by Gaussian statis- b
1
tics and the Power Spectral Density (PSD). Four different E = E , (11)
r t
noise sources are usually considered: turbulence, shipping, 5
wavesandthermalnoise.Theirstrengthcanberespectively wherel isthelengthofthepacketinbits,bisthebitratein
expressedas(indBreµPaperHz)[3] bps,T isthetimecostfortransmittingl bitsinsecond.
l
NL = 10logN (f)=17−30logf
t t
III. THEPROPOSEDS-DCCPROTOCALFORMUTI-HOP
NL = 10logN (f)=40+20(s−0.5)
s s UW-ASNS
+26logf −60log(f +0.03) A. SELECTIVEDYNAMICCODEDCOOPERATIVE
NL = 10logN (f)=50+7.5w(1/2) PROTOCOL
w w
Consider a burst-based transmission for the multi-hop UW-
+20logf −40log(f +0.4)
ASNsinthefollowingdiscussion.EachburstconsistsofN
bl
NL = 10log N (f)=−15+20logf, (4)
th th blocks, and we take the OFDM block as the example for
where s is the shipping activity factor, w is the wind speed analysis[14].OvertheN blblocks,weuseerasure-correction
inm/s.DefineNL (f)(i ∈ N− = {t,s,w,th}),thenthetotal channelcodefortheinter-blockencoding,whichisthefoun-
i
noiseis: dationforcodedcooperationatrelays.
Before illustrating the S-DCC protocol, we first briefly
N(f)=N t(f)+N s(f)+N w(f)+N th(f). (5) introduce the conventional stop and wait ARQ (S&W
ARQ) protocol, the cooperative ARQ (C-ARQ) proto-
ExpressedindB,thatis
col and the dynamic coded cooperation (DCC) protocol
NL =10logN(f)=10log (cid:88) 10NLi/10. (6) in [13], [15], [19]. They are illustrated in Figs. 2 (a),
i∈N− (b) and (c) respectively, where the (i-1)-th relay node
From(1),obviously,foragivenreceiverSNR 0withknown R i−1 is the transmitter, and the i-th relay node R i is the
TL and NL, the energy consumption at the transmitter can receiver. In each ‘‘R i−1-C i-R i’’ transmission unit, when
be calculated from the source level SL. And the SL is given adopting the S&W ARQ protocol, the receiver will send a
by[16] NAKsignaltothetransmitterforretransmissionrequestifit
cannot decode the blocks correctly, while it is to the coop-
I
SL =10log t , (7) erativenodewhenadoptingtheC-ARQprotocol.Therefore,
10 I
ref the C-ARQ protocol can improve the transmission success
whereI tistheintensityofthesoundemittedbythetransmit- ratesincethecooperativenodeislocatedbetweenthetrans-
ter,andthereferenceintensityI ref inunderwatersound[16] mitterandreceiver.Inthemeanwhile,itcanreducetheend-
is usually the intensity of a plane wave having an root- to-end delay because both NAK signal and retransmission
mean-square pressure equal to 1 µPa, denoted as I ref ≈ happeninashorterdistance,asshowninFig.2(b).Further
0.667×10−18 W/m2. That is related to the effective sound more,whenadoptingtheDCCprotocol,thecooperativenode
pressure,thedensityofseawater,andthepropagationveloc- only retransmits part of blocks (say N blocks) instead of
li
ityofsoundwavecinseawater.Withoutlossofgenerality, all the blocks (say N blocks) as shown in Fig. 2 (c) once
bl
weassumeaconstantspeedofc=1500m/s. retransmission occurs. It can further reduce the end-to-end
Inthecaseofcylindricalspreading,thepowerP t required delaybecauseoftheshorterretransmissiontime;meanwhile,
to achieve intensity I t at 1 meter from the source in the the N li blocks can be added to the front of N coop blocks
directionofthereceiveris[17]: for joint decoding and it can improve the performance of
decoding[13].
P =2π zI , (8)
t t
However,inDCCprotocol,aftersendingaNAKsignalto
whereP isinwattandzisthewaterdepthinmeter. the cooperative node C, the receiver R still needs to wait
t i i
VOLUME7,2019 70555


![image_4_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_4/image_4_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
decodingbycombiningtheN bl blocksfromnodeR i−1 with
thelastN blocksfromcooperativenodeC;ifitisunable
coop i
to decode correctly, the receiver node R will receive the
i
followingretransmittedN blocksfromcooperativenodeC,
li i
whichcanbeaddedtothepreviouslyavailableN blocksfor
bl
jointdecoding;ifthereceiverdecodescorrectly,itwillskip
these retransmitted N blocks and send ACK signal to the
li
transmitternodeR i−1.
Note that the cooperative node can retransmit N blocks
li
severaltimesuntilreachingthegivenmaximumretransmis-
siontime.Andthereceivermaycarryoutjointdecodingupon
thereceivedN blocks,N blocksandalltheretransmit-
bl coop
ted N blocks depending on the underwater acoustic chan-
li
nel state. However, as the underwater acoustic modem is
working on half-duplex mechanism, the cooperative node
can not receive the ACK signal from the receiver during its
retransmission of the N blocks to the receiver. Hence the
li
retransmittimecannotbesettoolarge,whichisdetermined
bytheunderwateracousticchannelstates,thelengthoftheN
li
blocks,andthedistancebetweenthecooperativenodeandthe
receivernode.Wewilladjustthisparameterbysimulationin
thefollowing.
FIGURE2. Differentcooperationschemesforeachhopinmulti-hop B. ENERGYCONSUMPTION
UW-ASNs:(a)ConventionalstopandwaitARQ(S&WARQ)protocol;
The summation of the energy consumption in each hop can
(b)CooperativeARQ(C-ARQ)protocol;(c)DynamicCodedCooperation
(DCC)protocol;(d)SelectiveDynamicCodedCooperation(S-DCC) bedescribedas
protocol.
(cid:88)Nh
E = E hop,i, (12)
total
fortheretransmissionfromnodeC.SincebothNAKsignal
i i=1
and data retransmission still occupy extra time, the receiver
where E hop,i is the energy consumed in the i-th hop. The
isinidleintheT period.Tofurthereliminatethiswaiting
wait energyconsumedintransmittingandreceivingoneblockis
time,weproposethatthecooperativenodeC iretransmitsthe representedasEblockandEblockrespectively.Whenoperating
N listeningblocksimmediatelyaftertheN cooperation tx rx
li coop in the idle mode, the energy consumed is written as E .
Idle
blocks,andthenthereceiverR cantakedifferentactionson
i Thenwecanfurtherexpresstheenergyconsumptionas:
these N blocks, depending on its instant decoding results.
li
TheproposedschemecanshortentheNAKsignal’stransmis- E tb xlock = P t ×T block
siontime,andespeciallyitcanobservablyshortentheoverall Eblock = P ×T
rx r block
end-to-end delay for the multi-hop UW-ASNs due to the E = P ×T , (13)
Idle Idle Idle
accumulatedbenefit.Asthereceiverselectivelyhandleswith
the redundant N li blocks, we name it as selective dynamic where P t, P r, P Idle, T block and T Idle are the transmission
codedcooperative(S-DCC)protocol. power, reception power, idle mode operating power, block
For the S-DCC protocol, to get a reliable transmission in transmissiontimeandidlemodeoperatingtime,respectively.
eachhop,itworksinthefollowingsteps. Besides,theenergyconsumptionoftransmittingandreceiv-
ACK/NAK
1) ACTIVE RETRANSMITTING BASED ON BURST ing an ACK or NAK signal can be expressed as E
tx
ACK/NAK
TRANSMISSION: during the listening phase, the coopera- and E respectively. In this paper, we assume the
rx
tive node C try to carry out instantaneous decoding every durationandenergyconsumptionofACKareequaltothose
i
timereceivingonemoreblockfromnodeR i−1;immediately oftheNAKbecauseofthesamelength.
after the information bits within one burst are successfully Following Section II A, the analysis of the energy con-
recovered,sayN blocks,thecooperativenodeC regenerates sumption of the whole network can be divided into each
li i
thecodedtransmissionblocks,sayN =N bl−N liblocks, independenthop.Forthei-thhop,i.e.,the‘‘R i−1-C i-R i’’unit
coop
and switches to cooperative phase and relays the data to inthemulti-hopUW-ASNsscenarioasshowninFig.2,the
node R. After this, the cooperative node C will actively totalenergyconsumptioncanbecalculatedas:
i i
retransmits the first N blocks following the N blocks
underagivenperiodofl ti ime,sayT ,asshowninco Fop ig.2(d). E hop,i =E Ri−1 +E Ci +E Ri, (14)
dyna
2) SELECTIVE RECEIVING BASED ON JOINT where E , E and E are the energy consumed at trans-
Ri−1 Ci Ri
DECODING:thereceivernodeR willfirstlycarryoutjoint mitternodeR i−1,thecooperativenodeC andreceivernode
i i
70556 VOLUME7,2019


![image_5_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_1.png)


![image_5_2](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_2.png)


![image_5_3](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_3.png)


![image_5_4](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_4.png)


![image_5_5](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_5.png)


![image_5_6](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_6.png)


![image_5_7](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_7.png)


![image_5_8](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_8.png)


![image_5_9](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_9.png)


![image_5_10](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_10.png)


![image_5_11](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_11.png)


![image_5_12](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_12.png)


![image_5_13](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_13.png)


![image_5_14](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_14.png)


![image_5_15](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_15.png)


![image_5_16](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_16.png)


![image_5_17](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_17.png)


![image_5_18](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_18.png)


![image_5_19](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_19.png)


![image_5_20](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_20.png)


![image_5_21](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_21.png)


![image_5_22](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_22.png)


![image_5_23](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_23.png)


![image_5_24](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_24.png)


![image_5_25](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_25.png)


![image_5_26](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_26.png)


![image_5_27](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_27.png)


![image_5_28](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_28.png)


![image_5_29](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_29.png)


![image_5_30](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_30.png)


![image_5_31](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_31.png)


![image_5_32](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_32.png)


![image_5_33](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_33.png)


![image_5_34](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_34.png)


![image_5_35](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_35.png)


![image_5_36](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_36.png)


![image_5_37](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_37.png)


![image_5_38](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_38.png)


![image_5_39](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_39.png)


![image_5_40](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_40.png)


![image_5_41](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_41.png)


![image_5_42](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_42.png)


![image_5_43](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_43.png)


![image_5_44](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_44.png)


![image_5_45](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_45.png)


![image_5_46](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_46.png)


![image_5_47](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_47.png)


![image_5_48](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_48.png)


![image_5_49](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_49.png)


![image_5_50](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_50.png)


![image_5_51](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_51.png)


![image_5_52](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_52.png)


![image_5_53](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_53.png)


![image_5_54](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_54.png)


![image_5_55](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_55.png)


![image_5_56](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_56.png)


![image_5_57](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_57.png)


![image_5_58](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_58.png)


![image_5_59](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_59.png)


![image_5_60](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_60.png)


![image_5_61](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_61.png)


![image_5_62](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_62.png)


![image_5_63](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_63.png)


![image_5_64](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_64.png)


![image_5_65](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_65.png)


![image_5_66](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_66.png)


![image_5_67](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_67.png)


![image_5_68](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_68.png)


![image_5_69](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_69.png)


![image_5_70](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_70.png)


![image_5_71](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_71.png)


![image_5_72](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_72.png)


![image_5_73](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_73.png)


![image_5_74](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_74.png)


![image_5_75](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_75.png)


![image_5_76](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_76.png)


![image_5_77](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_77.png)


![image_5_78](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_78.png)


![image_5_79](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_79.png)


![image_5_80](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_80.png)


![image_5_81](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_81.png)


![image_5_82](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_82.png)


![image_5_83](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_83.png)


![image_5_84](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_84.png)


![image_5_85](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_85.png)


![image_5_86](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_86.png)


![image_5_87](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_87.png)


![image_5_88](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_88.png)


![image_5_89](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_89.png)


![image_5_90](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_90.png)


![image_5_91](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_91.png)


![image_5_92](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_92.png)


![image_5_93](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_93.png)


![image_5_94](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_94.png)


![image_5_95](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_95.png)


![image_5_96](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_96.png)


![image_5_97](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_97.png)


![image_5_98](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_98.png)


![image_5_99](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_99.png)


![image_5_100](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_100.png)


![image_5_101](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_101.png)


![image_5_102](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_102.png)


![image_5_103](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_103.png)


![image_5_104](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_104.png)


![image_5_105](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_105.png)


![image_5_106](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_106.png)


![image_5_107](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_107.png)


![image_5_108](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_108.png)


![image_5_109](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_109.png)


![image_5_110](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_110.png)


![image_5_111](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_111.png)


![image_5_112](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_112.png)


![image_5_113](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_113.png)


![image_5_114](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_114.png)


![image_5_115](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_115.png)


![image_5_116](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_116.png)


![image_5_117](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_117.png)


![image_5_118](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_118.png)


![image_5_119](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_119.png)


![image_5_120](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_120.png)


![image_5_121](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_121.png)


![image_5_122](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_122.png)


![image_5_123](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_123.png)


![image_5_124](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_124.png)


![image_5_125](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_125.png)


![image_5_126](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_126.png)


![image_5_127](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_127.png)


![image_5_128](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_128.png)


![image_5_129](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_129.png)


![image_5_130](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_130.png)


![image_5_131](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_131.png)


![image_5_132](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_132.png)


![image_5_133](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_133.png)


![image_5_134](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_134.png)


![image_5_135](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_135.png)


![image_5_136](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_136.png)


![image_5_137](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_137.png)


![image_5_138](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_138.png)


![image_5_139](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_139.png)


![image_5_140](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_140.png)


![image_5_141](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_141.png)


![image_5_142](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_142.png)


![image_5_143](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_143.png)


![image_5_144](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_144.png)


![image_5_145](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_145.png)


![image_5_146](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_146.png)


![image_5_147](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_147.png)


![image_5_148](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_148.png)


![image_5_149](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_149.png)


![image_5_150](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_150.png)


![image_5_151](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_151.png)


![image_5_152](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_152.png)


![image_5_153](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_153.png)


![image_5_154](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_154.png)


![image_5_155](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_155.png)


![image_5_156](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_156.png)


![image_5_157](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_157.png)


![image_5_158](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_158.png)


![image_5_159](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_159.png)


![image_5_160](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_160.png)


![image_5_161](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_161.png)


![image_5_162](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_162.png)


![image_5_163](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_163.png)


![image_5_164](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_164.png)


![image_5_165](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_165.png)


![image_5_166](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_166.png)


![image_5_167](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_167.png)


![image_5_168](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_168.png)


![image_5_169](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_169.png)


![image_5_170](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_170.png)


![image_5_171](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_171.png)


![image_5_172](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_172.png)


![image_5_173](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_173.png)


![image_5_174](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_174.png)


![image_5_175](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_175.png)


![image_5_176](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_176.png)


![image_5_177](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_177.png)


![image_5_178](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_178.png)


![image_5_179](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_179.png)


![image_5_180](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_180.png)


![image_5_181](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_181.png)


![image_5_182](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_182.png)


![image_5_183](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_183.png)


![image_5_184](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_184.png)


![image_5_185](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_185.png)


![image_5_186](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_186.png)


![image_5_187](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_187.png)


![image_5_188](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_188.png)


![image_5_189](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_189.png)


![image_5_190](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_5/image_5_190.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
R,respectively.Inparticular,weassumethetransmitternode When j = 0, it means that the receiver can not decode
i
R i−1 transmits a packet comprising N bl blocks data for T x correctly after receiving N coop blocks and thus require the
timesintotal,invokingatotalofT cooperationprocessesin cooperativeN datablocksforjointdecoding.
x li
thecooperativenodeC,untilthepacketissuccessfullydeliv- SincethereceivernodeR receivestheN blocksfromthe
i i bl
eredtothereceivernodeR i;duringeachcooperationprocess, transmitternodeR i−1 andN coop blocksfromthecooperative
suchastheT -thcooperationprocess,thecooperativenodeC nodeC atthesametime,andthedurationtimeofN blocks
x i i bl
retransmitsC timesoftheN blocks,untilthereceivernode islongerthanthatofN blocks,wecanonlycalculatethe
x li coop
R successfullydecodedalltheN blocks.WhenT =uand duration time of N blocks in (19). That is why the energy
i bl x bl
C =v,(14)canbewrittenas consumption of receiving the N blocks do not show up
x coop
in(19).
E hop,i(cid:12) (cid:12) (cid:12)CTx x= =u =E Ri−1,i(cid:12) (cid:12) (cid:12)CTx x= =u +E Ci,i(cid:12) (cid:12) (cid:12)CTx x= =u +E Ri,i(cid:12) (cid:12) (cid:12)CTx x= =u v. Aboveall,plug(17),(18)and(19)into(15),fortheS-DCC
v v v
(15) protocolinthei-thhop,wehave:
proF bu ar bth ile itr ymo thre a, fw oe ade sfi ucn ce esP sfr u{ lT x de= livu e, rC yx it= tav k} esto Tbe =th ue E S−DCC,i(cid:12) (cid:12) (cid:12)CTx x= =u
t r v
x
times packet transmissions from the transmitter, and the = E Ri−1,i(cid:12) (cid:12) (cid:12)CTx x= =u +E Ci,i(cid:12) (cid:12) (cid:12)CTx x= =u +E Ri,i(cid:12) (cid:12) (cid:12)CTx x= =u
v v v
final delivery coming after C x = v times cooperation (cid:0) N +N (cid:1) Eblock +(N +N )Eblock 
h {0a ,v 1e ,b 2e ,e ·n ··r ,e Mqu mir ae xd },, ww hit eh reu M∈ max{1 r, e2 p, re3 s, e· n· t· s, t∞ he} ma an xd imv um∈ =u +vb (cid:16)l liEc xo lo op ck+t Ex aCC(cid:17)l +i xCb Kl /NAr Kx xCK/NAK
N tb dS y− nD E rA +E tA
transmission times of the cooperative node C i. Let E hop,i ∈ +ERi−1+ECi +ERi 
(cid:8) E S−DCC,i,E C−ARQ,i,E DCC,i(cid:9) denote three different proto- Idle Idle Idle (21)
cols,thenwehavethefinalexpressionofenergyconsumption
as: Similarly,fortheothertwocooperativeprotocols,wehave
(22)and(23),asshownatthetopofthenextpage,where
(cid:88)∞ M (cid:88)max
E hop,i = E hop,i(cid:12) (cid:12) (cid:12)CTx x= =u ×Pr{T x =u,C x =v}, (16) E dD yC naC =(cid:16) E tb xlock +E rb xlock(cid:17) N li+E tA xCK/NAK +E rA xCK/ANK
u=1 v=0 v
whereE hop,i ∈(cid:8) E S−DCC,i,E C−ARQ,i,E DCC,i(cid:9) and (24)
Therefore,with(21),(22)and(23)inhand,wecanuse(16)
E hop,i(cid:12) (cid:12) (cid:12)CTx x= =u v to calculate the energy consumption for the three different
(cid:26) (cid:27) protocols.
∈ E S−DCC,i(cid:12) (cid:12) (cid:12)CTx x= =u v,E C−ARQ,i(cid:12) (cid:12) (cid:12)CTx x= =u v,E DCC,i(cid:12) (cid:12) (cid:12)CTx x= =u ,
v
C. END-TO-ENDDELAY
correspondingly.
Similar to the derivation of energy consumption, we will
Nowlet’sderivetheenergyconsumptionofS-DCCproto-
brieflypresentthederivationoftheend-to-enddelayforthe
col E S−DCC,i first. When T x = u and C x = v, the energy
three different protocols in the following. The aggregated
consumption of the transmitter node R i−1 to transmit N bl
delayofeachhopcanbepresentedas
blockscanbegivenby:
E Ri−1,i(cid:12) (cid:12) (cid:12)CTx x= =u v = uE td xata+(u−1)E rN xAK+E rA xCK+uE IR di l− e1 T total =(cid:88)Nh T hop,i (25)
= u(cid:16) N Eblock +EACK/NAK +ERi−1(cid:17) (17) i=1
bl tx rx Idle Due to the independence between hops, we focus on the
whereEdataistheenergyconsumptionoftransmittingtheN delay analysis of one hop. For the i-th hop, the end-to-end
tx bl
blocksdata. delaycomprisingthepropagationdelayandthetransmission
Then,theenergyconsumptionatthecooperativenodeC latency:
i
andreceivernodeR canbesimilarlypresentedas:
i T hop,i =T pro,i+T tra,i (26)
E Ci,i(cid:12) (cid:12) (cid:12)CTx x= =u v where the propagation delay T pro,i is related to the retrans-
= u(cid:16) N Eblock +N Eblock +vN Eblock +ECi (cid:17) (18) missiontime,theend-to-enddistance,thesoundvelocityin
li rx coop tx li tx Idle water, and different cooperation protocols. In each hop, let
E =Ri, ui(cid:12) (cid:12) (cid:16)CTx N= bu T Nop hur ·co .db Fe ree lq hu ea itl cyt ao eth owe dr tee fla fefy r- erto no- tr de el ia ty nd ci es mt sa in bsc ese wnd e,i ev nii .d he od pTb ,y Tt ph re
(cid:12) x = v lE rb xlock +vE dS y− nD aCC +E tA xCK/NAK +E IR di le(cid:17) , (19) s d n ov to c sin fa ir o n st r aa n s i to e ., sp ro =
o
where and d/N h should be modified as T pro,i and d i(the distance
(cid:40) in the i-th hop), respectively. And T tra,i is the transmission
N Eblock, j=0
ES−DCC = li rx (20) time of a burst packet in each hop. It is related to the block
dyna 0, j=1 time duration and the number of blocks. Denote T as one
bl
VOLUME7,2019 70557


![image_6_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_6/image_6_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
E C−ARQ,i(cid:12) (cid:12) (cid:12)CTx x= =u = u  (cid:0) E tb +xlo Eck AC+ K2 /NE Arb Kxloc +k(cid:1) EN Ab Cl K+ /Nv A(cid:20) K+ +E(cid:0) tE A ExCtb Rx Kl io −/c 1Nk A ++ K EE + Crb x il Eoc rA +k xC(cid:1) K EN / Rb Nl iAK(cid:21)  (22)
v 
tx rx Idle Idle Idle
(cid:0) N +N (cid:1) Eblock +(N +N )Eblock
bl coop tx bl li rx
E (cid:12) (cid:12)Tx =u = u  +vE dD yC naC +E tA xCK/NAK +E rA xCK/NAK   (23)
DCC,i(cid:12) +ERi−1 +ECi +ERi
(cid:12)Cx =v
(cid:12) Idle Idle Idle
block time-duration, then T tra = N blT bl for one transmis- IV. NUMERICALRESULTS
sion. Assume the ACK, NAK signal duration is T ck. In the A. SIMULATIONSETUP
following,letT hop,i ∈ (cid:8) T C−ARQ,i,T DCC,i,T S−DCC,i(cid:9) denote For the N h-hop UW-ASNs network, let N h = 5, and the
thedelaycorrespondingtothreedifferentprotocols. distance in each hop is d/N = 2 km. In each burst packet,
h
DefineT str andT dec asthestatetransitiondelay,thenode let the transmission data burst size be N bl = 20 blocks
processing time, respectively. Synchronizing the reception codedoverI =10informationblocks,thentheinformation
bl
blockshasbeenillustratedin[13].Thus,accordingtoFig.2, rate is r = 0.5 bit/symbol. The OFDM parameters of the
let T x = u and C x = v, for the C-ARQ protocol, DCC transmitter are the same as those in [20], such as subcarrier
protocolandS-DCCprotocol,wecanderivethat number K = 1024, center frequency f = 10 kHz. We use
c
the quasi-static fading underwater acoustic channel model,
T C−ARQ,i(cid:12) (cid:12) (cid:12)CTx x= =u w 50he tar pe sth ine tm heul bti a- sp ea bth anc dh [a 2n ]n ,e [l 1s 4a ]r .e Wra itn hd oo um tll oy sg se on fe gra et ne ed raw lii tt yh
v ,
(cid:20) 2T +T +v(cid:0) T +T +T +2T (cid:1)(cid:21)
=u pro tra pro tra ck str (27) in the ‘‘R i−1-C i-R i’’ unit, we set the transmission times of
+T +2T
ck str R i−1isonlyonce,andthemaximumnumberoftransmissions
T DCC,i (cid:20)(cid:12) (cid:12) (cid:12)CT 2x T= =u io .f e.t ,h {e uc ,o Mo mp ae xr }at =ive {1n ,o 1d }e .C Thi ii ss ia sls to heo gn ee nd eu rari ln pg arth ames ei tm eru sl ea tt ti io nn g,
x v
+T +v(cid:0) T +T +T +2T (cid:1)(cid:21)
=u +Tpro +2Ttra pro dyna ck str (28) except during the study of impact of different M max values.
ck str Inaddition,toevaluatetheenergyconsumptionandend-to-
T S−DCC,i(cid:12) (cid:12) (cid:12)CTx x= =u enddelay,weuseMonteCarlomethodtoobtaintheresults
v
(cid:20) 2T +T +v(cid:0) T +T (cid:1)(cid:21) accordingto(12)and(25).
=u pro tra dyna dec (29) Instead of a practical code, we assume the erasure-
+T +2T
ck str correctioncodesarecapacity-achievingcodesthusthemutual
information (MI) can be adopted to calculate the outage
where T is the dynamic transmission time for the coop-
dyna
probability of the transmission, which can indicate whether
erative node to retransmit the blocks in the DCC or S-DCC
a packet can be decoded correctly at the receiver. For
protocol,andcanbeexpressedas
the node-to-node transmission with K OFDM sub-carriers,
an outage occurs if the total MI at the destination is
T =N T (30)
dyna li bl
lower than the information rate r, which can be expressed
as:
Introducing the Pr{T =u,C =v}, we have the final
x x
expressionofend-to-enddelayas Pout = Pr{MI <r}
 
K/2−1
T hop,i =(cid:88) u∞ =1M (cid:88) v=ma 0x T hop,i(cid:12) (cid:12) (cid:12)CTx x= =u ×Pr{T x =u,C x =v} (31) = Pr K1 k=(cid:88) −K/2log 2(cid:16) 1+|H[k]|2·E s(cid:14) N 0(cid:17) <r ,
v
(32)
whereT hop,i ∈(cid:8) T C−ARQ,i,T DCC,i,T S−DCC,i(cid:9) and
where H[k] is the channel complex equivalent factor at
(cid:14)
the k-th subcarrier, and E N is the SNR at the receiver
T hop,i(cid:12) (cid:12) (cid:12)CTx x= =u v node. s 0
(cid:26) (cid:27) Specifically, for the S-DCC protocol, in the i-th hop,
∈ T C−ARQ,i(cid:12) (cid:12) (cid:12)CTx x= =u v,T DCC,i(cid:12) (cid:12) (cid:12)CTx x= =u v,T S−DCC,i(cid:12) (cid:12) (cid:12)CTx x= =u , theoutageprobabilitycanbecalculatedin(33),asshownat
v
the bottom of the next page where H denotes the channel
sd
correspondingly. frequency response between the source and the destination,
The theoretical calculation of Pr{T =u,C =v} is H denotes the channel frequency response between the
x x rd
beyondthescopeofthispaper,hencecomputersimulations cooperativenodeandthedestination,andj = 0or1.When
areusedinstead. j=0,itregressestoDCCprotocol;whenj=1,itmeansthat
70558 VOLUME7,2019


![image_7_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_7/image_7_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
the receiver can not decode correctly after receiving N
coop
blocks and thus requires the cooperative N data blocks for
li
jointdecoding.
In the multi-hop network where the information is trans-
mitted hop by hop and the signal transmission in one hop
willnotaffecttheotherhops,eachhopwillhaveindependent
probabilityofoutageandthenetworkoutagewillhappenif
anyhopisoutage.Thentheoutageprobabilityofthewhole
N -hopsystemis
h
=1−(cid:89)Nh
Pout (cid:0) 1−Pout (cid:1) (34)
S−DCC S−DCC,i
i=1
B. SIMULATIONRESULTS
1) IMPACTOFDIFFERENTPROTOCOLS
Fig. 3 (a) demonstrates the overall outage probability of
S-DCC protocol and other protocols. We can see that the
proposed S-DCC protocol is slightly better than C-ARQ
protocol and overlaps with DCC protocol, and all of them
outperformtheS&WARQprotocol.AsshowninFig.3(b),
the proposed S-DCC protocol has the minimum end-to-end
delay among these protocols. Especially, for Pout ≤ 10−2
(P(cid:14)σ2 = 47 − 48dB, where P(cid:14)σ2 := SL − NL is
w w
the transmission SNR in dB), the performance of end-to-
end delay of S-DCC is better than that of DCC because of
thenewretransmissionmechanismforS-DCC.Specifically,
the S-DCC protocol can eliminate the feedback signal from
the R node to C node and hence reduces the overall end-
i i
to-end delay in retransmission. However, performances of
FIGURE3. Performancecomparisonofseveralnetworkschemes:
S-DCC and DCC become close at high transmission SNR (a)Overalloutageprobability;(b)End-to-enddelay.
region, and this is because no more retransmissions are
neededforbothofthemasthetransmissionSNRincreases.
Therefore, the proposed S-DCC protocol can achieve good thecomparisonofthethreecooperativeprotocolsinthedata
outage performance while reducing the end-to-end delay, transmissioninthefollowingdiscussions.
relative to existing protocols. Since (A) the outage perfor- To clearly understand energy consumption of the three
manceofS&WARQprotocolismuchworsethantheother cooperative protocols, Fig. 4 (a) shows the energy con-
three cooperative protocols, which is extremely detrimental sumption results. It can be found that in the low trans-
tothemulti-hopUW-ASNsscenario.Andallthecooperative mission SNR region (46-48 dB), the energy consumption
protocolsshouldhavethesameenergyconsumptionandtime of S-DCC is slightly lower than the other two protocols,
delayhappenedinthecooperativenodeselectionstage;(B)in but with the increase of transmission SNR, the energy con-
a relative static network (as required by DCC, because it sumption of S-DCC increases more than DCC. This is
needs the exact distance information between the 3 nodes), because that the receiver only needs one transmission to
theenergyconsumptionandtimedelayhappenedinthecoop- successfully decode the information without the coopera-
erativenodeselectionstageshouldbeinsignificantcompared tive node’s retransmission at high SNR region. Hence for
withthedatatransmission,wewillskipS&WARQandwill the S-DCC, the receiver does not use the extra N blocks
li
notincludetheenergyconsumptionandtimedelayhappened transmitted by cooperative node, causing additional energy
inthecooperativenodeselectionstage.Instead,wefocuson consumption.
Pout = Pr{MI <r}
S−DCC,i
 
Pr K1 k k= =(cid:88)K −/ K2− /21(cid:20) +N Nl lo ig g(cid:0) 21 (cid:0)+ 1+|H Hd[ rk d] [| k2 ]|· 2E E(cid:14) sN N(cid:1) 0+ N cooplog 2(cid:0) 1+|H sd[k]+H rd[k]|2·E s(cid:14) N 0(cid:1)(cid:21) bl
= b jl lo2 |s ·s (cid:14)0 <rN ,
(cid:1)
(33)
VOLUME7,2019 70559


![image_8_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_8/image_8_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
FIGURE4. Energyconsumptionsofseveralcooperativeschemes:
(a)Energyconsumption;(b)Energyconsumptioncomparison.
Set the target outage probability of the three cooperative
protocolstobePout ≤10−2,thecorrespondingtransmission
SNRisabout48dBaccordingtoFig.3(a).Fig.4(b)shows
the comparison of energy consumptions at the transmission
SNR around 48 dB. When meeting the outage probability
demand,theenergyconsumptionofS-DCCismoreeconom-
ical than the other two schemes at low transmission SNR
region.
2) IMPACTOFCOOPERATIVETRANSMISSIONTIMES
In (16) and (31), let M ∈ {1,2,3,4}, u = 1, then the
max
maximumnumberofcooperativenodetransmissiontimesis FIGURE5. Theimpactofthemaximumnumberofretransmissionson
systemperformance:(a)Overalloutageprobability;(b)End-to-end
between1and4.Toanalyzetheimpactofmaximumnumber delay;(c)Energyconsumption.
ofretransmissions,weshouldensurethatthelinkbetweenthe
transmitter and the cooperative node cannot be interrupted. notincreaseinfinitelywiththemaximumnumberofretrans-
Therefore the cooperative node is closer to the transmitter missionsincreasing.Inaddition,bothS-DCCandDCChave
than to the receiver in each hop. As shown in Fig. 5(a), similar overall outage probability under the same setting of
with the maximum number of retransmissions increasing, maximumnumberofretransmissions.
the possibility of the receiver decodes correctly increases. Set the target outage probability to be Pout ≤10−2,
Specifically, the cases of M = 2 and M = 3 have the end-to-end delay and the energy consumption of these
max max
about 0.5 dB and 0.7 dB gain, respectively, compared with two schemes are shown in Fig. 5 (b) and Fig. 5 (c). From
M = 1. The overall outage probability of M = 3 Fig.5(b),wecanseethatwiththenumberofretransmissions
max max
and M = 4 is similar. Thus, the outage probability will increasing,theend-to-enddelayofDCCorS-DCCincreases
max
70560 VOLUME7,2019


![image_9_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_9/image_9_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
FIGURE6. Theimpactofdataburstsizeonsystemperformance: FIGURE7. SeatestdataofunderwateracousticchannelfortheXiamen
(a)End-to-enddelay;(b)Energyconsumption. WuyuanBay:(a)Thesoundspeedprofile;(b)Channelimpulse
response.
slightly, and the end-to-end delay of S-DCC is always less V. EXPERIMENTALRESULTS
than that of DCC. From Fig. 5 (c), the energy consumption TofurthertesttheperformanceofS-DCC,thetestdatafrom
of S-DCC increases with the number of retransmissions, Xiamen Wuyuan bay on May 8, 2014, which lies in the
while the case for DCC is the opposite. When M max = 1, northern part of Xiamen, Fujian, China, are used to set up
the energy consumption of S-DCC is slightly smaller than the underwater acoustic channel model. The depth of the
the DCC, but when M max = 2, the energy of S-DCC is transmitter and the receiver is 3 m and 4 m, respectively.
consumed by more than 10% compared with DCC. This is The distance between them is 903 m. The detection signal
becauseathightransmissionSNRregion,DCConlyrequests is the LFM signal, whose duration is 24 ms and frequency
retransmission from the cooperative node as needed, while rangeis20-22kHz.Thesamplingfrequencyis80kHz,and
S-DCCmayretransmitunnecessarycooperativeblockswith- there is a 12 ms guard interval after detection signal. Fig. 7
out considering the receiver’s decoding results and result in (a) shows the sound speed profile of Xiamen Wuyuan Bay,
the energy waste. Therefore, at the high transmission SNR Fig.7(b)presentsthechannelimpulseresponseofWuyuan
region,M max =1isusuallyenoughforS-DCCprotocol. Bayunderwateracousticchannel,whichhave8multi-paths
andthemaximumdelayisapproximately12.5ms.Theresults
3) IMPACTOFDATABURSTSIZE aretestedinlevel3seastate.
Next,weinvestigatetheimpactofthedataburstsizeinunit Table2showstheperformancecomparisonofthesethree
of block on the end-to-end delay and energy consumption protocols for Wuyuan Bay sea test channel. As expected,
for DCC and S-DCC, where the information rate is fixed theS-DCCoutperformsbothC-ARQandDCCprotocolsat
at 0.5 bit/symbol. The results with target outage probability lower transmission SNR region (the cases of 39.96 dB and
performance are shown in Fig. 6. We can see that S-DCC 40.96 dB). As the transmission SNR increases (the cases
stilloutperformsDCCforanysizesettingofdatablock.This of41.96dBand42.96dB),oncethedecodingonthereceiver
is because in S-DCC, limited direct retransmission of the doesnotneedthecooperativenode’sretransmissionanymore,
cooperativeblockseliminatesthewaitingtimeofthereceiver, S-DCC does not have the advantage in end-to-end delay,
andlesstransmissionoffeedbacksignalreducestheenergy and its energy consumption is increasing rapidly. This is
consumption. consistentwiththepreviousanalysis.
VOLUME7,2019 70561


![image_10_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_10/image_10_1.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
TABLE2. Resultsbasedonseatestdatachannel. [8] G.Al-Habian,A.Ghrayeb,M.Hasna,andA.Abu-Dayya,‘‘Threshold-
basedrelayingincodedcooperativenetworks,’’IEEETrans.Veh.Technol.,
vol.60,no.1,pp.123–135,Jan.2011.
[9] Q.Li,S.Ting,andC.K.Ho,‘‘Ajointnetworkandchannelcodingstrategy
forwirelessdecode-and-forwardrelaynetworks,’’IEEETrans.Commun.,
vol.59,no.1,pp.181–193,Jan.2011.
[10] J. Castura and Y. Mao, ‘‘Rateless coding for wireless relay channels,’’
IEEETrans.WirelessCommun.,vol.6,no.5,pp.1638–1642,May2007.
[11] K.KumarandG.Caire,‘‘Codinganddecodingforthedynamicdecode
and forward relay protocol,’’ IEEE Trans. Inf. Theory, vol. 55, no. 7,
pp.3186–3205,Jul.2009.
[12] K.Ishibashi,K.Ishii,andH.Ochiai,‘‘Dynamiccodedcooperationusing
multipleturbocodesinwirelessrelaynetworks,’’IEEEJ.Sel.TopicsSignal
Process.,vol.5,no.1,pp.197–207,Feb.2011.
[13] Y. Chen, Z.-H. Wang, L. Wan, H. Zhou, S. Zhou, and X. Xu,
‘‘OFDM-modulated dynamic coded cooperation in underwater acous-
tic channels,’’ IEEE J. Ocean. Eng., vol. 40, no. 1, pp. 159–168,
Jan.2015.
[14] Y.Chen,X.Xu,S.Zhou,H.Su,andL.Zhang,‘‘Dynamiccodedcoop-
erativeARQformulti-hopunderwateracousticnetworks,’’inProc.IEEE
OCEANSTAIPEI,Apr.2014,pp.1–5.
[15] A.Ghosh,J.-W.Lee,andH.-S.Cho,‘‘Throughputandenergyefficiency
of a cooperative hybrid ARQ protocol for underwater acoustic sensor
networks,’’Sensors,vol.13,no.11,pp.15385–15408,Nov.2013.
[16] R. J. Urick, Principles of Underwater Sound. Los Altos, CA, USA:
PeninsulaPub,1983.
VI. CONCLUSION [17] L.M.BrekhovskikhandY.P.Lysanov,FundamentalsofOceanAcoustics.
In this paper, we investigate the improved dynamic coded NewYork,NY,USA:Springer,1982.
[18] (2007). LINKQUEST INC. Underwater Acoustic Modem. [Online].
cooperative protocol named as S-DCC for multi-hop
Available:http://www.linkquest.com
UW-ASNs in terms of end-to-end delay and energy con- [19] J.-W. Lee and H.-S. Cho, ‘‘A cooperative ARQ scheme for multi-hop
sumption. Compared with S&W ARQ, C-ARQ and DCC underwateracousticsensornetworks,’’inProc.IEEESymp.Underwater
Technol. Workshop Sci. Submarine Cables Rel. Technol. (SSC), Tokyo,
protocols, numerical results show that the proposed S-DCC
Japan,Apr.2011,pp.1–4.
protocolcanachievedecentoutageperformancewhilereduc- [20] H.Yanetal.,‘‘DSPbasedreceiverimplementationforOFDMacoustic
ingend-to-enddelaybyselectivecooperation,withoutextra modems,’’Phys.Commun.,vol.5,no.1,pp.22–32,Mar.2012.
energy consumption. Particularly, the S-DCC is a feasible
cooperativestrategyforlowtransmissionSNRcases.
YOUGAN CHEN (S’12–M’13) received the
B.S. degree in communication engineering from
ACKNOWLEDGMENT
Northwestern Polytechnical University (NPU),
The authors would like to thank Mr. Shenqin Huang and Xi’an, China, in 2007, and the Ph.D. degree in
Mr. Jianming Wu from Xiamen University for their contri- communicationengineeringfromXiamenUniver-
butionstothediscussionofthisresearch.KeyLaboratoryof sity(XMU),Xiamen,China,in2012.
He visited the Department of Electrical and
Underwater Acoustic Communication and Marine Informa-
Computer Engineering, University of Connecti-
tionTechnologyandShenzhenResearchInstituteofXiamen cut (UCONN), Storrs, CT, USA, from 2010 to
Universitycontributedequallytothiswork. 2012. He has been an Assistant Professor with
the Department of Applied Ocean Physics and Engineering, XMU, since
2013.Hisresearchinterestsincludecommunicationsandsignalprocessing,
REFERENCES currentlyfocusingonchannelcodingandcooperativecommunicationsfor
[1] S.M.Ghoreyshi,A.Shahrabi,T.Boutaleb,andM.Khalily,‘‘Mobiledata underwateracousticchannels.
gatheringwithhop-constrainedclusteringinunderwatersensornetworks,’’ Dr. Chen has served as the Technical Reviewer for many journals and
IEEEAccess,vol.7,pp.21118–21132,2019. conferences,suchastheIEEEJOURNALOFOCEANICENGINEERING,theIEEE
[2] S. Jiang, ‘‘On reliable data transfer in underwater acoustic networks: TRANSACTIONSONCOMMUNICATIONS,theIEEEACCESS,Sensors,IETCommuni-
Asurveyfromnetworkingperspective,’’IEEECommun.SurveysTuts., cations,andACMWUWNetConference.Hehasbeenappointedtoa3-year
vol.20,no.2,pp.1036–1055,2ndQuart.2018. termasAssociateEditorinIEEEAccesseffectiveMay2019.Heservedasa
[3] W. Zhang, M. Stojanovic, and U. Mitra, ‘‘Analysis of a linear multi- SecretaryfortheIEEEICSPCC2017.HereceivedTechnologicalInvention
hopunderwateracousticnetwork,’’IEEEJ.Ocean.Eng.,vol.35,no.4, AwardofFujianProvince,China,in2017.
pp.961–970,Oct.2010.
[4] M.Stojanovic,‘‘Ontherelationshipbetweencapacityanddistanceinan
underwateracousticcommunicationchannel,’’ACMSIGMOBILEMobile
XIAOTINGJINreceivedtheB.S.degreeinmarine
Comput.Commun.Rev.,vol.11,no.4,pp.34–43,Oct.2007.
technologyandtheM.S.degreeinmarinephysics
[5] M.Zorzi,P.Casari,N.Baldo,andA.F.Harris,‘‘Energy-efficientrouting
fromXiamenUniversity(XMU),Xiamen,China,
schemesforunderwateracousticnetworks,’’IEEEJ.Sel.AreasCommun.,
vol.26,no.9,pp.1754–1766,Dec.2008. in 2014 and 2017, respectively. She was with
[6] M.FelembanandE.Felemban,‘‘Energy-delaytradeoffsforunderwater XMU,andiscurrentlywiththeFujianProvincial
acoustic sensor networks,’’ in Proc. 1st Int. Black Sea Conf. Commun. DepartmentofOceanandFisheries.Herresearch
Netw.(BlackSeaCom),Jul.2013,pp.45–49. interestsincludechannelcoding,cooperativecom-
[7] S. Al-Dharrab, M. Uysal, and T. M. Duman, ‘‘Cooperative underwa- municationsforunderwateracousticchannels,and
ter acoustic communications,’’ IEEE Commun. Mag., vol. 51, no. 7, wirelesscommunicationandnavigationforfishing
pp.146–153,Jul.2013. vessel.
70562 VOLUME7,2019


![image_11_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_11/image_11_1.png)


![image_11_2](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_11/image_11_2.png)


![image_11_3](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_11/image_11_3.png)


Y.Chenetal.:S-DCCCommunicationsforMulti-HopUW-ASNs
LEI WAN (M’18) received the B.S. degree in XIAOMEIXUreceivedtheB.S.,M.S.,andPh.D.
electronic information engineering from Tianjin degreesinmarinephysicsfromXiamenUniversity
University(TJU),Tianjin,China,in2006,theM.S. (XMU),Xiamen,China,in1982,1988,and2002,
degreeinsignalandinformationprocessingfrom respectively.
theBeijingUniversityofPostsandTelecommu- She was a Visiting Scholar with the Depart-
nications (BUPT), Beijing, China, in 2009, and ment of Electrical and Computer Engineering,
the Ph.D. degree in electrical engineering from Oregon State University, Corvallis, OR, USA,
UniversityofConnecticut(UCONN),Storrs,CT, from1994to1995.ShevisitedtheDepartmentof
USA,in2014. ElectricalandComputerEngineering,University
HeiscurrentlyanAssociateProfessorwiththe ofConnecticut(UCONN),Storrs,CT,USA,asa
CollegeofUnderwaterAcousticEngineering,HarbinEngineeringUniver- SeniorVisitingScholar,in2012.SheiscurrentlyaFullProfessorwiththe
sity (HEU), Harbin, China. His research interests include the algorithm DepartmentofAppliedMarinePhysicsandEngineering,XMU.Herresearch
design,systemdevelopment,andperformanceanalysisforhighspeedunder- interestsincludemarineacoustics,underwateracoustictelemetryandremote
wateracousticcommunicationsystems. control,underwateracousticcommunication,andsignalprocessing.
Dr. Wan has served as the Technical Reviewer for many journals and
conferences.HereceivedtheIEEECommunicationsSociety’sExemplary
ReviewerAwardfortheIEEECOMMUNICATIONSLETTERS,in2013.
XIAOKANGZHANGreceivedtheB.S.andPh.D.
degreesinmarinephysicsfromXiamenUniversity
(XMU),Xiamen,China,in2005and2010,respec-
tively.From2010to2012,hewasaPostdoctoral
Research Associate with the Center of Environ-
mental Science and Engineering, XMU. He has
been a Senior Engineer with the Department of
AppliedMarinePhysicsandEngineering,XMU,
since2012.Hisresearchinterestincludesunder-
wateracousticcommunications.
VOLUME7,2019 70563


![image_12_1](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_12/image_12_1.png)


![image_12_2](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_12/image_12_2.png)


![image_12_3](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_12/image_12_3.png)


![image_12_4](https://doc2markdown.com/images/20260608/bbbf557e-d370-47e0-b573-fac708b19ab6/page_12/image_12_4.png)


