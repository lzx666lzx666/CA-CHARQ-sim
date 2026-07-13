#!/usr/bin/env python3
"""
CA-CHARQ v7 (MAX) — Multi-Chain Cooperative HARQ with MAC
==========================================================
v7: _link_level() activated via SNR sliding window (only change vs v6).
v6 baseline: B1 contend() coords, B2 chain_id, B3 c_pkt from PER, D4-6.

Scenario: 3 fan-shaped chains, 5 hops × 600m each.
Helpers CA-CHARQ: 6 randomly placed; Controls: 15 random (per-chain pre-assigned).
MAC: half-duplex + receiver capture.
"""

import simpy, math, random, numpy as np, matplotlib; matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from collections import defaultdict

from ca_charq_pro_v4_analytic import (
    SOUND_SPEED, BIT_RATE, TX_POWER_W, FREQ_KHZ, HOP_DIST, NUM_HOPS, MAX_RETRIES,
    RS_N_SYM, RS_K_SYM, RS_T_BASE, RS_BITS_PER_SYM, RS_TOTAL_BITS,
    MOD_BITS, N_CHANNEL_SYMS, RV_EXTRA_RS_SYMS,
    thorp_alpha, transmission_loss, snr_linear_tx_power, noise_var_for_target_snr_db,
    qpsk_ser_instant, average_qpsk_ser_rayleigh, ser_post_chase,
    per_rs_gaussian, compute_cpkt_rs, _qpsk_to_rs_ser, RV_MATRIX, link_level_from_gamma,
    compute_cpkt,
)

PROTO_SW_ARQ = "S&W ARQ"
PROTO_CARQ   = "C-ARQ"
PROTO_CHARQ  = "C-HARQ"
PROTO_CA     = "CA-CHARQ"

# ==========================================
# 0. Multi-chain Parameters
# ==========================================
NUM_CHAINS       = 3
N_HELPERS_TOTAL  = 6
N_HELPERS_PER_CHAIN_CTRL = 5
W1, W2, W3 = 0.40, 0.25, 0.35
T_MAX_WINDOW    = 1.5
T_PROTECTION_GAP = 0.05
INITIAL_ENERGY   = 10000.0
CHARQ_FEC_EXTRA  = 12
MAX_PARITY_QPSK  = 54
MIN_CAPTURE_SNR_LINEAR = 0.05
CHAIN_Y_OFFSETS = [-600, 0, 600]
T_BACKOFF_JITTER  = 0.08
SNR_WINDOW_SIZE = 8   # v7: sliding window for _link_level()

# 5-level RV
RV_EXTRA = {1: 6, 1.5: 9, 2: 12, 2.5: 15, 3: 18}


# ==========================================
# 1. HelperScheduler
# ==========================================
class HelperScheduler:
    """Per-helper priority queue with pending auto-processing."""
    def __init__(self, env):
        self.env = env
        self.busy_until = 0.0
        self.current      = None
        self.pending      = []  # [(priority, chain_id, pid, target, rv, creation_time), ...]
        self.served_log   = {}
        self.cross_talk_count = 0

    def request(self, chain_id, pid, target, cpkt, rv_base, creation_time):
        priority = 0.6 * (1.0 - cpkt / 3.0) + 0.2  # +0.2 for Q_link proxy

        key = (chain_id, pid)
        if key in self.served_log:
            rv_base = min(3.0, self.served_log[key][0] + 0.5)
            priority *= 0.7
            self.served_log[key] = (rv_base, self.env.now, self.served_log[key][2] + 1)
        else:
            self.served_log[key] = (rv_base, self.env.now, 1)

        if self._is_busy():
            entry = (priority, chain_id, pid, target, rv_base, creation_time)
            self.pending.append(entry)
            self.pending.sort(key=lambda x: -x[0])
            return 'queue', rv_base
        else:
            dur = (rv_base * RS_BITS_PER_SYM) / BIT_RATE + 0.05
            self.busy_until = self.env.now + dur
            self.current = (chain_id, pid, priority, rv_base)
            return 'serve', rv_base

    def on_complete(self):
        self.busy_until = self.env.now; self.current = None
        if self.pending:
            pri, cid, pid, target, rv, ct = self.pending.pop(0)
            dur = (rv * RS_BITS_PER_SYM) / BIT_RATE + 0.05
            self.busy_until = self.env.now + dur
            self.current = (cid, pid, pri, rv)
            return 'serve_next', rv, target, pid, ct, cid
        return 'idle', 0, None, 0, 0.0, 0

    def _is_busy(self):
        return self.env.now < self.busy_until


# ==========================================
# 2. MultiChainStats
# ==========================================
class MultiChainStats:
    def __init__(self, sim_time, n_chains):
        self.sim_time = sim_time
        self.n_chains = n_chains
        self.chain = [self._make_chain_stats() for _ in range(n_chains)]

    def _make_chain_stats(self):
        return {
            'tx_chunks': 0, 'data_tx': 0, 'nack_tx': 0, 'ack_tx': 0,
            'energy': 0.0, 'delays': [], 'success': 0, 'drops': 0, 'fate': {},
            'collisions': 0
        }

    def record_tx(self, cid, n_chunks):  self.chain[cid]['tx_chunks'] += n_chunks
    def record_data_tx(self, cid):       self.chain[cid]['data_tx'] += 1
    def record_nack_tx(self, cid):       self.chain[cid]['nack_tx'] += 1
    def record_ack_tx(self, cid):        self.chain[cid]['ack_tx'] += 1
    def record_energy(self, cid, j):     self.chain[cid]['energy'] += j
    def record_collision(self, cid):     self.chain[cid]['collisions'] += 1

    def e2e_success(self, cid, pid, delay):
        c = self.chain[cid]
        if pid not in c['fate']:
            c['fate'][pid] = 'success'
            c['success'] += 1
            c['delays'].append(delay)

    def e2e_drop(self, cid, pid):
        c = self.chain[cid]
        if pid not in c['fate']:
            c['fate'][pid] = 'dropped'
            c['drops'] += 1

    def get_chain_delay(self, cid):
        c = self.chain[cid]
        return float(np.mean(c['delays'])) if c['delays'] else float('nan')

    def get_chain_overhead(self, cid):
        c = self.chain[cid]
        useful = c['success'] * N_CHANNEL_SYMS
        return c['tx_chunks'] / useful if useful > 0 else float('nan')

    def get_chain_ee(self, cid):
        c = self.chain[cid]
        bits = c['success'] * RS_TOTAL_BITS
        return bits / c['energy'] if c['energy'] > 0 else float('nan')

    def get_global_delay(self):
        all_d = []
        for c in self.chain: all_d.extend(c['delays'])
        return float(np.mean(all_d)) if all_d else float('nan')

    def get_global_overhead(self):
        tot_chunks = sum(c['tx_chunks'] for c in self.chain)
        tot_succ = sum(c['success'] for c in self.chain)
        return tot_chunks / (tot_succ * N_CHANNEL_SYMS) if tot_succ > 0 else float('nan')

    def get_global_ee(self):
        tot_bits = sum(c['success'] * RS_TOTAL_BITS for c in self.chain)
        tot_energy = sum(c['energy'] for c in self.chain)
        return tot_bits / tot_energy if tot_energy > 0 else float('nan')

    def get_global_collisions(self):
        return sum(c['collisions'] for c in self.chain)


# ==========================================
# 3. Packets (with chain_id)
# ==========================================
PKT_DATA, PKT_ACK, PKT_NACK = 'DATA', 'ACK', 'NACK'

class PhysicalPacket:
    def __init__(self, pkt_type, hop_tx, hop_rx, pid, rv_level=0, creation_time=0.0,
                 fec_idx=-1, chain_id=0):
        self.pkt_type = pkt_type
        self.hop_tx, self.hop_rx = hop_tx, hop_rx
        self.pid, self.rv_level = pid, rv_level
        self.creation_time, self.fec_idx = creation_time, fec_idx
        self.chain_id = chain_id
        self.cpkt = -1; self.num_chunks = 0; self.received_snr = np.array([])

        if pkt_type == PKT_DATA:
            if fec_idx > 0:
                self.num_chunks = CHARQ_FEC_EXTRA // 2
            elif rv_level > 0:
                self.num_chunks = RV_EXTRA.get(rv_level, 6)
            else:
                self.num_chunks = N_CHANNEL_SYMS
        elif pkt_type in (PKT_ACK, PKT_NACK):
            self.num_chunks = 2
        else:
            self.num_chunks = 1

    def tx_duration(self):
        return self.num_chunks / BIT_RATE


# ==========================================
# 4. Channel (with cross-chain detection)
# ==========================================
class Channel:
    def __init__(self, env, noise_var, stats=None):
        self.env, self.nodes = env, []
        self.noise_var = noise_var
        self.cross_talk_events = 0
        self.collision_drops = 0
        self.stats = stats

    def broadcast(self, sender, pkt):
        for rx in self.nodes:
            if rx is sender: continue
            dist = math.hypot(sender.x - rx.x, sender.y - rx.y)
            prop = dist / SOUND_SPEED
            self.env.process(self._deliver(rx, sender, pkt, dist, prop))

    def _deliver(self, rx, sender, pkt, dist, delay):
        yield self.env.timeout(delay)

        # L2: half-duplex — rx cannot receive while transmitting
        if hasattr(rx, 'tx_busy_until') and self.env.now < rx.tx_busy_until:
            self.collision_drops += 1
            if self.stats:
                self.stats.record_collision(getattr(pkt, 'chain_id', 0))
            return

        # L2: single-signal constraint — rx already processing another signal
        if hasattr(rx, 'rx_busy_until') and self.env.now < rx.rx_busy_until:
            self.collision_drops += 1
            if self.stats:
                self.stats.record_collision(getattr(pkt, 'chain_id', 0))
            return

        # Compute SNR before capture decision
        mean_snr = 0.0
        if pkt.num_chunks > 0:
            loss = transmission_loss(dist, FREQ_KHZ)
            asnr = sender.tx_power / (loss * self.noise_var)
            I = np.random.randn(pkt.num_chunks) / math.sqrt(2.0)
            Q = np.random.randn(pkt.num_chunks) / math.sqrt(2.0)
            pkt.received_snr = asnr * (I**2 + Q**2)
            mean_snr = float(np.mean(pkt.received_snr))

        # Fix#5: capture receiver only if SNR exceeds threshold (weak signals don't block)
        dur = pkt.tx_duration()
        if pkt.num_chunks == 0 or mean_snr >= MIN_CAPTURE_SNR_LINEAR:
            rx.rx_busy_until = self.env.now + dur

        # Cross-chain detection for helper's scheduler
        if (hasattr(rx, 'scheduler') and rx.scheduler and
                hasattr(pkt, 'chain_id') and hasattr(rx, 'current_chain_id')):
            if pkt.chain_id != rx.current_chain_id and rx.current_chain_id >= 0:
                rx.scheduler.cross_talk_count += 1
        rx.inbox.put(pkt)


# ==========================================
# 5. UnderwaterNode (multi-chain aware)
# ==========================================
class UnderwaterNode:
    def __init__(self, env, node_id, x, y, role, protocol, stats, network, nv, chain_id=0):
        self.env = env; self.node_id = node_id; self.x, self.y = x, y
        self.role, self.protocol = role, protocol
        self.stats, self.network = stats, network
        self.nv, self.chain_id = nv, chain_id
        self.inbox = simpy.Store(env); self.tx_queue = simpy.Store(env)
        self.energy = INITIAL_ENERGY; self.tx_power = TX_POWER_W

        # L1: half-duplex / single-signal constraint
        self.tx_busy_until = 0.0
        self.rx_busy_until = 0.0

        self.soft_buffer = {}; self.merge_count = defaultdict(int)
        self.hop_source = {}; self.nack_count = defaultdict(int); self.nack_sent = set()
        self.fec_sent = defaultdict(int); self.helper_sent = defaultdict(int)
        self.ack_events = {}; self.pending_response = {}; self.helper_ack_events = {}
        self.helper_for_link = []   # list of (src_id, dst_id) tuples — full freedom
        self.is_selected         = False
        self.is_low_snr_selected   = False; self.is_selected = False
        self.is_low_snr_selected = False
        self.helper_cancel_events = {}; self.helper_tx_cnt = defaultdict(int)
        self.next_hop_id = None; self.is_dest = False
        self.snr_history = []     # v7: sliding window for _link_level()

        # v5 scheduler (helpers only)
        self.scheduler = None
        self.current_chain_id = -1  # for cross-chain detection

        self.env.process(self.recv_loop())
        if self.role == 'ROUTER':
            self.env.process(self.tx_loop())

    def _hkey(self, pid, pkt_chain=None):
        """Compound key for helpers: (chain_id, pid). Routers use pid only."""
        if self.role == 'HELPER' and pkt_chain is not None and pkt_chain >= 0:
            return (pkt_chain, pid)
        return pid

    # ========== Tx Loop ==========
    def tx_loop(self):
        while True:
            pid, creation_time = yield self.tx_queue.get()
            hop_ok = False
            self.pending_response.pop(pid, None)

            yield self.env.process(self._send_data(self.next_hop_id, pid, 0, creation_time))
            rtt = HOP_DIST / SOUND_SPEED * 2
            gto = rtt + 1.5

            for retry_i in range(MAX_RETRIES):
                if pid in self.pending_response:
                    msg = self.pending_response.pop(pid)
                    if msg['type'] == 'ACK':
                        hop_ok = True; break
                    elif self.protocol == PROTO_CA:
                        cpkt = msg.get('cpkt', 2)
                        if cpkt >= 3:
                            if self._grace_period(pid, cpkt):
                                hop_ok = True; break
                        yield self.env.process(self._send_data(self.next_hop_id, pid, 0, creation_time))
                        continue
                    else:
                        yield self.env.process(self._send_data(self.next_hop_id, pid, 0, creation_time))
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
                        hop_ok = True; break
                    elif msg['type'] == 'NACK':
                        if self.protocol == PROTO_CA:
                            cpkt = msg.get('cpkt', 2)
                            if cpkt >= 3:
                                if self._grace_period(pid, cpkt):
                                    hop_ok = True; break
                        yield self.env.process(self._send_data(self.next_hop_id, pid, 0, creation_time))
                else:
                    yield self.env.process(self._send_data(self.next_hop_id, pid, 0, creation_time))

            if not hop_ok and pid in self.pending_response:
                msg = self.pending_response.pop(pid)
                if msg['type'] == 'ACK': hop_ok = True
            if not hop_ok:
                self.stats.e2e_drop(self.chain_id, pid)

    def _grace_period(self, pid, cpkt):
        n_extra = RV_EXTRA.get(1, 6)
        rv_tx_t = (n_extra * RS_BITS_PER_SYM) / BIT_RATE
        grace_t = rv_tx_t + T_MAX_WINDOW / 4 + 3 * HOP_DIST / SOUND_SPEED + 0.3
        grace_to = self.env.timeout(grace_t)
        ack_he = simpy.Event(self.env)
        self.helper_ack_events[pid] = ack_he
        gr = yield grace_to | ack_he
        self.helper_ack_events.pop(pid, None)
        return ack_he in gr

    # ========== Rx Loop ==========
    def recv_loop(self):
        while True:
            pkt = yield self.inbox.get()
            self.env.process(self.handle(pkt))

    def handle(self, pkt):
        pid = pkt.pid

        if pkt.pkt_type == PKT_DATA:
            # --- Router: only accept matching chain_id ---
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                if getattr(pkt, 'chain_id', self.chain_id) != self.chain_id:
                    return  # cross-chain rejection
                if pid not in self.soft_buffer:
                    self.soft_buffer[pid] = np.zeros(N_CHANNEL_SYMS + MAX_PARITY_QPSK)
                    self.hop_source[pid] = pkt.hop_tx
                buf = self.soft_buffer[pid]
                if isinstance(buf, str):  # already decoded
                    yield self.env.process(self._send_ack(self.hop_source.get(pid, pkt.hop_tx), pid))
                    return

                self.merge_count[pid] += 1
                n_snr = min(len(pkt.received_snr), len(buf))
                if pkt.fec_idx > 0 or pkt.rv_level > 0:
                    par_start = N_CHANNEL_SYMS
                    if pkt.fec_idx == 2:
                        par_start += (CHARQ_FEC_EXTRA // 2) * (RS_BITS_PER_SYM // MOD_BITS)
                    for i in range(n_snr):
                        base = par_start + (RS_BITS_PER_SYM // MOD_BITS) * i
                        buf[base:base + RS_BITS_PER_SYM // MOD_BITS] += pkt.received_snr[i]
                else:
                    buf[:n_snr] += pkt.received_snr[:n_snr]

                decode_ok = self._try_decode(pid)
                if decode_ok:
                    self.soft_buffer[pid] = "SUCCESS"
                    yield self.env.process(self._send_ack(self.hop_source.get(pid, pkt.hop_tx), pid))
                    if self.is_dest:
                        self.stats.e2e_success(self.chain_id, pid, self.env.now - pkt.creation_time)
                    else:
                        self.tx_queue.put((pid, pkt.creation_time))
                elif self.merge_count[pid] >= MAX_RETRIES + 1:
                    self.soft_buffer.pop(pid, None); self.merge_count.pop(pid, None)
                else:
                    if (self.protocol == PROTO_CA and pkt.hop_tx == self.hop_source.get(pid)):
                        active = buf[buf > 0]
                        if len(active) > 0:
                            gamma_est = float(np.mean(active))
                            rs_ser_est = _qpsk_to_rs_ser(ser_post_chase(gamma_est, 2))
                            eta = RS_N_SYM * rs_ser_est / RS_T_BASE
                            if eta < 0.5:     cpkt = 3
                            elif eta < 1.5:   cpkt = 2
                            elif eta < 3.0:   cpkt = 1
                            else:             cpkt = 0
                        else: cpkt = 0
                        yield self.env.process(self._send_nack_cpkt(self.hop_source[pid], pid, cpkt))
                    elif pkt.hop_tx == self.hop_source.get(pid) and pid not in self.nack_sent:
                        self.nack_sent.add(pid)
                        yield self.env.process(self._send_nack(self.hop_source[pid], pid))

            # --- helper cancel (CA-CHARQ cross-competition) ---
            if (self.role == 'HELPER' and self.protocol == PROTO_CA
                    and pid in self.helper_cancel_events
                    and pkt.hop_tx != self.node_id
                    and self.helper_for_link is not None
                    and pkt.hop_rx in [l[1] for l in self.helper_for_link]):
                ce = self.helper_cancel_events[pid]
                if not ce.triggered: ce.succeed()

            # --- helper overhear source RV0 ---
            elif (self.role == 'HELPER'
                  and (pkt.hop_tx, pkt.hop_rx) in self.helper_for_link
                  and pkt.rv_level == 0 and pkt.fec_idx <= 0):
                hp = self._hkey(pid, getattr(pkt, 'chain_id', -1))
                if hp not in self.soft_buffer:
                    self.soft_buffer[hp] = np.zeros(N_CHANNEL_SYMS + MAX_PARITY_QPSK)
                buf = self.soft_buffer[hp]
                if isinstance(buf, dict): return
                n_snr = min(len(pkt.received_snr), len(buf))
                buf[:n_snr] += pkt.received_snr[:n_snr]
                decode_ok = self._try_decode(hp)
                if decode_ok:
                    # v7: track SNR for _link_level()
                    if len(pkt.received_snr) > 0:
                        self.snr_history.append(float(np.mean(pkt.received_snr)))
                        if len(self.snr_history) > SNR_WINDOW_SIZE:
                            self.snr_history.pop(0)
                    if self.protocol == PROTO_CA:
                        # B3 fix: compute c_pkt from actual PER (not hardcoded 0.5)
                        per_now = self._compute_per(buf)
                        cpkt_h = compute_cpkt(per_now)
                        self.soft_buffer[hp] = {"status": "DECODED", "creation_time": pkt.creation_time,
                                                "c_pkt": 1.0 - per_now, "cpkt": cpkt_h}
                    else:
                        self.soft_buffer[hp] = {"status": "DECODED", "creation_time": pkt.creation_time}

        # --- NACK ---
        elif pkt.pkt_type == PKT_NACK:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                matched = False
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'NACK', 'cpkt': pkt.cpkt}); matched = True; break
                if not matched:
                    self.pending_response[pid] = {'type': 'NACK', 'cpkt': pkt.cpkt}

            elif self.role == 'HELPER' and self.protocol == PROTO_CA:
                link_match = (pkt.hop_rx, pkt.hop_tx)
                if link_match in self.helper_for_link:
                    hp = self._hkey(pid, getattr(pkt, 'chain_id', -1))
                    buf = self.soft_buffer.get(hp)
                    if isinstance(buf, dict) and buf.get("status") == "DECODED":
                        cpkt_v = pkt.cpkt
                        if cpkt_v >= 2:
                            # Cpkt=2/3: compete for helpers (scarce resource)
                            self.env.process(self.contend(pkt))
                        else:
                            # Cpkt=0/1: direct send via scheduler, only bottleneck-best helper responds
                            if cpkt_v <= 1 and (not self.is_low_snr_selected or self.helper_tx_cnt[pid] >= 3):
                                pass
                            else:
                                link_lvl = self._link_level()
                                rv = RV_MATRIX.get(cpkt_v, {0:3, 1:3, 2:3}).get(link_lvl, 3)
                                self.helper_tx_cnt[pid] += 1
                                nack_cid = getattr(pkt, 'chain_id', 0)
                                # v5: route through scheduler
                                if self.scheduler:
                                    status, rv_s = self.scheduler.request(
                                        nack_cid, pid, pkt.hop_tx, cpkt_v, rv, buf["creation_time"])
                                    if status == 'serve':
                                        yield self.env.process(self._send_data(
                                            pkt.hop_tx, pid, rv_s, buf["creation_time"], chain_id=nack_cid))
                                else:
                                    yield self.env.process(self._send_data(
                                        pkt.hop_tx, pid, rv, buf["creation_time"], chain_id=nack_cid))

            elif self.role == 'HELPER' and self.is_selected:
                if (pkt.hop_rx, pkt.hop_tx) in self.helper_for_link:
                    buf = self.soft_buffer.get(pid)
                    if isinstance(buf, dict) and buf.get("status") == "DECODED":
                        if self.protocol == PROTO_CHARQ:
                            if self.fec_sent[pid] == 0:
                                self.fec_sent[pid] = 1
                                yield self.env.process(self._send_fec(pkt.hop_tx, pid, 1, buf["creation_time"],
                                                                      chain_id=getattr(pkt, 'chain_id', 0)))
                            if self.fec_sent[pid] == 1:
                                self.fec_sent[pid] = 2
                                yield self.env.timeout(T_PROTECTION_GAP + (CHARQ_FEC_EXTRA // 2) * RS_BITS_PER_SYM / BIT_RATE)
                                yield self.env.process(self._send_fec(pkt.hop_tx, pid, 2, buf["creation_time"],
                                                                      chain_id=getattr(pkt, 'chain_id', 0)))
                        elif self.protocol == PROTO_CARQ:
                            cnt = self.helper_sent[pid]
                            if cnt < MAX_RETRIES:
                                self.helper_sent[pid] = cnt + 1
                                yield self.env.process(self._send_data(pkt.hop_tx, pid, 0, buf["creation_time"],
                                                                       chain_id=getattr(pkt, 'chain_id', 0)))

        # --- ACK ---
        elif pkt.pkt_type == PKT_ACK:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                matched = False
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'ACK'}); matched = True; break
                if not matched: self.pending_response[pid] = {'type': 'ACK'}
                if self.protocol == PROTO_CA and pid in self.helper_ack_events:
                    hev = self.helper_ack_events[pid]
                    if not hev.triggered: hev.succeed({'type': 'ACK'})
            # D6: helpers in competition cancel on hearing ACK (reliable, via destination)
            if self.role == 'HELPER' and self.protocol == PROTO_CA and pid in self.helper_cancel_events:
                ce = self.helper_cancel_events[pid]
                if not ce.triggered: ce.succeed()

    # ========== Helper Contention ==========
    def contend(self, pkt):
        pid = pkt.pid
        if pid in self.helper_cancel_events: return
        hp = self._hkey(pid, getattr(pkt, 'chain_id', -1))
        buf = self.soft_buffer.get(hp)
        if not isinstance(buf, dict) or buf.get("status") != "DECODED": return

        my_c = buf.get("c_pkt", 1.0)
        # B1 fix: compute correct coordinates from node IDs
        link_src, link_dst = (pkt.hop_rx, pkt.hop_tx)  # NACK: rx=src, tx=dst
        cid_for_pos = getattr(pkt, 'chain_id', 0)
        y_off = CHAIN_Y_OFFSETS[cid_for_pos % 3]
        hop_src = link_src % 100
        hop_dst = link_dst % 100
        sx, sy = hop_src * HOP_DIST, y_off
        dx, dy = hop_dst * HOP_DIST, y_off
        d_src = math.hypot(self.x - sx, self.y - sy)
        d_dst = math.hypot(self.x - dx, self.y - dy)
        dist = max(d_src, d_dst); prop_u = dist / SOUND_SPEED
        score = (W1 * min(my_c, 1.5) + W2 * max(0.0, min(1.0, self.energy / INITIAL_ENERGY))
                 + W3 / (1.0 + prop_u / 0.4))
        t_backoff = (1.0 - np.clip(score, 0.0, 1.0)) * T_MAX_WINDOW * 2
        t_backoff += max(T_PROTECTION_GAP / 4, 0.05)
        # D4: removed is_low_snr_selected 0.02s shortcut — compete fairly
        # D5: add random jitter for realistic backoff diversity
        t_backoff += random.uniform(0, T_BACKOFF_JITTER)

        cancel_ev = simpy.Event(self.env)
        self.helper_cancel_events[pid] = cancel_ev
        result = yield self.env.timeout(t_backoff) | cancel_ev
        if cancel_ev not in result:
            link_lvl = self._link_level()
            rv = RV_MATRIX.get(pkt.cpkt, {0:3, 1:3, 2:3, 3:1}).get(link_lvl, 2)
            self.helper_tx_cnt[pid] += 1
            nack_cid = getattr(pkt, 'chain_id', 0)
            # v6: route through scheduler for serialized helper access
            if self.scheduler:
                status, rv_s = self.scheduler.request(
                    nack_cid, pid, pkt.hop_tx, pkt.cpkt, rv, buf["creation_time"])
                if status == 'serve':
                    yield self.env.process(self._send_data(
                        pkt.hop_tx, pid, rv_s, buf["creation_time"], chain_id=nack_cid))
            else:
                yield self.env.process(self._send_data(
                    pkt.hop_tx, pid, rv, buf["creation_time"], chain_id=nack_cid))
        self.helper_cancel_events.pop(pid, None)

    def _scheduler_callback(self):
        try:
            res = self.scheduler.on_complete()
            while res[0] == 'serve_next':
                _, rv, target, pid, ct, cid = res
                yield self.env.process(self._send_data(target, pid, rv, ct, chain_id=cid))
                res = self.scheduler.on_complete()
        except Exception:
            pass  # drain failed silently; pending tasks remain for next opportunity

    def _link_level(self):
        if not self.snr_history:
            return 0
        avg_snr = sum(self.snr_history) / len(self.snr_history)
        if avg_snr > 1.0:      return 0  # Good
        elif avg_snr > 0.1:    return 1  # Medium
        else:                  return 2  # Poor

    # ========== PHY Decode ==========
    def _compute_per(self, soft_buf):
        active_mask = soft_buf > 0
        if self.protocol in (PROTO_SW_ARQ, PROTO_CARQ):
            if not np.any(active_mask): return 1.0
            ser_vec = np.array([qpsk_ser_instant(float(g)) for g in soft_buf[active_mask]])
            return 1.0 - np.prod(1.0 - ser_vec)
        n_active = int(np.sum(active_mask)); qpr = RS_BITS_PER_SYM // MOD_BITS
        extra_qpsk = max(0, n_active - N_CHANNEL_SYMS)
        n_rs_total = RS_N_SYM + extra_qpsk // qpr
        t_eff = RS_T_BASE + max(0, n_rs_total - RS_N_SYM) // 2
        active_vals = soft_buf[active_mask]; n_rs = len(active_vals) // qpr
        ser_rs_vec = np.zeros(n_rs)
        for i in range(n_rs):
            p = [qpsk_ser_instant(float(active_vals[qpr*i+j])) for j in range(qpr)]
            ser_rs_vec[i] = 1.0 - np.prod([1.0 - pj for pj in p])
        return per_rs_gaussian(ser_rs_vec, t_eff)

    def _try_decode(self, key):
        buf = self.soft_buffer[key]; per_val = self._compute_per(buf)
        return random.random() > per_val

    # ========== Send Methods ==========
    def _tx_pkt(self, pkt):
        dur = pkt.tx_duration()
        # Fix#1: wait for any ongoing transmission to finish (TX gating)
        if self.env.now < self.tx_busy_until:
            yield self.env.timeout(self.tx_busy_until - self.env.now)
        cid = getattr(pkt, 'chain_id', self.chain_id)
        self.stats.record_tx(cid, pkt.num_chunks)
        if pkt.pkt_type == PKT_DATA: self.stats.record_data_tx(cid)
        elif pkt.pkt_type == PKT_NACK: self.stats.record_nack_tx(cid)
        elif pkt.pkt_type == PKT_ACK: self.stats.record_ack_tx(cid)
        self.energy -= self.tx_power * dur
        self.stats.record_energy(cid, self.tx_power * dur)
        # L1: mark node busy for transmission duration (half-duplex)
        self.tx_busy_until = self.env.now + dur
        yield self.env.timeout(dur)
        self.network.broadcast(self, pkt)
        # Fix#3b: auto-drain scheduler queue after every transmission
        if self.scheduler is not None:
            self.env.process(self._scheduler_callback())

    def _send_data(self, target, pid, rv, creation_time, chain_id=None):
        cid = chain_id if chain_id is not None else self.chain_id
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target, pid, rv, creation_time,
                             chain_id=cid)
        yield self.env.process(self._tx_pkt(pkt))

    def _send_fec(self, target, pid, fec_idx, creation_time, chain_id=None):
        cid = chain_id if chain_id is not None else self.chain_id
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target, pid, 0, creation_time,
                              fec_idx=fec_idx, chain_id=cid)
        yield self.env.process(self._tx_pkt(pkt))

    def _send_ack(self, target, pid):
        pkt = PhysicalPacket(PKT_ACK, self.node_id, target, pid, chain_id=self.chain_id)
        yield self.env.process(self._tx_pkt(pkt))

    def _send_nack(self, target, pid):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid, chain_id=self.chain_id)
        yield self.env.process(self._tx_pkt(pkt))

    def _send_nack_cpkt(self, target, pid, cpkt):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid, chain_id=self.chain_id)
        pkt.cpkt = cpkt
        yield self.env.process(self._tx_pkt(pkt))


# ==========================================
# 6. Topology Generator (v3: per-hop bottleneck helper selection)
# ==========================================
def build_topology(env, protocol, stats, ch, nv, seed):
    random.seed(seed); np.random.seed(seed)
    nodes = []
    chain_offsets = [-600, 0, 600]
    HOP_PER_CHAIN = NUM_HOPS  # 5
    HELPERS_PER_LINK = 3      # max helpers assigned per hop link

    # --- Phase 1: Create routers for all chains ---
    all_routers = []
    for cid in range(NUM_CHAINS):
        y_off = chain_offsets[cid]
        for i in range(HOP_PER_CHAIN + 1):
            x = i * HOP_DIST; nid = cid * 100 + i
            n = UnderwaterNode(env, nid, x, y_off, 'ROUTER', protocol, stats, ch, nv, chain_id=cid)
            if i < HOP_PER_CHAIN: n.next_hop_id = cid * 100 + i + 1
            if i == HOP_PER_CHAIN: n.is_dest = True
            all_routers.append(n); ch.nodes.append(n); nodes.append(n)

    # --- Phase 2: Place helpers randomly ---
    if protocol == PROTO_SW_ARQ:
        return nodes, None

    if protocol == PROTO_CA:
        n_helpers_total = N_HELPERS_TOTAL  # 15
    else:
        n_helpers_total = N_HELPERS_PER_CHAIN_CTRL * NUM_CHAINS  # 5*3 = 15

    helper_positions = []  # (x, y)
    placed = 0
    R = HOP_DIST
    while placed < n_helpers_total:
        x = random.random() * (R * HOP_PER_CHAIN)  # 0-3000m
        y = random.random() * 1800 - 900             # -900 to +900m
        # Must fall within at least one hop zone
        ok = False
        for cid in range(NUM_CHAINS):
            y_off = chain_offsets[cid]
            for hop in range(HOP_PER_CHAIN):
                sx, dx = hop * R, (hop + 1) * R
                if (math.hypot(x - sx, y - y_off) <= R and
                        math.hypot(x - dx, y - y_off) <= R):
                    ok = True; break
            if ok: break
        if not ok: continue
        helper_positions.append((x, y))
        placed += 1

    # --- Phase 3: Pre-compute per-link helper ranking ---
    # link_helpers[(cid, hop)] = [(distance_score, x, y), ...] sorted by bottleneck distance
    link_candidates = {}
    for cid in range(NUM_CHAINS):
        y_off = chain_offsets[cid]
        for hop in range(HOP_PER_CHAIN):
            sx, dx = hop * R, (hop + 1) * R
            key = (cid, hop)
            scores = []
            for (hx, hy) in helper_positions:
                d_src = math.hypot(hx - sx, hy - y_off)
                d_dst = math.hypot(hx - dx, hy - y_off)
                d_bn = max(d_src, d_dst)  # bottleneck distance
                scores.append((d_bn, hx, hy))
            scores.sort(key=lambda s: s[0])
            link_candidates[key] = scores[:HELPERS_PER_LINK]  # top 3

    # --- Phase 4: Create helper nodes, assign links ---
    helper_nodes = []
    for idx, (hx, hy) in enumerate(helper_positions):
        nid = 1000 + idx
        h = UnderwaterNode(env, nid, hx, hy, 'HELPER', protocol, stats, ch, nv, chain_id=-1)
        if protocol == PROTO_CA:
            h.scheduler = HelperScheduler(env)

        # Find which links this helper is top-3 for
        for cid in range(NUM_CHAINS):
            y_off = chain_offsets[cid]
            for hop in range(HOP_PER_CHAIN):
                key = (cid, hop)
                candidates = link_candidates.get(key, [])
                for rank, (d, cx, cy) in enumerate(candidates):
                    if abs(cx - hx) < 1e-6 and abs(cy - hy) < 1e-6:
                        link_src = cid * 100 + hop
                        link_dst = cid * 100 + hop + 1
                        h.helper_for_link.append((link_src, link_dst))
                        if rank == 0:  # bottleneck-best → low-SNR selected
                            h.is_low_snr_selected = True
                        if rank < HELPERS_PER_LINK and protocol in (PROTO_CARQ, PROTO_CHARQ) and rank == 0:
                            h.is_selected = True
                        # Set tx power from closest destination
                        sx = hop * R; dx = (hop + 1) * R
                        dd = math.hypot(hx - dx, hy - y_off)
                        h.tx_power = TX_POWER_W * min(1.0, (dd / HOP_DIST) ** 1.5)
        ch.nodes.append(h); nodes.append(h); helper_nodes.append(h)

    return nodes, all_routers


# ==========================================
# 7. Simulation Runner
# ==========================================
def run_sim(snr_db, protocol, sim_time, seed=0):
    random.seed(seed); np.random.seed(seed)
    env = simpy.Environment()
    stats = MultiChainStats(sim_time, NUM_CHAINS)
    nv = noise_var_for_target_snr_db(snr_db)
    ch = Channel(env, nv, stats=stats)

    _, routers_list = build_topology(env, protocol, stats, ch, nv, seed)

    # Packet generators (one per chain)
    def gen(cid):
        pid = 0
        while True:
            # Find source node for this chain
            src = None
            for node in ch.nodes:
                if node.role == 'ROUTER' and node.chain_id == cid and node.node_id == cid * 100:
                    src = node; break
            if src:
                src.tx_queue.put((pid, env.now))
            pid += 1
            yield env.timeout(random.expovariate(1.0 / 30.0))

    for cid in range(NUM_CHAINS):
        env.process(gen(cid))

    env.run(until=sim_time)

    return {
        'delays': [stats.get_chain_delay(i) for i in range(NUM_CHAINS)],
        'overheads': [stats.get_chain_overhead(i) for i in range(NUM_CHAINS)],
        'ees': [stats.get_chain_ee(i) for i in range(NUM_CHAINS)],
        'successes': [stats.chain[i]['success'] for i in range(NUM_CHAINS)],
        'global_delay': stats.get_global_delay(),
        'global_overhead': stats.get_global_overhead(),
        'global_ee': stats.get_global_ee(),
        'collisions': ch.collision_drops,
        'global_collisions': stats.get_global_collisions(),
    }


# ==========================================
# 8. Monte Carlo
# ==========================================
def mc_run(snr_db, protocol, sim_time, n_runs):
    g_delays, g_ohs, g_ees, succs, cols = [], [], [], [], []
    for run_i in range(n_runs):
        s = abs(42 + run_i * 7919 + int(snr_db * 3571) + (1 << 20)) % (2**31 - 1)
        r = run_sim(snr_db, protocol, sim_time, seed=s)
        g_delays.append(r['global_delay'] if not math.isnan(r['global_delay']) else None)
        g_ohs.append(r['global_overhead'] if not math.isnan(r['global_overhead']) else None)
        g_ees.append(r['global_ee'] if not math.isnan(r['global_ee']) else None)
        succs.append(sum(r['successes']))
        cols.append(r.get('collisions', 0))

    def ci(arr):
        a = np.array([x for x in arr if x is not None], dtype=float)
        if len(a) < 2: return (np.mean(a) if len(a) > 0 else float('nan'), 0.0)
        m = np.mean(a); se = np.std(a, ddof=1) / math.sqrt(len(a))
        return m, 1.96 * se

    d_m, d_ci = ci(g_delays); o_m, o_ci = ci(g_ohs); e_m, e_ci = ci(g_ees)
    return {
        'delay_mean': d_m, 'delay_ci95': d_ci,
        'overhead_mean': o_m, 'overhead_ci95': o_ci,
        'ee_mean': e_m, 'ee_ci95': e_ci,
        'avg_success': np.mean(succs),
        'collisions': int(np.mean(cols)) if cols else 0,
    }


# ==========================================
# 9. Main
# ==========================================
COLORS = {PROTO_SW_ARQ: '#4C72B0', PROTO_CARQ: '#DD8452',
          PROTO_CHARQ: '#55A868', PROTO_CA: '#C44E52'}
MARKERS = {PROTO_SW_ARQ: 's', PROTO_CARQ: '^',
           PROTO_CHARQ: 'D', PROTO_CA: 'o'}

if __name__ == "__main__":
    SNR_LIST = [0.0, 2.0, 4.0, 6.0, 8.0]
    SIM_TIME = 3000
    N_RUNS = 5
    ENABLE = {PROTO_SW_ARQ: True, PROTO_CARQ: True, PROTO_CHARQ: True, PROTO_CA: True}
    ENABLE = {PROTO_SW_ARQ: True, PROTO_CARQ: True, PROTO_CHARQ: True, PROTO_CA: True}
    PROTOCOLS = [p for p in [PROTO_SW_ARQ, PROTO_CARQ, PROTO_CHARQ, PROTO_CA] if ENABLE.get(p, True)]

    results = {p: {'delay': ([], []), 'overhead': ([], []), 'ee': ([], []), 'collisions': []}
               for p in PROTOCOLS}

    print("=" * 60)
    print(f"  CA-CHARQ v7 MAX — Multi-Chain + MAC | {N_RUNS} MC × {len(SNR_LIST)} SNR × {len(PROTOCOLS)} proto")
    print(f"  {NUM_CHAINS} chains × 5 hops × {HOP_DIST}m | {N_HELPERS_TOTAL} helpers (CA-CHARQ)")
    print(f"  SimTime: {SIM_TIME}s | Half-duplex + single-signal + scheduler")
    print("=" * 60)

    for proto in PROTOCOLS:
        print(f"\n--- {proto} ---")
        for snr in SNR_LIST:
            r = mc_run(snr, proto, SIM_TIME, N_RUNS)
            results[proto]['delay'][0].append(r['delay_mean'])
            results[proto]['delay'][1].append(r['delay_ci95'])
            results[proto]['overhead'][0].append(r['overhead_mean'])
            results[proto]['overhead'][1].append(r['overhead_ci95'])
            results[proto]['ee'][0].append(r['ee_mean'])
            results[proto]['ee'][1].append(r['ee_ci95'])
            results[proto]['collisions'].append(r.get('collisions', 0))
            print(f"  SNR={snr:+4.1f}dB  D={r['delay_mean']:7.0f}±{r['delay_ci95']:5.0f}s  "
                  f"OH={r['overhead_mean']:5.1f}±{r['overhead_ci95']:.1f}  "
                  f"EE={r['ee_mean']:5.0f}  Succ={r['avg_success']:.0f}  "
                  f"Col={r.get('collisions',0):.0f}")

    # Plots
    plt.rcParams.update({'font.size': 11})
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    for proto in PROTOCOLS:
        y = np.array(results[proto]['delay'][0]); mask = ~np.isnan(y)
        if mask.any():
            ax1.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto] + '-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto])
    ax1.set_xlabel("Per-Hop SNR (dB)"); ax1.set_ylabel("E2E Delay (s) — Global Avg")
    ax1.set_title("CA-CHARQ v7 MAX — 3-Chain with MAC")
    ax1.grid(True, ls='-', alpha=0.15, color='gray'); ax1.legend()

    for proto in PROTOCOLS:
        y = np.array(results[proto]['overhead'][0]); mask = ~np.isnan(y)
        if mask.any():
            ax2.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto] + '-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto])
    ax2.set_xlabel("Per-Hop SNR (dB)"); ax2.set_ylabel("Overhead (x Useful) — Global Avg")
    ax2.set_yscale('log')
    ax2.grid(True, ls='-', alpha=0.15, color='gray'); ax2.legend()

    plt.tight_layout()
    plt.savefig("output/max-v7/max-v7_Delay_Overhead.png", dpi=200, bbox_inches='tight')
    print("\n[OK] output/max-v7/max-v7_Delay_Overhead.png")
    plt.close('all')

    fig2, ax_ee = plt.subplots(1, 1, figsize=(7, 5))
    for proto in PROTOCOLS:
        y = np.array(results[proto]['ee'][0]); mask = ~np.isnan(y)
        if mask.any():
            ax_ee.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto] + '-',
                       color=COLORS[proto], lw=1.8, ms=7, label=proto,
                       markerfacecolor='white', markeredgecolor=COLORS[proto])
    ax_ee.set_xlabel("Per-Hop SNR (dB)"); ax_ee.set_ylabel("Energy Efficiency (bits/J) — Global Avg")
    ax_ee.grid(True, ls='-', alpha=0.15, color='gray'); ax_ee.legend()
    plt.tight_layout()
    plt.savefig("output/max-v7/max-v7_EE.png", dpi=200, bbox_inches='tight')
    print("[OK] output/max-v7/max-v7_EE.png")
    plt.close('all')

    print("=" * 60)
    print("CA-CHARQ v7 MAX with MAC Done.")
