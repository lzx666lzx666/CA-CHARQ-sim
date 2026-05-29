"""
CA-CHARQ v11 — Per Design Spec (刘子昕 设计方案0520)
Protocols: S&W ARQ | C-ARQ(fixed helper) | C-HARQ(fixed seq RV) | CA-CHARQ(confidence+backoff)
"""
import simpy, math, random, os
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from collections import defaultdict

# =============================================
# 1. Parameters
# =============================================
SOUND_SPEED = 1500.0; BIT_RATE = 1200.0; BITS_PER_CHUNK = 80
CHUNKS_SYS = 100; CHUNKS_PARITY_MAX = 90; TX_POWER_W = 15.0
TARGET_MI = 11000.0; MAX_HOP_RETRYS = 8; MAX_MERGE_ATTEMPTS = 16
T_MAX_WINDOW = 1.5; W1, W2, W3 = 0.40, 0.25, 0.35
INITIAL_ENERGY = 10000.0; RICIAN_K = 2.0; HOP_DIST = 600.0
NUM_HOPS = 5; N_HELPERS_PER_HOP = 3
RV_SLICES = {0: (0, 100), 1: (100, 130), 2: (100, 160), 3: (100, 190)}
CHARQ_RV = [(100, 130), (100, 160), (100, 190)]
CHARQ_RV_SZ = [30, 60, 90]
CA_HELPER_SKIP_RATIO = 0.75
PROTO_SW = "S&W ARQ"; PROTO_CARQ = "CARQ"; PROTO_CHARQ = "C-HARQ"; PROTO_CA = "CA-CHARQ"
ENABLE = {'SW_ARQ': True, 'CARQ': True, 'CHARQ': True, 'CA': True}

def noise_var_for_snr_db(snr_db):
    dkm = HOP_DIST / 1000.0
    loss = dkm**1.5 * (10.0**(0.04 * dkm)) + 1e-20
    return TX_POWER_W / (loss * 10.0**(snr_db / 10.0))

def avg_snr_db(noise_var):
    dkm = HOP_DIST / 1000.0
    loss = dkm**1.5 * (10.0**(0.04 * dkm)) + 1e-20
    return 10.0 * math.log10(max((TX_POWER_W / loss) / max(noise_var, 1e-30), 1e-30))

# =============================================
# 2. StatsTracker
# =============================================
class StatsTracker:
    def __init__(self, sim_time):
        self.sim_time = sim_time
        self.total_tx_chunks = 0; self.total_data_tx = 0; self.total_nack_tx = 0
        self.total_ack_tx = 0; self.total_energy = 0.0
        self.e2e_delays = []; self.e2e_success = 0; self.e2e_drops = 0
        self._pkt_fate = {}
    def record_tx(self, n_chunks, tx_dur):
        self.total_tx_chunks += n_chunks; self.total_energy += TX_POWER_W * tx_dur
    def record_data_tx(self): self.total_data_tx += 1
    def record_nack_tx(self): self.total_nack_tx += 1
    def record_ack_tx(self): self.total_ack_tx += 1
    def e2e_ok(self, pid, delay):
        if pid not in self._pkt_fate:
            self._pkt_fate[pid] = 'ok'; self.e2e_success += 1; self.e2e_delays.append(delay)
    def e2e_fail(self, pid):
        if pid not in self._pkt_fate:
            self._pkt_fate[pid] = 'fail'; self.e2e_drops += 1
    def throughput(self):
        return (self.e2e_success * CHUNKS_SYS) / max(self.sim_time, 1.0) if self.e2e_success > 0 else 0.0
    def avg_delay(self):
        return float(np.mean(self.e2e_delays)) if self.e2e_delays else float('nan')
    def delay_std(self):
        return float(np.std(self.e2e_delays)) if self.e2e_delays else float('nan')
    def overhead(self):
        u = self.e2e_success * CHUNKS_SYS
        return (self.total_tx_chunks / u) if u > 0 else float('nan')
    def drop_rate(self):
        t = self.e2e_success + self.e2e_drops
        return self.e2e_drops / t if t > 0 else 0.0
    def energy_eff(self):
        return (self.e2e_success * CHUNKS_SYS * BITS_PER_CHUNK) / max(self.total_energy, 1e-6) if self.e2e_success > 0 else 0.0

# =============================================
# 3. PhysicalPacket
# =============================================
PKT_DATA = 'DATA'; PKT_ACK = 'ACK'; PKT_NACK = 'NACK'
class PhysicalPacket:
    def __init__(self, pkt_type, hop_tx, hop_rx, pid, rv_level=0, creation_time=0.0, cn_rv=0):
        self.pkt_type = pkt_type; self.hop_tx = hop_tx; self.hop_rx = hop_rx
        self.pid = pid; self.rv_level = rv_level; self.creation_time = creation_time
        self.cn_rv = cn_rv  # CARQ/C-HARQ: RV level requested via NACK-CN
        s, e = RV_SLICES.get(rv_level, (0, 0))
        self.start_idx, self.end_idx = s, e
        if pkt_type == PKT_DATA:
            if cn_rv > 0:  # C-HARQ FEC packet via NACK-CN
                s, e = CHARQ_RV[cn_rv - 1]
                self.start_idx, self.end_idx = s, e
                self.num_chunks = CHARQ_RV_SZ[cn_rv - 1]
                self.rv_level = cn_rv
            else:
                self.num_chunks = max(e - s, 1)
        elif pkt_type in (PKT_ACK, PKT_NACK):
            self.num_chunks = 3
        else:
            self.num_chunks = 2
        self.received_snr_array = None; self.avg_snr_linear = 0.0
        self.nack_requested_rv = 0; self.skip_helper = False; self.header_ok = True
    def tx_duration(self):
        return self.num_chunks * BITS_PER_CHUNK / BIT_RATE

# =============================================
# 4. UnderwaterNode
# =============================================
class UnderwaterNode:
    def __init__(self, env, node_id, x, y, role, protocol, stats, network, noise_variance):
        self.env = env; self.node_id = node_id; self.x, self.y = x, y
        self.role = role; self.protocol = protocol; self.stats = stats
        self.network = network; self.noise_variance = noise_variance
        self.inbox = simpy.Store(env); self.tx_queue = simpy.Store(env)
        self.energy = INITIAL_ENERGY
        self.soft_buffer = {}; self.merge_count = defaultdict(int)
        self.hop_source = {}
        self.ack_events = {}; self.pending_response = {}
        self.helper_cancel_events = {}; self.helper_tx_cnt = defaultdict(int)
        self.next_hop_id = None; self.is_dest = False
        self.helper_for_link = None
        self.is_primary = False  # C-ARQ/C-HARQ designated helper
        self.primary_helper_id = None  # Router: designated helper ID
        self.primary_helper_pos = (0, 0)  # Router: helper position for RTT calc
        self._coordinating = set()  # Prevent duplicate C-HARQ/CARQ coordination
        self.env.process(self.recv_loop())
        if self.role == 'ROUTER':
            self.env.process(self.tx_loop())

    # ---------- tx_loop ----------
    def tx_loop(self):
        while True:
            pid, ct = yield self.tx_queue.get()
            hop_ok = False
            self.pending_response.pop(pid, None)
            yield self.env.process(self.send_data(self.next_hop_id, pid, 0, ct))
            rtt = HOP_DIST / SOUND_SPEED * 2
            gto = rtt + T_MAX_WINDOW * 3 + 8.0
            for ri in range(MAX_HOP_RETRYS):
                to_ev = self.env.timeout(gto)
                ack_ev = simpy.Event(self.env)
                key = f"{pid}_{ri}"
                self.ack_events[key] = ack_ev
                if pid in self.pending_response:
                    msg = self.pending_response.pop(pid)
                    ack_ev.succeed(msg)
                    result = yield ack_ev
                else:
                    result = yield ack_ev | to_ev
                self.ack_events.pop(key, None)
                if ack_ev in result:
                    msg = ack_ev.value
                    if msg['type'] == 'ACK':
                        hop_ok = True; break
                    elif msg['type'] == 'NACK':
                        skip_h = msg.get('skip_helper', False)
                        nack_rv = msg.get('req_rv', 0)
                        if self.protocol == PROTO_CA and not skip_h:
                            rv_c = RV_SLICES[nack_rv][1] - RV_SLICES[nack_rv][0]
                            grace_t = T_MAX_WINDOW * 2 + rv_c * BITS_PER_CHUNK / BIT_RATE + 2 * HOP_DIST / SOUND_SPEED + 1.0
                            grace = self.env.timeout(grace_t)
                            ag = simpy.Event(self.env)
                            gk = f"{pid}_g"
                            self.ack_events[gk] = ag
                            gr = yield ag | grace
                            self.ack_events.pop(gk, None)
                            if ag in gr:
                                hop_ok = True; break
                            # Grace expired → source acts as helper
                            yield self.env.process(self.send_data(self.next_hop_id, pid, nack_rv, ct))
                        else:
                            yield self.env.process(self.send_data(self.next_hop_id, pid, 0, ct))
                else:
                    yield self.env.process(self.send_data(self.next_hop_id, pid, 0, ct))
            if not hop_ok:
                if pid in self.pending_response and self.pending_response[pid]['type'] == 'ACK':
                    hop_ok = True
            if not hop_ok:
                self.stats.e2e_fail(pid)

    # ---------- recv_loop ----------
    def recv_loop(self):
        while True:
            pkt = yield self.inbox.get()
            self.env.process(self.handle(pkt))

    def handle(self, pkt):
        pid = pkt.pid
        if pkt.pkt_type == PKT_DATA:
            if self.role == 'HELPER':
                if pid in self.helper_cancel_events:
                    ce = self.helper_cancel_events[pid]
                    if not ce.triggered: ce.succeed()

            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                yield self.env.process(self._router_handle_data(pkt))
                return

            # Helper listens to source DATA (RV0 with cn_rv=0)
            if (self.role == 'HELPER' and pkt.rv_level == 0 and pkt.cn_rv == 0
                    and self.helper_for_link == (pkt.hop_tx, pkt.hop_rx)):
                if pkt.received_snr_array is not None:
                    mi = float(np.sum(np.log2(1.0 + pkt.received_snr_array)) * BITS_PER_CHUNK)
                    if mi >= TARGET_MI:
                        self.soft_buffer[pid] = {
                            "status": "DONE", "c_pkt": mi / TARGET_MI,
                            "creation_time": pkt.creation_time}

        elif pkt.pkt_type == PKT_NACK:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'NACK', 'req_rv': pkt.nack_requested_rv,
                                     'skip_helper': pkt.skip_helper})
                        return
                self.pending_response[pid] = {'type': 'NACK', 'req_rv': pkt.nack_requested_rv,
                                              'skip_helper': pkt.skip_helper}
            elif (self.role == 'HELPER'
                  and pkt.cn_rv > 0
                  and pkt.hop_rx == self.node_id):
                # C-ARQ/C-HARQ: NACK-CN directed to this helper
                buf = self.soft_buffer.get(pid)
                if isinstance(buf, dict) and buf.get("status") == "DONE":
                    ct = buf.get("creation_time", pkt.creation_time)
                    yield self.env.process(self.send_data_cn(
                        pkt.hop_tx, pid, pkt.cn_rv, ct))
            elif (self.role == 'HELPER'
                  and not pkt.cn_rv
                  and self.helper_for_link == (pkt.hop_rx, pkt.hop_tx)):
                # CA-CHARQ: broadcast NACK triggers competition
                if not pkt.skip_helper:
                    buf = self.soft_buffer.get(pid)
                    if isinstance(buf, dict) and buf.get("status") == "DONE":
                        cnt = self.helper_tx_cnt[pid]
                        if cnt < 3:
                            ct = buf.get("creation_time", pkt.creation_time)
                            self.env.process(self.contend(
                                pkt, buf["c_pkt"], ct))

        elif pkt.pkt_type == PKT_ACK:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'ACK'}); return
                self.pending_response[pid] = {'type': 'ACK'}

    def _router_handle_data(self, pkt):
        """Router/destination DATA handling with protocol-specific logic"""
        pid = pkt.pid
        if pid not in self.soft_buffer:
            self.soft_buffer[pid] = np.zeros(CHUNKS_SYS + CHUNKS_PARITY_MAX)
            self.merge_count[pid] = 0
            self.hop_source[pid] = pkt.hop_tx
        if isinstance(self.soft_buffer[pid], str):
            yield self.env.process(self.send_ack(self.hop_source.get(pid, pkt.hop_tx), pid))
            return

        self.merge_count[pid] += 1

        # Soft combining
        if self.protocol in (PROTO_SW, PROTO_CARQ):
            self.soft_buffer[pid][0:100] += pkt.received_snr_array
        elif self.protocol == PROTO_CHARQ:
            if pkt.cn_rv > 0:
                s, e = CHARQ_RV[pkt.cn_rv - 1]
                self.soft_buffer[pid][s:e] += pkt.received_snr_array
            else:
                self.soft_buffer[pid][0:100] += pkt.received_snr_array
        else:  # CA-CHARQ: IR merge
            a, b = pkt.start_idx, pkt.end_idx
            if b > a and pkt.received_snr_array is not None:
                self.soft_buffer[pid][a:b] += pkt.received_snr_array

        acc_mi = float(np.sum(np.log2(1.0 + self.soft_buffer[pid])) * BITS_PER_CHUNK)

        if acc_mi >= TARGET_MI and self.merge_count[pid] > 0:
            self.soft_buffer[pid] = "SUCCESS"
            yield self.env.process(self.send_ack(self.hop_source.get(pid, pkt.hop_tx), pid))
            if self.is_dest:
                self.stats.e2e_ok(pid, self.env.now - pkt.creation_time)
            else:
                self.tx_queue.put((pid, pkt.creation_time))
            return

        if self.merge_count[pid] >= MAX_MERGE_ATTEMPTS:
            self.soft_buffer.pop(pid, None); self.merge_count.pop(pid, None); return

        ratio = acc_mi / TARGET_MI

        if self.protocol == PROTO_CARQ:
            yield self.env.process(self._carq_nack(pkt, pid, ratio))
        elif self.protocol == PROTO_CHARQ:
            yield self.env.process(self._charq_nack(pkt, pid, ratio))
        elif self.protocol == PROTO_CA:
            rv = self._select_rv(ratio)
            skip_h = (ratio > CA_HELPER_SKIP_RATIO)
            yield self.env.process(self.send_nack(
                self.hop_source.get(pid, pkt.hop_tx), pid, rv, skip_h))
        else:  # S&W ARQ
            yield self.env.process(self.send_nack(
                self.hop_source.get(pid, pkt.hop_tx), pid, 0, False))

    def _carq_nack(self, pkt, pid, ratio):
        """CARQ: designate primary helper to send full RV0"""
        if pid in self._coordinating: return
        self._coordinating.add(pid)
        hid = self.primary_helper_id
        if hid is not None:
            yield self.env.process(self.send_nack_cn(hid, pid, 0))
            hx, hy = self.primary_helper_pos
            dist = math.hypot(self.x - hx, self.y - hy)
            rtt_h = dist / SOUND_SPEED * 2 + CHUNKS_SYS * BITS_PER_CHUNK / BIT_RATE + 0.5
            yield self.env.timeout(rtt_h)
        if not isinstance(self.soft_buffer.get(pid), str):
            yield self.env.process(self.send_nack(
                self.hop_source.get(pid, pkt.hop_tx), pid, 0, False))
        self._coordinating.discard(pid)

    def _charq_nack(self, pkt, pid, ratio):
        """C-HARQ: primary helper sends RV1→RV2→RV3 sequentially"""
        if pid in self._coordinating: return
        self._coordinating.add(pid)
        hid = self.primary_helper_id
        if hid is not None:
            hx, hy = self.primary_helper_pos
            dist = math.hypot(self.x - hx, self.y - hy)
            for rv_l in range(1, 4):
                if isinstance(self.soft_buffer.get(pid), str): break
                yield self.env.process(self.send_nack_cn(hid, pid, rv_l))
                rtt_h = dist / SOUND_SPEED * 2 + CHARQ_RV_SZ[rv_l - 1] * BITS_PER_CHUNK / BIT_RATE + 0.3
                yield self.env.timeout(rtt_h)
        if not isinstance(self.soft_buffer.get(pid), str):
            yield self.env.process(self.send_nack(
                self.hop_source.get(pid, pkt.hop_tx), pid, 0, False))
        self._coordinating.discard(pid)

    def _select_rv(self, ratio):
        if ratio < 0.3: return 3
        elif ratio < 0.5: return 2
        elif ratio < 0.7: return 1
        return 0

    # ---------- CA-CHARQ Helper contention ----------
    def contend(self, pkt, my_c, creation_time):
        pid = pkt.pid
        if pid in self.helper_cancel_events: return
        score = (W1 * min(my_c, 1.5)
                 + W2 * max(0.0, min(1.0, self.energy / INITIAL_ENERGY))
                 + W3 * 0.5)
        t = (1.0 - np.clip(score, 0.0, 1.0)) * T_MAX_WINDOW * 2
        cancel = simpy.Event(self.env)
        self.helper_cancel_events[pid] = cancel
        r = yield self.env.timeout(t) | cancel
        self.helper_cancel_events.pop(pid, None)
        if cancel in r: return
        self.helper_tx_cnt[pid] += 1
        rv = pkt.nack_requested_rv
        yield self.env.process(self.send_data(pkt.hop_tx, pid, rv, creation_time))

    # ---------- Send methods ----------
    def _tx_pkt(self, pkt):
        dur = pkt.tx_duration()
        self.stats.record_tx(pkt.num_chunks, dur)
        if pkt.pkt_type == PKT_DATA: self.stats.record_data_tx()
        elif pkt.pkt_type == PKT_NACK: self.stats.record_nack_tx()
        elif pkt.pkt_type == PKT_ACK: self.stats.record_ack_tx()
        self.energy -= TX_POWER_W * dur
        yield self.env.timeout(dur)
        self.network.broadcast(self, pkt)

    def send_data(self, target, pid, rv, creation_time):
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target, pid, rv, creation_time)
        yield self.env.process(self._tx_pkt(pkt))

    def send_data_cn(self, target, pid, cn_rv, creation_time):
        """Send data with cn_rv for C-HARQ FEC"""
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target, pid, 0, creation_time, cn_rv=cn_rv)
        yield self.env.process(self._tx_pkt(pkt))

    def send_ack(self, target, pid):
        pkt = PhysicalPacket(PKT_ACK, self.node_id, target, pid)
        yield self.env.process(self._tx_pkt(pkt))

    def send_nack(self, target, pid, rv, skip_h):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid, rv)
        pkt.nack_requested_rv = rv; pkt.skip_helper = skip_h
        yield self.env.process(self._tx_pkt(pkt))

    def send_nack_cn(self, target, pid, cn_rv):
        """NACK-CN: directed to specific helper with requested RV"""
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid, 0)
        pkt.cn_rv = cn_rv; pkt.nack_requested_rv = cn_rv
        yield self.env.process(self._tx_pkt(pkt))

# =============================================
# 5. Channel
# =============================================
class Channel:
    def __init__(self, env, noise_var, k=2.0):
        self.env = env; self.nodes = []
        self.noise_var = noise_var
        self.los = math.sqrt(k / (k + 1)); self.nlos = math.sqrt(1.0 / (2 * (k + 1)))
    def broadcast(self, sender, pkt):
        for rx in self.nodes:
            if rx is sender: continue
            dist = math.hypot(sender.x - rx.x, sender.y - rx.y)
            prop = dist / SOUND_SPEED
            clone = PhysicalPacket(pkt.pkt_type, pkt.hop_tx, pkt.hop_rx,
                                   pkt.pid, pkt.rv_level, pkt.creation_time, cn_rv=pkt.cn_rv)
            clone.nack_requested_rv = pkt.nack_requested_rv
            clone.skip_helper = pkt.skip_helper; clone.num_chunks = pkt.num_chunks
            clone.start_idx = pkt.start_idx; clone.end_idx = pkt.end_idx
            if pkt.pkt_type == PKT_DATA:
                dkm = dist / 1000.0
                loss = dkm**1.5 * (10.0**(0.04 * dkm)) + 1e-20
                asnr = (TX_POWER_W / loss) / self.noise_var
                n = clone.num_chunks
                I = self.los + self.nlos * np.random.randn(n)
                Q = self.nlos * np.random.randn(n)
                clone.received_snr_array = asnr * (I**2 + Q**2)
                clone.avg_snr_linear = float(np.mean(clone.received_snr_array))
            else:
                clone.received_snr_array = None
            self.env.process(self._deliver(rx, clone, prop))
    def _deliver(self, rx, pkt, delay):
        yield self.env.timeout(delay); rx.inbox.put(pkt)

# =============================================
# 6. Run single simulation
# =============================================
def run_sim(snr_db, protocol, sim_time=1500, seed=0):
    random.seed(seed); np.random.seed(seed)
    env = simpy.Environment(); stats = StatsTracker(sim_time)
    nv = noise_var_for_snr_db(snr_db); ch = Channel(env, nv, k=RICIAN_K)

    routers = []
    for i in range(NUM_HOPS + 1):
        n = UnderwaterNode(env, i, i * HOP_DIST, 0, 'ROUTER', protocol, stats, ch, nv)
        if i < NUM_HOPS: n.next_hop_id = i + 1
        if i == NUM_HOPS: n.is_dest = True
        routers.append(n); ch.nodes.append(n)

    if protocol != PROTO_SW:
        R = HOP_DIST
        for i in range(NUM_HOPS):
            sx, dx = i * R, (i + 1) * R
            hid = 10 + i * N_HELPERS_PER_HOP
            placed = 0; primary_set = False
            while placed < N_HELPERS_PER_HOP:
                x = sx + random.random() * R
                y = (random.random() * 2 - 1) * R
                if math.hypot(x - sx, y) <= R and math.hypot(x - dx, y) <= R:
                    h = UnderwaterNode(env, hid + placed, x, y, 'HELPER', protocol, stats, ch, nv)
                    h.helper_for_link = (i, i + 1)
                    if not primary_set:
                        h.is_primary = True; primary_set = True
                        # Notify source & dest routers
                        routers[i].primary_helper_id = hid + placed
                        routers[i].primary_helper_pos = (x, y)
                        routers[i + 1].primary_helper_id = hid + placed
                        routers[i + 1].primary_helper_pos = (x, y)
                    ch.nodes.append(h); placed += 1

    def gen():
        pid = 0
        while True:
            routers[0].tx_queue.put((pid, env.now)); pid += 1
            yield env.timeout(random.expovariate(1.0 / 30.0))

    env.process(gen()); env.run(until=sim_time)

    return {
        "delay": stats.avg_delay(), "delay_std": stats.delay_std(),
        "overhead": stats.overhead(), "throughput": stats.throughput(),
        "drop_rate": stats.drop_rate(), "energy_eff": stats.energy_eff(),
        "success": stats.e2e_success, "drops": stats.e2e_drops,
        "data_tx": stats.total_data_tx, "nack_tx": stats.total_nack_tx, "ack_tx": stats.total_ack_tx,
        "actual_snr": avg_snr_db(nv),
    }

# =============================================
# 7. Monte Carlo
# =============================================
def mc_run(snr_db, protocol, sim_time, n_runs):
    delays, ovhds, tputs, drops, eeffs = [], [], [], [], []
    for run_i in range(n_runs):
        s = abs(42 + run_i * 7919 + int(snr_db * 3571) + (1 << 20)) % (2**31 - 1)
        r = run_sim(snr_db, protocol, sim_time, seed=s)
        delays.append(r['delay'] if not math.isnan(r['delay']) else None)
        ovhds.append(r['overhead'] if not math.isnan(r['overhead']) else None)
        tputs.append(r['throughput']); drops.append(r['drop_rate'])
        eeffs.append(r['energy_eff'] if not math.isnan(r['energy_eff']) else None)
    def ci(arr):
        a = np.array([x for x in arr if x is not None], dtype=float)
        if len(a) == 0: return float('nan'), 0.0
        return float(np.mean(a)), 1.96 * float(np.std(a, ddof=1) / math.sqrt(len(a)))
    dm, dci = ci(delays); om, oci = ci(ovhds); tm, tci = ci(tputs)
    drm, drci = ci(drops); em, eci = ci(eeffs)
    return {"delay_mean": dm, "delay_ci95": dci, "overhead_mean": om, "overhead_ci95": oci,
            "throughput_mean": tm, "throughput_ci95": tci, "drop_rate_mean": drm, "drop_rate_ci95": drci,
            "energy_eff_mean": em, "energy_eff_ci95": eci}

# =============================================
# 8. Main
# =============================================
if __name__ == "__main__":
    SNR_LIST = np.arange(0, 6.01, 0.5)
    SIM_TIME = 1500; N_RUNS = 3

    PROTOCOLS = []
    if ENABLE['SW_ARQ']: PROTOCOLS.append(PROTO_SW)
    if ENABLE['CARQ']:   PROTOCOLS.append(PROTO_CARQ)
    if ENABLE['CHARQ']:  PROTOCOLS.append(PROTO_CHARQ)
    if ENABLE['CA']:     PROTOCOLS.append(PROTO_CA)

    COLORS = {PROTO_SW: '#4C72B0', PROTO_CARQ: '#DD8452',
              PROTO_CHARQ: '#55A868', PROTO_CA: '#C44E52'}
    MARKERS = {PROTO_SW: 's', PROTO_CARQ: '^', PROTO_CHARQ: 'D', PROTO_CA: 'o'}

    results = {p: {'delay': ([], []), 'overhead': ([], []),
                   'throughput': ([], []), 'drop_rate': ([], []), 'energy_eff': ([], [])}
               for p in PROTOCOLS}

    print("=" * 70)
    print(f" CA-CHARQ v11 (Design Spec) — SNR {SNR_LIST[0]:.1f}-{SNR_LIST[-1]:.1f}dB | SIM={SIM_TIME}s")
    print(f" Protocols: {' | '.join(PROTOCOLS)}")
    print(f" Hops={NUM_HOPS}×{HOP_DIST}m | Helpers={N_HELPERS_PER_HOP}/hop | skip_CA={CA_HELPER_SKIP_RATIO}")
    print("=" * 70)

    for proto in PROTOCOLS:
        print(f"\n--- {proto} ---")
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
            results[proto]['energy_eff'][0].append(r['energy_eff_mean'])
            results[proto]['energy_eff'][1].append(r['energy_eff_ci95'])
            d_str = f"{r['delay_mean']:8.1f}s" if not math.isnan(r['delay_mean']) else "     n/a"
            print(f"  SNR={snr:4.1f}dB | D={d_str}±{r['delay_ci95']:5.0f} | Ov={r['overhead_mean']:6.2f}x | "
                  f"Tput={r['throughput_mean']:6.1f} | Dr={r['drop_rate_mean']:.2f}")

    # ---- Save TXT ----
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v11_results.txt")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("=" * 90 + "\n")
        f.write(" CA-CHARQ v11 (Design Spec) Simulation Results\n")
        f.write(f" SNR: {SNR_LIST[0]:.1f}-{SNR_LIST[-1]:.1f}dB | SIM={SIM_TIME}s | RUNS={N_RUNS}\n")
        f.write(f" Hops={NUM_HOPS}×{HOP_DIST}m | Helpers={N_HELPERS_PER_HOP}/hop | Rician K={RICIAN_K}\n")
        f.write(f" TARGET_MI={TARGET_MI} | skip_CA={CA_HELPER_SKIP_RATIO}\n")
        f.write("=" * 90 + "\n\n")
        for mname, mkey, mfmt in [
            ("End-to-End Delay (s)", "delay", "{:8.1f} ±{:5.1f}"),
            ("Transmission Overhead (x)", "overhead", "{:6.2f} ±{:.2f}"),
            ("Throughput (chunks/s)", "throughput", "{:6.2f} ±{:.2f}"),
            ("Drop Rate", "drop_rate", "{:.3f} ±{:.3f}"),
            ("Energy Efficiency (bits/J)", "energy_eff", "{:6.2f} ±{:.2f}")]:
            f.write(f"--- {mname} ---\n")
            f.write(f"{'SNR':>7s}" + "".join(f"  {p:>22s}" for p in PROTOCOLS) + "\n")
            for i, s in enumerate(SNR_LIST):
                row = f"{s:+5.1f}dB"
                for proto in PROTOCOLS:
                    v = results[proto][mkey][0][i]
                    e = results[proto][mkey][1][i]
                    row += ("  " + mfmt.format(v, e)) if not math.isnan(v) else f"  {'n/a':>22s}"
                f.write(row + "\n")
            f.write("\n")
        f.write("--- CA-CHARQ vs S&W ARQ Gap ---\n")
        f.write(f"{'SNR':>7s}  {'Delay_gap%':>12s}  {'Ovhd_gap%':>12s}  {'EE_gap%':>12s}\n")
        for i, s in enumerate(SNR_LIST):
            d_sw = results[PROTO_SW]['delay'][0][i]
            d_ca = results[PROTO_CA]['delay'][0][i]
            o_sw = results[PROTO_SW]['overhead'][0][i]
            o_ca = results[PROTO_CA]['overhead'][0][i]
            e_sw = results[PROTO_SW]['energy_eff'][0][i]
            e_ca = results[PROTO_CA]['energy_eff'][0][i]
            dg = ((d_ca - d_sw) / d_sw * 100) if d_sw > 0 and not math.isnan(d_sw + d_ca) else float('nan')
            og = ((o_ca - o_sw) / o_sw * 100) if o_sw > 0 and not math.isnan(o_sw + o_ca) else float('nan')
            eg = ((e_ca - e_sw) / e_sw * 100) if e_sw > 0 and not math.isnan(e_sw + e_ca) else float('nan')
            f.write(f"{s:+5.1f}dB  {dg:+11.1f}%  {og:+11.1f}%  {eg:+11.1f}%\n")
    print(f"\n[OK] Results → {out_path}")

    # ---- Plots ----
    plt.rcParams.update({'font.size': 11, 'legend.fontsize': 9,
                         'xtick.labelsize': 9, 'ytick.labelsize': 9})
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    for proto in PROTOCOLS:
        y = np.array(results[proto]['delay'][0], dtype=float)
        mask = ~np.isnan(y) & (y < 1e5)
        if mask.any():
            ax1.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto], markeredgewidth=0.8)
    ax1.set_xlabel("SNR (dB)"); ax1.set_ylabel("E2E Delay (s)"); ax1.grid(True, ls='-', alpha=0.15, color='gray')
    ax1.legend(frameon=True, fancybox=False, edgecolor='gray', loc='upper right'); ax1.set_title("v11 Delay")
    for proto in PROTOCOLS:
        y = np.array(results[proto]['overhead'][0], dtype=float)
        mask = ~np.isnan(y) & (y < 500)
        if mask.any():
            ax2.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto], markeredgewidth=0.8)
    ax2.set_xlabel("SNR (dB)"); ax2.set_ylabel("Overhead (x)"); ax2.grid(True, ls='-', alpha=0.15, color='gray')
    ax2.legend(frameon=True, fancybox=False, edgecolor='gray', loc='upper right'); ax2.set_title("v11 Overhead")
    plt.tight_layout(); plt.savefig("v11_Delay_Overhead.png", dpi=200, bbox_inches='tight'); print("[OK] v11_Delay_Overhead.png")

    fig2, ax3 = plt.subplots(1, 1, figsize=(7, 5))
    for proto in PROTOCOLS:
        y = np.array(results[proto]['throughput'][0], dtype=float)
        mask = ~np.isnan(y)
        if mask.any():
            ax3.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto], markeredgewidth=0.8)
    ax3.set_xlabel("SNR (dB)"); ax3.set_ylabel("Throughput (chunks/s)"); ax3.grid(True, ls='-', alpha=0.15, color='gray')
    ax3.legend(frameon=True, fancybox=False, edgecolor='gray', loc='lower right'); ax3.set_title("v11 Throughput")
    plt.tight_layout(); plt.savefig("v11_Throughput.png", dpi=200, bbox_inches='tight'); print("[OK] v11_Throughput.png")

    fig3, ax4 = plt.subplots(1, 1, figsize=(7, 5))
    for proto in PROTOCOLS:
        y = np.array(results[proto]['energy_eff'][0], dtype=float)
        mask = ~np.isnan(y) & (y > 0)
        if mask.any():
            ax4.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto]+'-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto], markeredgewidth=0.8)
    ax4.set_xlabel("SNR (dB)"); ax4.set_ylabel("Energy Eff (bits/J)"); ax4.grid(True, ls='-', alpha=0.15, color='gray')
    ax4.legend(frameon=True, fancybox=False, edgecolor='gray', loc='upper left'); ax4.set_title("v11 Energy Efficiency")
    plt.tight_layout(); plt.savefig("v11_EnergyEfficiency.png", dpi=200, bbox_inches='tight'); print("[OK] v11_EnergyEfficiency.png")
    plt.close('all')

    print(f"\n{'='*70}\nDelay (s) Summary")
    hdr = f"{'SNR':>7s}" + "".join(f"  {p:>15s}" for p in PROTOCOLS); print(hdr)
    for i, s in enumerate(SNR_LIST):
        row = f"{s:+5.1f}dB"
        for proto in PROTOCOLS:
            v = results[proto]['delay'][0][i]
            row += f"  {v:13.1f}s" if not math.isnan(v) else f"  {'n/a':>15s}"
        print(row)
    print(f"\n{'='*70}\nOverhead (x) Summary")
    for i, s in enumerate(SNR_LIST):
        row = f"{s:+5.1f}dB"
        for proto in PROTOCOLS:
            v = results[proto]['overhead'][0][i]
            row += f"  {v:13.2f}x" if not math.isnan(v) else f"  {'n/a':>15s}"
        print(row)
    print("\n" + "=" * 70 + "\n v11 Done.\n" + "=" * 70)
