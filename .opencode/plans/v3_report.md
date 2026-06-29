# v6-plus-v3 完整设计报告

## 执行摘要

本报告详述了CA-CHARQ-v6-plus-v3.py仿真平台的全部设计细节，包括物理层参数、信道模型、四种协议逻辑（S&W ARQ, C-ARQ, C-HARQ, CA-CHARQ）、置信度反馈机制、退避竞争算法、Grace Period 等。同时给出协议对比的理论分析及实测结果。

---

## 一、物理层参数

| 参数 | 值 | 含义 |
|---|---|---|
| SOUND_SPEED | 1500 m/s | 水下声速 |
| BIT_RATE | 1200 bps | 码元速率 |
| BITS_PER_CHUNK | 80 bit | 每块信息量 |
| CHUNKS_SYS | 100 | 系统数据块数 |
| CHUNKS_PARITY_MAX | 90 | 最大校验块数 |
| TX_POWER_W | 15 W | 发射功率 |
| TARGET_MI | 11000 | 解码所需累积MI阈值 |
| RICIAN_K | 2.0 | Rician K因子 |
| HOP_DIST | 600 m | 单跳距离 |
| NUM_HOPS | 5 | 跳数 |
| N_HELPERS_PER_HOP | 3 | 每跳协作节点数 |

### RV分片定义
```
RV_SLICES = {0: (0, 100),   1: (100, 130),
             2: (100, 160), 3: (100, 190)}
```
- RV0: 系统数据块0-100 (100块), 用于Chase合并
- RV1: 校验块100-130 (30块), 少量冗余
- RV2: 校验块100-160 (60块), 中等冗余
- RV3: 校验块100-190 (90块), 大量冗余

### C-HARQ固定FEC分片
```
CHARQ_FEC = [(100, 150), (150, 190)]  # Pac-1: 50块, Pac-2: 40块
```

---

## 二、信道模型

### 传播损耗
```
TL(d) = d^1.5 × 10^(0.04×d_km)
```
其中d_km为距离(km)。包含扩展损耗和吸收损耗。

### SNR控制
```
noise_var = TX_POWER_W / (TL(600m) × SNR_linear)
```
通过调节noise_var使每跳600m处接收SNR达到目标值。

### Rician衰落
```
I = sqrt(K/(K+1)) + sqrt(1/(2(K+1))) × N(0,1)
Q = sqrt(1/(2(K+1))) × N(0,1)
SNR_chunk = asnr × (I² + Q²)
```
每个chunk独立生成I/Q，模拟块级衰落。K=2时LOS分量占主导。

---

## 三、数据包结构 (PhysicalPacket)

### 字段
| 字段 | 类型 | 说明 |
|---|---|---|
| pkt_type | PKT_DATA/PKT_ACK/PKT_NACK | 包类型 |
| hop_tx | int | 发送节点ID |
| hop_rx | int | 目标节点ID |
| pid | int | 数据包ID |
| rv_level | int (0-3) | RV冗余级别 |
| creation_time | float | 源端创建时间 (用于E2E延迟) |
| fec_idx | int (-1/1/2) | C-HARQ FEC编号 |
| cpkt | int (-1/0-3) | CA-CHARQ置信度量化值 |
| num_chunks | int | 包内块数 |
| received_snr_array | ndarray | 接收端逐块SNR |

### 包大小
- DATA(RV0): 100块 × 80/1200 = 6.67s
- DATA(RV1): 30块 × 80/1200 = 2.0s
- DATA(RV2): 60块 × 80/1200 = 4.0s
- DATA(RV3): 90块 × 80/1200 = 6.0s
- ACK/NACK: 3块 × 80/1200 = 0.2s

---

## 四、节点架构 (UnderwaterNode)

### 节点类型
- ROUTER: 源端/目的端，有 tx_loop + recv_loop + handle
- HELPER: 协作节点，有 recv_loop + handle，参与竞争

### 关键状态字段
| 字段 | 说明 |
|---|---|
| soft_buffer[pid] | 190维向量，累加全部已收SNR，或标记"SUCCESS"/DECODED状态 |
| merge_count[pid] | 合并次数计数器 |
| hop_source[pid] | 当前跳的源节点ID |
| ack_events | pid→Event映射，tx_loop等待ACK/NACK |
| pending_response | 异步ACK/NACK缓存 |
| is_selected | C-HARQ/C-ARQ预选helper标记 |
| fec_sent[pid] | C-HARQ已发送FEC计数 |
| helper_sent[pid] | C-ARQ已发送计数 |
| nack_sent[pid] | 对照组一次性NACK标记 |
| nack_count[pid] | CA-CHARQ NACK计数 (防无限循环) |
| helper_cancel_events[pid] | 竞争取消事件 |
| helper_tx_cnt[pid] | helper每pid发送次数 |
| helper_ack_events[pid] | Grace Period ACK等待事件 |

---

## 五、协议逻辑详述

### 5.1 S&W ARQ (停等ARQ)
**性质**: 无协作，纯源端重传

**流程**:
1. 源端 tx_loop 发送 RV0 (100块系统数据)
2. 目的端 handle 累加 soft_buffer[0:100]，计算MI
3. MI ≥ 11000 → ACK → 跳完成 → 转发下一跳
4. MI < 11000 且 merge_count < 8 → NACK (仅一次，nack_sent标记)
5. 源端收到NACK→发送RV0_retry→目的端Chase累加→重新判断
6. 超时(7.3s) 或 重传次数达MAX_HOP_RETRYS(5)→丢包

**特征**: 大延迟、低开销；多次Chase合并累积MI

### 5.2 C-ARQ (协作ARQ)
**性质**: 1个预选helper(距中点最近)，helper发送完整RV0

**流程**:
1. 源端发送RV0，helper侦听并解码
2. 目的端失败→发送NACK(一次)→源端发RV0_retry
3. 预选helper(已解码)听到NACK→发送完整RV0
4. 目的端对两路RV0做**纯Chase合并**
5. 每跳至多MAX_HOP_RETRYS次helper响应

**特征**: helper无IR增益(仅重复发送)，开销高，延迟与S&W持平；代表了最简单的协作形式

### 5.3 C-HARQ (协作HARQ, Ghosh 2013)
**性质**: 1个预选helper，Proactive双FEC机制

**流程**:
1. 源端发送RV0，helper侦听并解码
2. 目的端失败→发送NACK(一次)→源端发RV0_retry
3. 预选helper(已解码)**立即**发送Pac-1(50校验块,@100-150)
4. 等待3.5s后**无条件**发送Pac-2(40校验块,@150-190)
5. 目的端: 源RV0做Chase合并(0-100) + FEC做IR合并(100-150, 150-190)

**特征**: IR增益显著减少所需传输次数，中高SNR延迟优于S&W；
        但强制双FEC造成冗余浪费(Pac-2未必需要)

### 5.4 CA-CHARQ (置信度自适应协作HARQ)
**性质**: 3个helper竞争 + 置信度量化 + 自适应RV + Grace Period

**置信度量化** (confidence_quantize):
```
ratio = acc_mi / 11000
ratio < 0.45  → Cpkt=0  (最低置信)
0.45-0.65     → Cpkt=1
0.65-0.85     → Cpkt=2
> 0.85        → Cpkt=3  (最高置信)
```

**目的端handle** (行292-347):
1. 接收DATA→按类别累加(Chase或IR)→计算MI
2. MI达标→SUCCESS→ACK→转发下一跳
3. MI不达标且merge_count未超限→仅对**源端数据**(hop_tx==hop_source)发送NACK_cpkt
4. NACK中嵌入Cpkt，nack_count计数(上限3)

**源端tx_loop** (行203-284):
1. 发送RV0后等待ACK/NACK/超时
2. 收到NACK(Cpkt)→进入Grace Period(仅Cpkt≥3):
   - 计算Grace_t = rv_tx_t + T_MAX_WINDOW/4 + 3×prop + 0.3
   - 创建helper_ack_event等待
   - yield Grace超时 OR helper_ack_event
   - 若ACK在Grace期内到达 → 跳成功完成
   - 若Grace超时 → 源端发送RV0_retry进入常规重传
3. CA-CHARQ源端**始终发送RV0**(Chase增益最大化)
4. gto = 7.3s (与对照组相同)

**helper竞争机制** contend() (行437-471):
1. 得分计算:
   ```
   score = 0.40×min(c_pkt,1.5) + 0.25×(energy/INITIAL)
           + 0.35/(1 + prop_to_midpoint/0.4)
   ```
   - c_pkt: helper自身解码置信度(连续值)
   - prop_to_midpoint: helper到链路中点的传播延迟
2. 退避定时器:
   ```
   t = (1-score)×T_MAX_WINDOW×2 + max(T_PROTECTION_GAP/4, 0.05)
   若 score > 0.90 → t = 0 (零退避)
   ```
3. 竞争取消: 其他helper监听到获胜者发包→触发cancel_event→退让
4. 获胜helper按Cpkt发送自适应RV:
   ```
   Cpkt≥2 → RV1 (30块, 2.0s) — 高置信少量校验
   Cpkt=1 → RV2 (60块, 4.0s) — 中置信中等校验
   Cpkt=0 → RV3 (90块, 6.0s) — 低置信大量校验
   ```

**helper解码** (行359-378):
1. 侦听源端RV0传输，Chase累加soft_buffer[0:100]
2. MI≥11000→标记DECODED，存储c_pkt和cpkt
3. 对CA-CHARQ helper，额外存储自身置信度用于竞争得分

**竞争取消检测** (行349-357):
1. CA-CHARQ helper收到其他helper对该链路的DATA包
2. 触发helper_cancel_events[pid]→该helper的退避定时器终止→退让

**ACK Grace触发** (行432-435):
1. 源端收到ACK时检查helper_ack_events
2. 若有pending的Grace等待事件→触发→Grace成功→源端跳过重传

**自适应RV vs C-HARQ对比**:
| 置信度 | CA-CHARQ helper发 | C-HARQ helper发 |
|---|---|---|
| 高(Cpkt=2-3) | RV1(30块,2.0s) | Pac-1(50块,3.33s)+Pac-2(40块,2.67s) |
| 中(Cpkt=1) | RV2(60块,4.0s) | 同上 |
| 低(Cpkt=0) | RV3(90块,6.0s) | 同上 |

CA-CHARQ在高置信时仅发30块(2.0s)，远小于C-HARQ的固定90块(6.0s)，
这使其在目标MI接近阈值时获得显著延迟优势。

---

## 六、统计指标

### StatsTracker
| 指标 | 公式 | 含义 |
|---|---|---|
| 延迟 | mean(e2e_delays) | 源端creation_time→目的端ACK的平均时间 |
| 开销 | total_tx_chunks / (success×100) | 每有用数据块的传输开销倍数 |
| 吞吐量 | (success×100) / SIM_TIME | 固定分母(8000s) |
| 丢包率 | drops / (success+drops) | 超过MAX_HOP_RETRYS未成功的比例 |

### 蒙特卡洛
- 每SNR点5次独立运行，不同随机种子
- 种子公式: abs(42+run×7919+int(snr×3571)+(1<<20)) % (2^31-1)
- 报告95% CI: mean ± 1.96×SE

---

## 七、仿真拓扑

### 节点布局
- 路由器: 0→1→2→3→4→5，5跳链路，x=i×600m, y=0
- Helper: 每跳3个，随机分布在源-目的圆交叠区域
  ```
  约束: dist(helper, source) ≤ 600m AND dist(helper, dest) ≤ 600m
  ```
- C-HARQ/C-ARQ: 3个helper中预选距**中点**最近者 (is_selected=True)
- CA-CHARQ: 不预选，3个全部参与竞争

### 发包模型
- 稀疏发包: 指数分布，均值30s
- 模拟8000s≈~266个数据包

---

## 八、理论分析

### MI计算
```
MI_per_chunk = log2(1 + SNR_chunk) × 80 bits
MI_total = Σ(MI_per_chunk)
```
对于100块系统数据，一传MI近似:
```
MI_1tx ≈ 100 × log2(1 + SNR_linear) × 80
```

### 关键SNR阈值
| SNR | SNR_linear | MI_1tx | 需要几传 |
|---|---|---|---|
| 0dB | 1.00 | ~8000 | 2传(Chase→16000) |
| 1dB | 1.26 | ~9600 | 1-2传 |
| 2dB | 1.59 | ~10970 | 1-2传(临界) |
| 3dB | 2.00 | ~12600 | 1传✓ |
| 4dB | 2.51 | ~14500 | 1传✓ |

收敛SNR: TARGET=11000 → log2(1+SNR)=1.375 → SNR=2.03dB(理论)
         实际考虑Rician衰落方差，实收敛~3.5-4.0dB

### TARGET_MI=11000的理论意义
等效FEC码率 = 8000/11000 ≈ 0.727 ≈ 3/4码率
对应实用LDPC/Turbo码所需MI，在水声通信中具有物理合理性
在此阈值下，0-4dB区间恰好覆盖"必重传→临界→必成功"全过渡区

---

## 九、实际仿真结果

参数: 5跳, 8000s, 5次MC, Rician K=2

### 延迟 (s, mean ± 95%CI)
| SNR | S&W ARQ | C-ARQ | C-HARQ | CA-CHARQ |
|---|---|---|---|---|
| 0.0dB | 83±1 | 82±2 | 72±4 | 72±4 |
| 0.5dB | 84±2 | 83±2 | 70±3 | 66±6 |
| 1.0dB | 82±1 | 81±1 | 67±4 | 61±3 |
| 1.5dB | 84±2 | 82±1 | 67±3 | 59±4 |
| 2.0dB | 82±2 | 80±2 | 64±2 | 55±1 |
| 2.5dB | 78±2 | 75±1 | 60±1 | 50±0 |
| 3.0dB | 53±2 | 52±1 | 46±0 | 42±0 |
| 3.5dB | 39±0 | 39±0 | 38±0 | 38±0 |
| 4.0dB | 38±0 | 38±0 | 38±0 | 38±0 |

### 开销 (Tx/Useful, mean)
| SNR | S&W ARQ | C-ARQ | C-HARQ | CA-CHARQ |
|---|---|---|---|---|
| 0.0dB | 10.40 | 13.56 | 13.31 | 13.29 |
| 0.5dB | 10.35 | 14.37 | 14.05 | 13.37 |
| 1.0dB | 10.38 | 14.66 | 14.36 | 13.13 |
| 1.5dB | 10.35 | 14.75 | 14.45 | 12.19 |
| 2.0dB | 10.30 | 15.18 | 14.82 | 9.98 *低于S&W* |
| 2.5dB | 9.26 | 13.30 | 13.01 | 8.85 *低于S&W* |
| 3.0dB | 6.60 | 7.96 | 7.79 | 6.48 *低于S&W* |
| 3.5dB | 5.28 | 5.40 | 5.41 | 5.28 |
| 4.0dB | 5.16 | 5.17 | 5.17 | 5.17 |

### 结果解读

**延迟排序**: CA-CHARQ < C-HARQ < C-ARQ ≈ S&W (0.5-3.0dB)
- CA-CHARQ在0.5-3.0dB全域领先
- 0dB处CA-CHARQ与C-HARQ持平(72s): 低SNR时源端Chase重传主导，Grace仅Cpkt≥3启用→0dB(Cpkt=2)跳过Grace

**开销排序**: C-ARQ < C-HARQ, CA-CHARQ在2.0dB以上低于S&W
- 1.5dB起Grace启用→源端跳过重传→开销降低
- 2.0-3.0dB开销跌破S&W基准线，验证了"最少次重传"的设计目标

**CA-CHARQ领先的关键机制**:
1. Grace Period: 源端等待helper成功→跳过冗余重传(省100块/跳)
2. 自适应RV: 高置信时发30块(2.0s)代替C-HARQ的90块(6.0s)
3. 中点竞争: 选出双向信道均衡的helper
4. 零退避: 高分数helper立即响应

**CA-CHARQ在0dB持平的原因**:
- Cpkt=2→Grace不激活→回到无Grace模式
- 源端必须2次RV0(Chase主导延迟)，helper贡献不足以减少源端重传次数
- 这是低SNR下的物理限制: 信息积累需要多次Chase合并，协作只起确认作用

### 丢包率
所有协议在所有SNR下丢包率均为0 (MAX_HOP_RETRYS=5足够覆盖所需重传)

---

## 十、版本迭代历史

| 版本 | 关键改进 |
|---|---|
| v6-plus | 3个对照组建立 + CA-CHARQ基础框架 |
| v6-plus-v1 | 新增Grace Period (仅Cpkt≥3), helper自适应RV (仅校验) |
| v6-plus-v2 | 零退避优化 (score>0.9→t=0) |
| v6-plus-v3 | 中点竞争 + 缩短Grace_t + 零退避 (当前版本) |

--- 报告结束 ---
