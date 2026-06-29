#!/usr/bin/env python3
"""
CA-CHARQ Analytical Model v2.0
================================
Closed-form probability model for delay / overhead / energy-efficiency
of cooperative HARQ protocols in underwater acoustic sensor networks.

Framework: Goutham 2021 (HARQ-INCC) + Sklar 1988 (RS code formulas)
Approach : Independent analytical derivation, later validated by SimPy event simulation

Layer 1 — Underwater acoustic channel (Thorp + Rayleigh + QPSK SER)
Layer 2 — RS coding theory (Sklar decoded SER → PER → Cpkt quantization)
Layer 3 — Protocol state machine (S&W, C-ARQ, C-HARQ, CA-CHARQ)

Output   : Theoretical curves for delay, overhead, energy efficiency
Date     : 2026-06-17
Version  : 2.0.0
"""

import math
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

# ==========================================================================
# 0.  Global Parameters — aligned with Goutham 2021 & Ghosh 2013
# ==========================================================================
SOUND_SPEED     = 1500.0       # m/s
BIT_RATE        = 1200.0       # bps
TX_POWER_W      = 15.0         # W (source & relay)
FREQ_KHZ        = 20.0         # kHz carrier
HOP_DIST        = 600.0        # m per hop
NUM_HOPS        = 5
N_HELPERS       = 3        # helpers per hop (CA-CHARQ)
MAX_RETRIES     = 8            # max source retransmissions per hop

# Rician K = 0 → pure Rayleigh
RICIAN_K        = 0.0

# Reed–Solomon code :             Goutham uses RS(63, 57, t=3)
RS_BITS_PER_SYM = 6             # GF(2^6) → each RS symbol = 6 bits
RS_N_SYM        = 2**RS_BITS_PER_SYM - 1   # 63
RS_K_SYM        = 57            # data RS symbols
RS_T_BASE       = 3             # baseline error-correcting capability (t)
RS_PARITY_SYM   = RS_N_SYM - RS_K_SYM      # 6 parity RS symbols

# Total bits per full codeword
RS_TOTAL_BITS   = RS_N_SYM * RS_BITS_PER_SYM   # 63×6 = 378 bits

# Modulation : QPSK  (M = 4, m = log2 M = 2 bits/channel symbol)
MOD_BITS        = 2
N_CHANNEL_SYMS  = RS_TOTAL_BITS // MOD_BITS    # 378/2 = 189 QPSK symbols per codeword

# Chunk abstraction (for overhead counting)
# A "chunk" carries 16 bits and experiences independent fading — 
# but for the analytical model we work per-symbol.
# Mapping: 1 chunk = BITS_PER_CHUNK / MOD_BITS = 8 QPSK symbols.
BITS_PER_CHUNK  = 16
SYMS_PER_CHUNK  = BITS_PER_CHUNK // MOD_BITS    # 8
N_CHUNKS_SYS    = (RS_K_SYM * RS_BITS_PER_SYM) // BITS_PER_CHUNK # ≈ 21
# We round to a clean integer for protocol compatibility
N_CHUNKS_SYS    = 21
N_CHUNKS_TOTAL  = RS_TOTAL_BITS // BITS_PER_CHUNK  # 23-24

# RV slices in *chunk* space  (RV0 = all 23 chunks, parity split)
# Each chunk ~8 QPSK symbols, fading-independent
RV0_CHUNKS      = N_CHUNKS_SYS                     # 21 system chunks
N_PARITY_CHUNKS = N_CHUNKS_TOTAL - N_CHUNKS_SYS   # 2
# With only 2 parity chunks at 378 bits, granularity is poor → extend
# We use a larger mother-code view for IR:
MOTHER_N_SYM    = 255                              # GF(2^8) mother code
MOTHER_BITS     = MOTHER_N_SYM * RS_BITS_PER_SYM   # max codeword bits (not used)
# For practical IR amounts we define RV parity in *transmitted bit* multiples
# RV0 : 1st 63 RS symbols (system + 6 parity) — the Goutham base block
# RV1 : next 6 RS symbols
# RV2 : next 12 RS symbols
# RV3 : next 18 RS symbols
RV_EXTRA_RS_SYMS  = {1: 6, 2: 12, 3: 18}   # extra RS symbols per RV level
RV_EXTRA_BITS     = {k: v * RS_BITS_PER_SYM for k, v in RV_EXTRA_RS_SYMS.items()}


# ==========================================================================
# 1.  Underwater acoustic channel layer
# ==========================================================================
def thorp_alpha(f_khz):
    """Thorp absorption coefficient  α(f)  [dB/km]   (Goutham Eq.8 / Thorp 1967)"""
    f = f_khz
    return 0.11*f*f/(1+f*f) + 44*f*f/(4100+f*f) + 2.75e-4*f*f + 0.003


def transmission_loss(d_m, f_khz):
    """
    Combined spreading + absorption loss  TL  [linear multiplier]
    Cylindrical spreading in shallow water  (k = 1.0)  —  Goutham Eq.7
    """
    # Spread: (d / 1000)^1.5  for practical shallow-water (Ghosh 2013)
    spread = (d_m / 1000.0) ** 1.5
    alpha  = thorp_alpha(f_khz)
    absorb = 10.0 ** (alpha * d_m / 10000.0)   # α in dB/km → d/10000 for per-100m
    return spread * absorb + 1e-20


def snr_linear_tx_power(tx_power, dist_m, noise_var, f_khz=FREQ_KHZ):
    """Average linear SNR:  P_tx / (TL × N0)"""
    loss = transmission_loss(dist_m, f_khz)
    return tx_power / (loss * noise_var)


def noise_var_for_target_snr_db(target_snr_db, dist_m=HOP_DIST, tx_power=TX_POWER_W, f_khz=FREQ_KHZ):
    """Calibrate N0 so that a link at distance *dist_m* has *target_snr_db* avg SNR"""
    loss = transmission_loss(dist_m, f_khz)
    snr_lin = 10.0 ** (target_snr_db / 10.0)
    return tx_power / (loss * snr_lin)


def qpsk_ser_instant(gamma_lin):
    """
    Instantaneous QPSK symbol error rate.
    Exact : P_s = 1 − (1 − ½·erfc(√(γ/2)))²  (Goldsmith 2005, Sec 6.1.5)
    For large γ this approximates to erfc(√(γ/2)).
    """
    # Clip to avoid numerical issues
    g = max(gamma_lin, 1e-20)
    term = 0.5 * math.erfc(math.sqrt(g / 2.0))
    return 1.0 - (1.0 - term) ** 2


def average_qpsk_ser_rayleigh(gamma_avg_lin, n_integral=200):
    """
    Average QPSK SER over Rayleigh fading (K = 0).
    γ ∼ Exp(1/γ̄)  with  E[γ] = γ̄ = gamma_avg_lin.
    Numerically integrate  ∫ P_s(γ) · (1/γ̄)·e^{-γ/γ̄}  dγ.
    """
    if gamma_avg_lin < 1e-10:
        return 0.5       # complete failure
    gamma_max = 12.0 * gamma_avg_lin   # covers 99.994% of exponential mass
    dg = gamma_max / n_integral
    integral = 0.0
    for i in range(n_integral):
        gamma = (i + 0.5) * dg
        pdf = math.exp(-gamma / gamma_avg_lin) / gamma_avg_lin
        integral += qpsk_ser_instant(gamma) * pdf * dg
    return min(integral, 0.5)


def ser_post_chase(gamma_avg_lin, n_merge):
    """
    SER after n_merge Chase-combined transmissions.
    The combined SNR follows Gamma(n_merge, gamma_avg_lin), not Exp(n_merge * gamma_avg_lin).
    Gamma PDF: f(γ) = γ^{k-1} * exp(-γ/γ̄) / (γ̄^k * Γ(k))   with k = n_merge.
    This has much lighter-low-SNR tail than the naive Exp approximation.
    """
    if n_merge <= 1:
        return average_qpsk_ser_rayleigh(gamma_avg_lin)
    k = n_merge
    theta = gamma_avg_lin
    # Numerically integrate Gamma(k, θ) × QPSK SER
    # Mode of Gamma(k,θ) is at (k-1)θ; we cover [0, ~8×mean] for safety
    mean_val = k * theta
    gamma_max = max(8.0 * mean_val, gamma_avg_lin * 30)
    n_int = 300
    dg = gamma_max / n_int
    integral = 0.0
    log_k_fact = math.lgamma(k)  # log Γ(k) = log((k-1)!)
    for i in range(n_int):
        gamma = (i + 0.5) * dg
        # Gamma PDF: γ^{k-1} exp(-γ/θ) / (θ^k Γ(k))
        log_pdf = (k - 1) * math.log(max(gamma, 1e-30)) - gamma / theta - k * math.log(theta) - log_k_fact
        if log_pdf < -600:
            continue
        pdf = math.exp(log_pdf)
        integral += qpsk_ser_instant(gamma) * pdf * dg
    return min(integral, 0.5)


# ==========================================================================
# 2.  RS coding theory — Sklar 1988   (Goutham 2021  Eq.20–21)
# ==========================================================================

def _log_comb(n, k):
    """logarithm of binomial coefficient, stable for large n/k"""
    if k < 0 or k > n:
        return -float('inf')
    if k == 0 or k == n:
        return 0.0
    # Use symmetry:  C(n,k) = C(n, n-k)
    k = min(k, n - k)
    result = 0.0
    for i in range(1, k + 1):
        result += math.log(n - k + i) - math.log(i)
    return result


def rs_decoded_ser(ser_uncoded, n_sym=RS_N_SYM, t_error=RS_T_BASE):
    """
    R-S decoded symbol error rate after i.i.d. symbol errors (Sklar 1988, Eq. 7.27).

    P'_S = (1 / N) Σ_{r = t+1}^{N} r × C(N, r) × P_S^r × (1−P_S)^{N−r}

    Goutham 2021 Eq.20  |  N = 2^K − 1  |  t = (N − K_data) / 2
    For RS(63, 57, t=3):  N = 63, t = 3.

    Uses log-space summation to avoid underflow with very small P_S.
    """
    p = float(np.clip(ser_uncoded, 1e-30, 1.0 - 1e-30))
    if p < 1e-15:
        # P_S so small that the tail beyond t+1 is essentially 0
        return 0.0
    log_p = math.log(p)
    log_q = math.log(1.0 - p)
    total = 0.0
    for r in range(t_error + 1, n_sym + 1):
        log_term = _log_comb(n_sym, r) + r * log_p + (n_sym - r) * log_q
        if log_term < -700:  # exp(-700) ≈ 10⁻³⁰⁴ below double precision
            continue
        total += r * math.exp(log_term)
    return total / n_sym


# QPSK→RS SER mapping: 1 RS symbol = 6 bits = 3 QPSK symbols (for QPSK mod)
_SER_RS_FACTOR = RS_BITS_PER_SYM // MOD_BITS  # = 6//2 = 3

def _qpsk_to_rs_ser(ser_qpsk):
    """Probability an RS symbol (6 bits → 3 QPSK symbols) has ≥1 error."""
    return 1.0 - (1.0 - ser_qpsk) ** _SER_RS_FACTOR


def per_rs(ser_uncoded, n_sym=RS_N_SYM, n_info_sym=None, t_error=RS_T_BASE,
           mod_bits=MOD_BITS):
    """
    Packet error rate after RS decoding  (Goutham 2021 Eq.21).

    ser_uncoded : QPSK-level symbol error rate input.
    Internally converted to RS-symbol-level SER before Sklar formula.
    """
    ser_rs = _qpsk_to_rs_ser(ser_uncoded)
    p_s_prime = rs_decoded_ser(ser_rs, n_sym, t_error)
    # PER = 1 − (1 − P'_RS)^{N_RS_symbols}
    # Sklar: there are n_sym RS symbols, each decoded w/ error prob P'_RS
    per = 1.0 - (1.0 - p_s_prime) ** n_sym
    return float(np.clip(per, 1e-15, 1.0 - 1e-15))


def per_rs_gaussian(ser_vec, t_eff):
    """
    RS PER via Gaussian approximation to Poisson-Binomial. O(N), no MC.
    ser_vec[i] = RS-symbol error prob; t_eff = error-correcting capability.
    CLT: error count ≈ N(μ, σ²) for N≥30 (RS symbols 63-81 → well within regime).
    """
    mu = float(np.sum(ser_vec))
    var = float(np.sum(np.array(ser_vec) * (1.0 - np.array(ser_vec))))
    if var < 1e-15:
        return 0.0 if mu <= t_eff else 1.0
    z = (t_eff + 0.5 - mu) / math.sqrt(var)
    return float(1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))))


# ---------- Integration-based PER (fixes analytic↔SimPy mismatch) ----------

def _gamma_integrate(fn, shape_k, scale_theta, n_pts=300):
    """
    Integrate fn(γ) over Gamma(k, θ) distribution.
    fn: float→float, receives linear SNR γ.
    """
    if shape_k <= 0 or scale_theta < 1e-20:
        return fn(scale_theta * max(shape_k, 1))
    mean_val = shape_k * scale_theta
    gamma_max = max(10.0 * mean_val, scale_theta * 30, 5.0)
    dg = gamma_max / n_pts
    integral = 0.0
    log_gamma_k = math.lgamma(shape_k)
    for i in range(n_pts):
        gamma = (i + 0.5) * dg
        log_pdf = ((shape_k - 1) * math.log(max(gamma, 1e-30))
                   - gamma / scale_theta
                   - shape_k * math.log(scale_theta)
                   - log_gamma_k)
        if log_pdf < -600:
            continue
        integral += fn(gamma) * math.exp(log_pdf) * dg
    return min(integral, 1.0)


def per_no_fec_expected(k, gamma_lin, n_syms):
    """
    E[PER] for no-FEC protocol after k-round Chase.
    N independent symbols each with SNR ~ Gamma(k, γ̄).
    P(all correct) = E[1-SER(γ)]^N = Q_k^N  where Q_k = E[1-SER] over Gamma(k, γ̄).
    PER = 1 − Q_k^N.
    """
    def q_fn(g):
        return 1.0 - qpsk_ser_instant(g)  # prob one symbol is correct
    Q_k = _gamma_integrate(q_fn, k, gamma_lin) if k >= 1 else q_fn(gamma_lin)
    return 1.0 - Q_k ** n_syms


def per_rs_expected_one_path(k, gamma_lin, n_sym=RS_N_SYM, t_error=RS_T_BASE, n_mc=30):
    """
    E[PER] for RS FEC from a single-path after k-round Chase.
    Samples per-symbol SNRs, converts to RS-level SER, uses per_rs_vec.
    """
    per_acc = 0.0
    for _ in range(n_mc):
        gamma_vec = np.random.gamma(k, gamma_lin, n_sym)
        ser_vec = np.array([_qpsk_to_rs_ser(qpsk_ser_instant(float(g))) for g in gamma_vec])
        per_acc += per_rs_gaussian(ser_vec, t_error)
    return per_acc / n_mc


def per_rs_expected_two_path(k, gamma_sd_lin, gamma_hd_lin,
                               n_sys=RS_N_SYM, n_extra=12, t_eff=RS_T_BASE+6, n_mc=30):
    """
    E[PER] for 2-path RS FEC (source + helper) after k rounds.
    Per-symbol RS-level SNR → RS SER → per_rs_vec (Poisson-binomial).
    """
    per_acc = 0.0
    for _ in range(n_mc):
        sys_gamma = np.random.gamma(k, gamma_sd_lin, n_sys)
        par_gamma = np.random.gamma(k, gamma_hd_lin, n_extra)
        sys_ser = np.array([_qpsk_to_rs_ser(qpsk_ser_instant(float(g))) for g in sys_gamma])
        par_ser = np.array([_qpsk_to_rs_ser(qpsk_ser_instant(float(g))) for g in par_gamma])
        ser_vec = np.concatenate([sys_ser, par_ser])
        per_acc += per_rs_gaussian(ser_vec, t_eff)
    return per_acc / n_mc


# ---------- Cpkt quantisation ----------

def compute_cpkt(per_target):
    """
    Derive Cpkt ∈ {0,1,2,3} from targeted PER after first RV0 reception.
    The target PER here comes from the RS formula evaluated at the effective
    (possibly Chase-combined) SNR.

    Thresholds are mapped from BLER → SNR-margin  (as in CA-CHARQ summary §3.2),
    but here translated to PER space for RS code:
      Cpkt=3  : PER < 0.02   → destination almost decoded
      Cpkt=2  : PER < 0.20
      Cpkt=1  : PER < 0.70
      Cpkt=0  : otherwise
    """
    if per_target < 0.02:
        return 3
    elif per_target < 0.20:
        return 2
    elif per_target < 0.70:
        return 1
    else:
        return 0


def per_after_extra_parity(ser_sys, ser_par, n_extra_rs_sym, n_merge_sys=1):
    """
    Layered equivalent SNR for soft-combining.

    The soft buffer holds:
      System RS symbols  : Chase-combined from n_merge_sys source transmissions
                           → effective SER = ser_sys
      Parity RS symbols  : single helper transmission → effective SER = ser_par

    Total RS code :  N' = RS_N_SYM + n_extra_rs_sym
                     t' = RS_T_BASE + n_extra_rs_sym // 2

    The overall per-symbol SER is the weighted average:
      ser_avg = (RS_N_SYM * ser_sys + n_extra * ser_par) / N'

    Then compute R-S decoded SER and PER.
    """
    n_total_sym = RS_N_SYM + n_extra_rs_sym
    # Weighted SER
    ser_avg = (RS_N_SYM * ser_sys + n_extra_rs_sym * ser_par) / n_total_sym
    t_eff = RS_T_BASE + n_extra_rs_sym // 2
    return per_rs(ser_avg, n_sym=n_total_sym, t_error=t_eff)


# ==========================================================================
# 3.  Protocol state-machines — per-hop expected values
# ==========================================================================

def _gamma_sd_lin(snr_db):
    """Linear source→dest SNR given target avg per-hop SNR."""
    nv = noise_var_for_target_snr_db(snr_db)
    return snr_linear_tx_power(TX_POWER_W, HOP_DIST, nv)

def _gamma_hd_lin(snr_db):
    """Linear helper→dest SNR (midpoint, scaled power)."""
    nv = noise_var_for_target_snr_db(snr_db)
    return snr_linear_tx_power(
        TX_POWER_W * min(1.0, (0.55 * HOP_DIST / HOP_DIST) ** 1.5),
        0.55 * HOP_DIST, nv)

def _cross_round(q_fn, chunks_per_round, max_retries=MAX_RETRIES):
    """Generic cross-round accumulation.
    q_fn(k) returns PER after k rounds of accumulated transmissions.
    Returns (e_rounds, e_chunks, q_success), where q_success is per-hop."""
    q_succ = 0.0;  e_r = 0.0;  e_c = 0.0;  cum_f = 1.0
    for k in range(1, max_retries + 1):
        per_k = q_fn(k)
        p_ok   = cum_f * (1.0 - per_k)
        q_succ += p_ok;  e_r += k * p_ok;  e_c += k * chunks_per_round * p_ok
        cum_f  *= per_k
        if cum_f < 1e-15: break
    e_r += max_retries * cum_f;  e_c += max_retries * chunks_per_round * cum_f
    return e_r, e_c, q_succ

# ------------------------------------------------------------
#   S&W ARQ  (no FEC)
# ------------------------------------------------------------
def sw_arq_hop(snr_db, max_retries=MAX_RETRIES):
    """Stop-and-Wait without FEC.  Integration-based PER over Gamma distribution."""
    g = _gamma_sd_lin(snr_db);  n = N_CHANNEL_SYMS
    e_r, e_c, q = _cross_round(lambda k: per_no_fec_expected(k, g, n),
                               N_CHANNEL_SYMS, max_retries)
    t_round = HOP_DIST/SOUND_SPEED*2 + 1.0  # gto = rtt + 1.0
    return e_r * t_round, e_c, q

# ------------------------------------------------------------
#   C-ARQ  (no FEC, 1 helper sends RV0 per round)
# ------------------------------------------------------------
def carq_hop(snr_db, max_retries=MAX_RETRIES):
    """Cooperative ARQ without FEC, integration-based PER on both paths."""
    gs = _gamma_sd_lin(snr_db);  gh = _gamma_hd_lin(snr_db);  n = N_CHANNEL_SYMS
    def pk(k): return per_no_fec_expected(k, gs, n) * per_no_fec_expected(k, gh, n)
    e_r, e_c, q = _cross_round(pk, 2*N_CHANNEL_SYMS, max_retries)
    t_round = HOP_DIST/SOUND_SPEED*2 + 1.5  # gto + helper overhead
    return e_r * t_round, e_c, q

# ------------------------------------------------------------
#   C-HARQ  (RS FEC, fixed helper Pac-1+Pac-2 per round)
# ------------------------------------------------------------
def charq_hop(snr_db, max_retries=MAX_RETRIES):
    """C-HARQ: RS FEC, 12 extra RS parity, integration-based 2-path PER."""
    gs = _gamma_sd_lin(snr_db);  gh = _gamma_hd_lin(snr_db)
    NX = 12
    t_eff = RS_T_BASE + NX // 2
    def pk(k): return per_rs_expected_two_path(k, gs, gh, RS_N_SYM, NX, t_eff)
    cpk = N_CHANNEL_SYMS + NX
    e_r, e_c, q = _cross_round(pk, cpk, max_retries)
    t_round = HOP_DIST/SOUND_SPEED*2 + 1.5  # gto + helper TX overhead
    return e_r * t_round, e_c, q

# ------------------------------------------------------------
#   CA-CHARQ  (adaptive RS FEC, Grace Period, Cpkt-driven)
# ------------------------------------------------------------
def cacharq_hop(snr_db, max_retries=MAX_RETRIES):
    """CA-CHARQ with integration-based 2-path PER, Cpkt-driven RV selection."""
    gs = _gamma_sd_lin(snr_db);  gh = _gamma_hd_lin(snr_db)

    # Initial Cpkt (integration-based, single-round source PER)
    per1 = per_rs_expected_one_path(1, gs, n_sym=RS_N_SYM, t_error=RS_T_BASE)
    cpkt = compute_cpkt(per1)

    # RV selection
    RV_EXTRA = {1: 6, 2: 12, 3: 18}
    n_x = RV_EXTRA.get({0:3, 1:2, 2:1, 3:1}[cpkt], 6)
    t_eff = RS_T_BASE + n_x // 2

    def pk(k):
        return per_rs_expected_two_path(k, gs, gh, RS_N_SYM, n_x, t_eff)

    cpk = N_CHANNEL_SYMS + n_x
    e_r, e_c, q = _cross_round(pk, cpk, max_retries)

    t_p = HOP_DIST/SOUND_SPEED
    if cpkt == 3:
        t_round = t_p*2 + (n_x*RS_BITS_PER_SYM)/BIT_RATE + 0.5  # Grace: no source retx
    else:
        t_round = HOP_DIST/SOUND_SPEED*2 + 1.5  # gto + helper
    return e_r * t_round, e_c, q


# ==========================================================================
# 4.  End-to-end evaluation
# ==========================================================================

def e2e_metrics(snr_db, protocol, max_retries=MAX_RETRIES):
    """Return (delay_e2e, overhead, ee, q_success) for a given protocol at a given SNR."""
    q_hop = {PROTO_SW_ARQ: None, PROTO_CARQ: None, PROTO_CHARQ: None, PROTO_CA: None}

    if protocol == PROTO_SW_ARQ:
        d, c, q = sw_arq_hop(snr_db, max_retries)
    elif protocol == PROTO_CARQ:
        d, c, q = carq_hop(snr_db, max_retries)
    elif protocol == PROTO_CHARQ:
        d, c, q = charq_hop(snr_db, max_retries)
    elif protocol == PROTO_CA:
        d, c, q = cacharq_hop(snr_db, max_retries)
    else:
        raise ValueError(f"Unknown protocol: {protocol}")

    # E2E = NUM_HOPS × per-hop (assuming i.i.d. hops)
    # Delay: only count successfully delivered packets
    q_e2e = q ** NUM_HOPS
    q_hop_safe = max(q, 1e-12)
    delay_e2e  = (d / q_hop_safe) * NUM_HOPS
    chunks_e2e = c * NUM_HOPS
    q_e2e      = q ** NUM_HOPS

    overhead = chunks_e2e / (NUM_HOPS * RS_N_SYM * q_e2e) if q_e2e > 0 else float('nan')
    # Energy: each chunk = BITS_PER_CHUNK/8 QPSK symbols × TX time per symbol
    bits_useful = NUM_HOPS * RS_N_SYM * RS_BITS_PER_SYM * q_e2e  # successful info bits
    energy = chunks_e2e * TX_POWER_W / BIT_RATE
    ee = bits_useful / energy if energy > 0 else float('nan')

    return delay_e2e, overhead, ee, q_e2e


# ==========================================================================
# 5.  SNR scan + plotting
# ==========================================================================

PROTO_SW_ARQ = "S&W ARQ"
PROTO_CARQ   = "C-ARQ"
PROTO_CHARQ  = "C-HARQ"
PROTO_CA     = "CA-CHARQ"

COLORS = {PROTO_SW_ARQ: '#4C72B0', PROTO_CARQ: '#DD8452',
          PROTO_CHARQ: '#55A868', PROTO_CA: '#C44E52'}
MARKERS = {PROTO_SW_ARQ: 's', PROTO_CARQ: '^',
           PROTO_CHARQ: 'D', PROTO_CA: 'o'}


def run_analytic_sweep(snr_list, protocols, max_retries=MAX_RETRIES):
    """Scan SNR points for all protocols, return structured results."""
    results = {p: {'delay': [], 'overhead': [], 'ee': [], 'q_succ': []}
               for p in protocols}
    for proto in protocols:
        for snr in snr_list:
            d, ov, ee, q = e2e_metrics(snr, proto, max_retries)
            results[proto]['delay'].append(d)
            results[proto]['overhead'].append(ov)
            results[proto]['ee'].append(ee)
            results[proto]['q_succ'].append(q)
    return results


def plot_results(snr_list, results, suffix="alpha", out_dir="output"):
    """Generate delay, overhead, EE dual-panel and success curves."""
    protocols = list(results.keys())

    # ---- Delay + Overhead ----
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    for proto in protocols:
        y = np.array(results[proto]['delay'])
        mask = ~np.isnan(y)
        if mask.any():
            ax1.plot(np.array(snr_list)[mask], y[mask],
                     MARKERS[proto] + '-', color=COLORS[proto],
                     lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto],
                     markeredgewidth=0.8)
    ax1.set_xlabel("Average Per-Hop SNR (dB)")
    ax1.set_ylabel("End-to-End Delay (s)")
    ax1.set_title("E2E Delay — Analytical Model")
    ax1.grid(True, ls='-', alpha=0.15, color='gray')
    ax1.legend()

    for proto in protocols:
        y = np.array(results[proto]['overhead'])
        mask = ~np.isnan(y) & (y < 100)  # filter blow-ups
        if mask.any():
            ax2.plot(np.array(snr_list)[mask], y[mask],
                     MARKERS[proto] + '-', color=COLORS[proto],
                     lw=1.8, ms=7, label=proto,
                     markerfacecolor='white', markeredgecolor=COLORS[proto],
                     markeredgewidth=0.8)
    ax2.set_xlabel("Average Per-Hop SNR (dB)")
    ax2.set_ylabel("Transmission Overhead (x Useful)")
    ax2.set_title("Overhead — Analytical Model")
    ax2.grid(True, ls='-', alpha=0.15, color='gray')
    ax2.legend()
    plt.tight_layout()
    fname1 = f"{out_dir}/analytic_{suffix}_Delay_Overhead.png"
    plt.savefig(fname1, dpi=200, bbox_inches='tight')
    print(f"[OK] {fname1}")
    plt.close('all')

    # ---- EE ----
    fig2, ax_ee = plt.subplots(1, 1, figsize=(7, 5))
    for proto in protocols:
        y = np.array(results[proto]['ee'])
        mask = ~np.isnan(y)
        if mask.any():
            ax_ee.plot(np.array(snr_list)[mask], y[mask],
                       MARKERS[proto] + '-', color=COLORS[proto],
                       lw=1.8, ms=7, label=proto,
                       markerfacecolor='white', markeredgecolor=COLORS[proto],
                       markeredgewidth=0.8)
    ax_ee.set_xlabel("Average Per-Hop SNR (dB)")
    ax_ee.set_ylabel("Energy Efficiency (bits/Joule)")
    ax_ee.set_title("Energy Efficiency — Analytical Model")
    ax_ee.grid(True, ls='-', alpha=0.15, color='gray')
    ax_ee.legend()
    fname2 = f"{out_dir}/analytic_{suffix}_EE.png"
    plt.savefig(fname2, dpi=200, bbox_inches='tight')
    print(f"[OK] {fname2}")
    plt.close('all')

    # ---- Success probability ----
    fig3, ax_q = plt.subplots(1, 1, figsize=(7, 5))
    for proto in protocols:
        y = np.array(results[proto]['q_succ'])
        mask = ~np.isnan(y)
        if mask.any():
            ax_q.plot(np.array(snr_list)[mask], y[mask],
                      MARKERS[proto] + '-', color=COLORS[proto],
                      lw=1.8, ms=7, label=proto,
                      markerfacecolor='white', markeredgecolor=COLORS[proto],
                      markeredgewidth=0.8)
    ax_q.set_xlabel("Average Per-Hop SNR (dB)")
    ax_q.set_ylabel("End-to-End Success Probability")
    ax_q.set_title("E2E Reliability — Analytical Model")
    ax_q.grid(True, ls='-', alpha=0.15, color='gray')
    ax_q.legend()
    fname3 = f"{out_dir}/analytic_{suffix}_Success.png"
    plt.savefig(fname3, dpi=200, bbox_inches='tight')
    print(f"[OK] {fname3}")
    plt.close('all')


# ==========================================================================
# 6.  Main — scan SNR, report
# ==========================================================================
if __name__ == "__main__":
    # Initial scan: 0–24 dB in 0.5 dB steps (full Cpkt transition range)
    SNR_WIDE = [x * 0.5 for x in range(0, 49)]  # 0.0 .. 24.0
    PROTOCOLS = [PROTO_SW_ARQ, PROTO_CARQ, PROTO_CHARQ, PROTO_CA]

    print("=" * 65)
    print(" CA-CHARQ Analytical Model v2.0")
    print(f" PHY: RS({RS_N_SYM},{RS_K_SYM},t={RS_T_BASE}) + Sklar 1988")
    print(f" Chan: Rayleigh (K={RICIAN_K}), Thorp α≈{thorp_alpha(FREQ_KHZ):.1f}dB/km")
    print(f" Max retries/hop: {MAX_RETRIES}, Hops: {NUM_HOPS}")
    print(f" SNR scan: {SNR_WIDE[0]:.1f}–{SNR_WIDE[-1]:.1f} dB, {len(SNR_WIDE)} pts")
    print("=" * 65)

    # ======== Initial wide scan ========
    print("\n>>> Full-range scan ...")
    r_wide = run_analytic_sweep(SNR_WIDE, PROTOCOLS)
    plot_results(SNR_WIDE, r_wide, suffix="v3_full", out_dir="output/pro-v3")

    # Print summary table
    print(f"\n{'SNR':>6s} |", end="")
    for p in PROTOCOLS:
        print(f" {p:>11s} Q |", end="")
    print()
    for i, s in enumerate(SNR_WIDE):
        if i % 2 == 0:  # every 1 dB
            print(f"{s:+5.1f}dB |", end="")
            for p in PROTOCOLS:
                q = r_wide[p]['q_succ'][i]
                if np.isnan(q):
                    print(f" {'n/a':>11s} |", end="")
                else:
                    qpct = q * 100
                    bar = "#" * int(qpct / 10) + ("." if qpct < 100 else "")
                    print(f" {qpct:3.0f}% {bar:<6s}|", end="")
            print()

    # ======== Find "3-zone" display window ========
    # Zone 1: S&W fails (< 80% E2E) but CA-CHARQ succeeds (> 80%)
    # Zone 2: All succeed (> 95%), CA-CHARQ leads
    # Zone 3: All converge (~100%)
    print("\n>>> Finding 3-zone SNR window ...")
    zone1_start, zone1_end = None, None
    zone2_start, zone2_end = None, None
    for i, s in enumerate(SNR_WIDE):
        q_sw = r_wide[PROTO_SW_ARQ]['q_succ'][i]
        q_ca = r_wide[PROTO_CA]['q_succ'][i]
        if not np.isnan(q_sw) and not np.isnan(q_ca):
            if zone1_start is None and q_sw < 0.8 and q_ca > 0.8:
                zone1_start = s
            if zone1_start is not None and zone1_end is None and q_sw > 0.95:
                zone1_end = s
                zone2_start = s
            if zone2_start is not None and zone2_end is None and q_ca > 0.999:
                zone2_end = s
                break

    print(f"  Zone 1 (reliability gap):    {zone1_start or '?'} – {zone1_end or '?'} dB")
    print(f"  Zone 2 (all recover, compete): {zone2_start or '?'} – {zone2_end or '?'} dB")
    print(f"  Zone 3 (converged):           >{zone2_end or '?'} dB")
    print("Done.")

    plt.rcParams.update({'font.size': 11})
