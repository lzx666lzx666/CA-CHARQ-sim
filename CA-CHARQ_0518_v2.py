import simpy
import math
import random
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. 物理层与水声信道核心参数
# ==========================================
SOUND_SPEED = 1500.0       
BIT_RATE = 1200.0          
BITS_PER_CHUNK = 80        
CHUNKS_SYS = 100           
CHUNKS_PARITY_MAX = 90     # 修复：补充最大奇偶校验块数
TX_POWER_W = 15.0          
NOISE_VAR = 1e-7           

TARGET_MI = 260.0          
MAX_NACK_RETRYS = 3        
T_MAX_WINDOW = 3.0         
W1, W2, W3 = 0.4, 0.2, 0.4 
INITIAL_ENERGY = 10000.0   

RV_SLICES = {
    0: (0, 100),           # RV0: 全量数据 (100块)
    1: (100, 130),         # RV1: 少量冗余 (30块) - 置信度高
    2: (100, 160),         # RV2: 中量冗余 (60块) - 置信度中
    3: (100, 190)          # RV3: 大量冗余 (90块) - 置信度低
}

PROTO_CLASSIC = "Classic C-HARQ (Chase Combining)"
PROTO_CA = "CA-CHARQ (Proposed IR-HARQ)"

# ==========================================
# 2. 统计中心
# ==========================================
class AcademicStatsTracker:
    def __init__(self):
        self.total_success_packets = 0
        self.total_transmitted_chunks = 0
        self.delays = []
        self.dropped_packets = 0

    def record_tx(self, num_chunks):
        self.total_transmitted_chunks += num_chunks

    def record_e2e_success(self, delay):
        self.total_success_packets += 1
        self.delays.append(delay)
        
    def record_drop(self):
        self.dropped_packets += 1

    def get_throughput(self, total_time):
        return (self.total_success_packets * CHUNKS_SYS) / total_time

    def get_avg_delay(self):
        return np.mean(self.delays) if self.delays else 0.0

    def get_overhead(self):
        useful_chunks = self.total_success_packets * CHUNKS_SYS
        return self.total_transmitted_chunks / useful_chunks if useful_chunks > 0 else np.nan

# ==========================================
# 3. 数据包类 (引入单跳 Tx/Rx 标识)
# ==========================================
class PhysicalPacket:
    def __init__(self, pkt_type, hop_tx, hop_rx, pid, rv_level=0, creation_time=0.0):
        self.pkt_type = pkt_type        
        self.hop_tx = hop_tx  
        self.hop_rx = hop_rx  
        self.pid = pid
        self.rv_level = rv_level
        self.creation_time = creation_time
        
        self.start_idx, self.end_idx = RV_SLICES.get(rv_level, (0, 0))
        self.num_chunks = self.end_idx - self.start_idx if pkt_type == 'DATA' else 5
        
        self.received_snr_array = None  
        self.avg_snr_linear = 0.0       
        self.nack_requested_rv = 0      
        self.header_ok = True
        self.c_pkt = 0.0                

# ==========================================
# 4. 多跳路由节点与单跳 HARQ 状态机
# ==========================================
class UnderwaterNode:
    def __init__(self, env, node_id, x, y, role, protocol, stats, network):
        self.env, self.node_id = env, node_id
        self.x, self.y = x, y
        self.role = role 
        self.protocol, self.stats, self.network = protocol, stats, network
        
        self.inbox = simpy.Store(env)
        self.tx_queue = simpy.Store(env) 
        
        self.energy = INITIAL_ENERGY
        self.soft_buffer = {}      
        self.active_backoffs = {}  
        
        self.next_hop_id = None
        self.is_dest = False
        
        self.helper_for_link = None 

        self.env.process(self.recv_loop())
        if self.role == 'ROUTER':
            self.env.process(self.tx_loop()) 

    def tx_loop(self):
        while True:
            pid, creation_time = yield self.tx_queue.get()
            
            hop_success = False
            for attempt in range(2): 
                yield self.env.process(self.execute_transmit('DATA', self.next_hop_id, pid, rv_level=0, creation_time=creation_time))
                
                timeout_event = self.env.timeout((1500.0 / SOUND_SPEED) * 2 + T_MAX_WINDOW * 3)
                wait_ack = simpy.Event(self.env)
                self.active_backoffs[f"ack_{pid}"] = wait_ack
                
                res = yield wait_ack | timeout_event
                
                if wait_ack in res:
                    msg = wait_ack.value
                    if msg['type'] == 'ACK':
                        hop_success = True
                        break 
                    elif msg['type'] == 'NACK':
                        helper_wait_time = T_MAX_WINDOW + (1000.0/SOUND_SPEED)
                        yield self.env.timeout(helper_wait_time)
                        
                        if not self.active_backoffs.get(f"helper_heard_{pid}", False):
                            req_rv = msg['req_rv']
                            yield self.env.process(self.execute_transmit('DATA', self.next_hop_id, pid, rv_level=req_rv, creation_time=creation_time))
                
                if f"ack_{pid}" in self.active_backoffs: del self.active_backoffs[f"ack_{pid}"]
                self.active_backoffs[f"helper_heard_{pid}"] = False

            if not hop_success:
                self.stats.record_drop()

    def recv_loop(self):
        while True:
            pkt = yield self.inbox.get()
            self.env.process(self.process_packet(pkt))

    def process_packet(self, pkt):
        if not pkt.header_ok: return 
        pid = pkt.pid

        if pkt.pkt_type == 'DATA':
            if self.role == 'ROUTER' and pkt.hop_tx != self.node_id and pkt.hop_rx == self.next_hop_id:
                self.active_backoffs[f"helper_heard_{pid}"] = True

            if self.role == 'HELPER' and pid in self.active_backoffs:
                if not self.active_backoffs[pid].triggered: self.active_backoffs[pid].succeed()

            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                if pid not in self.soft_buffer:
                    self.soft_buffer[pid] = np.zeros(CHUNKS_SYS + CHUNKS_PARITY_MAX)
                
                if isinstance(self.soft_buffer[pid], str): return 

                if self.protocol == PROTO_CA:
                    self.soft_buffer[pid][pkt.start_idx : pkt.end_idx] += pkt.received_snr_array
                else: 
                    if pkt.rv_level == 0: self.soft_buffer[pid][0:100] += pkt.received_snr_array

                accumulated_mi = np.sum(np.log2(1.0 + self.soft_buffer[pid]))

                if accumulated_mi >= TARGET_MI:
                    self.soft_buffer[pid] = "SUCCESS"
                    yield self.env.process(self.execute_transmit('ACK', pkt.hop_tx, pid))
                    
                    if self.is_dest:
                        self.stats.record_e2e_success(self.env.now - pkt.creation_time)
                    else:
                        self.tx_queue.put((pid, pkt.creation_time))
                else:
                    c_pkt = self.calculate_confidence(np.mean(self.soft_buffer[pid]), CHUNKS_SYS * BITS_PER_CHUNK)
                    req_rv = 3 if c_pkt < 0.35 else (2 if c_pkt < 0.70 else 1) if self.protocol == PROTO_CA else 0
                    yield self.env.process(self.execute_transmit('NACK', pkt.hop_tx, pid, req_rv=req_rv, c_pkt=c_pkt))

            elif self.role == 'HELPER' and self.helper_for_link == (pkt.hop_tx, pkt.hop_rx):
                if pkt.rv_level == 0:
                    relay_mi = np.sum(np.log2(1.0 + pkt.received_snr_array))
                    if relay_mi >= TARGET_MI:
                        self.soft_buffer[pid] = {"status": "DONE", "c_pkt": self.calculate_confidence(pkt.avg_snr_linear, CHUNKS_SYS * BITS_PER_CHUNK)}

        elif pkt.pkt_type == 'NACK':
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                if f"ack_{pid}" in self.active_backoffs and not self.active_backoffs[f"ack_{pid}"].triggered:
                    self.active_backoffs[f"ack_{pid}"].succeed({'type': 'NACK', 'req_rv': pkt.nack_requested_rv})
            
            elif self.role == 'HELPER' and self.helper_for_link == (pkt.hop_rx, pkt.hop_tx): 
                buffer_state = self.soft_buffer.get(pid)
                if isinstance(buffer_state, dict) and buffer_state.get("status") == "DONE":
                    self.env.process(self.relay_contention_handler(pkt, buffer_state["c_pkt"]))
                
        elif pkt.pkt_type == 'ACK':
            if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
                if f"ack_{pid}" in self.active_backoffs and not self.active_backoffs[f"ack_{pid}"].triggered:
                    self.active_backoffs[f"ack_{pid}"].succeed({'type': 'ACK'})

    def calculate_confidence(self, snr_linear, num_bits):
        std_dev = np.sqrt(4 * snr_linear + 1e-9)
        llrs = np.random.normal(2 * snr_linear, std_dev, size=int(num_bits))
        return float(np.clip(np.mean(np.tanh(np.abs(llrs) / 2.0)), 0.0, 1.0))

    def relay_contention_handler(self, pkt, my_c_pkt):
        pid = pkt.pid
        if pid in self.active_backoffs: return 
            
        if self.protocol == PROTO_CA:
            score = W1 * 0.8 + W2 * (self.energy / INITIAL_ENERGY) + W3 * my_c_pkt 
            t_backoff = (1.0 - np.clip(score, 0.0, 1.0)) * T_MAX_WINDOW + (500.0 / SOUND_SPEED)
        else:
            t_backoff = random.uniform(0.0, T_MAX_WINDOW) 

        cancel_event = simpy.Event(self.env)
        self.active_backoffs[pid] = cancel_event
        
        result = yield self.env.timeout(t_backoff) | cancel_event
        if cancel_event not in result: 
            rv_to_send = pkt.nack_requested_rv if self.protocol == PROTO_CA else 0
            yield self.env.process(self.execute_transmit('DATA', pkt.hop_tx, pid, rv_level=rv_to_send, creation_time=pkt.creation_time))
            if pid in self.active_backoffs: del self.active_backoffs[pid]

    def execute_transmit(self, pkt_type, target_id, pid, rv_level=0, req_rv=0, c_pkt=0.0, creation_time=0.0):
        pkt = PhysicalPacket(pkt_type, self.node_id, target_id, pid, rv_level, creation_time)
        pkt.nack_requested_rv = req_rv
        pkt.c_pkt = c_pkt
        
        air_tx_time = pkt.num_chunks * (BITS_PER_CHUNK / BIT_RATE)
        self.stats.record_tx(pkt.num_chunks)
        self.energy -= TX_POWER_W * air_tx_time 
        
        yield self.env.timeout(air_tx_time) 
        self.network.broadcast(self, pkt)

# ==========================================
# 5. 水声信道与多跳拓扑构建引擎
# ==========================================
class UnderwaterAcousticChannel:
    def __init__(self, env):
        self.env, self.nodes = env, []
    def broadcast(self, sender, pkt):
        for receiver in self.nodes:
            if receiver == sender: continue
            dist = math.sqrt((sender.x - receiver.x)**2 + (sender.y - receiver.y)**2)
            prop_delay = dist / SOUND_SPEED
            
            clone = PhysicalPacket(pkt.pkt_type, pkt.hop_tx, pkt.hop_rx, pkt.pid, pkt.rv_level, pkt.creation_time)
            clone.nack_requested_rv, clone.c_pkt = pkt.nack_requested_rv, pkt.c_pkt
            
            if pkt.pkt_type == 'DATA':
                loss = (dist ** 2.0) * (10 ** ((4.2 * (dist / 1000.0)) / 10.0))
                avg_snr = (TX_POWER_W / loss) / NOISE_VAR if loss > 0 else 1.0
                clone.avg_snr_linear = avg_snr
                clone.received_snr_array = avg_snr * (np.random.rayleigh(1.0, pkt.num_chunks) ** 2.0)
                
            self.env.process(self.delay_delivery(receiver, clone, prop_delay))
    def delay_delivery(self, receiver, pkt, delay):
        yield self.env.timeout(delay)
        receiver.inbox.put(pkt)

def execute_academic_sim(e2e_distance, protocol, sim_time=15000):
    env = simpy.Environment()
    stats = AcademicStatsTracker()
    channel = UnderwaterAcousticChannel(env)
    
    num_hops = 3
    d = e2e_distance / num_hops 
    
    routers = []
    for i in range(num_hops + 1):
        node = UnderwaterNode(env, i, i * d, 0, 'ROUTER', protocol, stats, channel)
        if i < num_hops: node.next_hop_id = i + 1
        if i == num_hops: node.is_dest = True
        routers.append(node)
        channel.nodes.append(node)
        
    for i in range(num_hops):
        helper = UnderwaterNode(env, 10+i, i*d + d/2, 200, 'HELPER', protocol, stats, channel)
        helper.helper_for_link = (i, i+1) 
        channel.nodes.append(helper)
    
    def traffic_generator():
        pid = 0
        while True:
            routers[0].tx_queue.put((pid, env.now))
            pid += 1
            yield env.timeout(random.expovariate(1.0 / 20.0)) 
            
    env.process(traffic_generator())
    env.run(until=sim_time) 
    
    return {
        "throughput": stats.get_throughput(sim_time), 
        "delay": stats.get_avg_delay(),
        "overhead": stats.get_overhead(),
        "drops": stats.dropped_packets
    }

if __name__ == "__main__":
    test_distances = [1000, 1500, 2000, 2500, 3000] 
    
    ca_metrics = {'throughput': [], 'delay': [], 'overhead': []}
    classic_metrics = {'throughput': [], 'delay': [], 'overhead': []}
    
    TOTAL_SIM_TIME = 15000 
    
    print("🚀 启动水下多跳网络 (3 Hops) 仿真，测试单跳 HARQ 的端到端效能...")
    for dist in test_distances:
        print(f"   > 端到端距离: {dist}m (单跳 {dist/3:.1f}m) ...")
        
        res_ca = execute_academic_sim(dist, PROTO_CA, sim_time=TOTAL_SIM_TIME)
        ca_metrics['throughput'].append(res_ca['throughput'])
        ca_metrics['delay'].append(res_ca['delay'])
        ca_metrics['overhead'].append(res_ca['overhead'])
        print(f"     [CA-CHARQ] 丢包: {res_ca['drops']} | 平均延迟: {res_ca['delay']:.1f}s")
        
        res_cl = execute_academic_sim(dist, PROTO_CLASSIC, sim_time=TOTAL_SIM_TIME)
        classic_metrics['throughput'].append(res_cl['throughput'])
        classic_metrics['delay'].append(res_cl['delay'])
        classic_metrics['overhead'].append(res_cl['overhead'])
        print(f"     [Classic]  丢包: {res_cl['drops']} | 平均延迟: {res_cl['delay']:.1f}s")
        
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17, 5))
    
    ax1.plot(test_distances, ca_metrics['throughput'], 'b-o', linewidth=2.5, markersize=7, label=PROTO_CA)
    ax1.plot(test_distances, classic_metrics['throughput'], 'r--s', linewidth=2.5, markersize=7, label=PROTO_CLASSIC)
    ax1.set_title("E2E Throughput Capacity (Multi-Hop)")
    ax1.set_xlabel("E2E Distance (m)")
    ax1.set_ylabel("Effective Throughput (Chunks/sec)")
    ax1.grid(True, linestyle=':', alpha=0.6); ax1.legend()
    
    ax2.plot(test_distances, ca_metrics['delay'], 'b-o', linewidth=2.5, markersize=7, label=PROTO_CA)
    ax2.plot(test_distances, classic_metrics['delay'], 'r--s', linewidth=2.5, markersize=7, label=PROTO_CLASSIC)
    ax2.set_title("Average E2E Packet Delay")
    ax2.set_xlabel("E2E Distance (m)")
    ax2.set_ylabel("Latency Delay (seconds)")
    ax2.grid(True, linestyle=':', alpha=0.6); ax2.legend()
    
    ax3.plot(test_distances, ca_metrics['overhead'], 'b-o', linewidth=2.5, markersize=7, label=PROTO_CA)
    ax3.plot(test_distances, classic_metrics['overhead'], 'r--s', linewidth=2.5, markersize=7, label=PROTO_CLASSIC)
    ax3.set_title("Network Transmission Overhead Ratio")
    ax3.set_xlabel("E2E Distance (m)")
    ax3.set_ylabel("Total Tx / Successfully Decoded")
    ax3.grid(True, linestyle=':', alpha=0.6); ax3.legend()
    
    plt.tight_layout()
    plt.show()