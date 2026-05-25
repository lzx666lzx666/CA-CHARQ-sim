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
SOUND_SPEED = 1500.0
BIT_RATE = 1200.0
BITS_PER_CHUNK = 80
CHUNKS_SYS = 100
CHUNKS_PARITY_MAX = 90
TX_POWER_W = 15.0
TARGET_MI = 80.0
MAX_HOP_RETRYS = 8
MAX_MERGE_ATTEMPTS = 12
T_MAX_WINDOW = 1.5
T_PROTECTION_GAP = 0.2
W1, W2, W3 = 0.40, 0.25, 0.35
INITIAL_ENERGY = 10000.0
RICIAN_K = 2.0
HOP_DIST = 600.0
NUM_HOPS = 3

RV_SLICES = {0: (0, 100), 1: (100, 130), 2: (100, 160), 3: (100, 190)}

PROTO_CLASSIC = "Classic C-HARQ (Chase)"
PROTO_CA = "CA-CHARQ (IR-HARQ)"


# ==========================================
# 2. 统计中心（E2E 级别，用 packet 状态去重）
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

    def record_data_tx(self):
        self.total_data_tx += 1

    def record_nack_tx(self):
        self.total_nack_tx += 1

    def record_ack_tx(self):
        self.total_ack_tx += 1

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
# 5. 置信度
# ==========================================
def confidence_quantize(acc_mi):
    ratio = acc_mi / TARGET_MI
    if ratio < 0.45:
        return ratio, 3
    elif ratio < 0.65:
        return ratio, 2
    elif ratio < 0.85:
        return ratio, 1
    else:
        return ratio, 0


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
        self.helper_overheard = defaultdict(bool)
        self.helper_cancel_events = {}
        self.next_hop_id = None
        self.is_dest = False
        self.helper_for_link = None
        self.env.process(self.recv_loop())
        if self.role == 'ROUTER':
            self.env.process(self.tx_loop())

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
                        yield self.env.timeout(
                            T_MAX_WINDOW * 2 + T_PROTECTION_GAP)
                        if not self.helper_overheard.get(pid, False):
                            rv = msg['req_rv']
                            if self.protocol == PROTO_CLASSIC:
                                rv = 0
                            yield self.env.process(self.send_data(
                                self.next_hop_id, pid, rv, creation_time))
                        self.helper_overheard[pid] = False
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

    def recv_loop(self):
        while True:
            pkt = yield self.inbox.get()
            self.env.process(self.handle(pkt))

    def handle(self, pkt):
        if not pkt.header_ok:
            return
        pid = pkt.pid

        if pkt.pkt_type == 'DATA':
            if (self.role == 'ROUTER' and pkt.hop_tx != self.node_id
                    and pkt.hop_rx == self.next_hop_id):
                self.helper_overheard[pid] = True

            if (self.role == 'HELPER'
                    and pid in self.helper_cancel_events):
                ce = self.helper_cancel_events[pid]
                if not ce.triggered:
                    ce.succeed()

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

                if self.protocol == PROTO_CA:
                    a, b = pkt.start_idx, pkt.end_idx
                    self.soft_buffer[pid][a:b] += pkt.received_snr_array
                else:
                    self.soft_buffer[pid][0:100] += pkt.received_snr_array

                acc_mi = np.sum(np.log2(1.0 + self.soft_buffer[pid]))

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
                    c, rv = confidence_quantize(acc_mi)
                    if self.merge_count[pid] >= MAX_MERGE_ATTEMPTS:
                        self.soft_buffer.pop(pid, None)
                        self.merge_count.pop(pid, None)
                        return
                    yield self.env.process(self.send_nack(
                        pkt.hop_tx, pid, rv, c))

            elif (self.role == 'HELPER'
                  and self.helper_for_link == (pkt.hop_tx, pkt.hop_rx)):
                if pkt.rv_level == 0:
                    mi = np.sum(np.log2(1.0 + pkt.received_snr_array))
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

    def contend(self, pkt, my_c):
        pid = pkt.pid
        if pid in self.helper_cancel_events:
            return
        if self.protocol == PROTO_CA:
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
            rv = pkt.nack_requested_rv if self.protocol == PROTO_CA else 0
            yield self.env.process(self.send_data(
                pkt.hop_tx, pid, rv, pkt.creation_time))
        self.helper_cancel_events.pop(pid, None)

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
# 8. 仿真执行
# ==========================================
def run_sim(snr_db, protocol, sim_time=60000):
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

    for i in range(NUM_HOPS):
        h = UnderwaterNode(env, 10 + i,
                           i * HOP_DIST + HOP_DIST / 2, 200,
                           'HELPER', protocol, stats, ch, nv)
        h.helper_for_link = (i, i + 1)
        ch.nodes.append(h)

    def gen():
        pid = 0
        while True:
            routers[0].tx_queue.put((pid, env.now))
            pid += 1
            yield env.timeout(random.expovariate(1.0 / 30.0))

    env.process(gen())
    env.run(until=sim_time)

    return {
        "delay": stats.get_avg_delay(),
        "delay_std": stats.get_delay_std(),
        "overhead": stats.get_overhead(),
        "throughput": stats.get_throughput(sim_time),
        "drop_rate": stats.get_drop_rate(),
        "success": stats.e2e_success_count,
        "drops": stats.e2e_drop_count,
        "data_tx": stats.total_data_tx,
        "nack_tx": stats.total_nack_tx,
        "ack_tx": stats.total_ack_tx,
        "actual_snr": avg_snr_db(nv),
    }


# ==========================================
# 9. 主程序
# ==========================================
if __name__ == "__main__":
    SNR_LIST = [-8, -6, -4, -2, 0, 2, 4, 6]
    SIM_TIME = 60000

    ca = {'delay': [], 'overhead': [], 'throughput': [],
          'drop_rate': [], 'delay_std': []}
    cl = {'delay': [], 'overhead': [], 'throughput': [],
          'drop_rate': [], 'delay_std': []}

    print("=" * 60)
    print(" CA-CHARQ vs Classic C-HARQ | SNR Sweep")
    print(f" {NUM_HOPS} hops x {HOP_DIST}m = {NUM_HOPS*HOP_DIST}m E2E")
    print(f" SimTime={SIM_TIME}s TARGET_MI={TARGET_MI:.0f} RicianK={RICIAN_K} Retries={MAX_HOP_RETRYS}")
    print("=" * 60)

    for snr in SNR_LIST:
        print(f"\n--- SNR = {snr:+d} dB ---")

        r = run_sim(snr, PROTO_CA, SIM_TIME)
        ca['delay'].append(r['delay'])
        ca['overhead'].append(r['overhead'])
        ca['throughput'].append(r['throughput'])
        ca['drop_rate'].append(r['drop_rate'])
        ca['delay_std'].append(r['delay_std'])
        print(f"  CA-CHARQ: S={r['success']} Drops={r['drops']} "
              f"Delay={r['delay']}s Ovhd={r['overhead']} "
              f"DR={r['drop_rate']:.3f} "
              f"Data={r['data_tx']} Nack={r['nack_tx']} "
              f"SNR={r['actual_snr']:.1f}dB")

        r = run_sim(snr, PROTO_CLASSIC, SIM_TIME)
        cl['delay'].append(r['delay'])
        cl['overhead'].append(r['overhead'])
        cl['throughput'].append(r['throughput'])
        cl['drop_rate'].append(r['drop_rate'])
        cl['delay_std'].append(r['delay_std'])
        print(f"  Classic:  S={r['success']} Drops={r['drops']} "
              f"Delay={r['delay']}s Ovhd={r['overhead']} "
              f"DR={r['drop_rate']:.3f} "
              f"Data={r['data_tx']} Nack={r['nack_tx']} "
              f"SNR={r['actual_snr']:.1f}dB")

    print(f"\n{'=' * 60}")
    print("Summary:")
    for i, s in enumerate(SNR_LIST):
        print(f"  SNR={s:+3d}dB: "
              f"CA D={ca['delay'][i]:8.1f}s O={ca['overhead'][i]:6.3f} "
              f"DR={ca['drop_rate'][i]:.3f} | "
              f"CL D={cl['delay'][i]:8.1f}s O={cl['overhead'][i]:6.3f} "
              f"DR={cl['drop_rate'][i]:.3f}")
    print("=" * 60)

    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.5))

    ax1.errorbar(SNR_LIST, ca['delay'], yerr=ca['delay_std'],
                 fmt='b-o', capsize=4, lw=2.5, ms=8, label=PROTO_CA)
    ax1.errorbar(SNR_LIST, cl['delay'], yerr=cl['delay_std'],
                 fmt='r--s', capsize=4, lw=2.5, ms=8, label=PROTO_CLASSIC)
    ax1.set_title("E2E Packet Delay vs SNR", fontsize=13, fontweight='bold')
    ax1.set_xlabel("Per-Hop SNR (dB)")
    ax1.set_ylabel("End-to-End Delay (s)")
    ax1.grid(True, ls=':', alpha=0.5)
    ax1.legend(fontsize=10)

    ax2.plot(SNR_LIST, ca['overhead'], 'b-o', lw=2.5, ms=8, label=PROTO_CA)
    ax2.plot(SNR_LIST, cl['overhead'], 'r--s', lw=2.5, ms=8, label=PROTO_CLASSIC)
    ax2.set_title("Transmission Overhead vs SNR", fontsize=13, fontweight='bold')
    ax2.set_xlabel("Per-Hop SNR (dB)")
    ax2.set_ylabel("Overhead (Tx Chunks / Useful Chunks)")
    ax2.grid(True, ls=':', alpha=0.5)
    ax2.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig("SNR_Delay_Overhead.png", dpi=150, bbox_inches='tight')
    print("\n[OK] SNR_Delay_Overhead.png")

    fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(15, 5.5))

    ax3.plot(SNR_LIST, ca['drop_rate'], 'b-o', lw=2.5, ms=8, label=PROTO_CA)
    ax3.plot(SNR_LIST, cl['drop_rate'], 'r--s', lw=2.5, ms=8, label=PROTO_CLASSIC)
    ax3.set_title("E2E Drop Rate vs SNR", fontsize=13, fontweight='bold')
    ax3.set_xlabel("Per-Hop SNR (dB)")
    ax3.set_ylabel("Drop Rate")
    ax3.grid(True, ls=':', alpha=0.5)
    ax3.legend(fontsize=10)

    ax4.plot(SNR_LIST, ca['throughput'], 'b-o', lw=2.5, ms=8, label=PROTO_CA)
    ax4.plot(SNR_LIST, cl['throughput'], 'r--s', lw=2.5, ms=8, label=PROTO_CLASSIC)
    ax4.set_title("E2E Throughput vs SNR", fontsize=13, fontweight='bold')
    ax4.set_xlabel("Per-Hop SNR (dB)")
    ax4.set_ylabel("Throughput (Chunks/s)")
    ax4.grid(True, ls=':', alpha=0.5)
    ax4.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig("SNR_DropRate_Throughput.png", dpi=150, bbox_inches='tight')
    print("[OK] SNR_DropRate_Throughput.png")

    plt.close('all')
    print("\nDone.")
