#!/usr/bin/env python3
"""
CA-CHARQ Event Simulation v2.0 (SimPy)
=======================================
Event-driven validation of the analytical model.
PHY functions imported from ca_charq_analytic.py for consistency.

Protocols: S&W ARQ, C-ARQ, C-HARQ, CA-CHARQ
Date: 2026-06-17
"""

import simpy
import math
import random
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from collections import defaultdict

# Import PHY functions from analytic model
from ca_charq_pro_v2_analytic import (
    SOUND_SPEED, BIT_RATE, TX_POWER_W, FREQ_KHZ, HOP_DIST,
    NUM_HOPS, N_HELPERS, MAX_RETRIES,
    RS_N_SYM, RS_K_SYM, RS_T_BASE, RS_BITS_PER_SYM, RS_TOTAL_BITS,
    MOD_BITS, N_CHANNEL_SYMS, RV_EXTRA_RS_SYMS,
    thorp_alpha, transmission_loss,
    snr_linear_tx_power, noise_var_for_target_snr_db,
    qpsk_ser_instant, average_qpsk_ser_rayleigh, ser_post_chase,
    rs_decoded_ser, per_rs, per_rs_vec, compute_cpkt, _qpsk_to_rs_ser,
    per_rs_rs_ser,
)

PROTO_SW_ARQ = "S&W ARQ"
PROTO_CARQ   = "C-ARQ"
PROTO_CHARQ  = "C-HARQ"
PROTO_CA     = "CA-CHARQ"

# ==========================================
# 0.  Protocol switches & helper parameters
# ==========================================
W1, W2, W3 = 0.40, 0.25, 0.35
T_MAX_WINDOW    = 1.5
T_PROTECTION_GAP = 0.05
INITIAL_ENERGY = 10000.0

# C-HARQ fixed FEC
CHARQ_FEC_EXTRA = 12    # Pac-1(6) + Pac-2(6) extra RS symbols

# CA-CHARQ RV mapping
RV_EXTRA = {1: 6, 2: 12, 3: 18}   # extra RS symbols per RV level

# Max QPSK-level parity positions (18 RS symbols × 3 QPSK/RS)
MAX_PARITY_QPSK = 18 * (RS_BITS_PER_SYM // MOD_BITS)  # = 54

# ==========================================
# 1.  Channel Model
# ==========================================
class Channel:
    def __init__(self, env, noise_var):
        self.env = env
        self.nodes = []
        self.noise_var = noise_var

    def broadcast(self, sender, pkt):
        for rx in self.nodes:
            if rx is sender:
                continue
            dist = math.hypot(sender.x - rx.x, sender.y - rx.y)
            prop_delay = dist / SOUND_SPEED
            self.env.process(self._deliver(rx, sender, pkt, dist, prop_delay))

    def _deliver(self, rx, sender, pkt, dist, delay):
        yield self.env.timeout(delay)
        # Generate received SNR per chunk
        if pkt.num_chunks > 0:
            loss = transmission_loss(dist, FREQ_KHZ)
            asnr = sender.tx_power / (loss * self.noise_var)
            I = np.random.randn(pkt.num_chunks) / math.sqrt(2)
            Q = np.random.randn(pkt.num_chunks) / math.sqrt(2)
            pkt.received_snr = asnr * (I**2 + Q**2)
        rx.inbox.put(pkt)


# ==========================================
# 2.  Packets
# ==========================================
PKT_DATA = 'DATA'
PKT_ACK  = 'ACK'
PKT_NACK = 'NACK'

class PhysicalPacket:
    def __init__(self, pkt_type, hop_tx, hop_rx, pid,
                 rv_level=0, creation_time=0.0, fec_idx=-1):
        self.pkt_type = pkt_type
        self.hop_tx   = hop_tx
        self.hop_rx   = hop_rx
        self.pid      = pid
        self.rv_level = rv_level
        self.creation_time = creation_time
        self.fec_idx  = fec_idx
        self.cpkt     = -1
        self.num_chunks = 0
        self.received_snr = np.array([])

        if pkt_type == PKT_DATA:
            if fec_idx > 0:   # C-HARQ FEC packets
                self.num_chunks = CHARQ_FEC_EXTRA // 2  # per FEC block
                self.rs_sym_range = None
            elif rv_level > 0:  # CA-CHARQ RV1/RV2/RV3
                self.num_chunks = RV_EXTRA.get(rv_level, 6)
            else:
                self.num_chunks = N_CHANNEL_SYMS  # RV0 = full codeword
        elif pkt_type in (PKT_ACK, PKT_NACK):
            self.num_chunks = 2  # small control packet
        else:
            self.num_chunks = 1

    def tx_duration(self):
        return self.num_chunks / BIT_RATE   # symbols transmitted at BIT_RATE (bps)


# ==========================================
# 3.  Node
# ==========================================
class UnderwaterNode:
    def __init__(self, env, node_id, x, y, role, protocol, stats, network, nv):
        self.env      = env
        self.node_id  = node_id
        self.x, self.y = x, y
        self.role     = role
        self.protocol = protocol
        self.stats    = stats
        self.network  = network
        self.nv       = nv
        self.inbox    = simpy.Store(env)
        self.tx_queue = simpy.Store(env)
        self.energy   = INITIAL_ENERGY
        self.tx_power = TX_POWER_W

        # Per-packet state
        self.soft_buffer  = {}     # pid → np.ndarray of shape (N_CHANNEL_SYMS,)
        self.merge_count  = defaultdict(int)
        self.hop_source   = {}     # pid → original sender for this hop
        self.nack_count   = defaultdict(int)   # per-pkt NACK counter
        self.nack_sent    = set()
        self.fec_sent     = defaultdict(int)
        self.helper_sent  = defaultdict(int)

        # Events for source retry loop
        self.ack_events         = {}    # key → simpy.Event
        self.pending_response   = {}    # pid → {'type': ..., 'cpkt': ...}
        self.helper_ack_events  = {}    # pid → simpy.Event for Grace Period

        # Helper competition
        self.helper_for_link     = None
        self.is_selected         = False  # C-HARQ / C-ARQ single helper
        self.is_low_snr_selected   = False  # CA-CHARQ bottleneck-best for low SNR
        self.helper_cancel_events  = {}    # pid → simpy.Event for competition cancel
        self.helper_tx_cnt       = defaultdict(int)

        self.next_hop_id = None
        self.is_dest     = False

        self.env.process(self.recv_loop())
        if self.role == 'ROUTER':
            self.env.process(self.tx_loop())

    # ====================  Tx Loop (Router / Source) ====================
    def tx_loop(self):
        while True:
            pid, creation_time = yield self.tx_queue.get()
            hop_ok = False
            self.pending_response.pop(pid, None)

            # Send first RV0
            yield self.env.process(self._send_data(self.next_hop_id, pid, 0, creation_time))
            rtt = HOP_DIST / SOUND_SPEED * 2
            gto = rtt + 1.0  # unified for non-CA; CA overrides below
            if self.protocol == PROTO_CA:
                gto = rtt + T_MAX_WINDOW * 2 + 2.0

            for retry_i in range(MAX_RETRIES):
                # Check if response already arrived
                if pid in self.pending_response:
                    msg = self.pending_response.pop(pid)
                    if msg['type'] == 'ACK':
                        hop_ok = True
                        break
                    elif self.protocol == PROTO_CA:
                        cpkt = msg.get('cpkt', 2)
                        if cpkt >= 3:
                            if self._grace_period(pid, cpkt):
                                hop_ok = True
                                break
                        yield self.env.process(self._send_data(
                            self.next_hop_id, pid, 0, creation_time))
                        continue
                    else:
                        # S&W / C-ARQ / C-HARQ: retransmit immediately on NACK
                        yield self.env.process(self._send_data(
                            self.next_hop_id, pid, 0, creation_time))
                        continue

                # Wait for ACK/NACK or timeout
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
                                if self._grace_period(pid, cpkt):
                                    hop_ok = True
                                    break
                        # All protocols (incl C-HARQ): retransmit immediately on NACK
                        yield self.env.process(self._send_data(
                            self.next_hop_id, pid, 0, creation_time))
                else:
                    yield self.env.process(self._send_data(
                        self.next_hop_id, pid, 0, creation_time))

            # Final check
            if not hop_ok and pid in self.pending_response:
                msg = self.pending_response.pop(pid)
                if msg['type'] == 'ACK':
                    hop_ok = True
            if hop_ok:
                pass  # Packet forwarded by recv_loop
            else:
                self.stats.e2e_drop(pid)

    def _grace_period(self, pid, cpkt):
        """Grace Period: source waits for helper ACK, returns True if helper succeeded."""
        n_extra = RV_EXTRA.get(1, 6)   # Grace → helper sends RV1
        rv_tx_t = (n_extra * RS_BITS_PER_SYM) / BIT_RATE
        grace_t = rv_tx_t + T_MAX_WINDOW / 4 + 3 * HOP_DIST / SOUND_SPEED + 0.3
        grace_to = self.env.timeout(grace_t)
        ack_he = simpy.Event(self.env)
        self.helper_ack_events[pid] = ack_he
        gr = yield grace_to | ack_he
        self.helper_ack_events.pop(pid, None)
        return ack_he in gr

    # ====================  Rx Loop ====================
    def recv_loop(self):
        while True:
            pkt = yield self.inbox.get()
            self.env.process(self.handle(pkt))

    def handle(self, pkt):
        pid = pkt.pid

        if pkt.pkt_type == PKT_DATA:
            # ------ Router (destination) receives DATA ------
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                if pid not in self.soft_buffer:
                    self.soft_buffer[pid] = np.zeros(N_CHANNEL_SYMS + MAX_PARITY_QPSK)
                    self.hop_source[pid] = pkt.hop_tx
                buf = self.soft_buffer[pid]
                if isinstance(buf, str):  # already decoded
                    yield self.env.process(self._send_ack(
                        self.hop_source.get(pid, pkt.hop_tx), pid))
                    return

                # Accumulate SNR (Chase combining; parity → extended buffer positions)
                self.merge_count[pid] += 1
                n_snr = min(len(pkt.received_snr), len(buf))
                if pkt.fec_idx > 0 or pkt.rv_level > 0:
                    # Helper parity: write to QPSK positions after system block (189+)
                    par_start = N_CHANNEL_SYMS
                    if pkt.fec_idx == 2:   # C-HARQ Pac-2 offset after Pac-1
                        par_start += (CHARQ_FEC_EXTRA // 2) * (RS_BITS_PER_SYM // MOD_BITS)
                    for i in range(n_snr):
                        base = par_start + (RS_BITS_PER_SYM // MOD_BITS) * i
                        buf[base:base + RS_BITS_PER_SYM // MOD_BITS] += pkt.received_snr[i]
                else:
                    buf[:n_snr] += pkt.received_snr[:n_snr]

                decode_ok = self._try_decode(pid)
                if decode_ok:
                    self.soft_buffer[pid] = "SUCCESS"
                    yield self.env.process(self._send_ack(
                        self.hop_source.get(pid, pkt.hop_tx), pid))
                    if self.is_dest:
                        self.stats.e2e_success(pid, self.env.now - pkt.creation_time)
                    else:
                        self.tx_queue.put((pid, pkt.creation_time))
                elif self.merge_count[pid] >= MAX_RETRIES + 1:
                    self.soft_buffer.pop(pid, None)
                    self.merge_count.pop(pid, None)
                else:
                    # Send NACK (possibly with Cpkt)
                    if (self.protocol == PROTO_CA
                            and pkt.hop_tx == self.hop_source.get(pid)):
                        per_now = self._compute_per(buf)
                        cpkt = compute_cpkt(per_now)
                        yield self.env.process(self._send_nack_cpkt(
                            self.hop_source[pid], pid, cpkt))
                    elif pkt.hop_tx == self.hop_source.get(pid) and pid not in self.nack_sent:
                        self.nack_sent.add(pid)
                        yield self.env.process(self._send_nack(
                            self.hop_source[pid], pid))

            # ------ CA-CHARQ: Helper hears other helper's TX → cancel competition ------
            if (self.role == 'HELPER' and self.protocol == PROTO_CA
                    and pid in self.helper_cancel_events
                    and pkt.hop_tx != self.node_id
                    and self.helper_for_link is not None
                    and pkt.hop_rx == self.helper_for_link[1]):
                ce = self.helper_cancel_events[pid]
                if not ce.triggered:
                    ce.succeed()

            # ------ Helper overhears source RV0 → try to decode ------
            elif (self.role == 'HELPER'
                  and self.helper_for_link == (pkt.hop_tx, pkt.hop_rx)
                  and pkt.rv_level == 0 and pkt.fec_idx <= 0):
                if pid not in self.soft_buffer:
                    self.soft_buffer[pid] = np.zeros(N_CHANNEL_SYMS + MAX_PARITY_QPSK)
                buf = self.soft_buffer[pid]
                if isinstance(buf, dict):
                    return
                n_snr = min(len(pkt.received_snr), len(buf))
                buf[:n_snr] += pkt.received_snr[:n_snr]
                decode_ok = self._try_decode(pid)
                if decode_ok:
                    if self.protocol == PROTO_CA:
                        per_now = self._compute_per(buf)
                        cpkt_h = compute_cpkt(per_now)
                        self.soft_buffer[pid] = {
                            "status": "DECODED",
                            "creation_time": pkt.creation_time,
                            "c_pkt": 1.0 - per_now,
                            "cpkt": cpkt_h
                        }
                    else:
                        self.soft_buffer[pid] = {
                            "status": "DECODED",
                            "creation_time": pkt.creation_time
                        }

        # ------ NACK processing ------
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
                            # Cpkt=2 or Cpkt=3: contend (Cpkt=3 now allowed for Grace!)
                            self.env.process(self.contend(pkt))
                        elif self.is_low_snr_selected and self.helper_tx_cnt[pid] < 3:
                            # Low-SNR fallback: direct send
                            cpkt_v = pkt.cpkt
                            rv = {0: 3, 1: 2}.get(cpkt_v, 2)
                            if cpkt_v >= 1:
                                rv = 2
                            else:
                                rv = 3
                            self.helper_tx_cnt[pid] += 1
                            yield self.env.process(self._send_data(
                                pkt.hop_tx, pid, rv, buf["creation_time"]))

            elif self.role == 'HELPER' and self.is_selected:
                link_src, link_dst = self.helper_for_link
                if (pkt.hop_rx, pkt.hop_tx) == (link_src, link_dst):
                    buf = self.soft_buffer.get(pid)
                    if isinstance(buf, dict) and buf.get("status") == "DECODED":
                        if self.protocol == PROTO_CHARQ:
                            if self.fec_sent[pid] == 0:
                                self.fec_sent[pid] = 1
                                yield self.env.process(self._send_fec(
                                    pkt.hop_tx, pid, 1, buf["creation_time"]))
                            if self.fec_sent[pid] == 1:
                                self.fec_sent[pid] = 2
                                # Small delay before Pac-2
                                yield self.env.timeout(
                                    T_PROTECTION_GAP + (CHARQ_FEC_EXTRA // 2) * RS_BITS_PER_SYM / BIT_RATE)
                                yield self.env.process(self._send_fec(
                                    pkt.hop_tx, pid, 2, buf["creation_time"]))
                        elif self.protocol == PROTO_CARQ:
                            cnt = self.helper_sent[pid]
                            if cnt < MAX_RETRIES:
                                self.helper_sent[pid] = cnt + 1
                                yield self.env.process(self._send_data(
                                    pkt.hop_tx, pid, 0, buf["creation_time"]))

        # ------ ACK processing ------
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
                # Trigger Grace Period ACK event
                if self.protocol == PROTO_CA and pid in self.helper_ack_events:
                    hev = self.helper_ack_events[pid]
                    if not hev.triggered:
                        hev.succeed({'type': 'ACK'})

    # ====================  Helper Contention (CA-CHARQ) ====================
    def contend(self, pkt):
        pid = pkt.pid
        if pid in self.helper_cancel_events:
            return
        buf = self.soft_buffer.get(pid)
        if not isinstance(buf, dict) or buf.get("status") != "DECODED":
            return

        my_c   = buf.get("c_pkt", 1.0)
        link_src, link_dst = self.helper_for_link
        d_src = math.hypot(self.x - link_src * HOP_DIST, self.y)
        d_dst = math.hypot(self.x - link_dst * HOP_DIST, self.y)
        dist  = max(d_src, d_dst)
        prop_u = dist / SOUND_SPEED
        score = (W1 * min(my_c, 1.5)
                 + W2 * max(0.0, min(1.0, self.energy / INITIAL_ENERGY))
                 + W3 / (1.0 + prop_u / 0.4))
        t_backoff = (1.0 - np.clip(score, 0.0, 1.0)) * T_MAX_WINDOW * 2
        t_backoff += max(T_PROTECTION_GAP / 4, 0.05)
        if score > 0.90:
            t_backoff = 0.0
        elif pkt.cpkt < 3 and self.is_low_snr_selected:
            t_backoff = 0.02

        cancel_ev = simpy.Event(self.env)
        self.helper_cancel_events[pid] = cancel_ev

        result = yield self.env.timeout(t_backoff) | cancel_ev
        if cancel_ev not in result:
            cpkt_r = pkt.cpkt
            if cpkt_r <= 0:   rv = 3
            elif cpkt_r <= 1: rv = 2
            else:             rv = 1
            self.helper_tx_cnt[pid] += 1
            yield self.env.process(self._send_data(
                pkt.hop_tx, pid, rv, buf["creation_time"]))
        self.helper_cancel_events.pop(pid, None)

    # ====================  PHY Decode ====================
    def _compute_ser(self, soft_buf):
        """Average SER per QPSK symbol from accumulated SNR buffer."""
        active = soft_buf > 0
        if not np.any(active):
            return 0.5
        gamma_vec = soft_buf[active]
        ser_vec = np.array([qpsk_ser_instant(g) for g in gamma_vec])
        return float(np.mean(ser_vec))

    def _compute_per(self, soft_buf):
        """PER: per-QPSK product for no-FEC; avg RS-level SER → per_rs_rs_ser for FEC."""
        active_mask = soft_buf > 0
        if self.protocol in (PROTO_SW_ARQ, PROTO_CARQ):
            if not np.any(active_mask):
                return 1.0
            ser_vec = np.array([qpsk_ser_instant(float(g)) for g in soft_buf[active_mask]])
            return 1.0 - np.prod(1.0 - ser_vec)
        # RS FEC: group 3 QPSK positions → 1 RS symbol, average RS SER → per_rs_rs_ser
        n_active = int(np.sum(active_mask))
        qpsk_per_rs = RS_BITS_PER_SYM // MOD_BITS  # = 3
        extra_qpsk = max(0, n_active - N_CHANNEL_SYMS)
        n_rs_total = RS_N_SYM + extra_qpsk // qpsk_per_rs
        t_eff = RS_T_BASE + max(0, n_rs_total - RS_N_SYM) // 2
        active_vals = soft_buf[active_mask]
        n_rs = len(active_vals) // qpsk_per_rs
        ser_rs_vec = np.zeros(n_rs)
        for i in range(n_rs):
            p = [qpsk_ser_instant(float(active_vals[qpsk_per_rs*i+j])) for j in range(qpsk_per_rs)]
            ser_rs_vec[i] = 1.0 - np.prod([1.0 - pj for pj in p])
        return per_rs_rs_ser(float(np.mean(ser_rs_vec)), n_rs_total, t_eff)

    def _try_decode(self, pid):
        """Attempt decode: compute PER → random trial."""
        buf = self.soft_buffer[pid]
        per_val = self._compute_per(buf)
        return random.random() > per_val

    # ====================  Send methods ====================
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

    def _send_data(self, target, pid, rv, creation_time):
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target, pid, rv, creation_time)
        yield self.env.process(self._tx_pkt(pkt))

    def _send_fec(self, target, pid, fec_idx, creation_time):
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target, pid, 0, creation_time, fec_idx=fec_idx)
        yield self.env.process(self._tx_pkt(pkt))

    def _send_ack(self, target, pid):
        pkt = PhysicalPacket(PKT_ACK, self.node_id, target, pid)
        yield self.env.process(self._tx_pkt(pkt))

    def _send_nack(self, target, pid):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid)
        yield self.env.process(self._tx_pkt(pkt))

    def _send_nack_cpkt(self, target, pid, cpkt):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid)
        pkt.cpkt = cpkt
        yield self.env.process(self._tx_pkt(pkt))


# ==========================================
# 4.  Stats Tracker
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
    def record_energy(self, j):      self.total_energy += j

    def e2e_success(self, pid, delay):
        if pid not in self._pkt_fate:
            self._pkt_fate[pid] = 'success'
            self.e2e_success_count += 1
            self.e2e_delays.append(delay)

    def e2e_drop(self, pid):
        if pid not in self._pkt_fate:
            self._pkt_fate[pid] = 'dropped'
            self.e2e_drop_count += 1

    def get_avg_delay(self):
        return float(np.mean(self.e2e_delays)) if self.e2e_delays else float('nan')

    def get_overhead(self):
        useful = self.e2e_success_count * N_CHANNEL_SYMS
        return (self.total_transmitted_chunks / useful) if useful > 0 else float('nan')

    def get_drop_rate(self):
        total = self.e2e_success_count + self.e2e_drop_count
        return self.e2e_drop_count / total if total > 0 else 0.0

    def get_ee(self):
        bits = self.e2e_success_count * RS_TOTAL_BITS
        return bits / self.total_energy if self.total_energy > 0 else float('nan')


# ==========================================
# 5.  Simulation runner
# ==========================================
def run_sim(snr_db, protocol, sim_time, seed=0):
    random.seed(seed)
    np.random.seed(seed)
    env = simpy.Environment()
    stats = StatsTracker(sim_time)
    nv = noise_var_for_target_snr_db(snr_db)
    ch = Channel(env, nv)

    # --- Create routers ---
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

    # --- Create helpers ---
    if protocol != PROTO_SW_ARQ:
        R = HOP_DIST
        for i in range(NUM_HOPS):
            sx, dx = i * R, (i + 1) * R
            base_id = 100 + i * N_HELPERS
            helpers_for_link = []
            placed = 0
            while placed < N_HELPERS:
                x = sx + random.random() * R
                y = (random.random() * 2 - 1) * R
                if math.hypot(x - sx, y) <= R and math.hypot(x - dx, y) <= R:
                    h = UnderwaterNode(env, base_id + placed,
                                       x, y, 'HELPER', protocol, stats, ch, nv)
                    h.helper_for_link = (i, i + 1)
                    d_dst = math.hypot(x - dx, y)
                    h.tx_power = TX_POWER_W * min(1.0, (d_dst / HOP_DIST) ** 1.5)
                    ch.nodes.append(h)
                    helpers_for_link.append(h)
                    placed += 1

            if helpers_for_link:
                if protocol in (PROTO_CARQ, PROTO_CHARQ):
                    # Pre-select best (closest to midpoint)
                    mx, my = (sx + dx) / 2.0, 0.0
                    best = min(helpers_for_link,
                               key=lambda hh: math.hypot(hh.x - mx, hh.y - my))
                    best.is_selected = True
                elif protocol == PROTO_CA:
                    # Pre-select bottleneck-best for low SNR
                    best = min(helpers_for_link,
                               key=lambda hh: max(math.hypot(hh.x - sx, hh.y),
                                                  math.hypot(hh.x - dx, hh.y)))
                    best.is_low_snr_selected = True

    # --- Packet generator ---
    def gen():
        pid = 0
        while True:
            routers[0].tx_queue.put((pid, env.now))
            pid += 1
            yield env.timeout(random.expovariate(1.0 / 30.0))

    env.process(gen())
    env.run(until=sim_time)

    return {
        "delay":     stats.get_avg_delay(),
        "overhead":  stats.get_overhead(),
        "drop_rate": stats.get_drop_rate(),
        "success":   stats.e2e_success_count,
        "drops":     stats.e2e_drop_count,
        "data_tx":   stats.total_data_tx,
        "nack_tx":   stats.total_nack_tx,
        "ack_tx":    stats.total_ack_tx,
        "ee":        stats.get_ee(),
    }


# ==========================================
# 6.  Monte Carlo
# ==========================================
def mc_run(snr_db, protocol, sim_time, n_runs):
    delays, ovhds, drops, ees = [], [], [], []
    succs = []
    for run_i in range(n_runs):
        s = abs(42 + run_i * 7919 + int(snr_db * 3571) + (1 << 20)) % (2**31 - 1)
        r = run_sim(snr_db, protocol, sim_time, seed=s)
        delays.append(r['delay'] if not math.isnan(r['delay']) else None)
        ovhds.append(r['overhead'] if not math.isnan(r['overhead']) else None)
        drops.append(r['drop_rate'])
        ees.append(r['ee'] if not math.isnan(r['ee']) else None)
        succs.append(r['success'])

    def ci(arr):
        a = np.array([x for x in arr if x is not None], dtype=float)
        return (np.mean(a), 1.96 * np.std(a, ddof=1) / math.sqrt(len(a))) if len(a) > 0 else (float('nan'), 0.0)

    d_m, d_ci = ci(delays);  o_m, o_ci = ci(ovhds)
    dr_m, dr_ci = ci(drops); ee_m, ee_ci = ci(ees)
    return {
        "delay_mean": d_m, "delay_ci95": d_ci,
        "overhead_mean": o_m, "overhead_ci95": o_ci,
        "drop_rate_mean": dr_m, "drop_rate_ci95": dr_ci,
        "ee_mean": ee_m, "ee_ci95": ee_ci,
        "avg_success": np.mean(succs),
    }


# ==========================================
# 7.  Main
# ==========================================
if __name__ == "__main__":
    SNR_LIST   = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0]
    SIM_TIME   = 15000
    N_RUNS     = 5

    ENABLE = {PROTO_SW_ARQ: True, PROTO_CARQ: True, PROTO_CHARQ: True, PROTO_CA: True}
    PROTOCOLS = [p for p in [PROTO_SW_ARQ, PROTO_CARQ, PROTO_CHARQ, PROTO_CA] if ENABLE.get(p, True)]

    COLORS = {PROTO_SW_ARQ: '#4C72B0', PROTO_CARQ: '#DD8452',
              PROTO_CHARQ: '#55A868', PROTO_CA: '#C44E52'}
    MARKERS = {PROTO_SW_ARQ: 's', PROTO_CARQ: '^',
               PROTO_CHARQ: 'D', PROTO_CA: 'o'}

    results = {p: {'delay': ([], []), 'overhead': ([], []), 'ee': ([], [])}
               for p in PROTOCOLS}

    print("=" * 60)
    print(f"  SimPy Event Simulation v2.0  |  {N_RUNS} MC × {len(SNR_LIST)} SNR × {len(PROTOCOLS)} proto")
    print(f"  PHY: RS({RS_N_SYM},{RS_K_SYM},t={RS_T_BASE}) + Sklar 1988")
    print(f"  SimTime: {SIM_TIME}s, max retries: {MAX_RETRIES}")
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
            print(f"  SNR={snr:+4.1f}dB  D={r['delay_mean']:8.1f}±{r['delay_ci95']:5.1f}s  "
                  f"OH={r['overhead_mean']:6.2f}±{r['overhead_ci95']:.2f}  "
                  f"EE={r['ee_mean']:6.0f}  Succ={r['avg_success']:.0f}")

    # --- Plots ---
    plt.rcParams.update({'font.size': 11})
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    for proto in PROTOCOLS:
        y = np.array(results[proto]['delay'][0])
        mask = ~np.isnan(y)
        if mask.any():
            ax1.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto] + '-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto])
    ax1.set_xlabel("Per-Hop SNR (dB)"); ax1.set_ylabel("E2E Delay (s)")
    ax1.grid(True, ls='-', alpha=0.15, color='gray'); ax1.legend()

    for proto in PROTOCOLS:
        y = np.array(results[proto]['overhead'][0])
        mask = ~np.isnan(y)
        if mask.any():
            ax2.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto] + '-',
                     color=COLORS[proto], lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto])
    ax2.set_xlabel("Per-Hop SNR (dB)"); ax2.set_ylabel("Overhead (x Useful)")
    ax2.grid(True, ls='-', alpha=0.15, color='gray'); ax2.legend()

    plt.tight_layout()
    plt.savefig("output/pro-v2/simpy_v2_Delay_Overhead.png", dpi=200, bbox_inches='tight')
    print("\n[OK] output/pro-v2/simpy_v2_Delay_Overhead.png")
    plt.close('all')

    fig2, ax_ee = plt.subplots(1, 1, figsize=(7, 5))
    for proto in PROTOCOLS:
        y = np.array(results[proto]['ee'][0])
        mask = ~np.isnan(y)
        if mask.any():
            ax_ee.plot(np.array(SNR_LIST)[mask], y[mask], MARKERS[proto] + '-',
                       color=COLORS[proto], lw=1.8, ms=7, label=proto,
                       markerfacecolor='white', markeredgecolor=COLORS[proto])
    ax_ee.set_xlabel("Per-Hop SNR (dB)"); ax_ee.set_ylabel("Energy Efficiency (bits/J)")
    ax_ee.grid(True, ls='-', alpha=0.15, color='gray'); ax_ee.legend()
    plt.tight_layout()
    plt.savefig("output/pro-v2/simpy_v2_EE.png", dpi=200, bbox_inches='tight')
    print("[OK] output/pro-v2/simpy_v2_EE.png")
    plt.close('all')

    print("=" * 60)
    print("Done.")
    plt.rcParams.update({'font.size': 11})
