# v6-plus-v1 实施计划

## 目标
1. 拉宽收敛区间（TARGET_MI 11000→15000，SNR 0-8dB）
2. CA-CHARQ在0dB延迟领先（新增Grace Period）
3. CA-CHARQ在部分区间开销低于S&W（Grace期内helper成功则省去源端重传）

## 基础改动

### 1. 参数调整
- TARGET_MI: 11000 → 15000
- SNR_LIST: [0,0.5,...,4.0] (9点) → [0,0.5,...,8.0] (17点)

### 2. 创建文件
- 复制 `CA-CHARQ-v6-plus.py` → `CA-CHARQ-v6-plus-v1.py`
- 基于v6-plus所有优化（源端始终RV0、NACK源端数据防护、helper仅发校验块等）

## CA-CHARQ Grace Period 实现

### Grace Period 机制
源端tx_loop在收到NACK(Cpkt)后，不立即发RV0重传，而是：
1. 计算 Grace_t（基于Cpkt对应的helper传输时间 + 竞争延迟 + 传播）
2. 等待 Grace_t 或 ACK（取先到者）
3. 若ACK先到 → hop_ok=True（helper成功，源端无需重传）
4. 若Grace超时 → 源端发RV0，进入常规重传

### Grace_t 计算
```
rv_chunks = {2:30, 1:60, 0:90}[cpkt]  # Cpkt → RV映射对应的chunk数
rv_tx_time = rv_chunks × BITS_PER_CHUNK / BIT_RATE
max_backoff = T_MAX_WINDOW * 2
Grace_t = max_backoff + rv_tx_time + 3 × (HOP_DIST / SOUND_SPEED) + 0.5

Cpkt=2(RV1): Grace_t = 3.0 + 2.0 + 1.2 + 0.5 = 6.7s
Cpkt=1(RV2): Grace_t = 3.0 + 4.0 + 1.2 + 0.5 = 8.7s
Cpkt=0(RV3): Grace_t = 3.0 + 6.0 + 1.2 + 0.5 = 10.7s
```

### tx_loop 修改
在 NACK 处理分支（else 和 elif NACK）中：
```python
# CA-CHARQ: 启动Grace等待helper
if self.protocol == PROTO_CA:
    cpkt = msg.get('cpkt', 2)
    rv_chunks = {0: 90, 1: 60, 2: 30}.get(cpkt, 30)
    rv_tx_t = rv_chunks * BITS_PER_CHUNK / BIT_RATE
    grace_t = T_MAX_WINDOW * 2 + rv_tx_t + 3 * HOP_DIST / SOUND_SPEED + 0.5
    
    grace_ev = self.env.timeout(grace_t)
    helper_ack_ev = self.helper_ack_events.setdefault(pid, simpy.Event(self.env))
    
    result = yield helper_ack_ev | grace_ev
    if helper_ack_ev in result:
        hop_ok = True
        break
    else:
        yield self.env.process(self.send_data(
            self.next_hop_id, pid, 0, creation_time))
else:
    yield self.env.process(self.send_data(
        self.next_hop_id, pid, 0, creation_time))
```

### handle() 修改：ACK 处理（触发 helper_ack_ev）
在 ACK 处理部分，当 CA-CHARQ 源端收到 ACK 时，触发对应的 helper_ack_ev：
```python
elif pkt.pkt_type == PKT_ACK:
    if self.role == 'ROUTER' and pkt.hop_rx == self.node_id:
        # 现有逻辑：触发 ack_events
        ...
        # 新增：CA-CHARQ Grace触发
        if self.protocol == PROTO_CA and pid in self.helper_ack_events:
            hev = self.helper_ack_events.pop(pid, None)
            if hev and not hev.triggered:
                hev.succeed({'type': 'ACK'})
```

### UnderwaterNode.__init__ 新增字段
```python
self.helper_ack_events = {}  # pid → Event for Grace Period ACK
```

## 预期结果

### 延迟对比（预期）
| SNR | S&W | C-HARQ | CA-CHARQ(+Grace) |
|---|---|---|---|
| 0dB | 需要2-3传 | Pac-1辅助 | Grace成功→**最低延迟** |
| 2dB | 需要2传 | 辅助有效 | 自适应RV+竞争→**领先** |
| 4dB | ~1.5传 | 辅助有效 | 自适应→**持续领先** |
| 6-8dB | 收敛过渡区 | 收敛 | 收敛 |

### 开销对比（预期）
- 0-3dB：Grace期内helper成功 → CA-CHARQ开销**接近或低于S&W**
- 3-8dB：收敛区，趋同

## 不变部分
- 三个对照组（S&W ARQ / C-ARQ / C-HARQ）完全不变
- 信道模型、helper布局逻辑不变
- 竞争机制（contend）、Cpkt映射不变
- 延迟+开销两张图，不画吞吐量
