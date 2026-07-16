#!/usr/bin/env python3
"""
CA-CHARQ v10: bit-level RS(63,57) simulation for a concurrent UASN.

The four protocols share the same topology, traffic, payloads, channel model,
helper population and random seeds.  CA-CHARQ is not given a different PHY;
its only protocol-specific information is the destination confidence feedback,
distributed helper contention and adaptive redundancy scheduling.

Key corrections relative to v9
--------------------------------
1. A real systematic RS(63,57) codec over GF(2^6) is used.  RV0 carries the
   57 information symbols and two parity symbols; RV1 and RV2 carry two new
   parity symbols each.  A full-code failure is followed by Chase combining.
2. Every protocol state uses TxKey(chain_id, pid, hop_src, hop_dst).  Helpers
   can therefore assist several chains without PID aliasing.
3. Helper jobs are cancellable and a per-helper scheduler serialises concurrent
   jobs.  ACK processing removes queued jobs for the completed TxKey.
4. Durations and energy use transmitted bits / 1200 bit/s.  Useful payload is
   57 * 6 = 342 information bits, never the 378-bit mother-code length.

The default command runs the complete 4 protocol x 7 SNR x 5 seed experiment.
Use --quick for a short smoke run and --self-test for codec/state tests.
"""

from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
import os
import statistics
import time
import types
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

try:  # Prefer the standard package when present.
    import simpy  # type: ignore
except ImportError:  # Self-contained fallback used by the bundled document runtime.
    class _MiniEvent:
        def __init__(self, env):
            self.env = env
            self.triggered = False
            self.processed = False
            self.ok = True
            self.value = None
            self.callbacks = []

        def succeed(self, value=None):
            if self.triggered:
                raise RuntimeError("event already triggered")
            self.triggered = True
            self.value = value
            self.env._schedule(0.0, self._process)
            return self

        def fail(self, exception):
            if self.triggered:
                raise RuntimeError("event already triggered")
            self.triggered = True
            self.ok = False
            self.value = exception
            self.env._schedule(0.0, self._process)
            return self

        def _process(self):
            if self.processed:
                return
            self.processed = True
            callbacks, self.callbacks = self.callbacks, []
            for callback in callbacks:
                callback(self)

        def add_callback(self, callback):
            if self.processed:
                self.env._schedule(0.0, lambda: callback(self))
            else:
                self.callbacks.append(callback)

        def __or__(self, other):
            return _MiniCondition(self.env, [self, other], all_events=False)


    class _MiniTimeout(_MiniEvent):
        def __init__(self, env, delay, value=None):
            super().__init__(env)
            if delay < 0:
                raise ValueError("negative timeout")
            env._schedule(float(delay), lambda: self.succeed(value))


    class _MiniCondition(_MiniEvent):
        def __init__(self, env, events, all_events):
            super().__init__(env)
            self.events = list(events)
            self.all_events = all_events
            self.results = {}
            if not self.events:
                self.succeed({})
            for event in self.events:
                event.add_callback(self._check)

        def _check(self, event):
            if self.triggered:
                return
            if not event.ok:
                self.fail(event.value)
                return
            self.results[event] = event.value
            if not self.all_events or len(self.results) == len(self.events):
                self.succeed(dict(self.results))


    class _MiniProcess(_MiniEvent):
        def __init__(self, env, generator):
            super().__init__(env)
            self.generator = generator
            env._schedule(0.0, lambda: self._resume(None))

        def _resume(self, event):
            if self.triggered:
                return
            try:
                if event is None:
                    yielded = next(self.generator)
                elif event.ok:
                    yielded = self.generator.send(event.value)
                else:
                    yielded = self.generator.throw(event.value)
            except StopIteration as stop:
                self.succeed(stop.value)
                return
            except BaseException as exc:
                self.fail(exc)
                return
            if not isinstance(yielded, _MiniEvent):
                self.fail(TypeError(f"process yielded non-event {yielded!r}"))
                return
            yielded.add_callback(self._resume)


    class _MiniRequest(_MiniEvent):
        def __init__(self, resource):
            super().__init__(resource.env)
            self.resource = resource
            self.granted = False
            resource._request(self)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.resource.release(self)
            return False


    class _MiniResource:
        def __init__(self, env, capacity=1):
            self.env = env
            self.capacity = int(capacity)
            self.users = []
            self.queue = []

        def request(self):
            return _MiniRequest(self)

        def _request(self, request):
            if len(self.users) < self.capacity:
                self.users.append(request)
                request.granted = True
                request.succeed(request)
            else:
                self.queue.append(request)

        def release(self, request):
            if request in self.users:
                self.users.remove(request)
            elif request in self.queue:
                self.queue.remove(request)
            while self.queue and len(self.users) < self.capacity:
                next_request = self.queue.pop(0)
                self.users.append(next_request)
                next_request.granted = True
                next_request.succeed(next_request)


    class _MiniEnvironment:
        def __init__(self):
            self.now = 0.0
            self._queue = []
            self._sequence = 0

        def _schedule(self, delay, callback):
            self._sequence += 1
            heapq.heappush(self._queue, (self.now + float(delay), self._sequence, callback))

        def event(self):
            return _MiniEvent(self)

        def timeout(self, delay, value=None):
            return _MiniTimeout(self, delay, value)

        def process(self, generator):
            if isinstance(generator, _MiniProcess):
                return generator
            return _MiniProcess(self, generator)

        def run(self, until=None):
            limit = float("inf") if until is None else float(until)
            while self._queue and self._queue[0][0] <= limit:
                when, _, callback = heapq.heappop(self._queue)
                self.now = when
                callback()
            if until is not None:
                self.now = limit


    simpy = types.SimpleNamespace(
        Environment=_MiniEnvironment,
        Resource=_MiniResource,
        Event=_MiniEvent,
        events=types.SimpleNamespace(
            Event=_MiniEvent,
            AllOf=lambda env, events: _MiniCondition(env, events, all_events=True),
        ),
    )


# ---------------------------------------------------------------------------
# 0. Experiment constants
# ---------------------------------------------------------------------------
PROTO_SW_ARQ = "S&W ARQ"
PROTO_CARQ = "C-ARQ"
PROTO_CHARQ = "C-HARQ"
PROTO_CA = "CA-CHARQ"
PROTOCOLS = (PROTO_SW_ARQ, PROTO_CARQ, PROTO_CHARQ, PROTO_CA)

SOUND_SPEED = 1500.0
BIT_RATE = 1200.0
TX_POWER_W = 15.0
FREQ_KHZ = 20.0
HOP_DIST = 600.0
NUM_HOPS = 5
NUM_CHAINS = 3
N_HELPERS_TOTAL = 15
HELPERS_PER_LINK = 3
MAX_RETRIES = 8
INITIAL_ENERGY_J = 10000.0
CONTROL_BITS = 12
TRAFFIC_MEAN_S = 30.0

RS_N = 63
RS_K = 57
RS_NSYM = RS_N - RS_K
RS_BITS_PER_SYMBOL = 6
INFO_BITS = RS_K * RS_BITS_PER_SYMBOL
MOD_BITS = 2
RV_POSITIONS = {
    0: tuple(range(0, 59)),       # 57 data + parity p0,p1
    1: tuple(range(59, 61)),      # parity p2,p3
    2: tuple(range(61, 63)),      # parity p4,p5
}
CHARQ_IR_POSITIONS = RV_POSITIONS[1] + RV_POSITIONS[2]
FULL_CODE_POSITIONS = tuple(range(RS_N))
UNCODED_POSITIONS = tuple(range(RS_K))

CHAIN_Y_OFFSETS = (-600.0, 0.0, 600.0)
SINK_ID = 9999
SINK_POS = (3000.0, 0.0)
T_MAX_WINDOW = 0.65
T_BACKOFF_JITTER = 0.035
T_PROTECTION_GAP = 0.02


# ---------------------------------------------------------------------------
# 1. Pure-Python GF(64) and systematic RS(63,57)
# ---------------------------------------------------------------------------
class ReedSolomonError(Exception):
    """Raised when the received RS word is outside the correction bound."""


class GF64:
    """GF(2^6), primitive polynomial x^6 + x + 1 (0x43)."""

    prim = 0x43
    size = 64
    order = 63
    exp = [0] * (2 * order)
    log = [0] * size

    @classmethod
    def initialise(cls) -> None:
        x = 1
        for i in range(cls.order):
            cls.exp[i] = x
            cls.log[x] = i
            x <<= 1
            if x & cls.size:
                x ^= cls.prim
            x &= cls.size - 1
        for i in range(cls.order, 2 * cls.order):
            cls.exp[i] = cls.exp[i - cls.order]
        if x != 1 or len(set(cls.exp[: cls.order])) != cls.order:
            raise RuntimeError("0x43 is not primitive for GF(64)")

    @classmethod
    def add(cls, x: int, y: int) -> int:
        return x ^ y

    @classmethod
    def mul(cls, x: int, y: int) -> int:
        if x == 0 or y == 0:
            return 0
        return cls.exp[(cls.log[x] + cls.log[y]) % cls.order]

    @classmethod
    def div(cls, x: int, y: int) -> int:
        if y == 0:
            raise ZeroDivisionError("GF division by zero")
        if x == 0:
            return 0
        return cls.exp[(cls.log[x] - cls.log[y]) % cls.order]

    @classmethod
    def inverse(cls, x: int) -> int:
        if x == 0:
            raise ZeroDivisionError("GF inverse of zero")
        return cls.exp[cls.order - cls.log[x]]

    @classmethod
    def pow(cls, x: int, power: int) -> int:
        if power == 0:
            return 1
        if x == 0:
            return 0
        return cls.exp[(cls.log[x] * power) % cls.order]


GF64.initialise()


def gf_poly_scale(poly: Sequence[int], scalar: int) -> List[int]:
    return [GF64.mul(x, scalar) for x in poly]


def gf_poly_add(p: Sequence[int], q: Sequence[int]) -> List[int]:
    out = [0] * max(len(p), len(q))
    for i, value in enumerate(p):
        out[i + len(out) - len(p)] ^= value
    for i, value in enumerate(q):
        out[i + len(out) - len(q)] ^= value
    return out


def gf_poly_mul(p: Sequence[int], q: Sequence[int]) -> List[int]:
    out = [0] * (len(p) + len(q) - 1)
    for j, qj in enumerate(q):
        if qj:
            for i, pi in enumerate(p):
                if pi:
                    out[i + j] ^= GF64.mul(pi, qj)
    return out


def gf_poly_eval(poly: Sequence[int], x: int) -> int:
    y = poly[0]
    for value in poly[1:]:
        y = GF64.mul(y, x) ^ value
    return y


class RSCodec63_57:
    """Small, dependency-free systematic RS codec used by the simulator."""

    def __init__(self) -> None:
        generator = [1]
        for i in range(RS_NSYM):
            generator = gf_poly_mul(generator, [1, GF64.pow(2, i)])
        self.generator = generator

    def encode(self, message: Sequence[int]) -> Tuple[int, ...]:
        if len(message) != RS_K or any((x < 0 or x >= 64) for x in message):
            raise ValueError("RS(63,57) requires 57 GF(64) symbols")
        work = list(message) + [0] * RS_NSYM
        for i in range(RS_K):
            coef = work[i]
            if coef:
                for j in range(1, len(self.generator)):
                    work[i + j] ^= GF64.mul(self.generator[j], coef)
        return tuple(message) + tuple(work[RS_K:])

    @staticmethod
    def syndromes(codeword: Sequence[int]) -> List[int]:
        return [0] + [gf_poly_eval(codeword, GF64.pow(2, i)) for i in range(RS_NSYM)]

    @staticmethod
    def _forney_syndromes(synd: Sequence[int], erasures: Sequence[int], n: int) -> List[int]:
        fsynd = list(synd[1:])
        for pos in erasures:
            x = GF64.pow(2, n - 1 - pos)
            for j in range(len(fsynd) - 1):
                fsynd[j] = GF64.mul(fsynd[j], x) ^ fsynd[j + 1]
            fsynd.pop()
        return fsynd

    @staticmethod
    def _find_error_locator(synd: Sequence[int], nsym: int) -> List[int]:
        err_loc = [1]
        old_loc = [1]
        for i in range(nsym):
            delta = synd[i]
            for j in range(1, len(err_loc)):
                if i - j >= 0:
                    delta ^= GF64.mul(err_loc[-(j + 1)], synd[i - j])
            old_loc.append(0)
            if delta:
                if len(old_loc) > len(err_loc):
                    new_loc = gf_poly_scale(old_loc, delta)
                    old_loc = gf_poly_scale(err_loc, GF64.inverse(delta))
                    err_loc = new_loc
                err_loc = gf_poly_add(err_loc, gf_poly_scale(old_loc, delta))
        while len(err_loc) > 1 and err_loc[0] == 0:
            del err_loc[0]
        return err_loc

    @staticmethod
    def _find_error_positions(err_loc: Sequence[int], n: int) -> List[int]:
        count = len(err_loc) - 1
        positions = []
        # The BM polynomial orientation is reversed for Chien search.
        search_poly = list(reversed(err_loc))
        for i in range(n):
            if gf_poly_eval(search_poly, GF64.pow(2, i)) == 0:
                positions.append(n - 1 - i)
        if len(positions) != count:
            raise ReedSolomonError("could not locate all symbol errors")
        return positions

    @staticmethod
    def _solve_magnitudes(synd: Sequence[int], positions: Sequence[int], n: int) -> List[int]:
        m = len(positions)
        if m == 0:
            return []
        a = []
        for row in range(m):
            a.append([
                GF64.pow(2, row * (n - 1 - pos)) for pos in positions
            ] + [synd[row + 1]])

        # Gauss-Jordan elimination over GF(64).
        for col in range(m):
            pivot = next((r for r in range(col, m) if a[r][col] != 0), None)
            if pivot is None:
                raise ReedSolomonError("singular error-magnitude system")
            if pivot != col:
                a[col], a[pivot] = a[pivot], a[col]
            inv = GF64.inverse(a[col][col])
            a[col] = [GF64.mul(v, inv) for v in a[col]]
            for row in range(m):
                if row == col or a[row][col] == 0:
                    continue
                factor = a[row][col]
                a[row] = [
                    a[row][j] ^ GF64.mul(factor, a[col][j])
                    for j in range(m + 1)
                ]
        return [a[i][m] for i in range(m)]

    def decode(self, received: Sequence[int], erasures: Iterable[int] = ()) -> Tuple[int, ...]:
        if len(received) != RS_N:
            raise ValueError("RS(63,57) decoder requires 63 symbols")
        erased = sorted(set(int(p) for p in erasures))
        if any(p < 0 or p >= RS_N for p in erased) or len(erased) > RS_NSYM:
            raise ReedSolomonError("invalid or excessive erasures")
        work = list(received)
        for p in erased:
            work[p] = 0
        synd = self.syndromes(work)
        if max(synd) == 0 and not erased:
            return tuple(work[:RS_K])

        fsynd = self._forney_syndromes(synd, erased, RS_N)
        unknown_capacity = (RS_NSYM - len(erased)) // 2
        error_positions: List[int] = []
        if fsynd and max(fsynd) != 0 and unknown_capacity > 0:
            locator = self._find_error_locator(fsynd, len(fsynd))
            error_positions = self._find_error_positions(locator, RS_N)
            error_positions = [p for p in error_positions if p not in erased]
        all_positions = erased + error_positions
        if 2 * len(error_positions) + len(erased) > RS_NSYM:
            raise ReedSolomonError("RS correction bound exceeded")
        if not all_positions and max(synd) != 0:
            raise ReedSolomonError("non-zero syndrome without a locator")
        magnitudes = self._solve_magnitudes(synd, all_positions, RS_N)
        for pos, mag in zip(all_positions, magnitudes):
            work[pos] ^= mag
        if max(self.syndromes(work)) != 0:
            raise ReedSolomonError("uncorrectable RS word")
        return tuple(work[:RS_K])


CODEC = RSCodec63_57()


# ---------------------------------------------------------------------------
# 2. Channel and bit-level soft combining
# ---------------------------------------------------------------------------
def thorp_alpha(f_khz: float) -> float:
    f2 = f_khz * f_khz
    return 0.11 * f2 / (1.0 + f2) + 44.0 * f2 / (4100.0 + f2) + 2.75e-4 * f2 + 0.003


def transmission_loss(distance_m: float, f_khz: float = FREQ_KHZ) -> float:
    d = max(float(distance_m), 1.0)
    spread = (d / 1000.0) ** 1.5
    absorb = 10.0 ** (thorp_alpha(f_khz) * d / 10000.0)
    return spread * absorb + 1e-20


def noise_for_target_snr(snr_db: float) -> float:
    target = 10.0 ** (snr_db / 10.0)
    return TX_POWER_W / (transmission_loss(HOP_DIST) * target)


def stable_rng(seed: int, *values: int) -> np.random.Generator:
    material = [int(seed) & 0xFFFFFFFF]
    material.extend(int(v) & 0xFFFFFFFF for v in values)
    return np.random.default_rng(np.random.SeedSequence(material))


def symbol_bits(symbols: Sequence[int]) -> np.ndarray:
    values = np.asarray(symbols, dtype=np.uint8)
    shifts = np.arange(RS_BITS_PER_SYMBOL - 1, -1, -1, dtype=np.uint8)
    return ((values[:, None] >> shifts[None, :]) & 1).astype(np.int8)


class SoftBuffer:
    """Per-TxKey soft decisions.  No state can leak across chains or hops."""

    __slots__ = ("metric", "gamma", "seen")

    def __init__(self) -> None:
        self.metric = np.zeros((RS_N, RS_BITS_PER_SYMBOL), dtype=np.float64)
        self.gamma = np.zeros((RS_N, RS_BITS_PER_SYMBOL), dtype=np.float64)
        self.seen = np.zeros(RS_N, dtype=bool)

    def add(self, codeword: Sequence[int], positions: Sequence[int], avg_snr: float,
            rng: np.random.Generator) -> None:
        if not positions:
            return
        pos = np.asarray(positions, dtype=np.int16)
        bits = symbol_bits([codeword[int(p)] for p in pos])
        # One Rayleigh fade per QPSK symbol; its two bits share instantaneous SNR.
        qpsk_gamma = rng.exponential(max(avg_snr, 1e-12), size=(len(pos), 3))
        gamma = np.repeat(qpsk_gamma, 2, axis=1)
        signs = 1.0 - 2.0 * bits
        observation = gamma * signs + np.sqrt(gamma) * rng.normal(size=gamma.shape)
        self.metric[pos, :] += observation
        self.gamma[pos, :] += gamma
        self.seen[pos] = True

    def hard_symbols(self) -> Tuple[int, ...]:
        bits = (self.metric < 0.0).astype(np.uint8)
        weights = (1 << np.arange(5, -1, -1, dtype=np.uint8))[None, :]
        return tuple(int(v) for v in np.sum(bits * weights, axis=1))

    def decode_uncoded(self, expected_message: Sequence[int]) -> bool:
        if not bool(np.all(self.seen[:RS_K])):
            return False
        return self.hard_symbols()[:RS_K] == tuple(expected_message)

    def decode_rs(self, expected_message: Sequence[int]) -> bool:
        erasures = np.flatnonzero(~self.seen).tolist()
        if len(erasures) > RS_NSYM:
            return False
        try:
            decoded = CODEC.decode(self.hard_symbols(), erasures)
        except ReedSolomonError:
            return False
        # Perfect CRC is modelled by comparing to the generated payload.
        return decoded == tuple(expected_message)

    def confidence(self) -> int:
        """Four-level decoder confidence derived only from received soft metrics."""
        erasures = int(np.sum(~self.seen))
        if erasures > RS_NSYM:
            return 0
        seen_gamma = self.gamma[self.seen]
        if seen_gamma.size == 0:
            return 0
        # Q(sqrt(gamma)) matches the decision statistic used in add().
        q = np.vectorize(lambda x: 0.5 * math.erfc(math.sqrt(max(x, 0.0) / 2.0)))(seen_gamma)
        p_sym = 1.0 - np.prod(1.0 - q, axis=1)
        eta = float(np.sum(p_sym))
        correction_budget = max(0.0, (RS_NSYM - erasures) / 2.0)
        ratio = eta / max(correction_budget, 0.25)
        if ratio <= 0.30:
            return 3
        if ratio <= 0.75:
            return 2
        if ratio <= 1.35:
            return 1
        return 0


@dataclass(frozen=True, order=True)
class TxKey:
    chain_id: int
    pid: int
    hop_src: int
    hop_dst: int


@dataclass
class Stats:
    tx_bits: int = 0
    control_bits: int = 0
    energy_j: float = 0.0
    successes: int = 0
    drops: int = 0
    collisions: int = 0
    generated: int = 0
    delays: List[float] = field(default_factory=list)
    helper_services: int = 0
    helper_cross_chain_services: int = 0
    cancelled_helper_jobs: int = 0

    def summary(self) -> Dict[str, float]:
        useful = self.successes * INFO_BITS
        return {
            "delay": float(np.mean(self.delays)) if self.delays else float("nan"),
            "pdr": self.successes / self.generated if self.generated else float("nan"),
            "overhead": self.tx_bits / useful if useful else float("nan"),
            "energy_efficiency": useful / self.energy_j if self.energy_j else float("nan"),
            "successes": float(self.successes),
            "drops": float(self.drops),
            "generated": float(self.generated),
            "collisions": float(self.collisions),
            "helper_services": float(self.helper_services),
            "helper_cross_chain_services": float(self.helper_cross_chain_services),
            "cancelled_helper_jobs": float(self.cancelled_helper_jobs),
        }


@dataclass
class Node:
    env: simpy.Environment
    node_id: int
    x: float
    y: float
    role: str
    tx_power: float = TX_POWER_W
    energy_j: float = INITIAL_ENERGY_J
    rx_busy_until: float = 0.0

    def __post_init__(self) -> None:
        self.radio = simpy.Resource(self.env, capacity=1)


@dataclass
class Reception:
    receiver: Node
    buffer: SoftBuffer
    purpose: str


class AcousticChannel:
    def __init__(self, env: simpy.Environment, snr_db: float, seed: int, stats: Stats):
        self.env = env
        self.noise = noise_for_target_snr(snr_db)
        self.seed = seed
        self.stats = stats

    def avg_snr(self, sender: Node, receiver: Node) -> float:
        d = math.hypot(sender.x - receiver.x, sender.y - receiver.y)
        return sender.tx_power / (transmission_loss(d) * self.noise)

    def broadcast(self, sender: Node, receptions: Sequence[Reception], codeword: Sequence[int],
                  positions: Sequence[int], key: TxKey, tx_index: int):
        """One physical transmission with independent fades at every receiver."""
        bits = len(positions) * RS_BITS_PER_SYMBOL
        duration = bits / BIT_RATE
        with sender.radio.request() as request:
            yield request
            self.stats.tx_bits += bits
            energy = sender.tx_power * duration
            sender.energy_j -= energy
            self.stats.energy_j += energy
            yield self.env.timeout(duration)
            events = []
            for item in receptions:
                events.append(self.env.process(self._deliver(
                    sender, item, codeword, positions, key, tx_index, duration
                )))
            if events:
                yield simpy.events.AllOf(self.env, events)

    def _deliver(self, sender: Node, reception: Reception, codeword: Sequence[int],
                 positions: Sequence[int], key: TxKey, tx_index: int, duration: float):
        receiver = reception.receiver
        distance = math.hypot(sender.x - receiver.x, sender.y - receiver.y)
        yield self.env.timeout(distance / SOUND_SPEED)
        if self.env.now < receiver.rx_busy_until:
            self.stats.collisions += 1
            return False
        receiver.rx_busy_until = self.env.now + duration
        avg = self.avg_snr(sender, receiver)
        purpose_code = 1 if reception.purpose == "dest" else 2
        rng = stable_rng(
            self.seed, key.chain_id, key.pid, key.hop_src, key.hop_dst,
            tx_index, sender.node_id, receiver.node_id, purpose_code,
        )
        reception.buffer.add(codeword, positions, avg, rng)
        return True

    def control(self, sender: Node, receiver: Node, key: TxKey):
        duration = CONTROL_BITS / BIT_RATE
        with sender.radio.request() as request:
            yield request
            self.stats.tx_bits += CONTROL_BITS
            self.stats.control_bits += CONTROL_BITS
            energy = sender.tx_power * duration
            sender.energy_j -= energy
            self.stats.energy_j += energy
            yield self.env.timeout(duration)
            yield self.env.timeout(math.hypot(sender.x - receiver.x, sender.y - receiver.y) / SOUND_SPEED)


# ---------------------------------------------------------------------------
# 3. Cancellable per-helper scheduler
# ---------------------------------------------------------------------------
@dataclass
class HelperJob:
    key: TxKey
    chain_id: int
    ready_time: float
    priority: float
    sequence: int
    action: Callable[[], simpy.events.Event]
    done: simpy.Event
    cancelled: bool = False


class HelperScheduler:
    """Serialises one physical helper without merging unrelated packet IDs."""

    def __init__(self, env: simpy.Environment, helper_id: int, stats: Stats):
        self.env = env
        self.helper_id = helper_id
        self.stats = stats
        self.pending: List[HelperJob] = []
        self.active: Optional[HelperJob] = None
        self.sequence = 0
        self.wake = env.event()
        self.last_chain_id: Optional[int] = None
        self.env.process(self._worker())

    def submit(self, key: TxKey, ready_time: float, priority: float,
               action: Callable[[], simpy.events.Event]) -> HelperJob:
        self.sequence += 1
        job = HelperJob(
            key=key,
            chain_id=key.chain_id,
            ready_time=max(float(ready_time), self.env.now),
            priority=float(priority),
            sequence=self.sequence,
            action=action,
            done=self.env.event(),
        )
        self.pending.append(job)
        self._notify()
        return job

    def cancel(self, key: TxKey) -> int:
        cancelled = 0
        for job in self.pending:
            if job.key == key and not job.cancelled:
                job.cancelled = True
                cancelled += 1
                if not job.done.triggered:
                    job.done.succeed(False)
        if cancelled:
            self.pending = [job for job in self.pending if not job.cancelled]
            self.stats.cancelled_helper_jobs += cancelled
            self._notify()
        return cancelled

    def pending_count(self, key: Optional[TxKey] = None) -> int:
        return sum(
            1 for job in self.pending
            if not job.cancelled and (key is None or job.key == key)
        )

    def _notify(self) -> None:
        if not self.wake.triggered:
            self.wake.succeed()

    def _worker(self):
        while True:
            self.pending = [job for job in self.pending if not job.cancelled]
            if not self.pending:
                self.wake = self.env.event()
                yield self.wake
                continue

            ready = [job for job in self.pending if job.ready_time <= self.env.now + 1e-12]
            if not ready:
                next_ready = min(job.ready_time for job in self.pending)
                self.wake = self.env.event()
                yield self.env.timeout(max(0.0, next_ready - self.env.now)) | self.wake
                continue

            # Higher confidence/urgency priority first, then deterministic FIFO.
            job = max(ready, key=lambda item: (item.priority, -item.sequence))
            self.pending.remove(job)
            if job.cancelled:
                continue
            self.active = job
            if self.last_chain_id is not None and self.last_chain_id != job.chain_id:
                self.stats.helper_cross_chain_services += 1
            self.last_chain_id = job.chain_id
            self.stats.helper_services += 1
            try:
                result = yield self.env.process(job.action())
            except Exception as exc:
                if not job.done.triggered:
                    job.done.fail(exc)
            else:
                if not job.done.triggered:
                    job.done.succeed(bool(result))
            finally:
                self.active = None


@dataclass
class HelperState:
    node: Node
    scheduler: HelperScheduler
    link_rank: Dict[Tuple[int, int], int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 4. Concurrent three-chain network
# ---------------------------------------------------------------------------
class Network:
    def __init__(self, env: simpy.Environment, protocol: str, snr_db: float,
                 sim_time: float, seed: int):
        if protocol not in PROTOCOLS:
            raise ValueError(f"unknown protocol: {protocol}")
        self.env = env
        self.protocol = protocol
        self.snr_db = float(snr_db)
        self.sim_time = float(sim_time)
        self.seed = int(seed)
        self.stats = Stats()
        self.channel = AcousticChannel(env, snr_db, seed, self.stats)
        self.routers: Dict[Tuple[int, int], Node] = {}
        self.sink = Node(env, SINK_ID, SINK_POS[0], SINK_POS[1], "SINK")
        self.helpers: List[HelperState] = []
        self.link_candidates: Dict[Tuple[int, int], List[HelperState]] = {}
        self._tx_counter: Dict[TxKey, int] = {}
        self._build_topology()

    def _build_topology(self) -> None:
        for chain_id, y in enumerate(CHAIN_Y_OFFSETS):
            for hop in range(NUM_HOPS):
                node_id = chain_id * 100 + hop
                self.routers[(chain_id, hop)] = Node(
                    self.env, node_id, hop * HOP_DIST, y, "ROUTER"
                )

        rng = stable_rng(self.seed, 0x7010)
        positions: List[Tuple[float, float]] = []
        while len(positions) < N_HELPERS_TOTAL:
            x = float(rng.uniform(0.0, HOP_DIST * NUM_HOPS))
            y = float(rng.uniform(-900.0, 900.0))
            eligible = False
            for chain_y in CHAIN_Y_OFFSETS:
                for hop in range(NUM_HOPS):
                    src = (hop * HOP_DIST, chain_y)
                    dst = SINK_POS if hop == NUM_HOPS - 1 else ((hop + 1) * HOP_DIST, chain_y)
                    if (math.hypot(x - src[0], y - src[1]) <= HOP_DIST and
                            math.hypot(x - dst[0], y - dst[1]) <= HOP_DIST):
                        eligible = True
                        break
                if eligible:
                    break
            if eligible:
                positions.append((x, y))

        for index, (x, y) in enumerate(positions):
            node = Node(self.env, 1000 + index, x, y, "HELPER")
            self.helpers.append(HelperState(
                node=node,
                scheduler=HelperScheduler(self.env, node.node_id, self.stats),
            ))

        for chain_id, chain_y in enumerate(CHAIN_Y_OFFSETS):
            for hop in range(NUM_HOPS):
                src = (hop * HOP_DIST, chain_y)
                dst = SINK_POS if hop == NUM_HOPS - 1 else ((hop + 1) * HOP_DIST, chain_y)
                ranked = sorted(
                    self.helpers,
                    key=lambda helper: max(
                        math.hypot(helper.node.x - src[0], helper.node.y - src[1]),
                        math.hypot(helper.node.x - dst[0], helper.node.y - dst[1]),
                    ),
                )[:HELPERS_PER_LINK]
                self.link_candidates[(chain_id, hop)] = ranked
                for rank, helper in enumerate(ranked):
                    helper.link_rank[(chain_id, hop)] = rank

    def next_tx_index(self, key: TxKey) -> int:
        value = self._tx_counter.get(key, 0)
        self._tx_counter[key] = value + 1
        return value

    def payload(self, chain_id: int, pid: int) -> Tuple[int, ...]:
        rng = stable_rng(self.seed, 0xDA7A, chain_id, pid)
        return tuple(int(v) for v in rng.integers(0, 64, size=RS_K))

    def _destination(self, chain_id: int, hop: int) -> Node:
        return self.sink if hop == NUM_HOPS - 1 else self.routers[(chain_id, hop + 1)]

    def _decode(self, buffer: SoftBuffer, message: Sequence[int]) -> bool:
        if self.protocol in (PROTO_SW_ARQ, PROTO_CARQ):
            return buffer.decode_uncoded(message)
        return buffer.decode_rs(message)

    def _source_transmission(self, source: Node, destination: Node,
                             candidates: Sequence[HelperState], dest_buffer: SoftBuffer,
                             helper_buffers: Dict[int, SoftBuffer], codeword: Sequence[int],
                             positions: Sequence[int], key: TxKey):
        receptions = [Reception(destination, dest_buffer, "dest")]
        if self.protocol != PROTO_SW_ARQ:
            receptions.extend(
                Reception(helper.node, helper_buffers[helper.node.node_id], "helper")
                for helper in candidates
            )
        yield self.env.process(self.channel.broadcast(
            source, receptions, codeword, positions, key, self.next_tx_index(key)
        ))

    def _helper_transmission(self, helper: HelperState, destination: Node,
                             dest_buffer: SoftBuffer, codeword: Sequence[int],
                             positions: Sequence[int], key: TxKey, message: Sequence[int]):
        yield self.env.process(self.channel.broadcast(
            helper.node,
            [Reception(destination, dest_buffer, "dest")],
            codeword,
            positions,
            key,
            self.next_tx_index(key),
        ))
        return self._decode(dest_buffer, message)

    def _decoded_helpers(self, candidates: Sequence[HelperState],
                         buffers: Dict[int, SoftBuffer], message: Sequence[int]) -> List[HelperState]:
        return [
            helper for helper in candidates
            if self._decode(buffers[helper.node.node_id], message)
        ]

    def _fixed_helper_round(self, helper: HelperState, destination: Node,
                            dest_buffer: SoftBuffer, codeword: Sequence[int],
                            positions: Sequence[int], key: TxKey, message: Sequence[int]):
        # Fixed baselines use the best-ranked decoded helper and the same scheduler.
        def action():
            return self._helper_transmission(
                helper, destination, dest_buffer, codeword, positions, key, message
            )

        job = helper.scheduler.submit(key, self.env.now, 1.0, action)
        result = yield job.done
        return bool(result)

    def _ca_backoff(self, helper: HelperState, rank: int, key: TxKey,
                    helper_buffer: SoftBuffer, cpkt: int) -> Tuple[float, float]:
        confidence = helper_buffer.confidence() / 3.0
        energy = max(0.0, min(1.0, helper.node.energy_j / INITIAL_ENERGY_J))
        source = self._node_by_id(key.hop_src)
        destination = self._node_by_id(key.hop_dst)
        bottleneck = max(
            math.hypot(helper.node.x - source.x, helper.node.y - source.y),
            math.hypot(helper.node.x - destination.x, helper.node.y - destination.y),
        )
        delay_score = 1.0 / (1.0 + bottleneck / HOP_DIST)
        score = 0.40 * confidence + 0.25 * energy + 0.35 * delay_score
        rng = stable_rng(self.seed, 0xCA, key.chain_id, key.pid, key.hop_src,
                         helper.node.node_id, cpkt)
        jitter = float(rng.uniform(0.0, T_BACKOFF_JITTER))
        backoff = max(T_PROTECTION_GAP, (1.0 - score) * T_MAX_WINDOW)
        backoff += rank * 0.006 + jitter
        # Low C_pkt has greater urgency, but helper quality still determines rank.
        priority = 0.55 * (1.0 - cpkt / 3.0) + 0.45 * score
        return backoff, priority

    def _node_by_id(self, node_id: int) -> Node:
        if node_id == SINK_ID:
            return self.sink
        chain_id, hop = divmod(node_id, 100)
        return self.routers[(chain_id, hop)]

    def _ca_contender(self, helper: HelperState, rank: int, destination: Node,
                      dest_buffer: SoftBuffer, helper_buffer: SoftBuffer,
                      codeword: Sequence[int], positions: Sequence[int], key: TxKey,
                      message: Sequence[int], cpkt: int, ack_event: simpy.Event):
        backoff, priority = self._ca_backoff(helper, rank, key, helper_buffer, cpkt)
        yield self.env.timeout(backoff)
        if ack_event.triggered:
            return False

        def action():
            return self._helper_transmission(
                helper, destination, dest_buffer, codeword, positions, key, message
            )

        job = helper.scheduler.submit(key, self.env.now, priority, action)
        result = yield job.done | ack_event
        if job.done in result and bool(result[job.done]) and not ack_event.triggered:
            ack_event.succeed(helper.node.node_id)
            return True
        return False

    def _ca_helper_round(self, helpers: Sequence[HelperState], candidates: Sequence[HelperState],
                         destination: Node, dest_buffer: SoftBuffer,
                         helper_buffers: Dict[int, SoftBuffer], codeword: Sequence[int],
                         positions: Sequence[int], key: TxKey, message: Sequence[int], cpkt: int):
        ack_event = self.env.event()
        contender_events = []
        for helper in helpers:
            rank = candidates.index(helper)
            contender_events.append(self.env.process(self._ca_contender(
                helper, rank, destination, dest_buffer,
                helper_buffers[helper.node.node_id], codeword, positions,
                key, message, cpkt, ack_event,
            )))
        all_done = simpy.events.AllOf(self.env, contender_events)
        result = yield ack_event | all_done
        if ack_event in result:
            for candidate in candidates:
                candidate.scheduler.cancel(key)
            return True
        return self._decode(dest_buffer, message)

    @staticmethod
    def _charq_positions(retransmission_index: int) -> Tuple[int, ...]:
        """Fixed, non-adaptive C-HARQ schedule used by the control baseline.

        The first NACK supplies all four missing parity symbols in one acoustic
        round.  Later NACKs repeat the complete mother code so information and
        parity symbols receive the same Chase-combining opportunity.
        """
        if retransmission_index <= 0:
            raise ValueError("C-HARQ retransmission index must start at one")
        return CHARQ_IR_POSITIONS if retransmission_index == 1 else FULL_CODE_POSITIONS

    @staticmethod
    def _ca_positions(dest_buffer: SoftBuffer, cpkt: int) -> Tuple[int, ...]:
        missing_blocks = [
            RV_POSITIONS[index] for index in (1, 2)
            if not all(dest_buffer.seen[p] for p in RV_POSITIONS[index])
        ]
        if cpkt >= 3 and missing_blocks:
            return tuple(missing_blocks[0])
        if cpkt == 2 and missing_blocks:
            return tuple(p for block in missing_blocks for p in block)
        if cpkt <= 1:
            # Low confidence: one full mother-code transmission supplies all
            # missing parity and Chase-combines already received data symbols.
            return FULL_CODE_POSITIONS
        return RV_POSITIONS[0]

    def deliver_hop(self, chain_id: int, pid: int, hop: int,
                    message: Sequence[int], codeword: Sequence[int]):
        source = self.routers[(chain_id, hop)]
        destination = self._destination(chain_id, hop)
        key = TxKey(chain_id, pid, source.node_id, destination.node_id)
        candidates = self.link_candidates[(chain_id, hop)]
        dest_buffer = SoftBuffer()
        helper_buffers = {helper.node.node_id: SoftBuffer() for helper in candidates}
        charq_retransmission_index = 0

        for attempt in range(MAX_RETRIES + 1):
            if attempt == 0:
                positions = UNCODED_POSITIONS if self.protocol in (PROTO_SW_ARQ, PROTO_CARQ) else RV_POSITIONS[0]
                yield self.env.process(self._source_transmission(
                    source, destination, candidates, dest_buffer, helper_buffers,
                    codeword, positions, key,
                ))
            else:
                # One NACK is transmitted per failed decoding round and heard by
                # the source plus all candidate helpers.
                yield self.env.process(self.channel.control(destination, source, key))
                decoded_helpers = self._decoded_helpers(candidates, helper_buffers, message)

                if self.protocol == PROTO_SW_ARQ:
                    positions = UNCODED_POSITIONS
                    yield self.env.process(self._source_transmission(
                        source, destination, (), dest_buffer, helper_buffers,
                        codeword, positions, key,
                    ))
                elif self.protocol == PROTO_CARQ:
                    positions = UNCODED_POSITIONS
                    if decoded_helpers:
                        yield self.env.process(self._fixed_helper_round(
                            decoded_helpers[0], destination, dest_buffer, codeword,
                            positions, key, message,
                        ))
                    else:
                        yield self.env.process(self._source_transmission(
                            source, destination, candidates, dest_buffer, helper_buffers,
                            codeword, positions, key,
                        ))
                elif self.protocol == PROTO_CHARQ:
                    charq_retransmission_index += 1
                    positions = self._charq_positions(charq_retransmission_index)
                    if decoded_helpers:
                        yield self.env.process(self._fixed_helper_round(
                            decoded_helpers[0], destination, dest_buffer, codeword,
                            positions, key, message,
                        ))
                    else:
                        yield self.env.process(self._source_transmission(
                            source, destination, candidates, dest_buffer, helper_buffers,
                            codeword, positions, key,
                        ))
                else:
                    cpkt = dest_buffer.confidence()
                    positions = self._ca_positions(dest_buffer, cpkt)
                    if decoded_helpers:
                        yield self.env.process(self._ca_helper_round(
                            decoded_helpers, candidates, destination, dest_buffer,
                            helper_buffers, codeword, positions, key, message, cpkt,
                        ))
                    else:
                        yield self.env.process(self._source_transmission(
                            source, destination, candidates, dest_buffer, helper_buffers,
                            codeword, positions, key,
                        ))

            if self._decode(dest_buffer, message):
                for helper in candidates:
                    helper.scheduler.cancel(key)
                yield self.env.process(self.channel.control(destination, source, key))
                return True
        for helper in candidates:
            helper.scheduler.cancel(key)
        return False

    def deliver_packet(self, chain_id: int, pid: int, creation_time: float):
        message = self.payload(chain_id, pid)
        codeword = CODEC.encode(message)
        for hop in range(NUM_HOPS):
            ok = yield self.env.process(self.deliver_hop(
                chain_id, pid, hop, message, codeword
            ))
            if not ok:
                self.stats.drops += 1
                return
        self.stats.successes += 1
        self.stats.delays.append(self.env.now - creation_time)

    def traffic_generator(self, chain_id: int):
        rng = stable_rng(self.seed, 0xA771, chain_id)
        pid = 0
        while True:
            creation = self.env.now
            self.stats.generated += 1
            self.env.process(self.deliver_packet(chain_id, pid, creation))
            pid += 1
            yield self.env.timeout(float(rng.exponential(TRAFFIC_MEAN_S)))

    def start(self) -> None:
        for chain_id in range(NUM_CHAINS):
            self.env.process(self.traffic_generator(chain_id))


# ---------------------------------------------------------------------------
# 5. Simulation, aggregation and reproducible output
# ---------------------------------------------------------------------------
def run_sim(snr_db: float, protocol: str, sim_time: float, seed: int = 0) -> Dict[str, float]:
    env = simpy.Environment()
    network = Network(env, protocol, snr_db, sim_time, seed)
    network.start()
    env.run(until=sim_time)
    result = network.stats.summary()
    result.update({
        "snr_db": float(snr_db),
        "protocol": protocol,
        "sim_time": float(sim_time),
        "seed": int(seed),
    })
    return result


def finite_mean(values: Sequence[float]) -> float:
    valid = [float(v) for v in values if math.isfinite(float(v))]
    return statistics.fmean(valid) if valid else float("nan")


def ci95(values: Sequence[float]) -> float:
    valid = [float(v) for v in values if math.isfinite(float(v))]
    if len(valid) < 2:
        return 0.0 if valid else float("nan")
    return 1.96 * statistics.stdev(valid) / math.sqrt(len(valid))


def aggregate_results(raw: Sequence[Dict[str, float]]) -> List[Dict[str, float]]:
    grouped: Dict[Tuple[str, float], List[Dict[str, float]]] = {}
    for row in raw:
        grouped.setdefault((str(row["protocol"]), float(row["snr_db"])), []).append(row)
    output = []
    metrics = ("delay", "pdr", "overhead", "energy_efficiency", "successes",
               "collisions", "helper_services", "helper_cross_chain_services",
               "cancelled_helper_jobs")
    for protocol in PROTOCOLS:
        snrs = sorted(snr for proto, snr in grouped if proto == protocol)
        for snr in snrs:
            rows = grouped[(protocol, snr)]
            entry: Dict[str, float] = {
                "protocol": protocol,
                "snr_db": snr,
                "n_runs": float(len(rows)),
            }
            for metric in metrics:
                vals = [float(row[metric]) for row in rows]
                entry[f"{metric}_mean"] = finite_mean(vals)
                entry[f"{metric}_ci95"] = ci95(vals)
            output.append(entry)
    return output


def _run_task(args: Tuple[float, str, float, int]) -> Dict[str, float]:
    return run_sim(*args)


def run_sweep(snrs: Sequence[float], protocols: Sequence[str], sim_time: float,
              seeds: Sequence[int], jobs: int = 1) -> List[Dict[str, float]]:
    tasks = [(float(snr), proto, float(sim_time), int(seed))
             for proto in protocols for snr in snrs for seed in seeds]
    if jobs <= 1:
        return [_run_task(task) for task in tasks]
    rows: List[Dict[str, float]] = []
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        future_map = {pool.submit(_run_task, task): task for task in tasks}
        for future in as_completed(future_map):
            rows.append(future.result())
    return rows


def write_results(raw: Sequence[Dict[str, float]], summary: Sequence[Dict[str, float]],
                  output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_sorted = sorted(raw, key=lambda row: (PROTOCOLS.index(str(row["protocol"])),
                                               float(row["snr_db"]), int(row["seed"])))
    with (output_dir / "raw_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(raw_sorted[0].keys()))
        writer.writeheader()
        writer.writerows(raw_sorted)
    with (output_dir / "summary_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
    payload = {
        "model": {
            "rs": "RS(63,57), GF(2^6), primitive polynomial 0x43",
            "rv0": "57 information + 2 parity symbols",
            "rv1": "2 parity symbols",
            "rv2": "2 parity symbols",
            "useful_bits": INFO_BITS,
            "bit_rate": BIT_RATE,
            "topology": "3 chains x 5 hops, one shared sink, 15 shared helpers",
        },
        "raw": raw_sorted,
        "summary": list(summary),
    }
    (output_dir / "results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 6. Self-tests: codec boundary, full-key isolation and queue cancellation
# ---------------------------------------------------------------------------
def test_rs_codec() -> None:
    rng = np.random.default_rng(20260716)
    patterns = []
    for erasures in range(0, RS_NSYM + 1):
        for errors in range(0, (RS_NSYM - erasures) // 2 + 1):
            patterns.append((errors, erasures))
    for errors, erasures in patterns:
        for _ in range(6):
            message = tuple(int(v) for v in rng.integers(0, 64, size=RS_K))
            codeword = list(CODEC.encode(message))
            locations = rng.choice(RS_N, size=errors + erasures, replace=False).tolist()
            erased = locations[:erasures]
            corrupted = locations[erasures:]
            for pos in erased:
                codeword[pos] = 0
            for pos in corrupted:
                delta = int(rng.integers(1, 64))
                codeword[pos] ^= delta
            decoded = CODEC.decode(codeword, erased)
            assert decoded == message, (errors, erasures, locations)

    # One pattern outside 2e+s<=6 must not silently produce the true payload.
    message = tuple(int(v) for v in rng.integers(0, 64, size=RS_K))
    codeword = list(CODEC.encode(message))
    for pos in (1, 9, 23, 41):
        codeword[pos] ^= 7
    try:
        decoded = CODEC.decode(codeword)
    except ReedSolomonError:
        pass
    else:
        assert decoded != message


def test_soft_buffer_and_keys() -> None:
    message = tuple(range(RS_K))
    codeword = CODEC.encode(message)
    a = SoftBuffer()
    b = SoftBuffer()
    a.add(codeword, tuple(range(RS_N)), 1e6, stable_rng(1, 1))
    assert a.decode_rs(message)
    assert not b.decode_rs(message)
    keys = {
        TxKey(0, 7, 0, 1),
        TxKey(1, 7, 100, 101),
        TxKey(0, 7, 1, 2),
    }
    assert len(keys) == 3


def test_charq_fixed_schedule() -> None:
    assert Network._charq_positions(1) == CHARQ_IR_POSITIONS
    assert Network._charq_positions(2) == FULL_CODE_POSITIONS
    assert Network._charq_positions(MAX_RETRIES) == FULL_CODE_POSITIONS
    assert len(Network._charq_positions(1)) * RS_BITS_PER_SYMBOL == 24
    assert len(Network._charq_positions(2)) * RS_BITS_PER_SYMBOL == 378
    try:
        Network._charq_positions(0)
    except ValueError:
        pass
    else:
        raise AssertionError("C-HARQ round zero must be rejected")


def test_scheduler_cancellation() -> None:
    env = simpy.Environment()
    stats = Stats()
    scheduler = HelperScheduler(env, 1000, stats)
    key_a = TxKey(0, 0, 0, 1)
    key_b = TxKey(1, 0, 100, 101)
    served: List[TxKey] = []

    def action(key: TxKey):
        served.append(key)
        yield env.timeout(0.1)
        return True

    scheduler.submit(key_a, 0.5, 1.0, lambda: action(key_a))
    scheduler.submit(key_b, 0.6, 1.0, lambda: action(key_b))
    assert scheduler.cancel(key_a) == 1
    assert scheduler.pending_count(key_a) == 0
    env.run(until=1.0)
    assert served == [key_b]
    assert stats.cancelled_helper_jobs == 1


def run_self_tests() -> None:
    test_rs_codec()
    test_soft_buffer_and_keys()
    test_charq_fixed_schedule()
    test_scheduler_cancellation()


def print_summary(summary: Sequence[Dict[str, float]]) -> None:
    print("\nProtocol   SNR    Delay(s)       PDR    Overhead    EE(bit/J)")
    print("-" * 72)
    for row in summary:
        print(
            f"{str(row['protocol']):10s} {row['snr_db']:4.1f}  "
            f"{row['delay_mean']:8.3f} +/-{row['delay_ci95']:6.3f}  "
            f"{row['pdr_mean']:6.3f}  {row['overhead_mean']:8.3f}  "
            f"{row['energy_efficiency_mean']:10.3f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run codec/state tests and exit")
    parser.add_argument("--quick", action="store_true", help="3 SNR x 2 seeds x 600 s pilot")
    parser.add_argument("--sim-time", type=float, default=None)
    parser.add_argument("--runs", type=int, default=None)
    parser.add_argument("--snr", type=float, nargs="*", default=None)
    parser.add_argument("--protocol", choices=PROTOCOLS, nargs="*", default=None)
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=Path("output") / "v10")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.self_test:
        run_self_tests()
        print("v10 self-tests: PASS")
        return

    if args.quick:
        snrs = args.snr or [2.0, 5.0, 8.0]
        sim_time = args.sim_time or 600.0
        runs = args.runs or 2
    else:
        snrs = args.snr or [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        sim_time = args.sim_time or 3000.0
        runs = args.runs or 5
    protocols = args.protocol or list(PROTOCOLS)
    seeds = list(range(runs))
    print(
        f"CA-CHARQ v10: {len(protocols)} protocols x {len(snrs)} SNR x "
        f"{runs} seeds, sim_time={sim_time:g}s, jobs={args.jobs}"
    )
    started = time.perf_counter()
    raw = run_sweep(snrs, protocols, sim_time, seeds, max(1, args.jobs))
    summary = aggregate_results(raw)
    write_results(raw, summary, args.output)
    print_summary(summary)
    print(f"\nElapsed: {time.perf_counter() - started:.2f}s")
    print(f"Results: {args.output.resolve()}")


if __name__ == "__main__":
    main()
