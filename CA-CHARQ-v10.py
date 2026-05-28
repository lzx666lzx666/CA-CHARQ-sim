"""
CA-CHARQ v9 — SINR碰撞模型 + RTS锁定 + Grace Period + C-HARQ串行CREQ
Phase 1: 核心修复版
"""
import simpy
import math
import random
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from collections import defaultdict
from dataclasses import dataclass, field

# ==========================================
# 1. 核心参数
# ==========================================
SOUND_SPEED  = 1500.0
BIT_RATE     = 1200.0
BITS_PER_CHUNK = 80
CHUNKS_SYS     = 100
CHUNKS_PARITY_MAX = 90
TX_POWER_W     = 15.0
TARGET_MI      = 11000.0
MAX_HOP_RETRYS     = 8
MAX_MERGE_ATTEMPTS = 16
T_MAX_WINDOW    = 1.5
T_PROTECTION_GAP = 0.2
W1, W2, W3 = 0.40, 0.25, 0.35
INITIAL_ENERGY = 10000.0
RICIAN_K = 2.0
HOP_DIST = 600.0
NUM_HOPS = 5
N_HELPERS_PER_HOP = 3

RV_SLICES = {0: (0, 100), 1: (100, 130), 2: (100, 160), 3: (100, 190)}

# C-HARQ 固定 FEC 分片
CHARQ_FEC = [(100, 150), (150, 190)]
CHARQ_FEC_SIZE = [50, 40]

CA_HELPER_SKIP_RATIO = 0.50
CARQ_SKIP_RATIO      = 0.30
HELPER_MIN_MI        = 6000.0   # v10: helpers 解码概率>60% 时才激活 Grace

PROTO_SW_ARQ = "S&W ARQ"
PROTO_CARQ   = "CARQ"
PROTO_CHARQ  = "C-HARQ (Ghosh 2013)"
PROTO_CA     = "CA-CHARQ"

ENABLE = {'SW_ARQ': True, 'CARQ': True, 'CHARQ': True, 'CA': True}

# ==========================================
# 2. 统计中心
# ==========================================
class StatsTracker:
    def __init__(self, sim_time):
        self.total_transmitted_chunks = 0
        self.total_data_tx = 0
        self.total_nack_tx = 0
        self.total_ack_tx = 0
        self.e2e_delays = []
        self.e2e_success_count = 0
        self.e2e_drop_count = 0
        self._pkt_fate = {}
        self.sim_time = sim_time
        self.collision_count = 0

    def record_tx(self, n_chunks):  self.total_transmitted_chunks += n_chunks
    def record_data_tx(self):       self.total_data_tx += 1
    def record_nack_tx(self):       self.total_nack_tx += 1
    def record_ack_tx(self):        self.total_ack_tx += 1

    def record_collision(self):     self.collision_count += 1

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

    def get_energy_efficiency(self):
        if self.e2e_success_count == 0:
            return 0.0
        total_tx_s = self.total_transmitted_chunks * BITS_PER_CHUNK / BIT_RATE
        energy = TX_POWER_W * total_tx_s
        return (self.e2e_success_count * CHUNKS_SYS * BITS_PER_CHUNK) / max(energy, 1e-9)


# ==========================================
# 3. 信道模型
# ==========================================
def noise_var_for_snr_db(snr_db):
    dist_km = HOP_DIST / 1000.0
    spread = dist_km ** 1.5
    absorb = 10.0 ** (0.04 * dist_km)
    loss = spread * absorb + 1e-20
    snr_lin = 10.0 ** (snr_db / 10.0)
    return TX_POWER_W / (loss * snr_lin)

def avg_snr_db(noise_var):
    dist_km = HOP_DIST / 1000.0
    spread = dist_km ** 1.5
    absorb = 10.0 ** (0.04 * dist_km)
    loss = spread * absorb + 1e-20
    snr_lin = (TX_POWER_W / loss) / max(noise_var, 1e-30)
    return 10.0 * math.log10(max(snr_lin, 1e-30))


# ==========================================
# 4. 空中信号记录 (SINR 碰撞检测)
# ==========================================
@dataclass
class OnAirRecord:
    rx_id: int
    start_t: float
    end_t: float
    avg_snr_linear: float
    chunk_snr_arr: np.ndarray = field(repr=False)
    sender_id: int = 0
    pkt_type: str = ''

# ==========================================
# 5. 数据包
# ==========================================
PKT_DATA  = 'DATA'
PKT_ACK   = 'ACK'
PKT_NACK  = 'NACK'
PKT_CREQ  = 'CREQ'
PKT_CAVL  = 'CAVL'
PKT_RTS   = 'RTS'
PKT_LOCK  = 'LOCK'

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
                self.num_chunks = max(e - s, 1)
        elif pkt_type in (PKT_ACK, PKT_NACK, PKT_CREQ, PKT_CAVL, PKT_LOCK):
            self.num_chunks = 3
        elif pkt_type == PKT_RTS:
            self.num_chunks = 1
        else:
            self.num_chunks = 2
        self.received_snr_array = None
        self.avg_snr_linear = 0.0
        self.nack_requested_rv = 0
        self.header_ok = True
        self.c_pkt = 0.0
        self.skip_helper = False

    def tx_duration(self):
        return self.num_chunks * (BITS_PER_CHUNK / BIT_RATE)

# ==========================================
# 6. 置信度
# ==========================================
def confidence_quantize(acc_mi):
    ratio = acc_mi / TARGET_MI
    if ratio < 0.45:   return ratio, 3
    elif ratio < 0.65: return ratio, 2
    elif ratio < 0.85: return ratio, 1
    else:              return ratio, 0

# ==========================================
# 7. 水下节点
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
        self.soft_buffer = {}; self.merge_count = defaultdict(int)
        self.hop_source = {}
        self.ack_events = {}; self.pending_response = {}
        self.helper_cancel_events = {}
        self.next_hop_id = None; self.is_dest = False
        self.helper_for_link = None
        self.helper_tx_cnt = defaultdict(int)
        self.coop_available_cnodes = {}
        self.coop_fec_received = defaultdict(set)
        self.coop_cnode_position = {}
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
            # v9: C-HARQ/CARQ 需要长 gto 覆盖串行协调
            if self.protocol in (PROTO_CARQ, PROTO_CHARQ):
                gto = rtt + 10.0 + T_MAX_WINDOW * 3 + 2.0
            else:
                gto = rtt + T_MAX_WINDOW * 3 + 2.0

            for retry_i in range(MAX_HOP_RETRYS):
                to_ev = self.env.timeout(gto)
                ack_ev = simpy.Event(self.env)
                key = f"{pid}_{retry_i}"
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
                        hop_ok = True
                        break
                    elif msg['type'] == 'NACK':
                        skip_h = msg.get('skip_helper', False)
                        # v9: CA-CHARQ 自适应 Grace Period
                        if self.protocol == PROTO_CA and not skip_h:
                            rv_req = msg.get('req_rv', 0)
                            rv_chunks = RV_SLICES[rv_req][1] - RV_SLICES[rv_req][0]
                            grace_t = (T_MAX_WINDOW * 1.5
                                       + rv_chunks * BITS_PER_CHUNK / BIT_RATE
                                       + 3 * HOP_DIST / SOUND_SPEED + 1.2)
                            grace = self.env.timeout(grace_t)
                            ack_grace = simpy.Event(self.env)
                            gkey = f"{pid}_grace"
                            self.ack_events[gkey] = ack_grace
                            gr = yield ack_grace | grace
                            self.ack_events.pop(gkey, None)
                            if ack_grace in gr:
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
        if not pkt.header_ok: return
        pid = pkt.pid

        # ---- RTS 处理 (目的端锁定 Helper) ----
        if pkt.pkt_type == PKT_RTS:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                if pid not in self.soft_buffer or isinstance(self.soft_buffer.get(pid), str):
                    return
                lock_pkt = PhysicalPacket(PKT_LOCK, self.node_id, pkt.hop_tx, pid)
                lock_pkt.num_chunks = 3
                yield self.env.process(self._tx_pkt(lock_pkt))
            return

        # ---- LOCK 处理 (Helper 被锁定) ----
        if pkt.pkt_type == PKT_LOCK:
            if pkt.hop_rx == self.node_id:
                lkey = f"{pid}_lock"
                if lkey in self.ack_events:
                    evt = self.ack_events[lkey]
                    if not evt.triggered:
                        evt.succeed()
            return

        # ---- DATA 包取消其他 Helper 竞争 ----
        if pkt.pkt_type == PKT_DATA:
            if self.role == 'HELPER' and pid in self.helper_cancel_events:
                ce = self.helper_cancel_events[pid]
                if not ce.triggered: ce.succeed()

        if pkt.pkt_type == PKT_DATA:
            # --- 路由器接收 DATA ---
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

                # ---- 软合并 ----
                if self.protocol in (PROTO_CA, PROTO_SW_ARQ, PROTO_CARQ):
                    a, b = pkt.start_idx, pkt.end_idx
                    if a >= 0 and b > a:
                        self.soft_buffer[pid][a:b] += pkt.received_snr_array
                elif self.protocol == PROTO_CHARQ:
                    if pkt.fec_idx > 0:
                        s, e = CHARQ_FEC[pkt.fec_idx - 1]
                        self.soft_buffer[pid][s:e] += pkt.received_snr_array
                        self.coop_fec_received[pid].add(pkt.fec_idx)
                    else:
                        self.soft_buffer[pid][0:100] += pkt.received_snr_array

                acc_mi = np.sum(np.log2(1.0 + self.soft_buffer[pid])) * BITS_PER_CHUNK

                if acc_mi >= TARGET_MI:
                    self.soft_buffer[pid] = "SUCCESS"
                    yield self.env.process(self.send_ack(
                        self.hop_source.get(pid, pkt.hop_tx), pid))
                    if self.is_dest:
                        self.stats.e2e_success(
                            pid, self.env.now - pkt.creation_time)
                    else:
                        self.tx_queue.put((pid, pkt.creation_time))
                    return

                if self.merge_count[pid] >= MAX_MERGE_ATTEMPTS:
                    self.soft_buffer.pop(pid, None)
                    self.merge_count.pop(pid, None)
                    self.coop_available_cnodes.pop(pid, None)
                    return

                ratio = acc_mi / TARGET_MI

                # ---- CARQ: 串行 CREQ 协调 ----
                if self.protocol == PROTO_CARQ:
                    if pkt.fec_idx <= 0:
                        if ratio > CARQ_SKIP_RATIO:
                            yield self.env.process(self.send_nack(
                                self.hop_source.get(pid, pkt.hop_tx),
                                pid, 0, 0.0, skip_helper=True))
                            return
                        self.coop_available_cnodes.setdefault(pid, [])
                        yield self.env.process(self.send_creq(pkt.hop_tx, pid))
                        yield self.env.timeout(
                            HOP_DIST / SOUND_SPEED * 2 + 0.6)
                        cnodes = self.coop_available_cnodes.get(pid, [])
                        if cnodes:
                            dx, dy = self.x, self.y
                            cnodes.sort(key=lambda cid: math.hypot(
                                self.coop_cnode_position.get(cid, (0,0))[0] - dx,
                                self.coop_cnode_position.get(cid, (0,0))[1] - dy))
                            for cnode_id in cnodes[:1]:
                                if isinstance(self.soft_buffer.get(pid), str):
                                    break
                                yield self.env.process(self.send_nack_cn(
                                    cnode_id, pid, 0))
                                dist_cn = math.hypot(
                                    dx - self.coop_cnode_position.get(cnode_id,(0,0))[0],
                                    dy - self.coop_cnode_position.get(cnode_id,(0,0))[1])
                                rtt_val = (dist_cn / SOUND_SPEED * 2
                                           + 6.67 + 0.3)
                                yield self.env.timeout(rtt_val)
                        if not isinstance(self.soft_buffer.get(pid), str):
                            yield self.env.process(self.send_nack(
                                self.hop_source.get(pid, pkt.hop_tx),
                                pid, 0, 0.0))

                # ---- C-HARQ: 串行 CREQ + FEC ----
                elif self.protocol == PROTO_CHARQ:
                    if pkt.fec_idx <= 0:
                        if ratio > CARQ_SKIP_RATIO:
                            yield self.env.process(self.send_nack(
                                self.hop_source.get(pid, pkt.hop_tx),
                                pid, 0, 0.0, skip_helper=True))
                            return
                        self.coop_available_cnodes.setdefault(pid, [])
                        yield self.env.process(self.send_creq(pkt.hop_tx, pid))
                        yield self.env.timeout(
                            HOP_DIST / SOUND_SPEED * 2 + 0.6)
                        cnodes = self.coop_available_cnodes.get(pid, [])
                        if cnodes:
                            dx, dy = self.x, self.y
                            cnodes.sort(key=lambda cid: math.hypot(
                                self.coop_cnode_position.get(cid, (0,0))[0] - dx,
                                self.coop_cnode_position.get(cid, (0,0))[1] - dy))
                            fec_done = False
                            for cnode_id in cnodes[:1]:
                                for fec_j in [1, 2]:
                                    if isinstance(self.soft_buffer.get(pid), str):
                                        fec_done = True; break
                                    if fec_j in self.coop_fec_received.get(pid, set()):
                                        continue
                                    yield self.env.process(self.send_nack_cn(
                                        cnode_id, pid, fec_j))
                                    rtt_cn = (
                                        math.hypot(
                                            dx - self.coop_cnode_position.get(cnode_id,(0,0))[0],
                                            dy - self.coop_cnode_position.get(cnode_id,(0,0))[1])
                                        / SOUND_SPEED * 2
                                        + CHARQ_FEC_SIZE[fec_j-1] * BITS_PER_CHUNK / BIT_RATE
                                        + 0.3)
                                    yield self.env.timeout(rtt_cn)
                                    if isinstance(self.soft_buffer.get(pid), str):
                                        fec_done = True; break
                                if fec_done: break
                        if not isinstance(self.soft_buffer.get(pid), str):
                            yield self.env.process(self.send_nack(
                                self.hop_source.get(pid, pkt.hop_tx),
                                pid, 0, 0.0))

                # ---- CA-CHARQ: 广播 NACK + RTS 竞争 ----
                elif self.protocol == PROTO_CA:
                    c, rv = confidence_quantize(acc_mi)
                    skip_h = (ratio > CA_HELPER_SKIP_RATIO) or (acc_mi < HELPER_MIN_MI)
                    yield self.env.process(self.send_nack(
                        self.hop_source.get(pid, pkt.hop_tx),
                        pid, rv, c, skip_helper=skip_h))

                # ---- S&W ARQ ----
                else:
                    c, _ = confidence_quantize(acc_mi)
                    yield self.env.process(self.send_nack(
                        self.hop_source.get(pid, pkt.hop_tx),
                        pid, 0, c))

            # --- Helper 监听源端 DATA ---
            elif (self.role == 'HELPER'
                  and self.helper_for_link == (pkt.hop_tx, pkt.hop_rx)):
                if pkt.rv_level == 0 and pkt.fec_idx <= 0:
                    mi = np.sum(np.log2(1.0 + pkt.received_snr_array)) * BITS_PER_CHUNK
                    if mi >= TARGET_MI:
                        c, _ = confidence_quantize(mi)
                        self.soft_buffer[pid] = {
                            "status": "DONE",
                            "c_pkt": c,
                            "creation_time": pkt.creation_time
                        }

        # ---- CReq 处理 ----
        elif pkt.pkt_type == PKT_CREQ:
            if self.role == 'HELPER':
                buf = self.soft_buffer.get(pid)
                if isinstance(buf, dict) and buf.get("status") == "DONE":
                    yield self.env.process(self.send_cavl(pkt.hop_tx, pid))

        # ---- CAvl 处理 ----
        elif pkt.pkt_type == PKT_CAVL:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                cnode_id = pkt.hop_tx
                self.coop_available_cnodes.setdefault(pid, []).append(cnode_id)
                self.coop_cnode_position[cnode_id] = (0, 0)

        # ---- NACK 处理 ----
        elif pkt.pkt_type == PKT_NACK:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                matched = False
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'NACK',
                                     'req_rv': pkt.nack_requested_rv,
                                     'skip_helper': pkt.skip_helper})
                        matched = True; break
                if not matched:
                    self.pending_response[pid] = {
                        'type': 'NACK',
                        'req_rv': pkt.nack_requested_rv,
                        'skip_helper': pkt.skip_helper}
            elif self.role == 'HELPER' and (
                  self.helper_for_link == (pkt.hop_rx, pkt.hop_tx)
                  or (pkt.fec_idx >= 0 and pkt.hop_rx == self.node_id)):
                # CARQ / C-HARQ: NACK-CN 直接请求
                if self.protocol in (PROTO_CARQ, PROTO_CHARQ) and pkt.fec_idx >= 0:
                    buf = self.soft_buffer.get(pid)
                    if isinstance(buf, dict) and buf.get("status") == "DONE":
                        ct = buf.get("creation_time", pkt.creation_time)
                        if pkt.fec_idx > 0:
                            yield self.env.process(self.send_fec(
                                pkt.hop_tx, pid, pkt.fec_idx, ct))
                        else:
                            yield self.env.process(self.send_data(
                                pkt.hop_tx, pid, 0, ct))
                # CA-CHARQ: 广播 NACK 触发 RTS 竞争
                elif self.protocol == PROTO_CA:
                    if getattr(pkt, 'skip_helper', False):
                        pass
                    else:
                        cnt = self.helper_tx_cnt[pid]
                        if cnt >= 3:
                            pass
                        else:
                            buf = self.soft_buffer.get(pid)
                            if isinstance(buf, dict) and buf.get("status") == "DONE":
                                ct = buf.get("creation_time", pkt.creation_time)
                                self.env.process(self.contend(pkt, buf["c_pkt"], ct))

        # ---- ACK 处理 ----
        elif pkt.pkt_type == PKT_ACK:
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                matched = False
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'ACK'})
                        matched = True; break
                if not matched:
                    self.pending_response[pid] = {'type': 'ACK'}

    # ---------- Helper RTS 竞争 (CA-CHARQ) ----------
    def contend(self, pkt, my_c, creation_time):
        pid = pkt.pid
        if pid in self.helper_cancel_events:
            return

        score = (W1 * min(my_c, 1.5)
                 + W2 * max(0.0, min(1.0, self.energy / INITIAL_ENERGY))
                 + W3 * 0.5)
        t = (1.0 - np.clip(score, 0.0, 1.0)) * (T_MAX_WINDOW * 2)

        cancel = simpy.Event(self.env)
        self.helper_cancel_events[pid] = cancel
        r = yield self.env.timeout(t) | cancel
        self.helper_cancel_events.pop(pid, None)
        if cancel in r:
            return

        # Phase 1: 发送 RTS
        rts_pkt = PhysicalPacket(PKT_RTS, self.node_id, pkt.hop_tx,
                                 pid, 0, creation_time)
        yield self.env.process(self._tx_pkt(rts_pkt))

        # Phase 2: 等待 LOCK_ACK
        lock_ev = simpy.Event(self.env)
        lkey = f"{pid}_lock"
        self.ack_events[lkey] = lock_ev
        r2 = yield lock_ev | self.env.timeout(2 * HOP_DIST / SOUND_SPEED + 0.5)
        self.ack_events.pop(lkey, None)

        if lock_ev not in r2:
            return  # 未获锁

        # Phase 3: 发送 DATA
        self.helper_tx_cnt[pid] += 1
        rv = pkt.nack_requested_rv
        yield self.env.process(self.send_data(
            pkt.hop_tx, pid, rv, creation_time))

    # ---------- 发送方法 ----------
    def _tx_pkt(self, pkt):
        dur = pkt.tx_duration()
        self.stats.record_tx(pkt.num_chunks)
        if pkt.pkt_type == PKT_DATA: self.stats.record_data_tx()
        elif pkt.pkt_type == PKT_NACK: self.stats.record_nack_tx()
        elif pkt.pkt_type == PKT_ACK: self.stats.record_ack_tx()
        self.energy -= TX_POWER_W * dur
        yield self.env.timeout(dur)
        self.network.broadcast(self, pkt)

    def send_data(self, target, pid, rv, creation_time):
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target,
                             pid, rv, creation_time)
        yield self.env.process(self._tx_pkt(pkt))

    def send_fec(self, target, pid, fec_idx, creation_time):
        pkt = PhysicalPacket(PKT_DATA, self.node_id, target,
                             pid, 0, creation_time, fec_idx=fec_idx)
        yield self.env.process(self._tx_pkt(pkt))

    def send_ack(self, target, pid):
        pkt = PhysicalPacket(PKT_ACK, self.node_id, target, pid)
        yield self.env.process(self._tx_pkt(pkt))

    def send_nack(self, target, pid, rv, c, skip_helper=False):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid, rv)
        pkt.nack_requested_rv = rv
        pkt.c_pkt = c
        pkt.skip_helper = skip_helper
        yield self.env.process(self._tx_pkt(pkt))

    def send_nack_cn(self, target, pid, fec_idx):
        pkt = PhysicalPacket(PKT_NACK, self.node_id, target, pid, 0,
                             fec_idx=fec_idx)
        pkt.fec_idx = fec_idx
        yield self.env.process(self._tx_pkt(pkt))

    def send_creq(self, target, pid):
        pkt = PhysicalPacket(PKT_CREQ, self.node_id, target, pid)
        yield self.env.process(self._tx_pkt(pkt))

    def send_cavl(self, target, pid):
        pkt = PhysicalPacket(PKT_CAVL, self.node_id, target, pid)
        yield self.env.process(self._tx_pkt(pkt))


# ==========================================
# 8. 水声信道 (v9: SINR 碰撞模型)
# ==========================================
class Channel:
    def __init__(self, env, noise_var, k=2.0, stats=None):
        self.env = env
        self.nodes = []
        self.noise_var = noise_var
        self.stats = stats
        self.los = math.sqrt(k / (k + 1))
        self.nlos = math.sqrt(1.0 / (2 * (k + 1)))
        self._on_air: list = []  # List[OnAirRecord]

    def broadcast(self, sender, pkt):
        for rx in self.nodes:
            if rx is sender:
                continue
            dist = math.hypot(sender.x - rx.x, sender.y - rx.y)
            prop = dist / SOUND_SPEED
            tx_dur = pkt.tx_duration()

            # CAvl 携带 helper 位置
            if pkt.pkt_type == PKT_CAVL:
                rx.coop_cnode_position[sender.node_id] = (sender.x, sender.y)

            clone = PhysicalPacket(pkt.pkt_type, pkt.hop_tx, pkt.hop_rx,
                                   pkt.pid, pkt.rv_level, pkt.creation_time,
                                   fec_idx=pkt.fec_idx)
            clone.nack_requested_rv = pkt.nack_requested_rv
            clone.c_pkt = pkt.c_pkt
            clone.skip_helper = pkt.skip_helper
            clone.num_chunks = pkt.num_chunks

            # 计算 SNR
            if clone.num_chunks > 0:
                dkm = dist / 1000.0
                spread = dkm ** 1.5
                absorb = 10.0 ** (0.04 * dkm)
                loss = spread * absorb + 1e-20
                asnr = (TX_POWER_W / loss) / self.noise_var
                n = clone.num_chunks
                I = self.los + self.nlos * np.random.randn(n)
                Q = self.nlos * np.random.randn(n)
                clone.received_snr_array = asnr * (I ** 2 + Q ** 2)
                clone.avg_snr_linear = float(np.mean(clone.received_snr_array))
            else:
                clone.received_snr_array = np.array([])
                clone.avg_snr_linear = 0.0

            # 注册空中记录
            if self.env.now + prop + tx_dur > self.env.now:
                record = OnAirRecord(
                    rx_id=rx.node_id,
                    start_t=self.env.now + prop,
                    end_t=self.env.now + prop + tx_dur,
                    avg_snr_linear=clone.avg_snr_linear,
                    chunk_snr_arr=clone.received_snr_array.copy() if clone.received_snr_array is not None and len(clone.received_snr_array) > 0 else np.array([]),
                    sender_id=sender.node_id,
                    pkt_type=pkt.pkt_type,
                )
                self._on_air.append(record)

            self.env.process(self._deliver(rx, clone, prop))

    def _deliver(self, rx, pkt, delay):
        yield self.env.timeout(delay)

        # v9: SINR 碰撞检测 —— 查找时间窗口重叠的干扰信号
        now = self.env.now
        pkt_dur = pkt.tx_duration()
        pkt_start = now
        pkt_end = now + pkt_dur

        if pkt.pkt_type == PKT_DATA and pkt.received_snr_array is not None:
            interferers = []
            for otr in list(self._on_air):
                if otr.rx_id != rx.node_id:
                    continue
                if otr.sender_id == pkt.hop_tx:
                    continue
                if otr.start_t >= pkt_end or otr.end_t <= pkt_start:
                    continue
                interferers.append(otr)

            if interferers:
                self.stats.record_collision()
                for i in range(pkt.num_chunks):
                    chunk_start = pkt_start + i * BITS_PER_CHUNK / BIT_RATE
                    chunk_end = chunk_start + BITS_PER_CHUNK / BIT_RATE
                    I_lin = 0.0
                    for otr in interferers:
                        if chunk_start < otr.end_t and chunk_end > otr.start_t:
                            if len(otr.chunk_snr_arr) > 0:
                                idx = int((chunk_start - otr.start_t) / (
                                    BITS_PER_CHUNK / BIT_RATE))
                                if 0 <= idx < len(otr.chunk_snr_arr):
                                    I_lin += otr.chunk_snr_arr[idx]
                                else:
                                    I_lin += otr.avg_snr_linear
                            else:
                                I_lin += otr.avg_snr_linear
                    # SINR = signal / (1 + sum(interference/thermal_noise))
                    # received_snr_array 存的是 SNR (= signal/noise), 不是 signal power
                    pkt.received_snr_array[i] = pkt.received_snr_array[i] / (1.0 + I_lin)

        # 清理过期记录
        self._on_air = [otr for otr in self._on_air if otr.end_t > now]

        rx.inbox.put(pkt)


# ==========================================
# 9. 仿真执行
# ==========================================
def run_sim(snr_db, protocol, sim_time=5000, seed=0, k_factor=2.0):
    random.seed(seed); np.random.seed(seed)
    env = simpy.Environment()
    stats = StatsTracker(sim_time)
    nv = noise_var_for_snr_db(snr_db)
    ch = Channel(env, nv, k=k_factor, stats=stats)

    routers = []
    for i in range(NUM_HOPS + 1):
        n = UnderwaterNode(env, i, i * HOP_DIST, 0,
                           'ROUTER', protocol, stats, ch, nv)
        if i < NUM_HOPS: n.next_hop_id = i + 1
        if i == NUM_HOPS: n.is_dest = True
        routers.append(n); ch.nodes.append(n)

    if protocol != PROTO_SW_ARQ:
        R = HOP_DIST
        for i in range(NUM_HOPS):
            sx, dx = i * R, (i + 1) * R
            helper_base_id = 10 + i * N_HELPERS_PER_HOP
            placed = 0
            while placed < N_HELPERS_PER_HOP:
                x = sx + random.random() * R
                y = (random.random() * 2 - 1) * R
                if math.hypot(x - sx, y) <= R and math.hypot(x - dx, y) <= R:
                    h = UnderwaterNode(env, helper_base_id + placed,
                                       x, y, 'HELPER', protocol, stats, ch, nv)
                    h.helper_for_link = (i, i + 1)
                    ch.nodes.append(h)
                    for r in routers:
                        r.coop_cnode_position[helper_base_id + placed] = (x, y)
                    placed += 1

    # v9: 稀疏发包模型 (与 v8 一致，便于曲线对比)
    def gen():
        pid = 0
        while True:
            routers[0].tx_queue.put((pid, env.now))
            pid += 1
            yield env.timeout(random.expovariate(1.0 / 30.0))

    env.process(gen()); env.run(until=sim_time)

    return {
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
        "collisions": stats.collision_count,
        "ee": stats.get_energy_efficiency(),
        "actual_snr": avg_snr_db(nv),
    }


# ==========================================
# 10. 蒙特卡洛
# ==========================================
def mc_run(snr_db, protocol, sim_time, n_runs, k=2.0):
    delays, ovhds, tputs, drops, colls, ees = [], [], [], [], [], []
    succs, data_txs, nack_txs = [], [], []

    for run_i in range(n_runs):
        s = abs(42 + run_i * 7919 + int(snr_db * 3571) + (1 << 20)) % (2**31 - 1)
        r = run_sim(snr_db, protocol, sim_time, seed=s, k_factor=k)

        delays.append(r['delay'] if not math.isnan(r['delay']) else None)
        ovhds.append(r['overhead'] if not math.isnan(r['overhead']) else None)
        tputs.append(r['throughput']); drops.append(r['drop_rate'])
        colls.append(r['collisions'])
        ees.append(r['ee'] if not math.isnan(r['ee']) else None)
        succs.append(r['success']); data_txs.append(r['data_tx'])
        nack_txs.append(r['nack_tx'])

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
        "avg_collisions": np.mean(colls),
        "actual_snr": avg_snr_db(noise_var_for_snr_db(snr_db)),
    }


# ==========================================
# 11. 主程序
# ==========================================
if __name__ == "__main__":
    K_FACTORS = [('K2_Rician', 2.0), ('K0_Rayleigh', 0.0)]

    for k_label, k_val in K_FACTORS:
        print(f"\n{'='*65}")
        print(f" CA-CHARQ v10 — {k_label} — SINR碰撞 + RTS + Grace + MIN_MI门限")
        print(f" SNR: -5~15dB | TARGET_MI={TARGET_MI} | skip_CA={CA_HELPER_SKIP_RATIO} skip_CARQ={CARQ_SKIP_RATIO} MIN_MI={HELPER_MIN_MI}")
        print(f"{'='*65}")

        SNR_LIST   = [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15]
        SIM_TIME   = 8000
        N_RUNS     = 3 if k_val == 0.0 else 5

        PROTOCOLS = []
        if ENABLE['SW_ARQ']: PROTOCOLS.append(PROTO_SW_ARQ)
        if ENABLE['CARQ']:   PROTOCOLS.append(PROTO_CARQ)
        if ENABLE['CHARQ']:  PROTOCOLS.append(PROTO_CHARQ)
        if ENABLE['CA']:     PROTOCOLS.append(PROTO_CA)

        COLORS = {PROTO_SW_ARQ: '#4C72B0', PROTO_CARQ: '#DD8452',
                  PROTO_CHARQ: '#55A868', PROTO_CA: '#C44E52'}
        MARKERS = {PROTO_SW_ARQ: 's', PROTO_CARQ: '^',
                   PROTO_CHARQ: 'D', PROTO_CA: 'o'}

        results = {p: {'delay': ([], []), 'overhead': ([], []),
                       'ee': ([], []), 'drop_rate': ([], [])}
                   for p in PROTOCOLS}

        for proto in PROTOCOLS:
            print(f"\n  Protocol: {proto}")
            for snr in SNR_LIST:
                r = mc_run(snr, proto, SIM_TIME, N_RUNS, k=k_val)
                results[proto]['delay'][0].append(r['delay_mean'])
                results[proto]['delay'][1].append(r['delay_ci95'])
                results[proto]['overhead'][0].append(r['overhead_mean'])
                results[proto]['overhead'][1].append(r['overhead_ci95'])
                results[proto]['ee'][0].append(r['ee_mean'])
                results[proto]['ee'][1].append(r['ee_ci95'])
                results[proto]['drop_rate'][0].append(r['drop_rate_mean'])
                results[proto]['drop_rate'][1].append(r['drop_rate_ci95'])
                print(f"  SNR={snr:+4d}dB | D={r['delay_mean']:8.1f}±{r['delay_ci95']:5.0f}s | "
                      f"Ov={r['overhead_mean']:6.2f}x | "
                      f"EE={r['ee_mean']:8.1f} | "
                      f"Drop={r['drop_rate_mean']:.2f} | "
                      f"Succ={r['avg_success']:.0f} | "
                      f"Coll={r['avg_collisions']:.0f}")

        # ---- 绘图 ----
        plt.rcParams.update({'font.size': 11, 'legend.fontsize': 9,
                             'xtick.labelsize': 9, 'ytick.labelsize': 9})

        # 延迟 vs 开销
        fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        for proto in PROTOCOLS:
            y = np.array(results[proto]['delay'][0])
            mask = ~np.isnan(y) & (np.array(results[proto]['delay'][0]) < 1e4)
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
        ax1.set_title(f"v10 Delay ({k_label})")

        for proto in PROTOCOLS:
            y = np.array(results[proto]['overhead'][0])
            mask = ~np.isnan(y) & (y < 500)
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
        ax2.set_title(f"v10 Overhead ({k_label})")

        plt.tight_layout()
        plt.savefig(f"v10_Delay_Overhead_{k_label}.png", dpi=200, bbox_inches='tight')
        print(f"\n[OK] v10_Delay_Overhead_{k_label}.png")

        # 能效
        fig2, ax3 = plt.subplots(1, 1, figsize=(7, 5))
        for proto in PROTOCOLS:
            y = np.array(results[proto]['ee'][0])
            mask = ~np.isnan(y) & (y > 0)
            if mask.any():
                xm = np.array(SNR_LIST)[mask]
                ax3.plot(xm, y[mask], MARKERS[proto]+'-',
                         color=COLORS[proto], lw=1.8, ms=7, label=proto,
                         markerfacecolor='white', markeredgecolor=COLORS[proto],
                         markeredgewidth=0.8)
        ax3.set_xlabel("Average Per-Hop SNR (dB)")
        ax3.set_ylabel("Energy Efficiency (bits/J)")
        ax3.grid(True, ls='-', alpha=0.15, color='gray')
        ax3.legend(frameon=True, fancybox=False, edgecolor='gray', loc='lower right')
        ax3.set_title(f"v10 Energy Efficiency ({k_label})")

        plt.tight_layout()
        plt.savefig(f"v10_EE_{k_label}.png", dpi=200, bbox_inches='tight')
        print(f"[OK] v10_EE_{k_label}.png")
        plt.close('all')

        # 文本汇总
        print(f"\n{'='*65}")
        print(f"v10 Delay Summary ({k_label})")
        hdr = f"{'SNR':>5s} |" + "|".join(f" {p:>15s} " for p in PROTOCOLS)
        print(hdr)
        for i, s in enumerate(SNR_LIST):
            parts = []
            for proto in PROTOCOLS:
                v = results[proto]['delay'][0][i]
                parts.append(f"{v:10.0f}s" if not np.isnan(v) else "       n/a")
            row = " | ".join(f"{p:>15s}" for p in parts)
            print(f"{s:+4d}dB | {row}")

        print(f"\n{'='*65}")
        print(f"v10 Overhead Summary ({k_label})")
        for i, s in enumerate(SNR_LIST):
            parts = []
            for proto in PROTOCOLS:
                v = results[proto]['overhead'][0][i]
                parts.append(f"{v:8.2f}x" if not np.isnan(v) else "    n/a")
            row = " | ".join(f"{p:>15s}" for p in parts)
            print(f"{s:+4d}dB | {row}")

        print(f"\n{'='*65}")
        print(f"v10 EE Summary ({k_label})")
        for i, s in enumerate(SNR_LIST):
            parts = []
            for proto in PROTOCOLS:
                v = results[proto]['ee'][0][i]
                parts.append(f"{v:8.1f}" if not np.isnan(v) else "    n/a")
            row = " | ".join(f"{p:>15s}" for p in parts)
            print(f"{s:+4d}dB | {row}")

    print("\n" + "=" * 65)
    print(" CA-CHARQ v10 Done.")
    print("=" * 65)
