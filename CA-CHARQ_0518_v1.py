import simpy
import random
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict

# ==========================================
# 1. 物理层与网络全局参数配置
# ==========================================
SOUND_SPEED = 1500.0  # 水下声速 m/s
MAX_RANGE = 3000.0    # 节点间最大通信距离 3000m
T_PROP_MAX = MAX_RANGE / SOUND_SPEED  # 最大单程传播延迟 2.0s

# MAC层协作定时器参数配置 (极其关键的防碰撞护城河)
T_WINDOW = 3.0        # 协作节点竞争退避窗口 3.0s
T_PROCESS = 0.5       # 节点处理、编解码硬件时间

# 严格的定时器层级约束 (数学闭环)
T_PROBE = 2 * T_PROP_MAX + T_PROCESS                  # 源节点短探测定时器 (4.5s)
T_DEST_WAIT = 2 * T_PROP_MAX + T_WINDOW + T_PROCESS   # 目的节点等待冗余包定时器 (7.5s)
MAX_NACK_RETRIES = 3                                  # 目的节点最多发送NACK次数
T_SOURCE_LONG = MAX_NACK_RETRIES * T_DEST_WAIT + 1.0  # 源节点长静默兜底定时器 (23.5s)

# ==========================================
# 2. 数据包与帧结构设计 (分离校验思想)
# ==========================================
class PacketType:
    DATA = "DATA"
    NACK = "NACK"
    ACK = "ACK"

@dataclass
class MACHeader:
    src_id: int
    dest_id: int
    next_hop_id: int
    pid: int              # HARQ 进程号 (支持多进程并发)
    ndi: int              # 新数据指示符 (翻转代表新包)
    rv_level: int         # 冗余版本 (0=RV0初传, 1=RV1, 2=RV2, 3=RV3)
    crc_ok: bool = True   # Header 独立CRC校验状态

@dataclass
class Payload:
    data_id: str
    rv_level: int
    crc_ok: bool = True   # Payload 独立CRC校验状态
    # 模拟物理层软信息，真实环境中是 LLR 矩阵
    soft_info_quality: float = 1.0 

@dataclass
class Packet:
    pkt_type: str
    preamble_ok: bool = True  # 同步帧状态 (False代表物理层失聪)
    header: MACHeader = None
    payload: Payload = None
    
    # 专门为 富NACK (Rich NACK) 设计的字段
    nack_cpkt_quantized: int = 0  # 量化后的置信度 (例如: 3请求RV3大量冗余, 1请求RV1少量)
    
# ==========================================
# 3. 核心节点类设计 (含MAC层状态机)
# ==========================================
class UnderwaterNode:
    def __init__(self, env, node_id, x, y, role="RELAY"):
        self.env = env
        self.node_id = node_id
        self.x = x
        self.y = y
        self.role = role  # SOURCE, RELAY, DEST
        self.network = None
        self.energy = 100.0  # 初始能量
        
        self.inbox = simpy.Store(env)
        self.action = env.process(self.run())
        
        # 节点状态维护
        self.soft_combine_buffer = {}  # 软合并缓存池 (PID -> accumulated_quality)
        self.active_backoffs = {}      # 协作节点正在进行的退避定时器 (PID -> SimPy Event)
        self.source_nack_received = {} # 源节点记录是否收到了NACK (PID -> bool)

    def log(self, msg):
        print(f"[{self.env.now:05.1f}s] [Node {self.node_id}({self.role})] : {msg}")

    # --- 接收处理主循环 ---
    def run(self):
        while True:
            pkt = yield self.inbox.get()
            self.process_packet(pkt)

    def process_packet(self, pkt):
        # 1. 物理层同步帧检测
        if not pkt.preamble_ok:
            return  # 物理层失聪，直接丢弃，不唤醒上层

        # 2. Header 独立校验
        if not pkt.header.crc_ok:
            self.log(f"Header CRC 失败，无法识别数据，直接丢弃。")
            return
            
        pid = pkt.header.pid
        
        # 3. 业务逻辑分发
        if pkt.pkt_type == PacketType.DATA:
            self.handle_data(pkt)
        elif pkt.pkt_type == PacketType.NACK:
            self.handle_nack(pkt)
        elif pkt.pkt_type == PacketType.ACK:
            self.handle_ack(pkt)

    # --- 数据帧(DATA)处理逻辑 ---
    def handle_data(self, pkt):
        pid = pkt.header.pid
        
        # 协作节点：如果在退避中听到别人发了数据，立刻取消自己的退避 (CSMA防冲突)
        if self.role == "RELAY" and pid in self.active_backoffs:
            self.log(f"监听到其他节点已发送 RV 补丁，挂起/取消本地 PID {pid} 的退避竞争。")
            self.active_backoffs[pid].succeed() # 触发取消事件
            del self.active_backoffs[pid]

        if self.role == "DEST":
            # Payload 独立校验
            if pkt.payload.crc_ok:
                self.log(f"PID {pid} Payload CRC 成功！数据完美解码。")
                self.send_ack(pid)
            else:
                self.log(f"PID {pid} Payload CRC 失败！(RV={pkt.header.rv_level}) 触发跨层软合并与自适应求救。")
                self.trigger_harq_process(pkt)
                
        if self.role == "RELAY":
            # 真实环境中，协作节点尝试解码，存入本地，等NACK触发
            if pkt.payload.crc_ok:
                self.soft_combine_buffer[pid] = pkt # 备用
                
    # --- HARQ 软合并与富NACK触发 (Dest专属) ---
    def trigger_harq_process(self, pkt):
        pid = pkt.header.pid
        
        # 1. 软合并 LLR 信息 (此处用质量分累加简单模拟)
        if pid not in self.soft_combine_buffer:
            self.soft_combine_buffer[pid] = 0.0
        self.soft_combine_buffer[pid] += pkt.payload.soft_info_quality
        current_quality = self.soft_combine_buffer[pid]
        
        # 2. 计算 Cpkt 并量化映射到需要的 RV 等级
        if current_quality >= 2.0:  # 假设质量到2.0就能解出来
            self.log(f"跨路径软合并成功！恢复出原数据。")
            self.send_ack(pid)
            return
            
        # 量化置信度：质量越差，需要的冗余越多 (3对应RV3)
        req_rv = 3 if current_quality < 0.5 else (2 if current_quality < 1.0 else 1)
        self.log(f"当前置信度较低，量化 Cpkt 请求补丁级别: RV{req_rv}")
        
        # 3. 启动 $T_{dest\_wait}$ 定时器循环
        self.env.process(self.dest_wait_loop(pid, req_rv))

    def dest_wait_loop(self, pid, req_rv):
        for attempt in range(MAX_NACK_RETRIES):
            self.send_nack(pid, req_rv)
            self.log(f"启动 T_dest_wait 定时器 ({T_DEST_WAIT}s)，等待协作节点...")
            
            # 等待 RV 包到达 或 超时
            rv_arrived_event = simpy.Event(self.env)
            # (实战中需在 handle_data 中触发此 Event，此处为仿真简化，直接用 timeout 演示宏观状态)
            
            yield self.env.timeout(T_DEST_WAIT)
            self.log(f"T_dest_wait 超时！第 {attempt+1} 次 NACK 无响应。")
            
        self.log(f"已达到最大NACK重试次数，清空 PID {pid} 缓存，等待源节点长定时器兜底。")
        self.soft_combine_buffer.pop(pid, None)

    # --- 控制帧(NACK)处理逻辑 ---
    def handle_nack(self, pkt):
        pid = pkt.header.pid
        req_rv = pkt.nack_cpkt_quantized
        
        if self.role == "SOURCE":
            self.log(f"听到第一声 NACK！挂起短探测 T_probe，切入长静默兜底 T_source_long。")
            self.source_nack_received[pid] = True
            
        elif self.role == "RELAY":
            # 只有解码成功的协作节点才参与竞争
            if pid in self.soft_combine_buffer:
                self.env.process(self.relay_backoff_process(pid, req_rv))

    # --- 协作节点退避打分进程 (核心创新) ---
    def relay_backoff_process(self, pid, req_rv):
        # 计算综合得分 S_i (此处用随机数模拟 SNR、能量的综合映射 0~1)
        score_Si = random.uniform(0.3, 0.9)
        t_backoff = (1.0 - score_Si) * T_WINDOW
        
        self.log(f"收到请求，打分 Si={score_Si:.2f}，映射退避定时器 T_backoff={t_backoff:.2f}s")
        
        cancel_event = simpy.Event(self.env)
        self.active_backoffs[pid] = cancel_event
        
        # 竞争倒计时
        result = yield self.env.timeout(t_backoff) | cancel_event
        
        if cancel_event not in result: # 如果没有被挂起/取消，说明自己赢了
            self.log(f"倒计时结束，赢得竞争！下发自适应冗余补丁: RV{req_rv}")
            self.send_data(dest_id=self.network.dest.node_id, pid=pid, rv_level=req_rv)
            if pid in self.active_backoffs: del self.active_backoffs[pid]

    # --- 数据发送与源节点双阶段定时器 ---
    def start_source_transmission(self, dest_node, pid):
        self.log(f"---- 开始全新传输进程 PID {pid} ----")
        self.source_nack_received[pid] = False
        
        # 发送 RV0
        self.send_data(dest_node.node_id, pid, rv_level=0)
        
        # 阶段一：启动短探测定时器 T_probe
        self.log(f"启动短探测 T_probe ({T_PROBE}s)，监控目的节点存活状态...")
        yield self.env.timeout(T_PROBE)
        
        if not self.source_nack_received[pid]:
            self.log(f"【异常恢复】T_probe 超时！目的节点彻底失聪(未发NACK)，立即重启发送RV0！")
            self.env.process(self.start_source_transmission(dest_node, pid)) # 递归重传
            return
            
        # 阶段二：启动长静默定时器 T_source_long
        self.log(f"探测到目的节点存活。启动长静默兜底 T_source_long ({T_SOURCE_LONG}s)...")
        yield self.env.timeout(T_SOURCE_LONG)
        
        self.log(f"【异常恢复】T_source_long 彻底溢出！协作全军覆没，源节点强行兜底重传 RV0！")
        self.env.process(self.start_source_transmission(dest_node, pid))

    # --- 底层发包工具函数 ---
    def send_data(self, dest_id, pid, rv_level):
        hdr = MACHeader(src_id=self.node_id, dest_id=dest_id, next_hop_id=dest_id, pid=pid, ndi=1, rv_level=rv_level)
        pld = Payload(data_id="DATA", rv_level=rv_level, soft_info_quality=random.uniform(0.1, 0.4))
        pkt = Packet(pkt_type=PacketType.DATA, header=hdr, payload=pld)
        self.network.broadcast(self, pkt)

    def send_nack(self, pid, req_rv):
        hdr = MACHeader(src_id=self.node_id, dest_id=0, next_hop_id=0, pid=pid, ndi=0, rv_level=0)
        pkt = Packet(pkt_type=PacketType.NACK, header=hdr, nack_cpkt_quantized=req_rv)
        self.network.broadcast(self, pkt)
        
    def send_ack(self, pid):
        # 简化处理
        self.log("发送 ACK，完成当前进程。")

# ==========================================
# 4. 网络环境类 (信道延迟建模与故障注入)
# ==========================================
class UnderwaterNetwork:
    def __init__(self, env):
        self.env = env
        self.nodes = []
        # 故障注入控制器
        self.fault_config = {
            "force_preamble_loss": False,
            "force_payload_error": False,
            "force_nack_loss": False
        }

    def add_node(self, node):
        node.network = self
        self.nodes.append(node)
        if node.role == "DEST": self.dest = node

    def get_distance(self, n1, n2):
        return math.sqrt((n1.x - n2.x)**2 + (n1.y - n2.y)**2)

    def broadcast(self, sender, pkt):
        for receiver in self.nodes:
            if receiver == sender: continue
            
            # 计算水声长延迟
            dist = self.get_distance(sender, receiver)
            delay = dist / SOUND_SPEED
            
            # 克隆数据包用于独立信道传输
            pkt_clone = Packet(pkt_type=pkt.pkt_type, header=pkt.header, payload=pkt.payload, nack_cpkt_quantized=pkt.nack_cpkt_quantized)
            
            # ==== 故障注入层 ====
            if self.fault_config["force_preamble_loss"] and receiver.role == "DEST" and pkt.pkt_type == PacketType.DATA:
                pkt_clone.preamble_ok = False
            
            if self.fault_config["force_payload_error"] and pkt.pkt_type == PacketType.DATA and pkt.header.rv_level == 0:
                pkt_clone.payload.crc_ok = False
                
            if self.fault_config["force_nack_loss"] and pkt.pkt_type == PacketType.NACK:
                pkt_clone.preamble_ok = False # 让所有人听不到 NACK
            
            self.env.process(self.deliver_packet(receiver, pkt_clone, delay))

    def deliver_packet(self, receiver, pkt, delay):
        yield self.env.timeout(delay) # 真实水下传播过程
        receiver.inbox.put(pkt)

# ==========================================
# 5. 仿真运行与场景测试
# ==========================================
def run_simulation(scenario_name, faults):
    print(f"\n{'='*50}\n开始仿真场景: {scenario_name}\n{'='*50}")
    
    env = simpy.Environment()
    net = UnderwaterNetwork(env)
    net.fault_config.update(faults)
    
    # 构建拓扑: Source(0,0) --> Relay1(1000,500), Relay2(1500,-200) --> Dest(3000,0)
    # 单跳最大距离 = 3000m (最大延迟 2.0s)
    src = UnderwaterNode(env, node_id=1, x=0, y=0, role="SOURCE")
    r1 = UnderwaterNode(env, node_id=2, x=1000, y=500, role="RELAY")
    r2 = UnderwaterNode(env, node_id=3, x=1500, y=-200, role="RELAY")
    dest = UnderwaterNode(env, node_id=4, x=3000, y=0, role="DEST")
    
    net.add_node(src)
    net.add_node(r1)
    net.add_node(r2)
    net.add_node(dest)
    
    # 强制让 Relay 解码成功，具备协作资格 (为仿真控制变量)
    r1.soft_combine_buffer[99] = Packet("DATA") 
    r2.soft_combine_buffer[99] = Packet("DATA")

    # 启动进程 PID=99
    env.process(src.start_source_transmission(dest, pid=99))
    
    env.run(until=40) # 运行 40 秒

if __name__ == "__main__":
    
    # 场景 1: 完美协作 (Payload坏了，但NACK成功，R1/R2竞争，选出一个下发RV)
    run_simulation("正常自适应协作 (最佳中继下发RV补丁)", {
        "force_preamble_loss": False,
        "force_payload_error": True, # 让 RV0 必定报错触发 HARQ
        "force_nack_loss": False
    })
    
    # 场景 2: 致命物理层盲区 (同步帧在水下丢失，彻底失聪，源节点短定时器破局)
    run_simulation("物理层盲区应对 (T_probe 短探测生效)", {
        "force_preamble_loss": True, # Dest收不到RV0
        "force_payload_error": False,
        "force_nack_loss": False
    })
    
    # 场景 3: 绝望的孤岛 (目的节点发了NACK，但在海里丢了，源节点长定时器最终兜底)
    run_simulation("控制帧丢失与全局兜底 (T_source_long 破除死锁)", {
        "force_preamble_loss": False,
        "force_payload_error": True,
        "force_nack_loss": True     # NACK 发出后丢失
    })