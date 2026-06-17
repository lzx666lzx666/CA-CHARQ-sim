import simpy
import math
import random
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from collections import defaultdict

# ==========================================
# 1. 核心参数 & 协议开关
# ==========================================
SOUND_SPEED  = 1500.0
BIT_RATE     = 1200.0
BITS_PER_CHUNK = 16
CHUNKS_SYS     = 25
CHUNKS_PARITY_MAX = 19
TX_POWER_W     = 15.0
MAX_HOP_RETRYS     = 5
MAX_MERGE_ATTEMPTS = 8
T_MAX_WINDOW    = 1.5
T_PROTECTION_GAP = 0.2
INITIAL_ENERGY = 10000.0
RICIAN_K = 0.0
HOP_DIST = 600.0
NUM_HOPS = 5
N_HELPERS_PER_HOP = 3
FREQ_KHZ       = 20.0

RV_SLICES = {0: (0, 25), 1: (25, 31), 2: (25, 38), 3: (25, 44)}

def thorp_alpha(f_khz):
    f = f_khz
    return 0.11*f*f/(1+f*f) + 44*f*f/(4100+f*f) + 2.75e-4*f*f + 0.003

def compute_tl(d_m, f_khz):
    spread = (d_m / 1000.0) ** 1.5
    alpha = thorp_alpha(f_khz)
    absorb = 10.0 ** (alpha * d_m / 1000.0 / 10.0)
    return spread * absorb + 1e-20
CHARQ_FEC = [(25, 33), (33, 44)]
CHARQ_FEC_SIZE = [8, 11]

PROTO_SW_ARQ = "S&W ARQ"
PROTO_CARQ   = "C-ARQ"
PROTO_CHARQ  = "C-HARQ"
PROTO_CA     = "CA-CHARQ"

W1, W2, W3 = 0.40, 0.25, 0.35
NACK_MAX = 3

ENABLE = {
    'SW_ARQ': True,
    'CARQ':   True,
    'CHARQ':  True,
    'CA':     True,
}

def compute_packet_per(soft_buffer):
    active = soft_buffer > 0
    n_active = int(np.sum(active))
    if n_active < 25:
        return 1.0
    gamma = soft_buffer[active]
    ser_symbol = 1.0 - (1.0 - 0.5 * np.array([math.erfc(math.sqrt(max(g, 0) / 2.0)) for g in gamma]))**2
    n_sym = n_active * 8     # 16 bits/chunk = 8 QPSK symbols
    n_info_sym = 200          # 25 chunks × 8 symbols
    t_base = 43               # rate 0.70 baseline FEC
    t_extra = max(0, (n_sym - n_info_sym) // 2)
    t_correct = t_base + t_extra
    expected = np.sum(ser_symbol) * 8.0
    if expected <= t_correct:
        return 1e-6
    var_e = np.sum(ser_symbol * (1.0 - ser_symbol)) * 8.0
    z = (t_correct + 0.5 - expected) / np.sqrt(max(var_e, 1e-10))
    per = 1.0 - 0.5 * (1.0 + math.erf(z / np.sqrt(2.0)))
    return float(np.clip(per, 1e-8, 1.0 - 1e-8))

def rs_confidence(soft_buffer):
    per = compute_packet_per(soft_buffer)
    if per < 0.05:    return per, 3
    elif per < 0.30:  return per, 2
    elif per < 0.70:  return per, 1
    else:             return per, 0

# ==========================================
# 3. 统计中心
# ==========================================
class StatsTracker:
    def __init__(self, sim_time):
        self.sim_time = sim_time
        self.total_transmitted_chunks = 0
        self.total_data_tx = 0
        self.total_nack_tx = 0
        self.total_ack_tx = 0
        self.total_energy = 0.0
        self.e2e_delays = []
        self.e2e_success_count = 0
        self.e2e_drop_count = 0
        self._pkt_fate = {}

    def record_tx(self, n_chunks):  self.total_transmitted_chunks += n_chunks
    def record_data_tx(self):       self.total_data_tx += 1
    def record_nack_tx(self):       self.total_nack_tx += 1
    def record_ack_tx(self):        self.total_ack_tx += 1
    def record_energy(self, joules): self.total_energy += joules

    def e2e_success(self, pid, delay):
        if pid not in self._pkt_fate:
            self._pkt_fate[pid] = 'success'
            self.e2e_success_count += 1
            self.e2e_delays.append(delay)

    def e2e_drop(self, pid):
        if pid not in self._pkt_fate:
            self._pkt_fate[pid] = 'dropped'
            self.e2e_drop_count += 1

    def get_throughput(self):
        return (self.e2e_success_count * CHUNKS_SYS) / max(self.sim_time, 1.0) if self.e2e_success_count > 0 else 0.0

    def get_avg_delay(self):
        return float(np.mean(self.e2e_delays)) if self.e2e_delays else float('nan')

    def get_delay_std(self):
        return float(np.std(self.e2e_delays)) if self.e2e_delays else float('nan')

    def get_overhead(self):
        useful = self.e2e_success_count * CHUNKS_SYS
        return (self.total_transmitted_chunks / useful) if useful > 0 else float('nan')

    def get_drop_rate(self):
        total = self.e2e_success_count + self.e2e_drop_count
        return self.e2e_drop_count / total if total > 0 else 0.0

    def get_ee(self):
        bits = self.e2e_success_count * CHUNKS_SYS * BITS_PER_CHUNK
        return bits / self.total_energy if self.total_energy > 0 else float('nan')


# ==========================================
# 4. 信道模型 (仅 Rician K=2)
# ==========================================
def noise_var_for_snr_db(snr_db):
    loss = compute_tl(HOP_DIST, FREQ_KHZ)
    snr_lin = 10.0 ** (snr_db / 10.0)
    return TX_POWER_W / (loss * snr_lin)


def avg_snr_db(noise_var, dist_m=None):
    d_m = dist_m if dist_m else HOP_DIST
    loss = compute_tl(d_m, FREQ_KHZ)
    snr_lin = (TX_POWER_W / loss) / max(noise_var, 1e-30)
    return 10.0 * math.log10(max(snr_lin, 1e-30))


# ==========================================
# 5. 数据包
# ==========================================
PKT_DATA  = 'DATA'
PKT_ACK   = 'ACK'
PKT_NACK  = 'NACK'

class PhysicalPacket:
    def __init__(self, pkt_type, hop_tx, hop_rx, pid,
                 rv_level=0, creation_time=0.0, fec_idx=-1):
        self.pkt_type = pkt_type
        self.hop_tx = hop_tx
        self.hop_rx = hop_rx
        self.pid = pid
        self.rv_level = rv_level
        self.creation_time = creation_time
        self.fec_idx = fec_idx
        s, e = RV_SLICES.get(rv_level, (0, 0))
        self.start_idx, self.end_idx = s, e
        if pkt_type == PKT_DATA:
            if fec_idx > 0:
                s, e = CHARQ_FEC[fec_idx - 1]
                self.start_idx, self.end_idx = s, e
                self.num_chunks = CHARQ_FEC_SIZE[fec_idx - 1]
            else:
                self.num_chunks = e - s
        elif pkt_type == PKT_ACK:
            self.num_chunks = 3
        elif pkt_type == PKT_NACK:
            self.num_chunks = 3
        else:
            self.num_chunks = 2
        self.received_snr_array = None
        self.avg_snr_linear = 0.0
        self.header_ok = True
        self.cpkt = -1

    def tx_duration(self):
        return self.num_chunks * (BITS_PER_CHUNK / BIT_RATE)


# ==========================================
# 6. 水下节点
# ==========================================
class UnderwaterNode:
    def __init__(self, env, node_id, x, y, role, protocol,
                 stats, network, noise_variance):
        self.env = env; self.node_id = node_id; self.x, self.y = x, y
        self.role = role; self.protocol = protocol
        self.stats = stats; self.network = network
        self.noise_variance = noise_variance
        self.inbox = simpy.Store(env); self.tx_queue = simpy.Store(env)
        self.energy = INITIAL_ENERGY
        self.tx_power = TX_POWER_W
        self.soft_buffer = {}
        self.merge_count = defaultdict(int)
        self.hop_source = {}
        self.ack_events = {}
        self.pending_response = {}
        self.next_hop_id = None; self.is_dest = False
        self.helper_for_link = None
        self.is_selected = False
        self.is_low_snr_selected = False
        self.fec_sent = defaultdict(int)
        self.helper_sent = defaultdict(int)
        self.nack_sent = set()
        self.helper_cancel_events = {}
        self.helper_tx_cnt = defaultdict(int)
        self.nack_count = defaultdict(int)
        self.helper_ack_events = {}
        self.env.process(self.recv_loop())
        if self.role == 'ROUTER':
            self.env.process(self.tx_loop())

    # ---------- 发送循环 ----------
    def tx_loop(self):
        while True:
            pid, creation_time = yield self.tx_queue.get()
            hop_ok = False
            self.pending_response.pop(pid, None)

            yield self.env.process(self.send_data(
                self.next_hop_id, pid, 0, creation_time))

            rtt = HOP_DIST / SOUND_SPEED * 2
            gto = rtt + T_MAX_WINDOW * 3 + 2.0

            for retry_i in range(MAX_HOP_RETRYS):
                if pid in self.pending_response:
                    msg = self.pending_response.pop(pid)
                    if msg['type'] == 'ACK':
                        hop_ok = True
                        break
                    elif self.protocol == PROTO_CA:
                        cpkt = msg.get('cpkt', 2)
                        if cpkt >= 3:
                            rv_chunks = {0: 19, 1: 13, 2: 6}.get(cpkt, 6)
                            rv_tx_t = rv_chunks * BITS_PER_CHUNK / BIT_RATE
                            grace_t = rv_tx_t + T_MAX_WINDOW / 4 + 3 * HOP_DIST / SOUND_SPEED + 0.3
                            grace_to = self.env.timeout(grace_t)
                            ack_he = simpy.Event(self.env)
                            self.helper_ack_events[pid] = ack_he
                            gr = yield grace_to | ack_he
                            self.helper_ack_events.pop(pid, None)
                            if ack_he in gr:
                                hop_ok = True
                                break
                        yield self.env.process(self.send_data(
                            self.next_hop_id, pid, 0, creation_time))
                        continue
                    else:
                        yield self.env.process(self.send_data(
                            self.next_hop_id, pid, 0, creation_time))
                        continue

                to_ev = self.env.timeout(gto)
                ack_ev = simpy.Event(self.env)
                key = f"{pid}_{retry_i}"
                self.ack_events[key] = ack_ev

                result = yield ack_ev | to_ev
                self.ack_events.pop(key, None)

                if ack_ev in result:
                    msg = result[ack_ev]
                    if msg['type'] == 'ACK':
                        hop_ok = True
                        break
                    elif msg['type'] == 'NACK':
                        if self.protocol == PROTO_CA:
                            cpkt = msg.get('cpkt', 2)
                            if cpkt >= 3:
                                rv_chunks = {0: 19, 1: 13, 2: 6}.get(cpkt, 6)
                                rv_tx_t = rv_chunks * BITS_PER_CHUNK / BIT_RATE
                                grace_t = rv_tx_t + T_MAX_WINDOW / 4 + 3 * HOP_DIST / SOUND_SPEED + 0.3
                                grace_to = self.env.timeout(grace_t)
                                ack_he = simpy.Event(self.env)
                                self.helper_ack_events[pid] = ack_he
                                gr = yield grace_to | ack_he
                                self.helper_ack_events.pop(pid, None)
                                if ack_he in gr:
                                    hop_ok = True
                                    break
                        yield self.env.process(self.send_data(
                            self.next_hop_id, pid, 0, creation_time))
                else:
                    yield self.env.process(self.send_data(
                        self.next_hop_id, pid, 0, creation_time))

            if not hop_ok:
                if pid in self.pending_response:
                    msg = self.pending_response.pop(pid)
                    if msg['type'] == 'ACK':
                        hop_ok = True
            if not hop_ok:
                self.stats.e2e_drop(pid)

    # ---------- 接收循环 ----------
    def recv_loop(self):
        while True:
            pkt = yield self.inbox.get()
            self.env.process(self.handle(pkt))

    def handle(self, pkt):
        if not pkt.header_ok:
            return
        pid = pkt.pid

        if pkt.pkt_type == PKT_DATA:

            # 路由器 接收 DATA
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                if pid not in self.soft_buffer:
                    self.soft_buffer[pid] = np.zeros(CHUNKS_SYS + CHUNKS_PARITY_MAX)
                    self.merge_count[pid] = 0
                    self.hop_source[pid] = pkt.hop_tx
                if isinstance(self.soft_buffer[pid], str):
                    yield self.env.process(self.send_ack(
                        self.hop_source.get(pid, pkt.hop_tx), pid))
                    return

                self.merge_count[pid] += 1

                if pkt.fec_idx > 0:
                    s, e = CHARQ_FEC[pkt.fec_idx - 1]
                    self.soft_buffer[pid][s:e] += pkt.received_snr_array
                elif self.protocol == PROTO_CA and pkt.rv_level > 0:
                    s, e = pkt.start_idx, pkt.end_idx
                    self.soft_buffer[pid][s:e] += pkt.received_snr_array
                else:
                    self.soft_buffer[pid][0:25] += pkt.received_snr_array

                per = compute_packet_per(self.soft_buffer[pid])

                if random.random() > per:
                    self.soft_buffer[pid] = "SUCCESS"
                    yield self.env.process(self.send_ack(
                        self.hop_source.get(pid, pkt.hop_tx), pid))
                    if self.is_dest:
                        self.stats.e2e_success(
                            pid, self.env.now - pkt.creation_time)
                    else:
                        self.tx_queue.put((pid, pkt.creation_time))
                elif self.merge_count[pid] >= MAX_MERGE_ATTEMPTS:
                    self.soft_buffer.pop(pid, None)
                    self.merge_count.pop(pid, None)
                    return
                else:
                    if (self.protocol == PROTO_CA
                            and pkt.hop_tx == self.hop_source[pid]):
                        c, cpkt = rs_confidence(self.soft_buffer[pid])
                        max_n = NACK_MAX if cpkt >= 3 else 1
                        if self.nack_count[pid] < max_n:
                            self.nack_count[pid] += 1
                            yield self.env.process(self.send_nack_cpkt(
                                self.hop_source[pid], pid, cpkt))
                    elif pkt.hop_tx == self.hop_source[pid] and pid not in self.nack_sent:
                        self.nack_sent.add(pid)
                        yield self.env.process(self.send_nack(
                            self.hop_source[pid], pid))

            # CA-CHARQ helper 竞争取消 (监听到其他 helper 发包)
            if (self.role == 'HELPER' and self.protocol == PROTO_CA
                    and pid in self.helper_cancel_events
                    and pkt.hop_tx != self.node_id
                    and self.helper_for_link is not None
                    and pkt.hop_rx == self.helper_for_link[1]):
                ce = self.helper_cancel_events[pid]
                if not ce.triggered:
                    ce.succeed()

            # Helper 侦听源端数据
            elif (self.role == 'HELPER'
                  and self.helper_for_link == (pkt.hop_tx, pkt.hop_rx)
                  and pkt.rv_level == 0
                  and pkt.fec_idx <= 0):
                if pid not in self.soft_buffer:
                    self.soft_buffer[pid] = np.zeros(CHUNKS_SYS + CHUNKS_PARITY_MAX)
                if isinstance(self.soft_buffer[pid], dict):
                    return
                self.soft_buffer[pid][0:25] += pkt.received_snr_array
                per = compute_packet_per(self.soft_buffer[pid])
                if random.random() > per:
                    if self.protocol == PROTO_CA:
                        c, cpkt = rs_confidence(self.soft_buffer[pid])
                        self.soft_buffer[pid] = {"status": "DECODED",
                                                 "creation_time": pkt.creation_time,
                                                 "c_pkt": c, "cpkt": cpkt}
                    else:
                        self.soft_buffer[pid] = {"status": "DECODED",
                                                 "creation_time": pkt.creation_time}

        # ---- NACK 处理 ----
        elif pkt.pkt_type == PKT_NACK:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                matched = False
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'NACK', 'cpkt': pkt.cpkt})
                        matched = True
                        break
                if not matched:
                    self.pending_response[pid] = {'type': 'NACK', 'cpkt': pkt.cpkt}

            elif self.role == 'HELPER' and self.protocol == PROTO_CA:
                link_src, link_dst = self.helper_for_link
                if (pkt.hop_rx, pkt.hop_tx) == (link_src, link_dst):
                    buf = self.soft_buffer.get(pid)
                    if isinstance(buf, dict) and buf.get("status") == "DECODED":
                        if pkt.cpkt > 1:
                            self.env.process(self.contend(pkt))
                        elif self.is_low_snr_selected and self.helper_tx_cnt[pid] < 3:
                            cpkt = pkt.cpkt
                            rv = 2 if cpkt >= 1 else 3
                            self.helper_tx_cnt[pid] += 1
                            yield self.env.process(self.send_data(
                                pkt.hop_tx, pid, rv, buf["creation_time"]))

            elif self.role == 'HELPER' and self.is_selected:
                link_src, link_dst = self.helper_for_link
                if (pkt.hop_rx, pkt.hop_tx) == (link_src, link_dst):
                    buf = self.soft_buffer.get(pid)
                    if isinstance(buf, dict) and buf.get("status") == "DECODED":
                        if self.protocol == PROTO_CHARQ:
                            if self.fec_sent[pid] == 0:
                                self.fec_sent[pid] = 1
                                yield self.env.process(self.send_fec(
                                    pkt.hop_tx, pid, 1, buf["creation_time"]))
                                yield self.env.timeout(T_PROTECTION_GAP + CHARQ_FEC_SIZE[0] * BITS_PER_CHUNK / BIT_RATE)
                                if self.fec_sent[pid] == 1:
                                    self.fec_sent[pid] = 2
                                    yield self.env.process(self.send_fec(
                                        pkt.hop_tx, pid, 2, buf["creation_time"]))
                        elif self.protocol == PROTO_CARQ:
                            cnt = self.helper_sent[pid]
                            if cnt < MAX_HOP_RETRYS:
                                self.helper_sent[pid] = cnt + 1
                                yield self.env.process(self.send_data(
                                    pkt.hop_tx, pid, 0, buf["creation_time"]))

        # ---- ACK 处理 ----
        elif pkt.pkt_type == PKT_ACK:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                matched = False
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'ACK'})
                        matched = True
                        break
                if not matched:
                    self.pending_response[pid] = {'type': 'ACK'}
                if self.protocol == PROTO_CA and pid in self.helper_ack_events:
                    hev = self.helper_ack_events[pid]
                    if not hev.triggered:
                        hev.succeed({'type': 'ACK'})

    # ---------- CA-CHARQ Helper 退避竞争 ----------
    def contend(self, pkt):
        pid = pkt.pid
        if pid in self.helper_cancel_events or pkt.cpkt <= 1:
            return
        buf = self.soft_buffer.get(pid)
        if not isinstance(buf, dict) or buf.get("status") != "DECODED":
            return

        my_c = buf.get("c_pkt", 1.0)
        link_src, link_dst = self.helper_for_link
        d_src = math.hypot(self.x - link_src * HOP_DIST, self.y - 0)
        d_dst = math.hypot(self.x - link_dst * HOP_DIST, self.y - 0)
        dist = max(d_src, d_dst)
        prop_u = dist / SOUND_SPEED
        score = (W1 * min(my_c, 1.5)
                 + W2 * max(0.0, min(1.0, self.energy / INITIAL_ENERGY))
                 + W3 * (1.0 / (1.0 + prop_u / 0.4)))
        t = (1.0 - np.clip(score, 0.0, 1.0)) * T_MAX_WINDOW * 2
        t += max(T_PROTECTION_GAP / 4, 0.05)
        if score > 0.90:
            t = 0.0
        elif pkt.cpkt < 3 and self.is_low_snr_selected:
            t = 0.02

        cancel_ev = simpy.Event(self.env)
        self.helper_cancel_events[pid] = cancel_ev

        result = yield self.env.timeout(t) | cancel_ev
        if cancel_ev not in result:
            cpkt = pkt.cpkt
            if cpkt >= 2:   rv = 1
            elif cpkt >= 1: rv = 2
            else:           rv = 3
            self.helper_tx_cnt[pid] += 1
            yield self.env.process(self.send_data(
                pkt.hop_tx, pid, rv, buf["creation_time"]))
        self.helper_cancel_events.pop(pid, None)

    # ---------- 发送方法 ----------
    def _tx_pkt(self, pkt):
        dur = pkt.tx_duration()
        self.stats.record_tx(pkt.num_chunks)
        if pkt.pkt_type == PKT_DATA: self.stats.record_data_tx()
        elif pkt.pkt_type == PKT_NACK: self.stats.record_nack_tx()
        elif pkt.pkt_type == PKT_ACK: self.stats.record_ack_tx()
        self.energy -= self.tx_power * dur
        self.stats.record_energy(self.tx_power * dur)
        yield self.env.timeout(dur)
        self.network.broadcast(self, pkt)

    def send_data(self, target, pid, rv, creation_time):
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target, pid, rv, creation_time)
        yield self.env.process(self._tx_pkt(pkt))

    def send_fec(self, target, pid, fec_idx, creation_time):
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target, pid, 0, creation_time, fec_idx=fec_idx)
        yield self.env.process(self._tx_pkt(pkt))

    def send_ack(self, target, pid):
        pkt = PhysicalPacket(PKT_ACK, self.node_id, target, pid)
        yield self.env.process(self._tx_pkt(pkt))

    def send_nack(self, target, pid):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid)
        yield self.env.process(self._tx_pkt(pkt))

    def send_nack_cpkt(self, target, pid, cpkt):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid)
        pkt.cpkt = cpkt
        yield self.env.process(self._tx_pkt(pkt))


# ==========================================
# 7. 水声信道 (仅 Rician K=2)
# ==========================================
class Channel:
    def __init__(self, env, noise_var, k=2.0):
        self.env = env; self.nodes = []
        self.noise_var = noise_var
        self.los = math.sqrt(k / (k + 1))
        self.nlos = math.sqrt(1.0 / (2 * (k + 1)))

    def broadcast(self, sender, pkt):
        for rx in self.nodes:
            if rx is sender:
                continue
            dist = math.hypot(sender.x - rx.x, sender.y - rx.y)
            prop = dist / SOUND_SPEED

            clone = PhysicalPacket(pkt.pkt_type, pkt.hop_tx, pkt.hop_rx,
                                   pkt.pid, pkt.rv_level, pkt.creation_time,
                                   fec_idx=pkt.fec_idx)
            clone.header_ok = True
            clone.cpkt = pkt.cpkt

            if pkt.pkt_type == PKT_DATA:
                loss = compute_tl(dist, FREQ_KHZ)
                asnr = (sender.tx_power / loss) / self.noise_var
                n = clone.num_chunks
                I = self.los + self.nlos * np.random.randn(n)
                Q = self.nlos * np.random.randn(n)
                clone.received_snr_array = asnr * (I ** 2 + Q ** 2)
                clone.avg_snr_linear = float(np.mean(clone.received_snr_array))

            self.env.process(self._deliver(rx, clone, prop))

    def _deliver(self, rx, pkt, delay):
        yield self.env.timeout(delay)
        rx.inbox.put(pkt)


# ==========================================
# 8. 仿真执行
# ==========================================
def run_sim(snr_db, protocol, sim_time, seed=0, hop_dist=None, fixed_noise_var=None, n_helpers=None):
    if hop_dist is not None:
        global HOP_DIST
        saved_dist = HOP_DIST
        HOP_DIST = hop_dist
    if n_helpers is not None:
        global N_HELPERS_PER_HOP
        saved_helpers = N_HELPERS_PER_HOP
        N_HELPERS_PER_HOP = n_helpers
    random.seed(seed); np.random.seed(seed)
    env = simpy.Environment()
    stats = StatsTracker(sim_time)
    if fixed_noise_var is not None:
        nv = fixed_noise_var
    else:
        nv = noise_var_for_snr_db(snr_db)
    ch = Channel(env, nv, k=RICIAN_K)

    routers = []
    for i in range(NUM_HOPS + 1):
        n = UnderwaterNode(env, i, i * HOP_DIST, 0,
                           'ROUTER', protocol, stats, ch, nv)
        if i < NUM_HOPS:
            n.next_hop_id = i + 1
        if i == NUM_HOPS:
            n.is_dest = True
        routers.append(n)
        ch.nodes.append(n)

    if protocol != PROTO_SW_ARQ:
        R = HOP_DIST
        for i in range(NUM_HOPS):
            sx, dx = i * R, (i + 1) * R
            helper_base_id = 10 + i * N_HELPERS_PER_HOP
            helpers_for_link = []
            placed = 0
            while placed < N_HELPERS_PER_HOP:
                x = sx + random.random() * R
                y = (random.random() * 2 - 1) * R
                if math.hypot(x - sx, y) <= R and math.hypot(x - dx, y) <= R:
                    h = UnderwaterNode(env, helper_base_id + placed,
                                       x, y, 'HELPER', protocol, stats, ch, nv)
                    h.helper_for_link = (i, i + 1)
                    d_dst = math.hypot(x - dx, y - 0)
                    h.tx_power = TX_POWER_W * min(1.0, (d_dst / HOP_DIST) ** 1.5)
                    ch.nodes.append(h)
                    helpers_for_link.append(h)
                    placed += 1
            if helpers_for_link and protocol != PROTO_CA:
                mx, my = (sx + dx) / 2.0, 0.0
                nearest = min(helpers_for_link,
                              key=lambda hh: math.hypot(hh.x - mx, hh.y - my))
                nearest.is_selected = True
            if helpers_for_link and protocol == PROTO_CA:
                best = min(helpers_for_link,
                           key=lambda hh: max(math.hypot(hh.x - sx, hh.y - 0),
                                              math.hypot(hh.x - dx, hh.y - 0)))
                best.is_low_snr_selected = True

    def gen():
        pid = 0
        while True:
            routers[0].tx_queue.put((pid, env.now))
            pid += 1
            yield env.timeout(random.expovariate(1.0 / 30.0))

    env.process(gen())
    env.run(until=sim_time)

    result = {
        "delay": stats.get_avg_delay(),
        "delay_std": stats.get_delay_std(),
        "overhead": stats.get_overhead(),
        "throughput": stats.get_throughput(),
        "drop_rate": stats.get_drop_rate(),
        "success": stats.e2e_success_count,
        "drops": stats.e2e_drop_count,
        "data_tx": stats.total_data_tx,
        "nack_tx": stats.total_nack_tx,
        "ack_tx": stats.total_ack_tx,
        "ee": stats.get_ee(),
        "actual_snr": avg_snr_db(nv, hop_dist) if hop_dist else avg_snr_db(nv),
        "hop_dist": hop_dist,
    }
    if hop_dist is not None:
        HOP_DIST = saved_dist
    return result


# ==========================================
# 9. 蒙特卡洛
# ==========================================
def mc_run(snr_db, protocol, sim_time, n_runs, hop_dist=None, fixed_noise_var=None, n_helpers=None):
    delays, ovhds, tputs, drops, ees = [], [], [], [], []
    succs, data_txs, nack_txs = [], [], []

    for run_i in range(n_runs):
        s = abs(42 + run_i * 7919 + int(snr_db * 3571) + (1 << 20)) % (2**31 - 1)
        r = run_sim(snr_db, protocol, sim_time, seed=s,
                    hop_dist=hop_dist, fixed_noise_var=fixed_noise_var,
                    n_helpers=n_helpers)

        delays.append(r['delay'] if not math.isnan(r['delay']) else None)
        ovhds.append(r['overhead'] if not math.isnan(r['overhead']) else None)
        tputs.append(r['throughput']); drops.append(r['drop_rate'])
        ees.append(r['ee'] if not math.isnan(r['ee']) else None)
        succs.append(r['success']); data_txs.append(r['data_tx']); nack_txs.append(r['nack_tx'])

    def ci(arr):
        a = np.array([x for x in arr if x is not None], dtype=float)
        if len(a) == 0: return float('nan'), 0.0
        m = np.mean(a); se = np.std(a, ddof=1) / math.sqrt(len(a))
        return m, 1.96 * se

    d_m, d_ci = ci(delays); o_m, o_ci = ci(ovhds)
    t_m, t_ci = ci(tputs); dr_m, dr_ci = ci(drops)
    ee_m, ee_ci = ci(ees)

    return {
        "delay_mean": d_m, "delay_ci95": d_ci,
        "overhead_mean": o_m, "overhead_ci95": o_ci,
        "throughput_mean": t_m, "throughput_ci95": t_ci,
        "drop_rate_mean": dr_m, "drop_rate_ci95": dr_ci,
        "ee_mean": ee_m, "ee_ci95": ee_ci,
        "avg_success": np.mean(succs), "avg_data_tx": np.mean(data_txs),
        "avg_nack_tx": np.mean(nack_txs),
        "actual_snr": avg_snr_db(noise_var_for_snr_db(snr_db)),
    }


# ==========================================
# 10. 主程序
# ==========================================
if __name__ == "__main__":
    SNR_LIST   = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    SIM_TIME   = 15000
    N_RUNS     = 5

    PROTOCOLS = []
    LABELS    = []
    if ENABLE['SW_ARQ']: PROTOCOLS.append(PROTO_SW_ARQ); LABELS.append(PROTO_SW_ARQ)
    if ENABLE['CARQ']:   PROTOCOLS.append(PROTO_CARQ);   LABELS.append(PROTO_CARQ)
    if ENABLE['CHARQ']:  PROTOCOLS.append(PROTO_CHARQ);  LABELS.append(PROTO_CHARQ)
    if ENABLE['CA']:     PROTOCOLS.append(PROTO_CA);     LABELS.append(PROTO_CA)

    COLORS = {PROTO_SW_ARQ: '#4C72B0', PROTO_CARQ: '#DD8452',
              PROTO_CHARQ: '#55A868', PROTO_CA: '#C44E52'}
    MARKERS = {PROTO_SW_ARQ: 's', PROTO_CARQ: '^',
               PROTO_CHARQ: 'D', PROTO_CA: 'o'}

    results = {p: {'delay': ([], []), 'overhead': ([], []),
                   'throughput': ([], []), 'drop_rate': ([], []),
                   'ee': ([], [])}
               for p in PROTOCOLS}

    print("=" * 65)
    print(f" Monte Carlo: {N_RUNS} runs x {len(SNR_LIST)} SNR x {len(PROTOCOLS)} protocols")
    print(f" Channel: Rayleigh + Thorp α≈{thorp_alpha(FREQ_KHZ):.1f}dB/km + low-SNR pre-selected helper")
    print(f" Protocols: {', '.join(PROTOCOLS)}")
    print(f" PHY: RS code error-correct model (QPSK, t=(N-K)/2) — PER-based Cpkt")
    print("=" * 65)

    for proto in PROTOCOLS:
        print(f"\n{'='*50}\n  Protocol: {proto}\n{'='*50}")
        for snr in SNR_LIST:
            r = mc_run(snr, proto, SIM_TIME, N_RUNS)
            results[proto]['delay'][0].append(r['delay_mean'])
            results[proto]['delay'][1].append(r['delay_ci95'])
            results[proto]['overhead'][0].append(r['overhead_mean'])
            results[proto]['overhead'][1].append(r['overhead_ci95'])
            results[proto]['throughput'][0].append(r['throughput_mean'])
            results[proto]['throughput'][1].append(r['throughput_ci95'])
            results[proto]['drop_rate'][0].append(r['drop_rate_mean'])
            results[proto]['drop_rate'][1].append(r['drop_rate_ci95'])
            results[proto]['ee'][0].append(r['ee_mean'])
            results[proto]['ee'][1].append(r['ee_ci95'])
            print(f"  SNR={snr:+4.1f}dB | D={r['delay_mean']:8.1f}±{r['delay_ci95']:5.1f}s | "
                  f"Ovhd={r['overhead_mean']:6.3f}±{r['overhead_ci95']:.3f} | "
                  f"Drop={r['drop_rate_mean']:.3f}±{r['drop_rate_ci95']:.3f} | Succ={r['avg_success']:.0f}")

    # ---- 绘图 ----
    plt.rcParams.update({'font.size': 11, 'legend.fontsize': 9,
                         'xtick.labelsize': 9, 'ytick.labelsize': 9})

    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    for proto in PROTOCOLS:
        y = np.array(results[proto]['delay'][0])
        mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(SNR_LIST)[mask]
            ax1.plot(xm, y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto],
                     markeredgewidth=0.8)
    ax1.set_xlabel("Average Per-Hop SNR (dB)")
    ax1.set_ylabel("End-to-End Delay (s)")
    ax1.grid(True, ls='-', alpha=0.15, color='gray')
    ax1.legend(frameon=True, fancybox=False, edgecolor='gray', loc='upper right')

    for proto in PROTOCOLS:
        y = np.array(results[proto]['overhead'][0])
        mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(SNR_LIST)[mask]
            ax2.plot(xm, y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto],
                     markeredgewidth=0.8)
    ax2.set_xlabel("Average Per-Hop SNR (dB)")
    ax2.set_ylabel("Transmission Overhead (x Usefulness)")
    ax2.grid(True, ls='-', alpha=0.15, color='gray')
    ax2.legend(frameon=True, fancybox=False, edgecolor='gray', loc='upper right')

    plt.tight_layout()
    plt.savefig("output/pro-v1_Delay_Overhead.png", dpi=200, bbox_inches='tight')
    print("\n[OK] output/pro-v1_Delay_Overhead.png")
    plt.close('all')

    # EE 子图
    fig2, ax_ee = plt.subplots(1, 1, figsize=(7, 5))
    for proto in PROTOCOLS:
        y = np.array(results[proto]['ee'][0])
        mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(SNR_LIST)[mask]
            ax_ee.plot(xm, y[mask], MARKERS[proto]+'-',
                       color=COLORS[proto], lw=1.8, ms=7, label=proto,
                       markerfacecolor='white', markeredgecolor=COLORS[proto],
                       markeredgewidth=0.8)
    ax_ee.set_xlabel("Average Per-Hop SNR (dB)")
    ax_ee.set_ylabel("Energy Efficiency (bits/Joule)")
    ax_ee.grid(True, ls='-', alpha=0.15, color='gray')
    ax_ee.legend(frameon=True, fancybox=False, edgecolor='gray', loc='lower right')
    plt.tight_layout()
    plt.savefig("output/pro-v1_EE.png", dpi=200, bbox_inches='tight')
    print("[OK] output/pro-v1_EE.png")
    plt.close('all')

    # ---- 文本汇总 ----
    print(f"\n{'='*65}")
    print("Overhead (Tx/Useful) mean ± 95% CI")
    header = f"{'SNR':>6s} |" + "|".join(f" {p:>15s} " for p in PROTOCOLS)
    print(header)
    for i, s in enumerate(SNR_LIST):
        parts = []
        for proto in PROTOCOLS:
            v = results[proto]['overhead'][0][i]
            e = results[proto]['overhead'][1][i]
            parts.append(f"{v:.2f}±{e:.2f}" if not np.isnan(v) else "        n/a")
        print(f"{s:+4.1f}dB | " + " | ".join(f"{p:>15s}" for p in parts))

    print(f"\nDelay (s) mean ± 95% CI")
    print(header)
    for i, s in enumerate(SNR_LIST):
        parts = []
        for proto in PROTOCOLS:
            v = results[proto]['delay'][0][i]
            e = results[proto]['delay'][1][i]
            parts.append(f"{v:.0f}±{e:.0f}" if not np.isnan(v) else "        n/a")
        print(f"{s:+4.1f}dB | " + " | ".join(f"{p:>15s}" for p in parts))

    print(f"\nEnergy Efficiency (bits/Joule) mean ± 95% CI")
    print(header)
    for i, s in enumerate(SNR_LIST):
        parts = []
        for proto in PROTOCOLS:
            v = results[proto]['ee'][0][i]
            e = results[proto]['ee'][1][i]
            parts.append(f"{v:.1f}±{e:.1f}" if not np.isnan(v) else "        n/a")
        print(f"{s:+4.1f}dB | " + " | ".join(f"{p:>15s}" for p in parts))
    print("=" * 65)
    print("Done.")
    
    # ==========================================
    # 距离扫描 (不修改已有SNR图)
    # ==========================================
    D_LIST = [400, 600, 800, 1000]
    NV_D = noise_var_for_snr_db(0.0)
    SIM_T = 8000
    N_RUNS_DIST = 5
    
    print(f"\n{'='*65}")
    print(f" Distance sweep: {D_LIST}m, fixed noise (0dB@600m), SimTime={SIM_T}s")
    print(f" Protocols: {', '.join(PROTOCOLS)}")
    print("=" * 65)
    
    d_results = {p: {'delay': ([], []), 'overhead': ([], []), 'success': []}
                 for p in PROTOCOLS}
    
    for proto in PROTOCOLS:
        print(f"\n  Protocol: {proto}")
        for d in D_LIST:
            r = mc_run(0.0, proto, SIM_T, N_RUNS_DIST, hop_dist=d, fixed_noise_var=NV_D)
            d_results[proto]['delay'][0].append(r['delay_mean'])
            d_results[proto]['delay'][1].append(r['delay_ci95'])
            d_results[proto]['overhead'][0].append(r['overhead_mean'])
            d_results[proto]['overhead'][1].append(r['overhead_ci95'])
            d_results[proto]['success'].append(r['avg_success'])
            print(f"    Dist={d:5d}m (SNR{r['actual_snr']:+.1f}dB) | D={r['delay_mean']:8.1f}±{r['delay_ci95']:5.1f}s | "
                  f"Ovhd={r['overhead_mean']:6.3f}±{r['overhead_ci95']:.3f} | Succ={r['avg_success']:.0f}")
    
    x_d = D_LIST
    fig_d, (ax_d1, ax_d2) = plt.subplots(1, 2, figsize=(14, 5))
    for proto in PROTOCOLS:
        y = np.array(d_results[proto]['delay'][0]); mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(x_d)[mask]
            ax_d1.plot(xm, y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto],
                     markeredgewidth=0.8)
    ax_d1.set_xlabel("Hop Distance (m)"); ax_d1.set_ylabel("End-to-End Delay (s)")
    ax_d1.grid(True, ls='-', alpha=0.15, color='gray')
    ax_d1.legend(frameon=True, fancybox=False, edgecolor='gray', loc='upper left')
    
    for proto in PROTOCOLS:
        y = np.array(d_results[proto]['overhead'][0]); mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(x_d)[mask]
            ax_d2.plot(xm, y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto],
                     markeredgewidth=0.8)
    ax_d2.set_xlabel("Hop Distance (m)"); ax_d2.set_ylabel("Transmission Overhead (x Usefulness)")
    ax_d2.grid(True, ls='-', alpha=0.15, color='gray')
    ax_d2.legend(frameon=True, fancybox=False, edgecolor='gray', loc='upper left')
    
    plt.tight_layout()
    plt.savefig("output/pro-v1_Distance_Delay_Overhead.png", dpi=200, bbox_inches='tight')
    print("\n[OK] output/pro-v1_Distance_Delay_Overhead.png")
    plt.close('all')

    # 距离扫成功包数
    fig_succ, ax_succ = plt.subplots(1, 1, figsize=(7, 5))
    for proto in PROTOCOLS:
        y = np.array(d_results[proto]['success'])
        mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(x_d)[mask]
            ax_succ.plot(xm, y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto],
                     markeredgewidth=0.8)
    ax_succ.set_xlabel("Hop Distance (m)")
    ax_succ.set_ylabel("Successful Packets Delivered")
    ax_succ.grid(True, ls='-', alpha=0.15, color='gray')
    ax_succ.legend(frameon=True, fancybox=False, edgecolor='gray', loc='lower left')
    plt.tight_layout()
    plt.savefig("output/pro-v1_Distance_Success.png", dpi=200, bbox_inches='tight')
    print("[OK] output/pro-v1_Distance_Success.png")
    plt.close('all')

    # ==========================================
    # Helper数量扫 — 空间分集效应 (仅CA-CHARQ)
    # ==========================================
    H_LIST = [1, 2, 3, 4, 5]
    FIXED_SNR_H = 0.0
    SIM_T_H = 5000
    N_RUNS_H = 3
    
    print(f"\n{'='*65}")
    print(f" Helper count sweep (CA-CHARQ only): {H_LIST}, SNR={FIXED_SNR_H}dB, SimTime={SIM_T_H}s")
    print("=" * 65)
    
    ca_delays = []; ca_cis = []
    for n in H_LIST:
        r = mc_run(FIXED_SNR_H, PROTO_CA, SIM_T_H, N_RUNS_H, n_helpers=n)
        ca_delays.append(r['delay_mean'])
        ca_cis.append(r['delay_ci95'])
        print(f"  N_helpers={n} | D={r['delay_mean']:8.1f}±{r['delay_ci95']:5.1f}s | Succ={r['avg_success']:.0f}")
    
    fig_h2, ax_h2 = plt.subplots(1, 1, figsize=(6, 4.5))
    y = np.array(ca_delays); mask = ~np.isnan(y)
    xm = np.array(H_LIST)[mask]
    ax_h2.plot(xm, y[mask], 'o-', color='#C44E52', lw=2.0, ms=8,
               markerfacecolor='white', markeredgecolor='#C44E52', markeredgewidth=1.5)
    ax_h2.set_xlabel("Number of Helpers per Hop")
    ax_h2.set_ylabel("End-to-End Delay (s)")
    ax_h2.set_title("CA-CHARQ Delay vs Helper Count (SNR=0dB)")
    ax_h2.grid(True, ls='-', alpha=0.15, color='gray')
    plt.tight_layout()
    plt.savefig("output/pro-v1_Helpers_Delay.png", dpi=200, bbox_inches='tight')
    print("\n[OK] output/pro-v1_Helpers_Delay.png")
    plt.close('all')
