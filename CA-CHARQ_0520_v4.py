import simpy
import math
import random
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from collections import defaultdict

# ==========================================
# 1. 核心参数
# ==========================================
SOUND_SPEED  = 1500.0
BIT_RATE     = 1200.0
BITS_PER_CHUNK = 80
CHUNKS_SYS     = 100
CHUNKS_PARITY_MAX = 90
TX_POWER_W     = 15.0
TARGET_MI      = 20000.0
MAX_HOP_RETRYS     = 12
MAX_MERGE_ATTEMPTS = 16
T_MAX_WINDOW    = 1.5
T_PROTECTION_GAP = 0.2
W1, W2, W3 = 0.40, 0.25, 0.35
INITIAL_ENERGY = 10000.0
RICIAN_K = 2.0
HOP_DIST = 600.0
NUM_HOPS = 3
N_HELPERS_PER_HOP = 1          # 每跳 1 个协作节点（与退避竞争机制匹配）

RV_SLICES = {0: (0, 100), 1: (100, 130), 2: (100, 160), 3: (100, 190)}

PROTO_SW_ARQ = "S&W ARQ"
PROTO_CARQ   = "CARQ"
PROTO_CA     = "CA-CHARQ"

# ==========================================
# 2. 统计中心
# ==========================================
class StatsTracker:
    def __init__(self):
        self.total_transmitted_chunks = 0
        self.total_data_tx = 0
        self.total_nack_tx = 0
        self.total_ack_tx = 0
        self.e2e_delays = []
        self.e2e_success_count = 0
        self.e2e_drop_count = 0
        self._pkt_fate = {}

    def record_tx(self, n_chunks):
        self.total_transmitted_chunks += n_chunks

    def record_data_tx(self):   self.total_data_tx += 1
    def record_nack_tx(self):   self.total_nack_tx += 1
    def record_ack_tx(self):    self.total_ack_tx += 1

    def e2e_success(self, pid, delay):
        if pid not in self._pkt_fate:
            self._pkt_fate[pid] = 'success'
            self.e2e_success_count += 1
            self.e2e_delays.append(delay)

    def e2e_drop(self, pid):
        if pid not in self._pkt_fate:
            self._pkt_fate[pid] = 'dropped'
            self.e2e_drop_count += 1

    def get_throughput(self, total_time):
        return (self.e2e_success_count * CHUNKS_SYS) / max(total_time, 1.0)

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
# 4. 数据包
# ==========================================
class PhysicalPacket:
    def __init__(self, pkt_type, hop_tx, hop_rx, pid,
                 rv_level=0, creation_time=0.0):
        self.pkt_type = pkt_type
        self.hop_tx = hop_tx
        self.hop_rx = hop_rx
        self.pid = pid
        self.rv_level = rv_level
        self.creation_time = creation_time
        s, e = RV_SLICES.get(rv_level, (0, 0))
        self.start_idx, self.end_idx = s, e
        if pkt_type == 'DATA':
            self.num_chunks = e - s
        elif pkt_type in ('ACK', 'NACK'):
            self.num_chunks = 3
        else:
            self.num_chunks = 2
        self.received_snr_array = None
        self.avg_snr_linear = 0.0
        self.nack_requested_rv = 0
        self.header_ok = True
        self.c_pkt = 0.0

    def tx_duration(self):
        return self.num_chunks * (BITS_PER_CHUNK / BIT_RATE)


# ==========================================
# 5. 置信度 + RV 映射（仅 CA-CHARQ 使用；CARQ 固定 rv=0）
# ==========================================
def confidence_quantize(acc_mi):
    ratio = acc_mi / TARGET_MI
    if ratio < 0.45:   return ratio, 3
    elif ratio < 0.65: return ratio, 2
    elif ratio < 0.85: return ratio, 1
    else:              return ratio, 0


# ==========================================
# 6. 水下节点
# ==========================================
class UnderwaterNode:
    def __init__(self, env, node_id, x, y, role, protocol,
                 stats, network, noise_variance):
        self.env = env
        self.node_id = node_id
        self.x, self.y = x, y
        self.role = role
        self.protocol = protocol
        self.stats = stats
        self.network = network
        self.noise_variance = noise_variance
        self.inbox = simpy.Store(env)
        self.tx_queue = simpy.Store(env)
        self.energy = INITIAL_ENERGY
        self.soft_buffer = {}
        self.merge_count = defaultdict(int)
        self.ack_events = {}
        self.pending_response = {}
        self.helper_heard_events = {}
        self.helper_cancel_events = {}
        self.next_hop_id = None
        self.is_dest = False
        self.helper_for_link = None
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
                        helper_ev = simpy.Event(self.env)
                        self.helper_heard_events[pid] = helper_ev
                        deadline = T_MAX_WINDOW * 2 + 7.0
                        dl_ev = self.env.timeout(deadline)

                        result2 = yield helper_ev | dl_ev
                        self.helper_heard_events.pop(pid, None)

                        if helper_ev not in result2:
                            rv = msg['req_rv']
                            if self.protocol != PROTO_CA:
                                rv = 0
                            yield self.env.process(self.send_data(
                                self.next_hop_id, pid, rv, creation_time))
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

        if pkt.pkt_type == 'DATA':

            # 源节点：监听到 helper 发包 → 通知 tx_loop
            if (self.role == 'ROUTER' and pkt.hop_tx != self.node_id
                    and pkt.hop_rx == self.next_hop_id):
                if pid in self.helper_heard_events:
                    ev = self.helper_heard_events[pid]
                    if not ev.triggered:
                        ev.succeed()

            # Helper：收到任意 DATA → 取消其他 helper 竞争（自己已占先机）
            if (self.role == 'HELPER'
                    and pid in self.helper_cancel_events):
                ce = self.helper_cancel_events[pid]
                if not ce.triggered:
                    ce.succeed()

            # 目的路由器：接收
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                if pid not in self.soft_buffer:
                    self.soft_buffer[pid] = np.zeros(
                        CHUNKS_SYS + CHUNKS_PARITY_MAX)
                    self.merge_count[pid] = 0
                if isinstance(self.soft_buffer[pid], str):
                    yield self.env.process(self.send_ack(
                        pkt.hop_tx, pid))
                    return

                self.merge_count[pid] += 1

                # ---- 不同协议的软信息合并策略 ----
                if self.protocol == PROTO_CA:
                    a, b = pkt.start_idx, pkt.end_idx
                    self.soft_buffer[pid][a:b] += pkt.received_snr_array
                else:
                    # S&W ARQ / CARQ: 始终 Chase 合并到 [0:100]
                    self.soft_buffer[pid][0:100] += pkt.received_snr_array

                acc_mi = np.sum(np.log2(1.0 + self.soft_buffer[pid])) * BITS_PER_CHUNK

                if acc_mi >= TARGET_MI:
                    self.soft_buffer[pid] = "SUCCESS"
                    yield self.env.process(self.send_ack(
                        pkt.hop_tx, pid))
                    if self.is_dest:
                        self.stats.e2e_success(
                            pid, self.env.now - pkt.creation_time)
                    else:
                        self.tx_queue.put((pid, pkt.creation_time))
                else:
                    # ---- 不同协议的 RV 请求 ----
                    c, rv = confidence_quantize(acc_mi)
                    if self.protocol != PROTO_CA:
                        rv = 0
                    if self.merge_count[pid] >= MAX_MERGE_ATTEMPTS:
                        self.soft_buffer.pop(pid, None)
                        self.merge_count.pop(pid, None)
                        return
                    yield self.env.process(self.send_nack(
                        pkt.hop_tx, pid, rv, c))

            # Helper 偷听（仅 RV0）
            elif (self.role == 'HELPER'
                  and self.helper_for_link == (pkt.hop_tx, pkt.hop_rx)):
                if pkt.rv_level == 0:
                    mi = np.sum(np.log2(1.0 + pkt.received_snr_array)) * BITS_PER_CHUNK
                    if mi >= TARGET_MI:
                        c, _ = confidence_quantize(mi)
                        self.soft_buffer[pid] = {
                            "status": "DONE", "c_pkt": c}

        elif pkt.pkt_type == 'NACK':
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                matched = False
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({
                            'type': 'NACK',
                            'req_rv': pkt.nack_requested_rv})
                        matched = True
                        break
                if not matched:
                    self.pending_response[pid] = {
                        'type': 'NACK',
                        'req_rv': pkt.nack_requested_rv}
            elif (self.role == 'HELPER'
                  and self.helper_for_link == (pkt.hop_rx, pkt.hop_tx)):
                buf = self.soft_buffer.get(pid)
                if isinstance(buf, dict) and buf.get("status") == "DONE":
                    self.env.process(self.contend(pkt, buf["c_pkt"]))

        elif pkt.pkt_type == 'ACK':
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                matched = False
                for k, evt in list(self.ack_events.items()):
                    if k.startswith(f"{pid}_") and not evt.triggered:
                        evt.succeed({'type': 'ACK'})
                        matched = True
                        break
                if not matched:
                    self.pending_response[pid] = {'type': 'ACK'}

    # ---------- Helper 竞争 ----------
    def contend(self, pkt, my_c):
        pid = pkt.pid
        if pid in self.helper_cancel_events:
            return
        if self.protocol in (PROTO_CA, PROTO_CARQ):
            score = (W1 * min(my_c, 1.5)
                     + W2 * max(0.0, min(1.0, self.energy / INITIAL_ENERGY))
                     + W3 * 0.5)
            t = (1.0 - np.clip(score, 0.0, 1.0)) * (T_MAX_WINDOW * 2)
        else:
            t = random.uniform(0.0, T_MAX_WINDOW * 2)

        cancel = simpy.Event(self.env)
        self.helper_cancel_events[pid] = cancel
        result = yield self.env.timeout(t) | cancel
        if cancel not in result:
            # CARQ 始终发 RV0，CA-CHARQ 发 NACK 请求的 RV
            rv = pkt.nack_requested_rv if self.protocol == PROTO_CA else 0
            yield self.env.process(self.send_data(
                pkt.hop_tx, pid, rv, pkt.creation_time))
        self.helper_cancel_events.pop(pid, None)

    # ---------- 发送方法 ----------
    def send_data(self, target, pid, rv, creation_time):
        pkt = PhysicalPacket('DATA', self.node_id, target,
                             pid, rv, creation_time)
        dur = pkt.tx_duration()
        self.stats.record_tx(pkt.num_chunks)
        self.stats.record_data_tx()
        self.energy -= TX_POWER_W * dur
        yield self.env.timeout(dur)
        self.network.broadcast(self, pkt)

    def send_ack(self, target, pid):
        pkt = PhysicalPacket('ACK', self.node_id, target, pid)
        dur = pkt.tx_duration()
        self.stats.record_tx(pkt.num_chunks)
        self.stats.record_ack_tx()
        self.energy -= TX_POWER_W * dur
        yield self.env.timeout(dur)
        self.network.broadcast(self, pkt)

    def send_nack(self, target, pid, rv, c):
        pkt = PhysicalPacket('NACK', self.node_id, target, pid, rv)
        pkt.nack_requested_rv = rv
        pkt.c_pkt = c
        dur = pkt.tx_duration()
        self.stats.record_tx(pkt.num_chunks)
        self.stats.record_nack_tx()
        self.energy -= TX_POWER_W * dur
        yield self.env.timeout(dur)
        self.network.broadcast(self, pkt)


# ==========================================
# 7. 水声信道
# ==========================================
class Channel:
    def __init__(self, env, noise_var, k=2.0):
        self.env = env
        self.nodes = []
        self.noise_var = noise_var
        self.los = math.sqrt(k / (k + 1))
        self.nlos = math.sqrt(1.0 / (2 * (k + 1)))

    def broadcast(self, sender, pkt):
        for rx in self.nodes:
            if rx is sender:
                continue
            dist = math.hypot(sender.x - rx.x, sender.y - rx.y)
            prop = dist / SOUND_SPEED

            clone = PhysicalPacket(pkt.pkt_type, pkt.hop_tx,
                                   pkt.hop_rx, pkt.pid,
                                   pkt.rv_level, pkt.creation_time)
            clone.nack_requested_rv = pkt.nack_requested_rv
            clone.c_pkt = pkt.c_pkt

            if pkt.pkt_type == 'DATA':
                dkm = dist / 1000.0
                spread = dkm ** 1.5
                absorb = 10.0 ** (0.04 * dkm)
                loss = spread * absorb + 1e-20
                asnr = (TX_POWER_W / loss) / self.noise_var
                n = clone.num_chunks
                I = self.los + self.nlos * np.random.randn(n)
                Q = self.nlos * np.random.randn(n)
                clone.received_snr_array = asnr * (I ** 2 + Q ** 2)
                clone.avg_snr_linear = float(np.mean(
                    clone.received_snr_array))

            self.env.process(self._deliver(rx, clone, prop))

    def _deliver(self, rx, pkt, delay):
        yield self.env.timeout(delay)
        rx.inbox.put(pkt)


# ==========================================
# 8. 仿真执行（单次 run）
# ==========================================
def run_sim(snr_db, protocol, sim_time=60000, seed=0):
    random.seed(seed)
    np.random.seed(seed)

    env = simpy.Environment()
    stats = StatsTracker()
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

    # S&W ARQ: 不创建 helper；CARQ 和 CA-CHARQ：每跳 N 个随机 helper
    if protocol != PROTO_SW_ARQ:
        R = HOP_DIST
        for i in range(NUM_HOPS):
            sx, dx = i * R, (i + 1) * R
            helper_base_id = 10 + i * N_HELPERS_PER_HOP
            placed = 0
            # rejection sampling：在 lens 区域（两圆 R 交叠）内随机撒点
            while placed < N_HELPERS_PER_HOP:
                x = sx + random.random() * R
                y = (random.random() * 2 - 1) * R
                d_src = math.hypot(x - sx, y)
                d_dst = math.hypot(x - dx, y)
                if d_src <= R and d_dst <= R:
                    h = UnderwaterNode(env, helper_base_id + placed,
                                       x, y, 'HELPER', protocol, stats, ch, nv)
                    h.helper_for_link = (i, i + 1)
                    ch.nodes.append(h)
                    placed += 1

    def gen():
        pid = 0
        while True:
            routers[0].tx_queue.put((pid, env.now))
            pid += 1
            yield env.timeout(random.expovariate(1.0 / 30.0))

    env.process(gen())
    env.run(until=sim_time)

    return {
        "delay":      stats.get_avg_delay(),
        "delay_std":  stats.get_delay_std(),
        "overhead":   stats.get_overhead(),
        "throughput": stats.get_throughput(sim_time),
        "drop_rate":  stats.get_drop_rate(),
        "success":    stats.e2e_success_count,
        "drops":      stats.e2e_drop_count,
        "data_tx":    stats.total_data_tx,
        "nack_tx":    stats.total_nack_tx,
        "ack_tx":     stats.total_ack_tx,
        "actual_snr": avg_snr_db(nv),
    }


# ==========================================
# 9. 多 run 蒙特卡洛 + 置信区间
# ==========================================
def mc_run(snr_db, protocol, sim_time, n_runs):
    """返回 {metric: (mean, ci95)} 字典"""
    delays, ovhds, tputs, drops = [], [], [], []
    succs, data_txs, nack_txs = [], [], []

    for run_i in range(n_runs):
        s = abs(seed_base + run_i * 7919 + int(snr_db * 3571) + (1 << 20)) % (2**31 - 1)
        r = run_sim(snr_db, protocol, sim_time, seed=s)

        delays.append(r['delay'] if not math.isnan(r['delay']) else None)
        ovhds.append(r['overhead'] if not math.isnan(r['overhead']) else None)
        tputs.append(r['throughput'])
        drops.append(r['drop_rate'])
        succs.append(r['success'])
        data_txs.append(r['data_tx'])
        nack_txs.append(r['nack_tx'])

    def ci(arr):
        a = np.array([x for x in arr if x is not None], dtype=float)
        if len(a) == 0:
            return float('nan'), 0.0
        m = np.mean(a)
        se = np.std(a, ddof=1) / math.sqrt(len(a))
        return m, 1.96 * se

    d_m, d_ci = ci(delays)
    o_m, o_ci = ci(ovhds)
    t_m, t_ci = ci(tputs)
    dr_m, dr_ci = ci(drops)

    return {
        "delay_mean": d_m,     "delay_ci95": d_ci,
        "overhead_mean": o_m,  "overhead_ci95": o_ci,
        "throughput_mean": t_m, "throughput_ci95": t_ci,
        "drop_rate_mean": dr_m, "drop_rate_ci95": dr_ci,
        "avg_success": np.mean(succs),
        "avg_data_tx": np.mean(data_txs),
        "avg_nack_tx": np.mean(nack_txs),
        "actual_snr": avg_snr_db(noise_var_for_snr_db(snr_db)),
    }


# ==========================================
# 10. 主程序
# ==========================================
if __name__ == "__main__":
    SNR_LIST   = [0, 4, 8, 12, 16, 20, 25, 30]
    SIM_TIME   = 40000
    N_RUNS     = 10
    seed_base  = 42

    PROTOCOLS  = [PROTO_SW_ARQ, PROTO_CARQ, PROTO_CA]
    COLORS     = {'S&W ARQ': 'gray', 'CARQ': 'orangered', 'CA-CHARQ': 'steelblue'}
    STYLES     = {'S&W ARQ': 's--',  'CARQ': '^-.',  'CA-CHARQ': 'o-'}

    results = {p: {'delay': ([], []), 'overhead': ([], []),
                   'throughput': ([], []), 'drop_rate': ([], [])}
               for p in PROTOCOLS}

    print("=" * 65)
    print(f" Monte Carlo: {N_RUNS} runs × {len(SNR_LIST)} SNR × 3 protocols")
    print(f" Topo: {NUM_HOPS} hops × {HOP_DIST}m, {N_HELPERS_PER_HOP} helpers/hop, SimTime={SIM_TIME}s")
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
            print(f"  SNR={snr:+3d}dB | "
                  f"Delay={r['delay_mean']:8.1f}±{r['delay_ci95']:5.1f}s | "
                  f"Ovhd={r['overhead_mean']:6.3f}±{r['overhead_ci95']:.3f} | "
                  f"Drop={r['drop_rate_mean']:.3f}±{r['drop_rate_ci95']:.3f} | "
                  f"Succ={r['avg_success']:.0f}")

    # ---- 绘图 ----
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5))
    for proto in PROTOCOLS:
        y = np.array(results[proto]['delay'][0]); e = np.array(results[proto]['delay'][1])
        mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(SNR_LIST)[mask]
            ax1.errorbar(xm, y[mask], yerr=e[mask], fmt=STYLES[proto],
                         color=COLORS[proto], capsize=3, lw=2, ms=7, label=proto)
        else:
            ax1.plot([], [], STYLES[proto], color=COLORS[proto], label=proto)
    ax1.set_title("E2E Packet Delay vs SNR", fontsize=13, fontweight='bold')
    ax1.set_xlabel("Per-Hop SNR (dB)")
    ax1.set_ylabel("Delay (s)")
    ax1.grid(True, ls=':', alpha=0.5)
    ax1.legend(fontsize=9)

    for proto in PROTOCOLS:
        y = np.array(results[proto]['overhead'][0]); e = np.array(results[proto]['overhead'][1])
        mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(SNR_LIST)[mask]
            ax2.errorbar(xm, y[mask], yerr=e[mask], fmt=STYLES[proto],
                         color=COLORS[proto], capsize=3, lw=2, ms=7, label=proto)
        else:
            ax2.plot([], [], STYLES[proto], color=COLORS[proto], label=proto)
    ax2.set_title("Transmission Overhead vs SNR", fontsize=13, fontweight='bold')
    ax2.set_xlabel("Per-Hop SNR (dB)")
    ax2.set_ylabel("Overhead (Tx / Useful Chunks)")
    ax2.grid(True, ls=':', alpha=0.5)
    ax2.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig("SNR_Delay_Overhead_v4.png", dpi=150, bbox_inches='tight')
    print("\n[OK] SNR_Delay_Overhead_v4.png")

    fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(16, 5.5))
    for proto in PROTOCOLS:
        y = np.array(results[proto]['drop_rate'][0]); e = np.array(results[proto]['drop_rate'][1])
        mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(SNR_LIST)[mask]
            ax3.errorbar(xm, y[mask], yerr=e[mask], fmt=STYLES[proto],
                         color=COLORS[proto], capsize=3, lw=2, ms=7, label=proto)
        else:
            ax3.plot([], [], STYLES[proto], color=COLORS[proto], label=proto)
    ax3.set_title("E2E Drop Rate vs SNR", fontsize=13, fontweight='bold')
    ax3.set_xlabel("Per-Hop SNR (dB)")
    ax3.set_ylabel("Drop Rate")
    ax3.grid(True, ls=':', alpha=0.5)
    ax3.legend(fontsize=9)

    for proto in PROTOCOLS:
        y = np.array(results[proto]['throughput'][0]); e = np.array(results[proto]['throughput'][1])
        mask = ~np.isnan(y)
        if mask.any():
            xm = np.array(SNR_LIST)[mask]
            ax4.errorbar(xm, y[mask], yerr=e[mask], fmt=STYLES[proto],
                         color=COLORS[proto], capsize=3, lw=2, ms=7, label=proto)
        else:
            ax4.plot([], [], STYLES[proto], color=COLORS[proto], label=proto)
    ax4.set_title("E2E Throughput vs SNR", fontsize=13, fontweight='bold')
    ax4.set_xlabel("Per-Hop SNR (dB)")
    ax4.set_ylabel("Throughput (Chunks/s)")
    ax4.grid(True, ls=':', alpha=0.5)
    ax4.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig("SNR_DropRate_Throughput_v4.png", dpi=150, bbox_inches='tight')
    print("[OK] SNR_DropRate_Throughput_v4.png")
    plt.close('all')

    # ---- 文本汇总（容 NaN）----
    print(f"\n{'='*65}")
    print("Final Summary (mean ± 95% CI)")
    print(f"{'SNR':>5s} | {'S&W ARQ Delay':>20s} | {'CARQ Delay':>20s} | {'CA-CHARQ Delay':>22s}")
    for i, s in enumerate(SNR_LIST):
        def fmt_d(arr): return f"{arr[0][i]:.0f}±{arr[1][i]:.0f}s" if not np.isnan(arr[0][i]) else "       n/a"
        d_sw = fmt_d(results[PROTO_SW_ARQ]['delay'])
        d_cq = fmt_d(results[PROTO_CARQ]['delay'])
        d_ca = fmt_d(results[PROTO_CA]['delay'])
        print(f"{s:+4d}dB | {d_sw:>20s} | {d_cq:>20s} | {d_ca:>22s}")

    print(f"\n{'SNR':>5s} | {'S&W ARQ Ovhd':>16s} | {'CARQ Ovhd':>16s} | {'CA-CHARQ Ovhd':>18s}")
    for i, s in enumerate(SNR_LIST):
        def fmt_o(arr): return f"{arr[0][i]:.3f}±{arr[1][i]:.3f}" if not np.isnan(arr[0][i]) else "         n/a"
        o_sw = fmt_o(results[PROTO_SW_ARQ]['overhead'])
        o_cq = fmt_o(results[PROTO_CARQ]['overhead'])
        o_ca = fmt_o(results[PROTO_CA]['overhead'])
        print(f"{s:+4d}dB | {o_sw:>16s} | {o_cq:>16s} | {o_ca:>18s}")
    print("=" * 65)
    print("Done.")
