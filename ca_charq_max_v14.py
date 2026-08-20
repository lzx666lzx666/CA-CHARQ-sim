#!/usr/bin/env python3
"""
Priority-aware CA-CHARQ simulation for a concurrent underwater acoustic sensor
network.

The formal experiment compares Stop-and-Wait ARQ, C-ARQ, C-HARQ and CA-CHARQ.
CA-CHARQ uses packet importance in the initial redundancy,
confidence-adaptive retransmission, cooperative contention, and every
non-preemptive transmitter queue.  A legacy CA-CHARQ-Base entry remains
available only for compatibility and self-tests; it is not part of formal
simulation runs or paper figures.

All protocols share the topology, traffic, payloads, channel model, helper
population, important-packet IDs and random seeds.  Important traffic is judged
primarily by on-time delivery ratio and P95 latency.  System-wide overhead,
energy efficiency, and normal-packet reliability are reported as cost and
fairness constraints.

The default command runs the complete 4 protocol x 7 SNR x 5 seed experiment.
The --topology-sweep mode performs one-factor sensitivity experiments for total
node count, nominal node spacing, selected path count, and hops per selected
path.  Every run writes CSV/JSON data and creates paper-style PNG and editable
SVG figures.  Use --quick for a short pilot and --self-test for
codec/state/importance/topology tests.
"""

from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
import os
import statistics
import textwrap
import time
import types
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape as xml_escape

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
        def __init__(self, resource, priority=0):
            super().__init__(resource.env)
            self.resource = resource
            self.priority = int(priority)
            resource._request_sequence += 1
            self.sequence = resource._request_sequence
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
            self._request_sequence = 0

        def request(self, priority=0):
            return _MiniRequest(self, priority)

        def _request(self, request):
            if len(self.users) < self.capacity:
                self.users.append(request)
                request.granted = True
                request.succeed(request)
            else:
                self.queue.append(request)
                self.queue.sort(key=lambda item: (item.priority, item.sequence))

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
        PriorityResource=_MiniResource,
        Event=_MiniEvent,
        events=types.SimpleNamespace(
            Event=_MiniEvent,
            AllOf=lambda env, events: _MiniCondition(env, events, all_events=True),
        ),
    )


# ---------------------------------------------------------------------------
# 0. Experiment constants
# ---------------------------------------------------------------------------
PROTO_SW_ARQ = "停等ARQ"
LEGACY_PROTO_SW_ARQ = "S&W ARQ"
PROTO_CARQ = "C-ARQ"
PROTO_CHARQ = "C-HARQ"
PROTO_CA_BASE = "CA-CHARQ-Base"
PROTO_CA = "CA-CHARQ"
PROTOCOLS = (
    PROTO_SW_ARQ,
    PROTO_CARQ,
    PROTO_CHARQ,
    PROTO_CA_BASE,
    PROTO_CA,
)
# CA-CHARQ-Base remains available only as a compatibility/diagnostic protocol.
# Formal paper comparisons always keep packet-importance awareness enabled and
# therefore compare the following four protocols.
PAPER_PROTOCOLS = (
    PROTO_SW_ARQ,
    PROTO_CARQ,
    PROTO_CHARQ,
    PROTO_CA,
)

# Protocol identifiers are also used as CSV keys; read_summary_csv normalizes
# legacy "S&W ARQ" files. Paper figures use these reader-facing labels.
PAPER_PROTOCOL_LABELS = {
    PROTO_SW_ARQ: "S&W ARQ",
    PROTO_CARQ: PROTO_CARQ,
    PROTO_CHARQ: PROTO_CHARQ,
    PROTO_CA: "本方法",
}

# The simulations retain total_nodes=(21, 31, 41, 51).  Paper-facing
# node-scale plots use the requested display labels only; no topology or
# numeric result is recomputed.
PAPER_NODE_SCALE_DISPLAY_LABELS = {
    "21": "20",
    "31": "30",
    "41": "40",
    "51": "50",
}

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
IMPORTANT_EXTRA_RETRIES = 0
INITIAL_ENERGY_J = 10000.0
CONTROL_BITS = 12
TRAFFIC_MEAN_S = 30.0
DEFAULT_IMPORTANCE_RATIO = 0.20
IMPORTANT_DEADLINE_S = 35.0
# A fixed penalty makes unsuccessful and still-in-flight packets visible in
# delay analysis instead of reporting only the easier successfully delivered
# subset.  It is deliberately twice the important-packet deadline.
UNDELIVERED_DELAY_PENALTY_S = 2.0 * IMPORTANT_DEADLINE_S
IMPORTANCE_SIGNAL_BITS = 1
IMPORTANCE_NORMAL = 0
IMPORTANCE_HIGH = 1
IMPORTANCE_LABELS = {
    IMPORTANCE_NORMAL: "normal",
    IMPORTANCE_HIGH: "important",
}

# Importance-aware helper contention and queueing.  An active acoustic
# transmission is never pre-empted.
IMPORTANT_BACKOFF_REDUCTION = 0.20
QUEUE_AGING_RATE = 0.025
QUEUE_AGING_CAP = 0.20
MAX_CONSECUTIVE_IMPORTANT_SERVICES = 3

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

SINK_ID = 9999
T_MAX_WINDOW = 0.65
T_BACKOFF_JITTER = 0.035
T_PROTECTION_GAP = 0.02

FORMATION_RECTANGULAR = "rectangular"
FORMATION_STAGGERED = "staggered"
FORMATION_CONVERGING = "converging"
FORMATION_RANDOM = "random"
FORMATIONS = (
    FORMATION_RECTANGULAR,
    FORMATION_STAGGERED,
    FORMATION_CONVERGING,
    FORMATION_RANDOM,
)
FORMATION_LABELS = {
    FORMATION_RECTANGULAR: "Rectangular",
    FORMATION_STAGGERED: "Staggered",
    FORMATION_CONVERGING: "Converging",
    FORMATION_RANDOM: "Random",
}


@dataclass(frozen=True)
class TopologyConfig:
    """A fixed homogeneous deployment with selected routes through the field.

    ``total_nodes`` includes the common sink.  All other nodes are physically
    identical sensors and may participate in cooperative retransmission.
    ``deployment_chains`` and ``deployment_hops`` define the master physical
    deployment.  ``num_chains``, ``num_hops`` and the active-index fields only
    select route overlays for the current experiment.  Changing the number of
    active paths or hops therefore does not rebuild or resize the node field.
    """

    total_nodes: int = NUM_CHAINS * NUM_HOPS + N_HELPERS_TOTAL + 1
    spacing_m: float = HOP_DIST
    formation: str = FORMATION_RECTANGULAR
    num_chains: int = NUM_CHAINS
    num_hops: int = NUM_HOPS
    deployment_chains: int = NUM_CHAINS
    deployment_hops: int = NUM_HOPS
    active_chain_indices: Tuple[int, ...] = ()
    active_hop_start: int = 0
    candidates_per_link: int = HELPERS_PER_LINK
    snr_reference_distance_m: float = HOP_DIST

    @property
    def route_node_count(self) -> int:
        return self.num_chains * self.num_hops

    @property
    def deployment_route_node_count(self) -> int:
        return self.deployment_chains * self.deployment_hops

    @property
    def extra_node_count(self) -> int:
        return self.total_nodes - self.deployment_route_node_count - 1

    @property
    def cooperative_node_count(self) -> int:
        """Number of homogeneous non-sink nodes eligible to cooperate."""
        return self.total_nodes - 1

    @property
    def active_chain_ids(self) -> Tuple[int, ...]:
        if self.active_chain_indices:
            return self.active_chain_indices
        return tuple(range(self.num_chains))

    def validate(self) -> "TopologyConfig":
        if self.num_chains < 1:
            raise ValueError("num_chains must be positive")
        if self.num_hops < 1:
            raise ValueError("num_hops must be positive")
        if self.deployment_chains < 1:
            raise ValueError("deployment_chains must be positive")
        if self.deployment_hops < 1:
            raise ValueError("deployment_hops must be positive")
        if len(self.active_chain_ids) != self.num_chains:
            raise ValueError(
                "active_chain_indices must contain one entry per active path"
            )
        if len(set(self.active_chain_ids)) != self.num_chains:
            raise ValueError("active_chain_indices must be unique")
        if any(
            chain_id < 0 or chain_id >= self.deployment_chains
            for chain_id in self.active_chain_ids
        ):
            raise ValueError("active_chain_indices exceed the master deployment")
        if self.active_hop_start < 0:
            raise ValueError("active_hop_start cannot be negative")
        if self.active_hop_start + self.num_hops != self.deployment_hops:
            raise ValueError(
                "selected hop suffix must terminate at the common sink"
            )
        if self.spacing_m <= 0.0:
            raise ValueError("spacing_m must be positive")
        if self.formation not in FORMATIONS:
            raise ValueError(f"unknown formation: {self.formation}")
        if self.extra_node_count < 1:
            raise ValueError(
                "total_nodes must leave at least one sensor beyond route anchors"
            )
        if self.candidates_per_link < 1:
            raise ValueError("candidates_per_link must be positive")
        if self.snr_reference_distance_m <= 0.0:
            raise ValueError("snr_reference_distance_m must be positive")
        return self


BASE_TOPOLOGY = TopologyConfig()


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


def noise_for_target_snr(
    snr_db: float,
    reference_distance_m: float = HOP_DIST,
) -> float:
    target = 10.0 ** (snr_db / 10.0)
    return TX_POWER_W / (
        transmission_loss(reference_distance_m) * target
    )


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
        # Draw a complete mother-code channel realization and select the symbols
        # carried by this action.  Shared codeword positions therefore see the
        # same fade/noise under paired protocol runs even when one protocol
        # transmits RV0 and another transmits the full code.  This common-random-
        # number construction lowers comparison variance without changing the
        # marginal Rayleigh/QPSK model.
        qpsk_gamma_all = rng.exponential(
            max(avg_snr, 1e-12), size=(RS_N, 3)
        )
        qpsk_gamma = qpsk_gamma_all[pos, :]
        gamma = np.repeat(qpsk_gamma, 2, axis=1)
        signs = 1.0 - 2.0 * bits
        noise_all = rng.normal(size=(RS_N, RS_BITS_PER_SYMBOL))
        observation = (
            gamma * signs
            + np.sqrt(gamma) * noise_all[pos, :]
        )
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
        # Thresholds are calibrated on failed-decoding states rather than on
        # all receptions.  This prevents almost every NACK from collapsing into
        # C_pkt=0 and preserves distinct IR, parity-completion and Chase actions.
        if ratio <= 0.50:
            return 3
        if ratio <= 1.50:
            return 2
        if ratio <= 4.00:
            return 1
        return 0


@dataclass(frozen=True, order=True)
class TxKey:
    chain_id: int
    pid: int
    hop_src: int
    hop_dst: int


@dataclass
class PacketContext:
    """End-to-end packet state; importance and payload do not change by hop."""

    chain_id: int
    pid: int
    creation_time: float
    importance: int
    message: Tuple[int, ...]
    codeword: Tuple[int, ...]


@dataclass
class PacketClassStats:
    tx_bits: int = 0
    energy_j: float = 0.0
    successes: int = 0
    drops: int = 0
    collisions: int = 0
    generated: int = 0
    deadline_misses: int = 0
    delays: List[float] = field(default_factory=list)
    helper_services: int = 0
    queue_waits: List[float] = field(default_factory=list)
    radio_queue_waits: List[float] = field(default_factory=list)


@dataclass
class Stats:
    important_deadline_s: float = IMPORTANT_DEADLINE_S
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
    classes: Dict[int, PacketClassStats] = field(default_factory=lambda: {
        IMPORTANCE_NORMAL: PacketClassStats(),
        IMPORTANCE_HIGH: PacketClassStats(),
    })

    def packet_generated(self, importance: int) -> None:
        self.generated += 1
        self.classes[importance].generated += 1

    def packet_success(self, importance: int, delay: float, deadline_s: float) -> None:
        self.successes += 1
        self.delays.append(float(delay))
        class_stats = self.classes[importance]
        class_stats.successes += 1
        class_stats.delays.append(float(delay))
        if importance == IMPORTANCE_HIGH and delay > deadline_s:
            class_stats.deadline_misses += 1

    def packet_drop(self, importance: int) -> None:
        self.drops += 1
        class_stats = self.classes[importance]
        class_stats.drops += 1
        if importance == IMPORTANCE_HIGH:
            class_stats.deadline_misses += 1

    def record_tx(self, importance: int, bits: int, energy_j: float,
                  control: bool = False) -> None:
        self.tx_bits += int(bits)
        self.energy_j += float(energy_j)
        if control:
            self.control_bits += int(bits)
        class_stats = self.classes[importance]
        class_stats.tx_bits += int(bits)
        class_stats.energy_j += float(energy_j)

    def record_collision(self, importance: int) -> None:
        self.collisions += 1
        self.classes[importance].collisions += 1

    def record_helper_service(self, importance: int, queue_wait: float) -> None:
        self.helper_services += 1
        class_stats = self.classes[importance]
        class_stats.helper_services += 1
        class_stats.queue_waits.append(max(0.0, float(queue_wait)))

    def record_radio_queue_wait(self, importance: int, queue_wait: float) -> None:
        self.classes[importance].radio_queue_waits.append(
            max(0.0, float(queue_wait))
        )

    def summary(self) -> Dict[str, float]:
        useful = self.successes * INFO_BITS
        undelivered = max(0, self.generated - self.successes)
        output = {
            "delay": float(np.mean(self.delays)) if self.delays else float("nan"),
            "delay_p95": (
                float(np.percentile(self.delays, 95))
                if self.delays else float("nan")
            ),
            "delivery_penalized_delay": (
                (sum(self.delays) + undelivered * UNDELIVERED_DELAY_PENALTY_S)
                / self.generated
                if self.generated else float("nan")
            ),
            "pdr": self.successes / self.generated if self.generated else float("nan"),
            "overhead": self.tx_bits / useful if useful else float("nan"),
            "energy_efficiency": useful / self.energy_j if self.energy_j else float("nan"),
            "tx_bits_per_generated": (
                self.tx_bits / self.generated
                if self.generated else float("nan")
            ),
            "energy_per_generated": (
                self.energy_j / self.generated
                if self.generated else float("nan")
            ),
            "successes": float(self.successes),
            "drops": float(self.drops),
            "generated": float(self.generated),
            "collisions": float(self.collisions),
            "helper_services": float(self.helper_services),
            "helper_cross_chain_services": float(self.helper_cross_chain_services),
            "cancelled_helper_jobs": float(self.cancelled_helper_jobs),
        }
        for importance, label in IMPORTANCE_LABELS.items():
            class_stats = self.classes[importance]
            class_useful = class_stats.successes * INFO_BITS
            class_undelivered = max(
                0, class_stats.generated - class_stats.successes
            )
            prefix = f"{label}_"
            output.update({
                prefix + "delay": (
                    float(np.mean(class_stats.delays))
                    if class_stats.delays else float("nan")
                ),
                prefix + "delay_p95": (
                    float(np.percentile(class_stats.delays, 95))
                    if class_stats.delays else float("nan")
                ),
                prefix + "delivery_penalized_delay": (
                    (
                        sum(class_stats.delays)
                        + class_undelivered * UNDELIVERED_DELAY_PENALTY_S
                    ) / class_stats.generated
                    if class_stats.generated else float("nan")
                ),
                prefix + "on_time_pdr": (
                    sum(
                        delay <= self.important_deadline_s
                        for delay in class_stats.delays
                    )
                    / class_stats.generated
                    if class_stats.generated else float("nan")
                ),
                prefix + "pdr": (
                    class_stats.successes / class_stats.generated
                    if class_stats.generated else float("nan")
                ),
                prefix + "overhead": (
                    class_stats.tx_bits / class_useful
                    if class_useful else float("nan")
                ),
                prefix + "energy_efficiency": (
                    class_useful / class_stats.energy_j
                    if class_stats.energy_j else float("nan")
                ),
                prefix + "successes": float(class_stats.successes),
                prefix + "drops": float(class_stats.drops),
                prefix + "generated": float(class_stats.generated),
                prefix + "collisions": float(class_stats.collisions),
                prefix + "helper_services": float(class_stats.helper_services),
                prefix + "queue_wait": (
                    float(np.mean(class_stats.queue_waits))
                    if class_stats.queue_waits else 0.0
                ),
                prefix + "radio_queue_wait": (
                    float(np.mean(class_stats.radio_queue_waits))
                    if class_stats.radio_queue_waits else 0.0
                ),
                prefix + "tx_bits_per_generated": (
                    class_stats.tx_bits / class_stats.generated
                    if class_stats.generated else float("nan")
                ),
                prefix + "energy_per_generated": (
                    class_stats.energy_j / class_stats.generated
                    if class_stats.generated else float("nan")
                ),
            })
            if importance == IMPORTANCE_HIGH:
                output[prefix + "deadline_miss_rate"] = (
                    class_stats.deadline_misses / class_stats.generated
                    if class_stats.generated else float("nan")
                )
        return output


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
        self.radio = simpy.PriorityResource(self.env, capacity=1)


@dataclass
class Reception:
    receiver: Node
    buffer: SoftBuffer
    purpose: str


class AcousticChannel:
    def __init__(self, env: simpy.Environment, snr_db: float, seed: int,
                 stats: Stats, importance_aware: bool = False,
                 snr_reference_distance_m: float = HOP_DIST):
        self.env = env
        self.noise = noise_for_target_snr(
            snr_db, snr_reference_distance_m
        )
        self.seed = seed
        self.stats = stats
        self.importance_aware = bool(importance_aware)

    def radio_priority(self, importance: int) -> int:
        return (
            0
            if self.importance_aware and importance == IMPORTANCE_HIGH
            else 1
        )

    def avg_snr(self, sender: Node, receiver: Node) -> float:
        d = math.hypot(sender.x - receiver.x, sender.y - receiver.y)
        return sender.tx_power / (transmission_loss(d) * self.noise)

    def broadcast(self, sender: Node, receptions: Sequence[Reception], codeword: Sequence[int],
                  positions: Sequence[int], key: TxKey, tx_index: int, importance: int):
        """One physical transmission with independent fades at every receiver."""
        coded_bits = len(positions) * RS_BITS_PER_SYMBOL
        bits = coded_bits + IMPORTANCE_SIGNAL_BITS
        duration = bits / BIT_RATE
        queued_at = self.env.now
        with sender.radio.request(
            priority=self.radio_priority(importance)
        ) as request:
            yield request
            self.stats.record_radio_queue_wait(
                importance, self.env.now - queued_at
            )
            energy = sender.tx_power * duration
            sender.energy_j -= energy
            self.stats.record_tx(importance, bits, energy)
            yield self.env.timeout(duration)
            events = []
            for item in receptions:
                events.append(self.env.process(self._deliver(
                    sender, item, codeword, positions, key, tx_index, duration,
                    importance,
                )))
            if events:
                yield simpy.events.AllOf(self.env, events)

    def _deliver(self, sender: Node, reception: Reception, codeword: Sequence[int],
                 positions: Sequence[int], key: TxKey, tx_index: int, duration: float,
                 importance: int):
        receiver = reception.receiver
        distance = math.hypot(sender.x - receiver.x, sender.y - receiver.y)
        yield self.env.timeout(distance / SOUND_SPEED)
        if self.env.now < receiver.rx_busy_until:
            self.stats.record_collision(importance)
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

    def control(self, sender: Node, receiver: Node, key: TxKey, importance: int):
        duration = CONTROL_BITS / BIT_RATE
        queued_at = self.env.now
        with sender.radio.request(
            priority=self.radio_priority(importance)
        ) as request:
            yield request
            self.stats.record_radio_queue_wait(
                importance, self.env.now - queued_at
            )
            energy = sender.tx_power * duration
            sender.energy_j -= energy
            self.stats.record_tx(importance, CONTROL_BITS, energy, control=True)
            yield self.env.timeout(duration)
            yield self.env.timeout(math.hypot(sender.x - receiver.x, sender.y - receiver.y) / SOUND_SPEED)


# ---------------------------------------------------------------------------
# 3. Cancellable per-helper scheduler
# ---------------------------------------------------------------------------
@dataclass
class HelperJob:
    key: TxKey
    chain_id: int
    importance: int
    importance_aware: bool
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
        self.consecutive_important_services = 0
        self.env.process(self._worker())

    def submit(self, key: TxKey, ready_time: float, priority: float,
               action: Callable[[], simpy.events.Event], importance: int = IMPORTANCE_NORMAL,
               importance_aware: bool = False) -> HelperJob:
        self.sequence += 1
        job = HelperJob(
            key=key,
            chain_id=key.chain_id,
            importance=int(importance),
            importance_aware=bool(importance_aware),
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

            # Ageing prevents a long-waiting normal packet from being buried by
            # a stream of newly arrived important jobs.
            def effective_priority(item: HelperJob) -> float:
                waited = max(0.0, self.env.now - item.ready_time)
                ageing = min(QUEUE_AGING_CAP, QUEUE_AGING_RATE * waited)
                return item.priority + ageing

            aware_normal = [
                item for item in ready
                if item.importance_aware and item.importance == IMPORTANCE_NORMAL
            ]
            if (self.consecutive_important_services >= MAX_CONSECUTIVE_IMPORTANT_SERVICES
                    and aware_normal):
                job = min(aware_normal, key=lambda item: (item.ready_time, item.sequence))
            else:
                # Highest dynamic priority first, then deterministic FIFO.
                job = max(
                    ready,
                    key=lambda item: (
                        effective_priority(item),
                        -item.ready_time,
                        -item.sequence,
                    ),
                )
            self.pending.remove(job)
            if job.cancelled:
                continue
            self.active = job
            if self.last_chain_id is not None and self.last_chain_id != job.chain_id:
                self.stats.helper_cross_chain_services += 1
            self.last_chain_id = job.chain_id
            self.stats.record_helper_service(
                job.importance, self.env.now - job.ready_time
            )
            if job.importance_aware and job.importance == IMPORTANCE_HIGH:
                self.consecutive_important_services += 1
            elif job.importance_aware:
                self.consecutive_important_services = 0
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
# 4. Concurrent routes selected from a homogeneous sensor-node deployment
# ---------------------------------------------------------------------------
class Network:
    def __init__(self, env: simpy.Environment, protocol: str, snr_db: float,
                 sim_time: float, seed: int,
                 importance_ratio: float = DEFAULT_IMPORTANCE_RATIO,
                 important_deadline_s: float = IMPORTANT_DEADLINE_S,
                 topology: Optional[TopologyConfig] = None):
        if protocol not in PROTOCOLS:
            raise ValueError(f"unknown protocol: {protocol}")
        if not 0.0 <= importance_ratio <= 1.0:
            raise ValueError("importance_ratio must be between zero and one")
        if important_deadline_s <= 0.0:
            raise ValueError("important_deadline_s must be positive")
        self.env = env
        self.protocol = protocol
        self.snr_db = float(snr_db)
        self.sim_time = float(sim_time)
        self.seed = int(seed)
        self.importance_ratio = float(importance_ratio)
        self.important_deadline_s = float(important_deadline_s)
        self.topology = (topology or BASE_TOPOLOGY).validate()
        self.importance_aware = protocol == PROTO_CA
        self.stats = Stats(important_deadline_s=self.important_deadline_s)
        self.channel = AcousticChannel(
            env, snr_db, seed, self.stats,
            importance_aware=self.importance_aware,
            snr_reference_distance_m=(
                self.topology.snr_reference_distance_m
            ),
        )
        self.routers: Dict[Tuple[int, int], Node] = {}
        self.master_routers: Dict[Tuple[int, int], Node] = {}
        self.nodes_by_id: Dict[int, Node] = {}
        self.chain_offsets = self._chain_offsets()
        self.sink_position = (
            self.topology.deployment_hops * self.topology.spacing_m,
            0.0,
        )
        self.sink = Node(
            env, SINK_ID, self.sink_position[0],
            self.sink_position[1], "SINK",
        )
        self.nodes_by_id[SINK_ID] = self.sink
        self.helpers: List[HelperState] = []
        self.helpers_by_node_id: Dict[int, HelperState] = {}
        self.link_candidates: Dict[Tuple[int, int], List[HelperState]] = {}
        self._tx_counter: Dict[TxKey, int] = {}
        self._build_topology()

    def _chain_offsets(self) -> Tuple[float, ...]:
        count = self.topology.deployment_chains
        if count == 1:
            return (0.0,)
        half_span = self.topology.spacing_m
        return tuple(
            -half_span + 2.0 * half_span * index / (count - 1)
            for index in range(count)
        )

    def _route_position(self, chain_id: int, hop: int) -> Tuple[float, float]:
        spacing = self.topology.spacing_m
        x = hop * spacing
        offset = self.chain_offsets[chain_id]
        formation = self.topology.formation
        if formation == FORMATION_RECTANGULAR:
            y = offset
        elif formation == FORMATION_STAGGERED:
            direction = -1.0 if (chain_id + hop) % 2 else 1.0
            y = offset + direction * 0.10 * spacing
        elif formation == FORMATION_CONVERGING:
            progress = hop / self.topology.deployment_hops
            y = offset * (1.0 - progress)
        else:
            rng = stable_rng(self.seed, 0xF071, chain_id, hop)
            if hop > 0:
                x += float(rng.uniform(-0.08, 0.08)) * spacing
            y = offset + float(rng.uniform(-0.18, 0.18)) * spacing
        return float(x), float(y)

    def _candidate_position(
        self,
        index: int,
        links: Sequence[Tuple[Tuple[float, float], Tuple[float, float]]],
    ) -> Tuple[float, float]:
        """Place an off-route sensor according to the whole-network formation."""
        spacing = self.topology.spacing_m
        link_count = len(links)
        link_index = (index * 11) % link_count
        layer = index // link_count
        source, destination = links[link_index]
        delta_x = destination[0] - source[0]
        delta_y = destination[1] - source[1]
        length = max(math.hypot(delta_x, delta_y), 1.0)
        tangent = (delta_x / length, delta_y / length)
        normal = (-tangent[1], tangent[0])
        midpoint = (
            0.5 * (source[0] + destination[0]),
            0.5 * (source[1] + destination[1]),
        )
        sign = -1.0 if (link_index + layer) % 2 else 1.0
        formation = self.topology.formation
        if formation == FORMATION_RECTANGULAR:
            normal_offset = sign * (0.20 + 0.08 * (layer % 3)) * spacing
            tangent_offset = ((layer % 3) - 1) * 0.08 * spacing
        elif formation == FORMATION_STAGGERED:
            normal_offset = sign * (0.30 + 0.06 * (layer % 3)) * spacing
            tangent_offset = -sign * (0.10 + 0.04 * (layer % 2)) * spacing
        elif formation == FORMATION_CONVERGING:
            normal_offset = sign * (0.17 + 0.06 * (layer % 3)) * spacing
            tangent_offset = ((layer % 3) - 1) * 0.06 * spacing
        else:
            rng = stable_rng(self.seed, 0xC071, index)
            normal_offset = float(rng.uniform(-0.48, 0.48)) * spacing
            tangent_offset = float(rng.uniform(-0.32, 0.32)) * spacing
        return (
            midpoint[0] + tangent[0] * tangent_offset
            + normal[0] * normal_offset,
            midpoint[1] + tangent[1] * tangent_offset
            + normal[1] * normal_offset,
        )

    def _build_topology(self) -> None:
        # Build the master physical deployment once.  Route-count and hop-count
        # experiments select subsets of these same Node objects.
        for chain_id in range(self.topology.deployment_chains):
            for hop in range(self.topology.deployment_hops):
                x, y = self._route_position(chain_id, hop)
                node_id = chain_id * 100 + hop
                node = Node(
                    self.env, node_id, x, y, "SENSOR"
                )
                self.master_routers[(chain_id, hop)] = node
                self.nodes_by_id[node_id] = node

        links: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        for chain_id in range(self.topology.deployment_chains):
            for hop in range(self.topology.deployment_hops):
                source_node = self.master_routers[(chain_id, hop)]
                destination_node = (
                    self.sink
                    if hop == self.topology.deployment_hops - 1
                    else self.master_routers[(chain_id, hop + 1)]
                )
                links.append((
                    (source_node.x, source_node.y),
                    (destination_node.x, destination_node.y),
                ))

        positions = [
            self._candidate_position(index, links)
            for index in range(self.topology.extra_node_count)
        ]

        for index, (x, y) in enumerate(positions):
            node = Node(self.env, 1000 + index, x, y, "SENSOR")
            self.nodes_by_id[node.node_id] = node

        # Every non-sink device is a homogeneous sensor and receives one
        # physical helper scheduler.  A route node can therefore assist another
        # route whenever its own radio queue permits.
        for node_id, node in sorted(self.nodes_by_id.items()):
            if node_id == SINK_ID:
                continue
            helper = HelperState(
                node=node,
                scheduler=HelperScheduler(self.env, node.node_id, self.stats),
            )
            self.helpers.append(helper)
            self.helpers_by_node_id[node_id] = helper

        # Map local traffic-chain and hop indices onto the selected suffixes of
        # the fixed master deployment.
        for local_chain_id, master_chain_id in enumerate(
            self.topology.active_chain_ids
        ):
            for local_hop in range(self.topology.num_hops):
                master_hop = self.topology.active_hop_start + local_hop
                self.routers[(local_chain_id, local_hop)] = (
                    self.master_routers[(master_chain_id, master_hop)]
                )

        for chain_id in range(self.topology.num_chains):
            for hop in range(self.topology.num_hops):
                source_node = self.routers[(chain_id, hop)]
                destination_node = (
                    self.sink
                    if hop == self.topology.num_hops - 1
                    else self.routers[(chain_id, hop + 1)]
                )
                source = (source_node.x, source_node.y)
                destination = (destination_node.x, destination_node.y)
                ranked = sorted(
                    (
                        helper for helper in self.helpers
                        if helper.node.node_id not in {
                            source_node.node_id,
                            destination_node.node_id,
                        }
                    ),
                    key=lambda helper: max(
                        math.hypot(
                            helper.node.x - source[0],
                            helper.node.y - source[1],
                        ),
                        math.hypot(
                            helper.node.x - destination[0],
                            helper.node.y - destination[1],
                        ),
                    ),
                )[:self.topology.candidates_per_link]
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

    def packet_importance(self, chain_id: int, pid: int) -> int:
        """Protocol-independent, reproducible application priority assignment."""
        rng = stable_rng(self.seed, 0x1A17, chain_id, pid)
        return (
            IMPORTANCE_HIGH
            if float(rng.random()) < self.importance_ratio
            else IMPORTANCE_NORMAL
        )

    def _destination(self, chain_id: int, hop: int) -> Node:
        return (
            self.sink
            if hop == self.topology.num_hops - 1
            else self.routers[(chain_id, hop + 1)]
        )

    def _decode(self, buffer: SoftBuffer, message: Sequence[int]) -> bool:
        if self.protocol in (PROTO_SW_ARQ, PROTO_CARQ):
            return buffer.decode_uncoded(message)
        return buffer.decode_rs(message)

    def _source_transmission(self, source: Node, destination: Node,
                             candidates: Sequence[HelperState], dest_buffer: SoftBuffer,
                             helper_buffers: Dict[int, SoftBuffer], codeword: Sequence[int],
                             positions: Sequence[int], key: TxKey, importance: int):
        receptions = [Reception(destination, dest_buffer, "dest")]
        if self.protocol != PROTO_SW_ARQ:
            receptions.extend(
                Reception(helper.node, helper_buffers[helper.node.node_id], "helper")
                for helper in candidates
            )
        yield self.env.process(self.channel.broadcast(
            source, receptions, codeword, positions, key, self.next_tx_index(key),
            importance,
        ))

    def _helper_transmission(self, helper: HelperState, destination: Node,
                             dest_buffer: SoftBuffer, codeword: Sequence[int],
                             positions: Sequence[int], key: TxKey, message: Sequence[int],
                             importance: int):
        yield self.env.process(self.channel.broadcast(
            helper.node,
            [Reception(destination, dest_buffer, "dest")],
            codeword,
            positions,
            key,
            self.next_tx_index(key),
            importance,
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
                            positions: Sequence[int], key: TxKey, message: Sequence[int],
                            importance: int):
        # Fixed baselines use the best-ranked decoded helper and the same scheduler.
        def action():
            return self._helper_transmission(
                helper, destination, dest_buffer, codeword, positions, key, message,
                importance,
            )

        job = helper.scheduler.submit(
            key, self.env.now, 1.0, action, importance=importance
        )
        result = yield job.done
        return bool(result)

    def _ca_backoff(self, helper: HelperState, rank: int, key: TxKey,
                    helper_buffer: SoftBuffer, cpkt: int,
                    importance: int) -> Tuple[float, float]:
        confidence = helper_buffer.confidence() / 3.0
        energy = max(0.0, min(1.0, helper.node.energy_j / INITIAL_ENERGY_J))
        source = self._node_by_id(key.hop_src)
        destination = self._node_by_id(key.hop_dst)
        bottleneck = max(
            math.hypot(helper.node.x - source.x, helper.node.y - source.y),
            math.hypot(helper.node.x - destination.x, helper.node.y - destination.y),
        )
        delay_score = 1.0 / (
            1.0 + bottleneck / self.topology.spacing_m
        )
        score = 0.40 * confidence + 0.25 * energy + 0.35 * delay_score
        rng = stable_rng(self.seed, 0xCA, key.chain_id, key.pid, key.hop_src,
                         helper.node.node_id, cpkt, importance)
        jitter = float(rng.uniform(0.0, T_BACKOFF_JITTER))
        backoff = max(T_PROTECTION_GAP, (1.0 - score) * T_MAX_WINDOW)
        if importance == IMPORTANCE_HIGH:
            backoff = max(
                T_PROTECTION_GAP,
                backoff * (1.0 - IMPORTANT_BACKOFF_REDUCTION),
            )
        backoff += rank * 0.006 + jitter
        # Reliability urgency, application importance and helper quality jointly
        # determine queue service.  Ageing is added dynamically by the scheduler.
        priority = (
            0.42 * (1.0 - cpkt / 3.0)
            + 0.33 * score
            + 0.25 * float(importance)
        )
        return backoff, priority

    def _node_by_id(self, node_id: int) -> Node:
        return self.nodes_by_id[node_id]

    def _ca_contender(self, helper: HelperState, rank: int, destination: Node,
                      dest_buffer: SoftBuffer, helper_buffer: SoftBuffer,
                      codeword: Sequence[int], positions: Sequence[int], key: TxKey,
                      message: Sequence[int], cpkt: int,
                      traffic_importance: int, policy_importance: int,
                      ack_event: simpy.Event, backoff: float,
                      priority: float):
        yield self.env.timeout(backoff)
        if ack_event.triggered:
            return False

        def action():
            return self._helper_transmission(
                helper, destination, dest_buffer, codeword, positions, key, message,
                traffic_importance,
            )

        job = helper.scheduler.submit(
            key, self.env.now, priority, action,
            importance=traffic_importance,
            importance_aware=self.importance_aware,
        )
        result = yield job.done | ack_event
        if job.done in result and bool(result[job.done]) and not ack_event.triggered:
            ack_event.succeed(helper.node.node_id)
            return True
        return False

    def _ca_helper_round(self, helpers: Sequence[HelperState], candidates: Sequence[HelperState],
                         destination: Node, dest_buffer: SoftBuffer,
                         helper_buffers: Dict[int, SoftBuffer], codeword: Sequence[int],
                         positions: Sequence[int], key: TxKey, message: Sequence[int],
                         cpkt: int, traffic_importance: int,
                         policy_importance: int):
        ack_event = self.env.event()
        contender_events = []
        offers = []
        for helper in helpers:
            rank = candidates.index(helper)
            backoff, priority = self._ca_backoff(
                helper, rank, key, helper_buffers[helper.node.node_id],
                cpkt, policy_importance,
            )
            offers.append((backoff, helper.node.node_id, priority, helper, rank))
        offers.sort(key=lambda item: (item[0], item[1]))
        first_backoff = offers[0][0]
        # One contention slot covers the longest contender-to-destination
        # propagation and the current redundancy burst.  This makes timer
        # suppression effective in a long-delay acoustic channel: the next
        # ranked helper transmits only if no earlier attempt has restored the
        # packet.  Candidate quality still determines the ordering.
        transmission_duration = (
            len(positions) * RS_BITS_PER_SYMBOL + IMPORTANCE_SIGNAL_BITS
        ) / BIT_RATE
        contention_slot = max(
            math.hypot(
                helper.node.x - destination.x,
                helper.node.y - destination.y,
            ) / SOUND_SPEED
            for helper in helpers
        ) + transmission_duration + T_PROTECTION_GAP
        for order, (_, _, priority, helper, rank) in enumerate(offers):
            scheduled_backoff = first_backoff + order * contention_slot
            contender_events.append(self.env.process(self._ca_contender(
                helper, rank, destination, dest_buffer,
                helper_buffers[helper.node.node_id], codeword, positions,
                key, message, cpkt, traffic_importance, policy_importance,
                ack_event, scheduled_backoff, priority,
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
    def _ca_positions(dest_buffer: SoftBuffer, cpkt: int,
                      importance: int) -> Tuple[int, ...]:
        if importance == IMPORTANCE_HIGH:
            # Important packets favour one strong recovery opportunity over
            # another long underwater feedback cycle.
            return FULL_CODE_POSITIONS
        missing_blocks = [
            RV_POSITIONS[index] for index in (1, 2)
            if not all(dest_buffer.seen[p] for p in RV_POSITIONS[index])
        ]
        if cpkt >= 3 and missing_blocks:
            return tuple(missing_blocks[0])
        if cpkt == 2 and missing_blocks:
            # Medium confidence is handled by completing the parity set before
            # repeating information symbols.  Important packets bypass this
            # cost-saving step and request a full Chase opportunity.
            return tuple(p for block in missing_blocks for p in block)
        if cpkt <= 1:
            # Low confidence: one full mother-code transmission supplies all
            # missing parity and Chase-combines already received data symbols.
            return FULL_CODE_POSITIONS
        return RV_POSITIONS[0]

    def _initial_positions(self, importance: int) -> Tuple[int, ...]:
        if self.protocol in (PROTO_SW_ARQ, PROTO_CARQ):
            return UNCODED_POSITIONS
        if self.protocol == PROTO_CA and importance == IMPORTANCE_HIGH:
            return FULL_CODE_POSITIONS
        return RV_POSITIONS[0]

    def deliver_hop(self, packet: PacketContext, hop: int):
        source = self.routers[(packet.chain_id, hop)]
        destination = self._destination(packet.chain_id, hop)
        key = TxKey(
            packet.chain_id, packet.pid, source.node_id, destination.node_id
        )
        candidates = self.link_candidates[(packet.chain_id, hop)]
        dest_buffer = SoftBuffer()
        helper_buffers = {helper.node.node_id: SoftBuffer() for helper in candidates}
        charq_retransmission_index = 0
        retry_limit = MAX_RETRIES + (
            IMPORTANT_EXTRA_RETRIES
            if self.importance_aware
            and packet.importance == IMPORTANCE_HIGH
            else 0
        )

        for attempt in range(retry_limit + 1):
            if attempt == 0:
                positions = self._initial_positions(packet.importance)
                yield self.env.process(self._source_transmission(
                    source, destination, candidates, dest_buffer, helper_buffers,
                    packet.codeword, positions, key, packet.importance,
                ))
            else:
                decoded_helpers = self._decoded_helpers(
                    candidates, helper_buffers, packet.message
                )
                # Important CA traffic uses a local recovery NACK when a decoded
                # helper is already available.  The nearest decoded helper is
                # activated first; the source is contacted only when local
                # recovery is unavailable.  This removes part of the long
                # underwater feedback path without adding a control frame.
                feedback_receiver = source
                if (self.importance_aware
                        and packet.importance == IMPORTANCE_HIGH
                        and decoded_helpers):
                    feedback_receiver = min(
                        decoded_helpers,
                        key=lambda helper: math.hypot(
                            helper.node.x - destination.x,
                            helper.node.y - destination.y,
                        ),
                    ).node
                yield self.env.process(self.channel.control(
                    destination, feedback_receiver, key, packet.importance
                ))

                if self.protocol == PROTO_SW_ARQ:
                    positions = UNCODED_POSITIONS
                    yield self.env.process(self._source_transmission(
                        source, destination, (), dest_buffer, helper_buffers,
                        packet.codeword, positions, key, packet.importance,
                    ))
                elif self.protocol == PROTO_CARQ:
                    positions = UNCODED_POSITIONS
                    if decoded_helpers:
                        yield self.env.process(self._fixed_helper_round(
                            decoded_helpers[0], destination, dest_buffer,
                            packet.codeword, positions, key, packet.message,
                            packet.importance,
                        ))
                    else:
                        yield self.env.process(self._source_transmission(
                            source, destination, candidates, dest_buffer, helper_buffers,
                            packet.codeword, positions, key, packet.importance,
                        ))
                elif self.protocol == PROTO_CHARQ:
                    charq_retransmission_index += 1
                    positions = self._charq_positions(charq_retransmission_index)
                    if decoded_helpers:
                        yield self.env.process(self._fixed_helper_round(
                            decoded_helpers[0], destination, dest_buffer,
                            packet.codeword, positions, key, packet.message,
                            packet.importance,
                        ))
                    else:
                        yield self.env.process(self._source_transmission(
                            source, destination, candidates, dest_buffer, helper_buffers,
                            packet.codeword, positions, key, packet.importance,
                        ))
                else:
                    cpkt = dest_buffer.confidence()
                    policy_importance = (
                        packet.importance
                        if self.importance_aware
                        else IMPORTANCE_NORMAL
                    )
                    positions = self._ca_positions(
                        dest_buffer, cpkt, policy_importance
                    )
                    if decoded_helpers:
                        yield self.env.process(self._ca_helper_round(
                            decoded_helpers, candidates, destination, dest_buffer,
                            helper_buffers, packet.codeword, positions, key,
                            packet.message, cpkt, packet.importance,
                            policy_importance,
                        ))
                    else:
                        yield self.env.process(self._source_transmission(
                            source, destination, candidates, dest_buffer, helper_buffers,
                            packet.codeword, positions, key, packet.importance,
                        ))

            if self._decode(dest_buffer, packet.message):
                for helper in candidates:
                    helper.scheduler.cancel(key)
                yield self.env.process(self.channel.control(
                    destination, source, key, packet.importance
                ))
                return True
        for helper in candidates:
            helper.scheduler.cancel(key)
        return False

    def deliver_packet(self, chain_id: int, pid: int, creation_time: float):
        message = self.payload(chain_id, pid)
        packet = PacketContext(
            chain_id=chain_id,
            pid=pid,
            creation_time=float(creation_time),
            importance=self.packet_importance(chain_id, pid),
            message=message,
            codeword=CODEC.encode(message),
        )
        for hop in range(self.topology.num_hops):
            ok = yield self.env.process(self.deliver_hop(
                packet, hop
            ))
            if not ok:
                self.stats.packet_drop(packet.importance)
                return
        self.stats.packet_success(
            packet.importance,
            self.env.now - packet.creation_time,
            self.important_deadline_s,
        )

    def traffic_generator(self, chain_id: int):
        rng = stable_rng(self.seed, 0xA771, chain_id)
        pid = 0
        while True:
            creation = self.env.now
            importance = self.packet_importance(chain_id, pid)
            self.stats.packet_generated(importance)
            self.env.process(self.deliver_packet(chain_id, pid, creation))
            pid += 1
            yield self.env.timeout(float(rng.exponential(TRAFFIC_MEAN_S)))

    def start(self) -> None:
        for chain_id in range(self.topology.num_chains):
            self.env.process(self.traffic_generator(chain_id))


# ---------------------------------------------------------------------------
# 5. Simulation, aggregation and reproducible output
# ---------------------------------------------------------------------------
def run_sim(snr_db: float, protocol: str, sim_time: float, seed: int = 0,
            importance_ratio: float = DEFAULT_IMPORTANCE_RATIO,
            important_deadline_s: float = IMPORTANT_DEADLINE_S,
            topology: Optional[TopologyConfig] = None) -> Dict[str, float]:
    topology_config = (topology or BASE_TOPOLOGY).validate()
    env = simpy.Environment()
    network = Network(
        env, protocol, snr_db, sim_time, seed,
        importance_ratio=importance_ratio,
        important_deadline_s=important_deadline_s,
        topology=topology_config,
    )
    network.start()
    env.run(until=sim_time)
    result = network.stats.summary()
    result["goodput_bps"] = result["successes"] * INFO_BITS / sim_time
    for label in IMPORTANCE_LABELS.values():
        result[f"{label}_goodput_bps"] = (
            result[f"{label}_successes"] * INFO_BITS / sim_time
        )
    result.update({
        "snr_db": float(snr_db),
        "protocol": protocol,
        "sim_time": float(sim_time),
        "seed": int(seed),
        "importance_ratio": float(importance_ratio),
        "important_deadline_s": float(important_deadline_s),
        "total_nodes": int(topology_config.total_nodes),
        "spacing_m": float(topology_config.spacing_m),
        "formation": topology_config.formation,
        "num_chains": int(topology_config.num_chains),
        "num_hops": int(topology_config.num_hops),
        "deployment_chains": int(topology_config.deployment_chains),
        "deployment_hops": int(topology_config.deployment_hops),
        "active_chain_indices": ",".join(
            str(value) for value in topology_config.active_chain_ids
        ),
        "active_hop_start": int(topology_config.active_hop_start),
        "cooperative_nodes": int(topology_config.cooperative_node_count),
        "extra_nodes": int(topology_config.extra_node_count),
        "candidates_per_link": int(topology_config.candidates_per_link),
        "snr_reference_distance_m": float(
            topology_config.snr_reference_distance_m
        ),
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
    metrics = [
        "delay", "delay_p95", "delivery_penalized_delay", "pdr",
        "overhead", "energy_efficiency", "tx_bits_per_generated",
        "energy_per_generated", "goodput_bps", "successes",
        "collisions", "helper_services", "helper_cross_chain_services",
        "cancelled_helper_jobs",
    ]
    for label in IMPORTANCE_LABELS.values():
        metrics.extend([
            f"{label}_delay",
            f"{label}_delay_p95",
            f"{label}_delivery_penalized_delay",
            f"{label}_on_time_pdr",
            f"{label}_pdr",
            f"{label}_overhead",
            f"{label}_energy_efficiency",
            f"{label}_successes",
            f"{label}_drops",
            f"{label}_generated",
            f"{label}_collisions",
            f"{label}_helper_services",
            f"{label}_queue_wait",
            f"{label}_radio_queue_wait",
            f"{label}_tx_bits_per_generated",
            f"{label}_energy_per_generated",
            f"{label}_goodput_bps",
        ])
    metrics.append("important_deadline_miss_rate")
    delta_metrics = (
        "important_on_time_gain_pp",
        "important_pdr_gain_pp",
        "important_mean_delay_reduction_pct",
        "important_p95_reduction_pct",
        "overhead_reduction_pct",
        "normal_pdr_change_pp",
        "normal_p95_change_pct",
    )
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
            for metric in delta_metrics:
                entry[f"{metric}_mean"] = float("nan")
                entry[f"{metric}_ci95"] = float("nan")
            output.append(entry)

    entries = {
        (str(entry["protocol"]), float(entry["snr_db"])): entry
        for entry in output
    }
    paired_snrs = sorted(
        snr for protocol, snr in grouped
        if protocol == PROTO_CA
        and (PROTO_CA_BASE, snr) in grouped
    )
    for snr in paired_snrs:
        base_by_seed = {
            int(row["seed"]): row for row in grouped[(PROTO_CA_BASE, snr)]
        }
        aware_by_seed = {
            int(row["seed"]): row for row in grouped[(PROTO_CA, snr)]
        }
        seeds = sorted(set(base_by_seed) & set(aware_by_seed))
        paired_values: Dict[str, List[float]] = {
            metric: [] for metric in delta_metrics
        }
        for seed in seeds:
            base = base_by_seed[seed]
            aware = aware_by_seed[seed]
            paired_values["important_on_time_gain_pp"].append(
                100.0 * (
                    float(aware["important_on_time_pdr"])
                    - float(base["important_on_time_pdr"])
                )
            )
            paired_values["important_pdr_gain_pp"].append(
                100.0 * (
                    float(aware["important_pdr"])
                    - float(base["important_pdr"])
                )
            )
            base_mean_delay = float(base["important_delay"])
            aware_mean_delay = float(aware["important_delay"])
            paired_values["important_mean_delay_reduction_pct"].append(
                100.0 * (
                    base_mean_delay - aware_mean_delay
                ) / base_mean_delay
                if math.isfinite(base_mean_delay) and base_mean_delay > 0.0
                and math.isfinite(aware_mean_delay) else float("nan")
            )
            base_p95 = float(base["important_delay_p95"])
            aware_p95 = float(aware["important_delay_p95"])
            paired_values["important_p95_reduction_pct"].append(
                100.0 * (base_p95 - aware_p95) / base_p95
                if math.isfinite(base_p95) and base_p95 > 0.0
                and math.isfinite(aware_p95) else float("nan")
            )
            base_overhead = float(base["overhead"])
            paired_values["overhead_reduction_pct"].append(
                100.0 * (
                    base_overhead - float(aware["overhead"])
                ) / base_overhead
                if math.isfinite(base_overhead) and base_overhead > 0.0
                else float("nan")
            )
            paired_values["normal_pdr_change_pp"].append(
                100.0 * (
                    float(aware["normal_pdr"])
                    - float(base["normal_pdr"])
                )
            )
            base_normal_p95 = float(base["normal_delay_p95"])
            aware_normal_p95 = float(aware["normal_delay_p95"])
            paired_values["normal_p95_change_pct"].append(
                100.0 * (
                    aware_normal_p95 - base_normal_p95
                ) / base_normal_p95
                if math.isfinite(base_normal_p95) and base_normal_p95 > 0.0
                and math.isfinite(aware_normal_p95) else float("nan")
            )
        entry = entries[(PROTO_CA, snr)]
        for metric, values in paired_values.items():
            entry[f"{metric}_mean"] = finite_mean(values)
            entry[f"{metric}_ci95"] = ci95(values)
    return output


def _run_task(args: Tuple[object, ...]) -> Dict[str, float]:
    return run_sim(*args)


def run_sweep(snrs: Sequence[float], protocols: Sequence[str], sim_time: float,
              seeds: Sequence[int], importance_ratio: float,
              important_deadline_s: float, jobs: int = 1,
              topology: Optional[TopologyConfig] = None) -> List[Dict[str, float]]:
    topology_config = (topology or BASE_TOPOLOGY).validate()
    tasks = [
        (
            float(snr), proto, float(sim_time), int(seed),
            float(importance_ratio), float(important_deadline_s),
            topology_config,
        )
             for proto in protocols for snr in snrs for seed in seeds]
    if jobs <= 1:
        return [_run_task(task) for task in tasks]
    rows: List[Dict[str, float]] = []
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        future_map = {pool.submit(_run_task, task): task for task in tasks}
        for future in as_completed(future_map):
            rows.append(future.result())
    return rows


TOPOLOGY_FACTORS = (
    "node_scale",
    "spacing",
    "formation",
    "path_count",
    "hop_count",
)
PAPER_TOPOLOGY_FACTORS = (
    "node_scale",
    "spacing",
    "path_count",
    "hop_count",
)
TOPOLOGY_FACTOR_LABELS = {
    "node_scale": "Total deployed nodes",
    "spacing": "Nominal inter-node spacing (m)",
    "formation": "Whole-network formation",
    "path_count": "Selected end-to-end paths",
    "hop_count": "Hops per selected path",
}
TOPOLOGY_FIGURE_TITLES = {
    "node_scale": "Protocol sensitivity to total network size",
    "spacing": "Protocol sensitivity to inter-node spacing",
    "formation": "Protocol sensitivity to whole-network formation",
    "path_count": "Protocol sensitivity to concurrent selected paths",
    "hop_count": "Protocol sensitivity to path hop count",
}


@dataclass(frozen=True)
class TopologyScenario:
    factor: str
    level_index: int
    level_value: float
    level_label: str
    config: TopologyConfig

    @property
    def scenario_id(self) -> str:
        return f"{self.factor}:{self.level_label}"


def topology_scenarios(
    factors: Optional[Sequence[str]] = None,
) -> List[TopologyScenario]:
    selected = set(factors or TOPOLOGY_FACTORS)
    unknown = selected.difference(TOPOLOGY_FACTORS)
    if unknown:
        raise ValueError(f"unknown topology factors: {sorted(unknown)}")
    scenarios: List[TopologyScenario] = []

    def add(
        factor: str,
        level_value: float,
        level_label: str,
        config: TopologyConfig,
    ) -> None:
        if factor not in selected:
            return
        level_index = sum(1 for item in scenarios if item.factor == factor)
        scenarios.append(TopologyScenario(
            factor=factor,
            level_index=level_index,
            level_value=float(level_value),
            level_label=str(level_label),
            config=config.validate(),
        ))

    for total_nodes in (21, 31, 41, 51):
        add(
            "node_scale", total_nodes, str(total_nodes),
            replace(BASE_TOPOLOGY, total_nodes=total_nodes),
        )
    for spacing_m in (400.0, 500.0, 600.0, 700.0, 800.0):
        add(
            "spacing", spacing_m, f"{spacing_m:g}",
            replace(BASE_TOPOLOGY, spacing_m=spacing_m),
        )
    for formation_index, formation in enumerate(FORMATIONS):
        add(
            "formation", formation_index, FORMATION_LABELS[formation],
            replace(BASE_TOPOLOGY, formation=formation),
        )
    path_activation = {
        1: (2,),
        3: (1, 2, 3),
        5: (0, 1, 2, 3, 4),
    }
    for path_count, active_chains in path_activation.items():
        add(
            "path_count", path_count, str(path_count),
            replace(
                BASE_TOPOLOGY,
                total_nodes=41,
                num_chains=path_count,
                deployment_chains=5,
                active_chain_indices=active_chains,
            ),
        )
    for hop_count in (3, 4, 5, 6, 7):
        add(
            "hop_count", hop_count, str(hop_count),
            replace(
                BASE_TOPOLOGY,
                total_nodes=37,
                num_hops=hop_count,
                deployment_hops=7,
                active_hop_start=7 - hop_count,
            ),
        )
    return scenarios


def _run_topology_task(args: Tuple[object, ...]) -> Dict[str, float]:
    (
        scenario, snr_db, protocol, sim_time, seed,
        importance_ratio, important_deadline_s,
    ) = args
    if not isinstance(scenario, TopologyScenario):
        raise TypeError("topology task requires a TopologyScenario")
    result = run_sim(
        float(snr_db), str(protocol), float(sim_time), int(seed),
        float(importance_ratio), float(important_deadline_s),
        scenario.config,
    )
    result.update({
        "factor": scenario.factor,
        "scenario_id": scenario.scenario_id,
        "level_index": int(scenario.level_index),
        "level_value": float(scenario.level_value),
        "level_label": scenario.level_label,
    })
    return result


def run_topology_sweep(
    scenarios: Sequence[TopologyScenario],
    protocols: Sequence[str],
    snr_db: float,
    sim_time: float,
    seeds: Sequence[int],
    importance_ratio: float,
    important_deadline_s: float,
    jobs: int = 1,
) -> List[Dict[str, float]]:
    tasks = [
        (
            scenario, float(snr_db), protocol, float(sim_time), int(seed),
            float(importance_ratio), float(important_deadline_s),
        )
        for scenario in scenarios
        for protocol in protocols
        for seed in seeds
    ]
    if jobs <= 1:
        return [_run_topology_task(task) for task in tasks]
    rows: List[Dict[str, float]] = []
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        future_map = {
            pool.submit(_run_topology_task, task): task for task in tasks
        }
        for future in as_completed(future_map):
            rows.append(future.result())
    return rows


TOPOLOGY_METRICS = (
    "delay",
    "delay_p95",
    "delivery_penalized_delay",
    "pdr",
    "overhead",
    "energy_efficiency",
    "tx_bits_per_generated",
    "energy_per_generated",
    "goodput_bps",
    "collisions",
    "important_delay",
    "important_delay_p95",
    "important_delivery_penalized_delay",
    "important_on_time_pdr",
    "important_pdr",
    "important_goodput_bps",
    "important_tx_bits_per_generated",
    "important_energy_per_generated",
    "normal_delay",
    "normal_delay_p95",
    "normal_delivery_penalized_delay",
    "normal_pdr",
    "normal_goodput_bps",
)
TOPOLOGY_DELTA_METRICS = (
    "important_on_time_gain_pp",
    "important_pdr_gain_pp",
    "important_mean_delay_reduction_pct",
    "important_p95_reduction_pct",
    "overhead_reduction_pct",
    "normal_pdr_change_pp",
    "overall_delay_reduction_vs_charq_pct",
    "important_on_time_gain_vs_charq_pp",
)


def topology_paired_deltas(
    aware: Dict[str, float],
    base: Dict[str, float],
    charq: Dict[str, float],
) -> Dict[str, float]:
    def reduction(base_value: object, aware_value: object) -> float:
        denominator = float(base_value)
        numerator = float(aware_value)
        if (
            not math.isfinite(denominator)
            or denominator <= 0.0
            or not math.isfinite(numerator)
        ):
            return float("nan")
        return 100.0 * (denominator - numerator) / denominator

    return {
        "important_on_time_gain_pp": 100.0 * (
            float(aware["important_on_time_pdr"])
            - float(base["important_on_time_pdr"])
        ),
        "important_pdr_gain_pp": 100.0 * (
            float(aware["important_pdr"])
            - float(base["important_pdr"])
        ),
        "important_mean_delay_reduction_pct": reduction(
            base["important_delay"], aware["important_delay"]
        ),
        "important_p95_reduction_pct": reduction(
            base["important_delay_p95"], aware["important_delay_p95"]
        ),
        "overhead_reduction_pct": reduction(
            base["overhead"], aware["overhead"]
        ),
        "normal_pdr_change_pp": 100.0 * (
            float(aware["normal_pdr"]) - float(base["normal_pdr"])
        ),
        "overall_delay_reduction_vs_charq_pct": reduction(
            charq["delay"], aware["delay"]
        ),
        "important_on_time_gain_vs_charq_pp": 100.0 * (
            float(aware["important_on_time_pdr"])
            - float(charq["important_on_time_pdr"])
        ),
    }


def aggregate_topology_results(
    raw: Sequence[Dict[str, float]],
) -> List[Dict[str, float]]:
    has_ablation = any(
        str(row["protocol"]) == PROTO_CA_BASE for row in raw
    )
    grouped: Dict[
        Tuple[str, int, str, str], List[Dict[str, float]]
    ] = {}
    for row in raw:
        key = (
            str(row["factor"]),
            int(row["level_index"]),
            str(row["level_label"]),
            str(row["protocol"]),
        )
        grouped.setdefault(key, []).append(row)

    output: List[Dict[str, float]] = []
    for factor in TOPOLOGY_FACTORS:
        factor_keys = sorted(
            (
                key for key in grouped if key[0] == factor
            ),
            key=lambda key: (key[1], PROTOCOLS.index(key[3])),
        )
        for key in factor_keys:
            _, level_index, level_label, protocol = key
            rows = grouped[key]
            first = rows[0]
            entry: Dict[str, float] = {
                "factor": factor,
                "level_index": float(level_index),
                "level_value": float(first["level_value"]),
                "level_label": level_label,
                "protocol": protocol,
                "snr_db": float(first["snr_db"]),
                "n_runs": float(len(rows)),
                "total_nodes": float(first["total_nodes"]),
                "spacing_m": float(first["spacing_m"]),
                "formation": str(first["formation"]),
                "num_chains": float(first["num_chains"]),
                "num_hops": float(first["num_hops"]),
                "deployment_chains": float(first["deployment_chains"]),
                "deployment_hops": float(first["deployment_hops"]),
                "active_chain_indices": str(first["active_chain_indices"]),
                "active_hop_start": float(first["active_hop_start"]),
                "cooperative_nodes": float(first["cooperative_nodes"]),
                "extra_nodes": float(first["extra_nodes"]),
            }
            for metric in TOPOLOGY_METRICS:
                values = [float(row[metric]) for row in rows]
                entry[f"{metric}_mean"] = finite_mean(values)
                entry[f"{metric}_ci95"] = ci95(values)
            if has_ablation:
                for metric in TOPOLOGY_DELTA_METRICS:
                    entry[f"{metric}_mean"] = float("nan")
                    entry[f"{metric}_ci95"] = float("nan")
            output.append(entry)

    entries = {
        (
            str(entry["factor"]),
            int(entry["level_index"]),
            str(entry["protocol"]),
        ): entry
        for entry in output
    }
    raw_groups: Dict[
        Tuple[str, int, str], Dict[int, Dict[str, float]]
    ] = {}
    for row in raw:
        key = (
            str(row["factor"]),
            int(row["level_index"]),
            str(row["protocol"]),
        )
        raw_groups.setdefault(key, {})[int(row["seed"])] = row
    for factor in (TOPOLOGY_FACTORS if has_ablation else ()):
        level_indices = sorted({
            level_index
            for item_factor, level_index, protocol in raw_groups
            if item_factor == factor and protocol == PROTO_CA
        })
        for level_index in level_indices:
            aware_by_seed = raw_groups.get(
                (factor, level_index, PROTO_CA), {}
            )
            base_by_seed = raw_groups.get(
                (factor, level_index, PROTO_CA_BASE), {}
            )
            charq_by_seed = raw_groups.get(
                (factor, level_index, PROTO_CHARQ), {}
            )
            seeds = sorted(
                set(aware_by_seed)
                & set(base_by_seed)
                & set(charq_by_seed)
            )
            paired = {
                metric: [] for metric in TOPOLOGY_DELTA_METRICS
            }
            for seed in seeds:
                deltas = topology_paired_deltas(
                    aware_by_seed[seed],
                    base_by_seed[seed],
                    charq_by_seed[seed],
                )
                for metric, value in deltas.items():
                    paired[metric].append(value)
            entry = entries[(factor, level_index, PROTO_CA)]
            for metric, values in paired.items():
                entry[f"{metric}_mean"] = finite_mean(values)
                entry[f"{metric}_ci95"] = ci95(values)
    return output


def aggregate_topology_robustness(
    raw: Sequence[Dict[str, float]],
) -> List[Dict[str, float]]:
    grouped: Dict[
        Tuple[str, int, str], Dict[int, Dict[str, float]]
    ] = {}
    for row in raw:
        key = (
            str(row["factor"]),
            int(row["level_index"]),
            str(row["protocol"]),
        )
        grouped.setdefault(key, {})[int(row["seed"])] = row
    output: List[Dict[str, float]] = []
    for factor_index, factor in enumerate(TOPOLOGY_FACTORS):
        paired = {
            metric: [] for metric in TOPOLOGY_DELTA_METRICS
        }
        levels = sorted({
            level
            for item_factor, level, protocol in grouped
            if item_factor == factor and protocol == PROTO_CA
        })
        for level in levels:
            aware_by_seed = grouped.get((factor, level, PROTO_CA), {})
            base_by_seed = grouped.get((factor, level, PROTO_CA_BASE), {})
            charq_by_seed = grouped.get((factor, level, PROTO_CHARQ), {})
            seeds = sorted(
                set(aware_by_seed)
                & set(base_by_seed)
                & set(charq_by_seed)
            )
            for seed in seeds:
                deltas = topology_paired_deltas(
                    aware_by_seed[seed],
                    base_by_seed[seed],
                    charq_by_seed[seed],
                )
                for metric, value in deltas.items():
                    paired[metric].append(value)
        entry: Dict[str, float] = {
            "protocol": "CA-CHARQ paired advantage",
            "factor": factor,
            "factor_index": float(factor_index),
            "factor_label": TOPOLOGY_FACTOR_LABELS[factor],
            "n_pairs": float(len(paired[TOPOLOGY_DELTA_METRICS[0]])),
        }
        for metric, values in paired.items():
            entry[f"{metric}_mean"] = finite_mean(values)
            entry[f"{metric}_ci95"] = ci95(values)
        output.append(entry)
    return output


def write_topology_results(
    raw: Sequence[Dict[str, float]],
    summary: Sequence[Dict[str, float]],
    output_dir: Path,
) -> List[Dict[str, float]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    factor_rank = {
        factor: index for index, factor in enumerate(TOPOLOGY_FACTORS)
    }
    raw_sorted = sorted(
        raw,
        key=lambda row: (
            factor_rank[str(row["factor"])],
            int(row["level_index"]),
            PROTOCOLS.index(str(row["protocol"])),
            int(row["seed"]),
        ),
    )
    with (output_dir / "topology_raw_results.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(raw_sorted[0].keys()))
        writer.writeheader()
        writer.writerows(raw_sorted)
    with (output_dir / "topology_summary_results.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
    has_ablation = any(
        str(row["protocol"]) == PROTO_CA_BASE for row in raw
    )
    robustness = aggregate_topology_robustness(raw) if has_ablation else []
    robustness_path = output_dir / "topology_robustness_summary.csv"
    if robustness:
        with robustness_path.open(
            "w", newline="", encoding="utf-8-sig"
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(robustness[0].keys())
            )
            writer.writeheader()
            writer.writerows(robustness)
    elif robustness_path.exists():
        robustness_path.unlink()
    payload = {
        "node_semantics": (
            "all non-sink devices are homogeneous sensor nodes; selected "
            "forwarding paths and cooperative participation are run-time roles"
        ),
        "experimental_design": (
            "one factor at a time around the 31-node, 600-m, rectangular, "
            "3-path, 5-hop baseline; all protocols share each topology and seed"
        ),
        "factors": {
            factor: [
                {
                    "level": scenario.level_label,
                    "config": asdict(scenario.config),
                }
                for scenario in topology_scenarios([factor])
            ]
            for factor in TOPOLOGY_FACTORS
            if any(str(row["factor"]) == factor for row in raw_sorted)
        },
        "raw": raw_sorted,
        "summary": list(summary),
        "robustness_summary": robustness,
    }
    (output_dir / "topology_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return robustness


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
            "important_initial": "full RS(63,57) mother code",
            "important_retransmission": "full-code Chase combining",
            "ca_base": (
                "same CA contention and confidence policy, packet importance "
                "recorded but ignored"
            ),
            "importance_aware_queues": (
                "non-preemptive priority at every transmitter and helper queue"
            ),
            "importance_ratio": (
                float(raw_sorted[0]["importance_ratio"]) if raw_sorted else None
            ),
            "importance_signal_bits_per_data_frame": IMPORTANCE_SIGNAL_BITS,
            "important_deadline_s": (
                float(raw_sorted[0]["important_deadline_s"]) if raw_sorted else None
            ),
            "useful_bits": INFO_BITS,
            "bit_rate": BIT_RATE,
            "node_semantics": (
                "all non-sink nodes are homogeneous sensors; forwarding-path "
                "and cooperative-candidate labels are per-run protocol roles"
            ),
            "topology": {
                "total_nodes_including_sink": (
                    int(raw_sorted[0]["total_nodes"]) if raw_sorted else None
                ),
                "selected_paths": (
                    int(raw_sorted[0]["num_chains"]) if raw_sorted else None
                ),
                "hops_per_path": (
                    int(raw_sorted[0]["num_hops"]) if raw_sorted else None
                ),
                "off_route_nodes": (
                    int(raw_sorted[0]["cooperative_nodes"])
                    if raw_sorted else None
                ),
                "spacing_m": (
                    float(raw_sorted[0]["spacing_m"]) if raw_sorted else None
                ),
                "formation": (
                    str(raw_sorted[0]["formation"]) if raw_sorted else None
                ),
            },
        },
        "raw": raw_sorted,
        "summary": list(summary),
    }
    (output_dir / "results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 6. Dependency-light paper figures (editable SVG + PNG)
# ---------------------------------------------------------------------------
PLOT_COLORS = {
    PROTO_SW_ARQ: "#4C78A8",
    PROTO_CARQ: "#F58518",
    PROTO_CHARQ: "#54A24B",
    PROTO_CA_BASE: "#79706E",
    PROTO_CA: "#B279A2",
    "CA-CHARQ gain vs Base": "#E45756",
    "CA-CHARQ paired advantage": "#E45756",
    "Normal": "#4C78A8",
    "Important": "#E45756",
    "All packets": "#54A24B",
}
PLOT_MARKERS = {
    PROTO_SW_ARQ: "circle",
    PROTO_CARQ: "square",
    PROTO_CHARQ: "triangle",
    PROTO_CA_BASE: "circle",
    PROTO_CA: "diamond",
    "CA-CHARQ gain vs Base": "diamond",
    "CA-CHARQ paired advantage": "diamond",
    "Normal": "circle",
    "Important": "diamond",
    "All packets": "triangle",
}
PLOT_DASHES = {
    PROTO_SW_ARQ: (),
    PROTO_CARQ: (9, 5),
    PROTO_CHARQ: (3, 4),
    PROTO_CA_BASE: (7, 3, 2, 3),
    PROTO_CA: (12, 4, 3, 4),
    "CA-CHARQ gain vs Base": (),
    "CA-CHARQ paired advantage": (),
    "Normal": (),
    "Important": (10, 4),
    "All packets": (3, 4),
}


def _paper_protocol_label(protocol: str) -> str:
    return PAPER_PROTOCOL_LABELS.get(protocol, protocol)


def _plot_style_key(label: str) -> str:
    """Map a reader-facing legend label back to its internal style key."""
    for protocol, display_label in PAPER_PROTOCOL_LABELS.items():
        if label == display_label:
            return protocol
    return label


def _topology_tick_labels(
    factor: str, rows: Sequence[Dict[str, float]]
) -> Dict[float, str]:
    labels = {
        float(row["level_index"]): str(row["level_label"])
        for row in rows
    }
    if factor == "node_scale":
        labels = {
            position: PAPER_NODE_SCALE_DISPLAY_LABELS.get(label, label)
            for position, label in labels.items()
        }
    return labels


class PaperFigure:
    """Draw the same figure to SVG and, when Pillow is available, PNG."""

    def __init__(self, width: int, height: int) -> None:
        self.width = int(width)
        self.height = int(height)
        self.svg: List[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}">'
            ),
            '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        ]
        self.image = None
        self.draw = None
        self._pil_font = None
        self._font_cache: Dict[Tuple[int, bool], object] = {}
        try:
            from PIL import Image, ImageDraw, ImageFont  # type: ignore
        except ImportError:
            return
        self._pil_font = ImageFont
        self.image = Image.new("RGB", (self.width, self.height), "#FFFFFF")
        self.draw = ImageDraw.Draw(self.image)

    def font(self, size: int, bold: bool = False):
        if self._pil_font is None:
            return None
        key = (int(size), bool(bold))
        if key in self._font_cache:
            return self._font_cache[key]
        names = (
            (
                r"C:\Windows\Fonts\msyhbd.ttc",
                r"C:\Windows\Fonts\simhei.ttf",
                "arialbd.ttf",
                "DejaVuSans-Bold.ttf",
            )
            if bold else (
                r"C:\Windows\Fonts\msyh.ttc",
                r"C:\Windows\Fonts\simhei.ttf",
                "arial.ttf",
                "DejaVuSans.ttf",
            )
        )
        for name in names:
            try:
                font = self._pil_font.truetype(name, int(size))
                self._font_cache[key] = font
                return font
            except OSError:
                continue
        font = self._pil_font.load_default()
        self._font_cache[key] = font
        return font

    def text(self, x: float, y: float, value: str, size: int = 24,
             color: str = "#222222", anchor: str = "middle",
             bold: bool = False) -> None:
        anchor_map = {
            "start": "lm",
            "middle": "mm",
            "end": "rm",
        }
        weight = 700 if bold else 400
        self.svg.append(
            f'<text x="{x:.2f}" y="{y:.2f}" fill="{color}" '
            f'font-family="Microsoft YaHei,SimHei,Arial,sans-serif" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" '
            f'dominant-baseline="middle">{xml_escape(str(value))}</text>'
        )
        if self.draw is not None:
            self.draw.text(
                (float(x), float(y)), str(value), fill=color,
                font=self.font(size, bold), anchor=anchor_map[anchor],
            )

    def line(self, x1: float, y1: float, x2: float, y2: float,
             color: str, width: int = 2, dash: Tuple[int, ...] = ()) -> None:
        dash_attr = (
            f' stroke-dasharray="{",".join(str(v) for v in dash)}"'
            if dash else ""
        )
        self.svg.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="{width}"{dash_attr}/>'
        )
        if self.draw is None:
            return
        if not dash:
            self.draw.line((x1, y1, x2, y2), fill=color, width=width)
            return
        length = math.hypot(x2 - x1, y2 - y1)
        if length <= 0.0:
            return
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        distance = 0.0
        index = 0
        draw_segment = True
        while distance < length:
            step = float(dash[index % len(dash)])
            end = min(length, distance + step)
            if draw_segment:
                self.draw.line(
                    (
                        x1 + ux * distance, y1 + uy * distance,
                        x1 + ux * end, y1 + uy * end,
                    ),
                    fill=color, width=width,
                )
            distance = end
            index += 1
            draw_segment = not draw_segment

    def polyline(self, points: Sequence[Tuple[float, float]], color: str,
                 width: int = 4, dash: Tuple[int, ...] = ()) -> None:
        if len(points) < 2:
            return
        point_text = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        dash_attr = (
            f' stroke-dasharray="{",".join(str(v) for v in dash)}"'
            if dash else ""
        )
        self.svg.append(
            f'<polyline points="{point_text}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linejoin="round" '
            f'stroke-linecap="round"{dash_attr}/>'
        )
        if self.draw is not None:
            for first, second in zip(points[:-1], points[1:]):
                self.line(
                    first[0], first[1], second[0], second[1],
                    color, width, dash,
                )

    def marker(self, x: float, y: float, kind: str, color: str,
               radius: int = 7) -> None:
        r = float(radius)
        if kind == "square":
            points = [(x - r, y - r), (x + r, y - r),
                      (x + r, y + r), (x - r, y + r)]
        elif kind == "triangle":
            points = [(x, y - r - 1), (x + r + 1, y + r),
                      (x - r - 1, y + r)]
        elif kind == "diamond":
            points = [(x, y - r - 1), (x + r + 1, y),
                      (x, y + r + 1), (x - r - 1, y)]
        else:
            self.svg.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" '
                f'fill="#FFFFFF" stroke="{color}" stroke-width="3"/>'
            )
            if self.draw is not None:
                self.draw.ellipse(
                    (x - r, y - r, x + r, y + r),
                    fill="#FFFFFF", outline=color, width=3,
                )
            return
        point_text = " ".join(f"{px:.2f},{py:.2f}" for px, py in points)
        self.svg.append(
            f'<polygon points="{point_text}" fill="#FFFFFF" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        if self.draw is not None:
            self.draw.polygon(points, fill="#FFFFFF")
            self.draw.line(points + [points[0]], fill=color, width=3)

    def save(self, stem: Path) -> Tuple[Path, Optional[Path]]:
        stem.parent.mkdir(parents=True, exist_ok=True)
        svg_path = stem.with_suffix(".svg")
        svg_path.write_text(
            "\n".join(self.svg + ["</svg>"]), encoding="utf-8"
        )
        png_path: Optional[Path] = None
        if self.image is not None:
            png_path = stem.with_suffix(".png")
            self.image.save(png_path, format="PNG", dpi=(180, 180))
        return svg_path, png_path


def _plot_value(row: Dict[str, float], key: str) -> float:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return float("nan")


def _metric_format(value: float, metric: str) -> str:
    if "pdr" in metric or "miss_rate" in metric:
        return f"{value:.2f}"
    if "queue_wait" in metric:
        return f"{value:.3f}"
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _series_rows(
    summary: Sequence[Dict[str, float]],
    protocol: str,
    x_key: str = "snr_db",
) -> List[Dict[str, float]]:
    return sorted(
        (row for row in summary if str(row["protocol"]) == protocol),
        key=lambda row: float(row[x_key]),
    )


def _draw_panel(canvas: PaperFigure, bounds: Tuple[float, float, float, float],
                summary: Sequence[Dict[str, float]], title: str, ylabel: str,
                series: Sequence[Tuple[str, str, str]],
                y_bounds: Optional[Tuple[float, float]] = None,
                log_y: bool = False,
                x_key: str = "snr_db",
                xlabel: str = "Mean hop SNR (dB)",
                x_tick_labels: Optional[Dict[float, str]] = None) -> None:
    x0, y0, width, height = bounds
    title_lines = textwrap.wrap(
        title,
        width=38,
        break_long_words=False,
        break_on_hyphens=False,
    )[:2] or [title]
    left, right = 88.0, 30.0
    top = 84.0 + 27.0 * (len(title_lines) - 1)
    bottom = 72.0
    px0, px1 = x0 + left, x0 + width - right
    py0, py1 = y0 + top, y0 + height - bottom
    for line_index, line in enumerate(title_lines):
        canvas.text(
            x0 + width / 2,
            y0 + 18 + line_index * 27,
            line,
            23,
            bold=True,
        )
    canvas.text(px0, py0 - 18, ylabel, 19, "#333333", anchor="start")

    prepared = []
    all_values: List[float] = []
    all_snrs: List[float] = []
    for label, protocol, metric in series:
        rows = _series_rows(summary, protocol, x_key=x_key)
        points = []
        for row in rows:
            snr = float(row[x_key])
            value = _plot_value(row, f"{metric}_mean")
            ci = _plot_value(row, f"{metric}_ci95")
            if math.isfinite(value):
                points.append((snr, value, ci if math.isfinite(ci) else 0.0))
                all_snrs.append(snr)
                all_values.extend([value - max(ci, 0.0), value + max(ci, 0.0)])
        prepared.append((label, metric, points))
    if not all_snrs or not all_values:
        canvas.text(x0 + width / 2, y0 + height / 2, "No finite data", 22)
        return

    x_min, x_max = min(all_snrs), max(all_snrs)
    if x_max <= x_min:
        x_max = x_min + 1.0
    if log_y:
        centers = [
            value for _, _, points in prepared
            for _, value, _ in points if value > 0.0
        ]
        uppers = [
            value + max(ci, 0.0) for _, _, points in prepared
            for _, value, ci in points if value > 0.0
        ]
        y_min = max(min(centers) * 0.75, 1e-6)
        y_max = max(max(uppers) * 1.08, y_min * 1.5)
    elif y_bounds is None:
        y_min = 0.0
        y_max = max(0.0, max(all_values))
        if y_max <= y_min:
            y_max = y_min + 1.0
        y_max += 0.08 * (y_max - y_min)
    else:
        y_min, y_max = y_bounds

    def map_x(value: float) -> float:
        return px0 + (value - x_min) / (x_max - x_min) * (px1 - px0)

    def map_y(value: float) -> float:
        clipped = min(max(value, y_min), y_max)
        if log_y:
            return py1 - (
                (math.log10(clipped) - math.log10(y_min))
                / (math.log10(y_max) - math.log10(y_min))
                * (py1 - py0)
            )
        return py1 - (clipped - y_min) / (y_max - y_min) * (py1 - py0)

    for index in range(6):
        if log_y:
            value = 10.0 ** (
                math.log10(y_min)
                + (math.log10(y_max) - math.log10(y_min)) * index / 5.0
            )
        else:
            value = y_min + (y_max - y_min) * index / 5.0
        y = map_y(value)
        canvas.line(px0, y, px1, y, "#D9D9D9", 1)
        canvas.text(
            px0 - 12, y, _metric_format(value, series[0][2]),
            18, "#555555", anchor="end",
        )
    if not log_y and y_min < 0.0 < y_max:
        canvas.line(px0, map_y(0.0), px1, map_y(0.0), "#888888", 2)
    for snr in sorted(set(all_snrs)):
        x = map_x(snr)
        canvas.line(x, py1, x, py1 + 7, "#333333", 2)
        tick_label = (
            x_tick_labels.get(snr, f"{snr:g}")
            if x_tick_labels is not None
            else f"{snr:g}"
        )
        canvas.text(x, py1 + 27, tick_label, 18, "#444444")
    canvas.line(px0, py0, px0, py1, "#333333", 2)
    canvas.line(px0, py1, px1, py1, "#333333", 2)
    canvas.text((px0 + px1) / 2, py1 + 57, xlabel, 19)

    for label, metric, points in prepared:
        if not points:
            continue
        style_key = _plot_style_key(label)
        color = PLOT_COLORS[style_key]
        marker = PLOT_MARKERS[style_key]
        dash = PLOT_DASHES[style_key]
        mapped = [(map_x(snr), map_y(value)) for snr, value, _ in points]
        canvas.polyline(mapped, color, 4, dash)
        for (snr, value, ci), (x, y) in zip(points, mapped):
            if ci > 0.0:
                y_low = map_y(value - ci)
                y_high = map_y(value + ci)
                canvas.line(x, y_low, x, y_high, color, 2)
                canvas.line(x - 5, y_low, x + 5, y_low, color, 2)
                canvas.line(x - 5, y_high, x + 5, y_high, color, 2)
            canvas.marker(x, y, marker, color)


def _draw_legend(canvas: PaperFigure, labels: Sequence[str],
                 y: float, width: float) -> None:
    unique = list(dict.fromkeys(labels))
    item_width = min(280.0, width / max(len(unique), 1))
    total = item_width * len(unique)
    start = (width - total) / 2.0
    for index, label in enumerate(unique):
        x = start + index * item_width + 12
        style_key = _plot_style_key(label)
        color = PLOT_COLORS[style_key]
        canvas.line(x, y, x + 48, y, color, 4, PLOT_DASHES[style_key])
        canvas.marker(x + 24, y, PLOT_MARKERS[style_key], color, 6)
        canvas.text(x + 60, y, label, 20, "#222222", anchor="start")


def _create_figure(summary: Sequence[Dict[str, float]], output_dir: Path,
                   filename: str, figure_title: str,
                   panels: Sequence[Dict[str, object]]) -> List[Path]:
    columns = 1 if len(panels) == 1 else 2
    rows = max(1, math.ceil(len(panels) / columns))
    width = 1600
    margin_y, gap_y = 110.0, 30.0
    panel_h = 650.0 if columns == 1 else 480.0
    height = int(margin_y + rows * panel_h + (rows - 1) * gap_y + 30.0)
    canvas = PaperFigure(width, height)
    canvas.text(width / 2, 38, figure_title, 30, bold=True)
    legend_labels = [
        label
        for panel in panels
        for label, _, _ in panel["series"]  # type: ignore[index]
    ]
    _draw_legend(canvas, legend_labels, 82, width)
    margin_x, gap_x = 90.0 if columns == 1 else 45.0, 35.0
    panel_w = (
        width - 2 * margin_x
        if columns == 1
        else (width - 2 * margin_x - gap_x) / 2.0
    )
    for index, panel in enumerate(panels):
        col, row = index % columns, index // columns
        bounds = (
            margin_x + col * (panel_w + gap_x),
            margin_y + row * (panel_h + gap_y),
            panel_w,
            panel_h,
        )
        _draw_panel(
            canvas,
            bounds,
            summary,
            "" if columns == 1 else str(panel["title"]),
            str(panel["ylabel"]),
            panel["series"],  # type: ignore[arg-type]
            panel.get("y_bounds"),  # type: ignore[arg-type]
            bool(panel.get("log_y", False)),
            str(panel.get("x_key", "snr_db")),
            str(panel.get("xlabel", "Mean hop SNR (dB)")),
            panel.get("x_tick_labels"),  # type: ignore[arg-type]
        )
    svg_path, png_path = canvas.save(output_dir / "figures" / filename)
    paths = [svg_path]
    if png_path is not None:
        paths.append(png_path)
    return paths


def create_plots(summary: Sequence[Dict[str, float]], output_dir: Path) -> List[Path]:
    protocols = [
        proto for proto in PAPER_PROTOCOLS
        if any(str(row["protocol"]) == proto for row in summary)
    ]
    overall_series = lambda metric: [
        (_paper_protocol_label(proto), proto, metric) for proto in protocols
    ]
    important_series = lambda metric: [
        (_paper_protocol_label(proto), proto, f"important_{metric}")
        for proto in protocols
    ]
    normal_series = lambda metric: [
        (_paper_protocol_label(proto), proto, f"normal_{metric}")
        for proto in protocols
    ]
    ca_protocols = [
        proto for proto in (PROTO_CA_BASE, PROTO_CA) if proto in protocols
    ]
    ca_series = lambda metric: [
        (proto, proto, metric) for proto in ca_protocols
    ]
    ca_important_series = lambda metric: [
        (proto, proto, f"important_{metric}") for proto in ca_protocols
    ]
    ca_normal_series = lambda metric: [
        (proto, proto, f"normal_{metric}") for proto in ca_protocols
    ]
    gain_series = lambda metric: [
        ("CA-CHARQ gain vs Base", PROTO_CA, metric)
    ]

    created: List[Path] = []
    created.extend(_create_figure(
        summary, output_dir, "overall-performance",
        "End-to-end performance of concurrent underwater sensor chains",
        [
            {"title": "(a) End-to-end delay", "ylabel": "Delay (s)",
             "series": overall_series("delay")},
            {"title": "(b) Packet delivery ratio", "ylabel": "PDR",
             "series": overall_series("pdr"), "y_bounds": (0.0, 1.05)},
            {"title": "(c) Normalized transmission overhead",
             "ylabel": "Transmitted bits / delivered payload bit (log scale)",
             "series": overall_series("overhead"), "log_y": True},
            {"title": "(d) Energy efficiency", "ylabel": "Useful bits / J",
             "series": overall_series("energy_efficiency")},
        ],
    ))
    created.extend(_create_figure(
        summary, output_dir, "important-packet-protocol-comparison",
        "Important-packet reliability under system-wide cost constraints",
        [
            {"title": "(a) Important-packet on-time delivery ratio",
             "ylabel": f"Delivered within {IMPORTANT_DEADLINE_S:g} s",
             "series": important_series("on_time_pdr"),
             "y_bounds": (0.0, 1.05)},
            {"title": "(b) Important-packet P95 latency",
             "ylabel": "P95 delay (s)",
             "series": important_series("delay_p95")},
            {"title": "(c) Important-packet delivery ratio", "ylabel": "PDR",
             "series": important_series("pdr"), "y_bounds": (0.0, 1.05)},
            {"title": "(d) System-wide normalized overhead",
             "ylabel": "Transmitted bits / delivered payload bit (log scale)",
             "series": overall_series("overhead"), "log_y": True},
            {"title": "(e) System-wide energy efficiency",
             "ylabel": "Useful bits / J",
             "series": overall_series("energy_efficiency")},
            {"title": "(f) Normal-packet delivery ratio",
             "ylabel": "Normal-packet PDR",
             "series": normal_series("pdr"), "y_bounds": (0.0, 1.05)},
        ],
    ))
    if len(ca_protocols) == 2:
        created.extend(_create_figure(
            summary, output_dir, "importance-awareness-ablation",
            "Causal effect of packet-importance awareness",
            [
                {"title": "(a) Important-packet on-time delivery ratio",
                 "ylabel": f"Delivered within {IMPORTANT_DEADLINE_S:g} s",
                 "series": ca_important_series("on_time_pdr"),
                 "y_bounds": (0.0, 1.05)},
                {"title": "(b) Important-packet P95 latency",
                 "ylabel": "P95 delay (s)",
                 "series": ca_important_series("delay_p95")},
                {"title": "(c) System-wide normalized overhead",
                 "ylabel": "Transmitted bits / delivered payload bit (log scale)",
                 "series": ca_series("overhead"), "log_y": True},
                {"title": "(d) Normal-packet delivery ratio",
                 "ylabel": "Normal-packet PDR",
                 "series": ca_normal_series("pdr"),
                 "y_bounds": (0.0, 1.05)},
            ],
        ))
        created.extend(_create_figure(
            summary, output_dir, "importance-cost-benefit",
            "Paired gain and cost of packet-importance awareness",
            [
                {"title": "(a) Important on-time delivery gain",
                 "ylabel": "Percentage-point gain",
                 "series": gain_series("important_on_time_gain_pp"),
                 "y_bounds": (-5.0, 20.0)},
                {"title": "(b) Important P95 latency reduction",
                 "ylabel": "Reduction (%)",
                 "series": gain_series("important_p95_reduction_pct"),
                 "y_bounds": (-5.0, 20.0)},
                {"title": "(c) Important mean-latency reduction",
                 "ylabel": "Reduction (%)",
                 "series": gain_series("important_mean_delay_reduction_pct"),
                 "y_bounds": (-5.0, 15.0)},
                {"title": "(d) Important-packet PDR gain",
                 "ylabel": "Percentage-point gain",
                 "series": gain_series("important_pdr_gain_pp"),
                 "y_bounds": (-10.0, 15.0)},
                {"title": "(e) System-wide overhead reduction",
                 "ylabel": "Reduction (%)",
                 "series": gain_series("overhead_reduction_pct"),
                 "y_bounds": (-10.0, 20.0)},
                {"title": "(f) Normal-packet PDR change",
                 "ylabel": "Percentage-point change",
                 "series": gain_series("normal_pdr_change_pp"),
                 "y_bounds": (-3.0, 3.0)},
            ],
        ))
    figures_dir = output_dir / "figures"
    obsolete_stems = (
        "important-packet-performance",
        "ca-charq-importance-tradeoff",
        "importance-awareness-ablation",
        "importance-cost-benefit",
    )
    for stem in obsolete_stems:
        for suffix in (".png", ".svg"):
            obsolete = figures_dir / f"{stem}{suffix}"
            if obsolete.exists():
                obsolete.unlink()

    comparison_rows = []
    comparison_fields = (
        "protocol", "snr_db",
        "important_delay_mean", "important_delay_ci95",
        "important_delay_p95_mean", "important_delay_p95_ci95",
        "important_on_time_pdr_mean", "important_on_time_pdr_ci95",
        "important_pdr_mean", "important_pdr_ci95",
        "important_deadline_miss_rate_mean",
        "important_deadline_miss_rate_ci95",
        "overhead_mean", "overhead_ci95",
        "energy_efficiency_mean", "energy_efficiency_ci95",
        "normal_pdr_mean", "normal_pdr_ci95",
        "normal_delay_p95_mean", "normal_delay_p95_ci95",
        "important_on_time_gain_pp_mean", "important_on_time_gain_pp_ci95",
        "important_pdr_gain_pp_mean", "important_pdr_gain_pp_ci95",
        "important_mean_delay_reduction_pct_mean",
        "important_mean_delay_reduction_pct_ci95",
        "important_p95_reduction_pct_mean",
        "important_p95_reduction_pct_ci95",
        "overhead_reduction_pct_mean", "overhead_reduction_pct_ci95",
        "normal_pdr_change_pp_mean", "normal_pdr_change_pp_ci95",
        "normal_p95_change_pct_mean", "normal_p95_change_pct_ci95",
    )
    for row in summary:
        comparison_rows.append({
            field: row[field] for field in comparison_fields
        })
    figures_dir.mkdir(parents=True, exist_ok=True)
    with (figures_dir / "important_packet_comparison.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_fields))
        writer.writeheader()
        writer.writerows(comparison_rows)

    manifest = {
        "figures": [str(path.name) for path in created],
        "comparison_basis": (
            "The same deterministic important-packet sequence is used by all "
            "protocols. Important-packet reliability and P95 latency are judged "
            "with system-wide cost and normal-packet PDR as constraints."
        ),
        "note": "SVG files are editable vector figures; PNG files are 180 dpi.",
    }
    (figures_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return created


def create_paper_plots(
    summary: Sequence[Dict[str, float]], output_dir: Path
) -> List[Path]:
    """Create one metric per figure for direct insertion into a paper."""
    protocols = [
        protocol for protocol in PAPER_PROTOCOLS
        if any(str(row["protocol"]) == protocol for row in summary)
    ]
    series = lambda metric: [
        (_paper_protocol_label(protocol), protocol, metric)
        for protocol in protocols
    ]
    specifications = (
        ("paper-snr-delay", "End-to-end delay", "Delay (s)", "delay", None, False),
        ("paper-snr-pdr", "Packet delivery ratio", "PDR", "pdr", (0.0, 1.05), False),
        (
            "paper-snr-overhead", "Normalized transmission overhead",
            "Transmitted bits / delivered payload bit", "overhead", None, True,
        ),
        (
            "paper-snr-energy-efficiency", "Energy efficiency",
            "Useful payload bit / J", "energy_efficiency", None, False,
        ),
        (
            "paper-snr-important-on-time", "Important-packet on-time delivery",
            f"Delivered within {IMPORTANT_DEADLINE_S:g} s",
            "important_on_time_pdr", (0.0, 1.05), False,
        ),
        (
            "paper-snr-important-p95", "Important-packet P95 latency",
            "P95 delay (s)", "important_delay_p95", None, False,
        ),
        (
            "paper-snr-penalized-delay", "Failure-penalized end-to-end delay",
            f"Delay with {UNDELIVERED_DELAY_PENALTY_S:g} s penalty",
            "delivery_penalized_delay", None, False,
        ),
        (
            "paper-snr-goodput", "Delivered application goodput",
            "Useful payload bit/s", "goodput_bps", None, False,
        ),
    )
    created: List[Path] = []
    for filename, title, ylabel, metric, y_bounds, log_y in specifications:
        created.extend(_create_figure(
            summary,
            output_dir,
            filename,
            title,
            [{
                "title": title,
                "ylabel": ylabel,
                "series": series(metric),
                "y_bounds": y_bounds,
                "log_y": log_y,
            }],
        ))
    return created


def create_formation_layout_figure(output_dir: Path) -> List[Path]:
    """Show whole-node deployments; selected paths are an overlay, not node types."""
    width, height = 1600, 1030
    canvas = PaperFigure(width, height)
    canvas.text(
        width / 2, 38,
        "Whole-network formations with selected forwarding paths",
        30, bold=True,
    )
    legend_y = 80.0
    canvas.marker(510, legend_y, "circle", "#4C78A8", 6)
    canvas.text(530, legend_y, "Homogeneous sensor node", 19, anchor="start")
    canvas.line(775, legend_y, 825, legend_y, "#79706E", 3)
    canvas.text(840, legend_y, "Selected path", 19, anchor="start")
    canvas.marker(1010, legend_y, "diamond", "#E45756", 7)
    canvas.text(1030, legend_y, "Common sink", 19, anchor="start")

    margin_x, gap_x = 55.0, 40.0
    panel_w = (width - 2 * margin_x - gap_x) / 2.0
    panel_h = 420.0
    top = 115.0
    for index, formation in enumerate(FORMATIONS):
        col, row = index % 2, index // 2
        x0 = margin_x + col * (panel_w + gap_x)
        y0 = top + row * (panel_h + 35.0)
        canvas.text(
            x0 + panel_w / 2, y0 + 18,
            f"({chr(ord('a') + index)}) {FORMATION_LABELS[formation]}",
            24, bold=True,
        )
        config = replace(BASE_TOPOLOGY, formation=formation)
        env = simpy.Environment()
        network = Network(
            env, PROTO_CA_BASE, 5.0, 1.0, 0, topology=config
        )
        nodes = [
            node for node_id, node in network.nodes_by_id.items()
            if node_id != SINK_ID
        ]
        all_x = [node.x for node in nodes] + [network.sink.x]
        all_y = [node.y for node in nodes] + [network.sink.y]
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        x_pad = max(0.08 * (x_max - x_min), 100.0)
        y_pad = max(0.12 * (y_max - y_min), 100.0)
        plot_left, plot_right = x0 + 45.0, x0 + panel_w - 25.0
        plot_top, plot_bottom = y0 + 55.0, y0 + panel_h - 45.0

        def map_point(px: float, py: float) -> Tuple[float, float]:
            mx = plot_left + (
                (px - (x_min - x_pad))
                / ((x_max + x_pad) - (x_min - x_pad))
                * (plot_right - plot_left)
            )
            my = plot_bottom - (
                (py - (y_min - y_pad))
                / ((y_max + y_pad) - (y_min - y_pad))
                * (plot_bottom - plot_top)
            )
            return mx, my

        canvas.line(
            plot_left, plot_top, plot_right, plot_top, "#D9D9D9", 1
        )
        canvas.line(
            plot_right, plot_top, plot_right, plot_bottom, "#D9D9D9", 1
        )
        canvas.line(
            plot_right, plot_bottom, plot_left, plot_bottom, "#D9D9D9", 1
        )
        canvas.line(
            plot_left, plot_bottom, plot_left, plot_top, "#D9D9D9", 1
        )
        for chain_id in range(config.num_chains):
            path = [
                map_point(
                    network.routers[(chain_id, hop)].x,
                    network.routers[(chain_id, hop)].y,
                )
                for hop in range(config.num_hops)
            ]
            path.append(map_point(network.sink.x, network.sink.y))
            canvas.polyline(path, "#79706E", 3, (6, 4))
        for node in nodes:
            mx, my = map_point(node.x, node.y)
            canvas.marker(mx, my, "circle", "#4C78A8", 5)
        sink_x, sink_y = map_point(network.sink.x, network.sink.y)
        canvas.marker(sink_x, sink_y, "diamond", "#E45756", 7)
        canvas.text(
            x0 + panel_w / 2, y0 + panel_h - 15,
            "All non-sink devices use the same sensor-node model",
            17, "#555555",
        )

    svg_path, png_path = canvas.save(
        output_dir / "figures" / "whole-network-formations"
    )
    paths = [svg_path]
    if png_path is not None:
        paths.append(png_path)
    return paths


def create_topology_plots(
    summary: Sequence[Dict[str, float]],
    output_dir: Path,
    robustness: Optional[Sequence[Dict[str, float]]] = None,
) -> List[Path]:
    protocols = [
        protocol for protocol in PAPER_PROTOCOLS
        if any(str(row["protocol"]) == protocol for row in summary)
    ]
    series = lambda metric: [
        (_paper_protocol_label(protocol), protocol, metric)
        for protocol in protocols
    ]
    created: List[Path] = []
    for factor in PAPER_TOPOLOGY_FACTORS:
        factor_rows = [
            row for row in summary if str(row["factor"]) == factor
        ]
        if not factor_rows:
            continue
        tick_labels = dict(sorted(
            _topology_tick_labels(factor, factor_rows).items()
        ))
        common = {
            "x_key": "level_index",
            "xlabel": TOPOLOGY_FACTOR_LABELS[factor],
            "x_tick_labels": tick_labels,
        }
        panels = [
            {
                **common,
                "title": "(a) Successful-packet mean delay",
                "ylabel": "Delay (s)",
                "series": series("delay"),
            },
            {
                **common,
                "title": "(b) Packet delivery ratio",
                "ylabel": "PDR",
                "series": series("pdr"),
                "y_bounds": (0.0, 1.05),
            },
            {
                **common,
                "title": "(c) Normalized transmission overhead",
                "ylabel": (
                    "Transmitted bits / delivered payload bit (log scale)"
                ),
                "series": series("overhead"),
                "log_y": True,
            },
            {
                **common,
                "title": "(d) Energy efficiency",
                "ylabel": "Useful bits / J",
                "series": series("energy_efficiency"),
            },
            {
                **common,
                "title": "(e) Important-packet on-time delivery",
                "ylabel": f"Delivered within {IMPORTANT_DEADLINE_S:g} s",
                "series": series("important_on_time_pdr"),
                "y_bounds": (0.0, 1.05),
            },
            {
                **common,
                "title": "(f) Important-packet P95 latency",
                "ylabel": "P95 delay (s)",
                "series": series("important_delay_p95"),
            },
        ]
        created.extend(_create_figure(
            factor_rows,
            output_dir,
            f"sensitivity-{factor.replace('_', '-')}",
            TOPOLOGY_FIGURE_TITLES[factor],
            panels,
        ))
        robust_panels = [
            {
                **common,
                "title": "(a) Failure-penalized end-to-end delay",
                "ylabel": (
                    f"Delay with {UNDELIVERED_DELAY_PENALTY_S:g} s "
                    "per undelivered packet"
                ),
                "series": series("delivery_penalized_delay"),
            },
            {
                **common,
                "title": "(b) Delivered application goodput",
                "ylabel": "Useful payload bit/s",
                "series": series("goodput_bps"),
            },
            {
                **common,
                "title": "(c) Load-normalized transmission cost",
                "ylabel": "Transmitted bit / generated packet",
                "series": series("tx_bits_per_generated"),
            },
            {
                **common,
                "title": "(d) Load-normalized energy cost",
                "ylabel": "J / generated packet",
                "series": series("energy_per_generated"),
            },
        ]
        created.extend(_create_figure(
            factor_rows,
            output_dir,
            f"robust-{factor.replace('_', '-')}",
            f"Robust performance measures: {TOPOLOGY_FIGURE_TITLES[factor]}",
            robust_panels,
        ))
    figures_dir = output_dir / "figures"
    for stem in (
        "sensitivity-formation",
        "whole-network-formations",
        "topology-robustness-cost-benefit",
    ):
        for suffix in (".png", ".svg"):
            obsolete = figures_dir / f"{stem}{suffix}"
            if obsolete.exists():
                obsolete.unlink()
    manifest = {
        "figures": [path.name for path in created],
        "design": (
            "one-factor-at-a-time topology sensitivity with common random "
            "numbers across the four formal comparison protocols"
        ),
        "node_semantics": (
            "all non-sink devices are homogeneous sensors; selected paths are "
            "route overlays through the whole deployment"
        ),
        "excluded_from_formal_figures": (
            "diagnostic ablation and whole-network formation comparisons"
        ),
        "robust_delay_definition": (
            f"successful delay sum plus {UNDELIVERED_DELAY_PENALTY_S:g} s "
            "for every generated packet not delivered before the run ends, "
            "divided by generated packets"
        ),
        "note": "SVG files are editable vector figures; PNG files are 180 dpi.",
    }
    figures_dir.mkdir(parents=True, exist_ok=True)
    (figures_dir / "topology_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return created


def create_paper_topology_plots(
    summary: Sequence[Dict[str, float]], output_dir: Path
) -> List[Path]:
    """Create standalone topology-sensitivity figures for paper layout."""
    protocols = [
        protocol for protocol in PAPER_PROTOCOLS
        if any(str(row["protocol"]) == protocol for row in summary)
    ]
    series = lambda metric: [
        (_paper_protocol_label(protocol), protocol, metric)
        for protocol in protocols
    ]
    specifications = (
        ("delay", "Successful-packet mean delay", "Delay (s)", None, False),
        ("pdr", "Packet delivery ratio", "PDR", (0.0, 1.05), False),
        (
            "overhead", "Normalized transmission overhead",
            "Transmitted bits / delivered payload bit", None, True,
        ),
        (
            "energy-efficiency", "Energy efficiency",
            "Useful payload bit / J", None, False,
        ),
        (
            "important-on-time", "Important-packet on-time delivery",
            f"Delivered within {IMPORTANT_DEADLINE_S:g} s", (0.0, 1.05), False,
        ),
        (
            "important-p95", "Important-packet P95 latency",
            "P95 delay (s)", None, False,
        ),
        (
            "penalized-delay", "Failure-penalized end-to-end delay",
            f"Delay with {UNDELIVERED_DELAY_PENALTY_S:g} s penalty", None, False,
        ),
        (
            "goodput", "Delivered application goodput",
            "Useful payload bit/s", None, False,
        ),
    )
    metric_keys = {
        "delay": "delay",
        "pdr": "pdr",
        "overhead": "overhead",
        "energy-efficiency": "energy_efficiency",
        "important-on-time": "important_on_time_pdr",
        "important-p95": "important_delay_p95",
        "penalized-delay": "delivery_penalized_delay",
        "goodput": "goodput_bps",
    }
    created: List[Path] = []
    for factor in PAPER_TOPOLOGY_FACTORS:
        factor_rows = [
            row for row in summary if str(row["factor"]) == factor
        ]
        if not factor_rows:
            continue
        tick_labels = _topology_tick_labels(factor, factor_rows)
        for stem, title, ylabel, y_bounds, log_y in specifications:
            created.extend(_create_figure(
                factor_rows,
                output_dir,
                f"paper-{factor.replace('_', '-')}-{stem}",
                f"{title}: {TOPOLOGY_FACTOR_LABELS[factor]}",
                [{
                    "title": title,
                    "ylabel": ylabel,
                    "series": series(metric_keys[stem]),
                    "y_bounds": y_bounds,
                    "log_y": log_y,
                    "x_key": "level_index",
                    "xlabel": TOPOLOGY_FACTOR_LABELS[factor],
                    "x_tick_labels": tick_labels,
                }],
            ))
    return created


def read_summary_csv(path: Path) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    string_fields = {
        "protocol",
        "factor",
        "factor_label",
        "level_label",
        "formation",
        "scenario_id",
        "active_chain_indices",
    }
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            row: Dict[str, float] = {}
            for key, value in raw.items():
                if key in string_fields:
                    if key == "protocol" and value == LEGACY_PROTO_SW_ARQ:
                        value = PROTO_SW_ARQ
                    row[key] = value  # type: ignore[assignment]
                else:
                    try:
                        row[key] = float(value)
                    except (TypeError, ValueError):
                        row[key] = float("nan")
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 7. Self-tests: codec, full-key isolation, importance and queue cancellation
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
    full = SoftBuffer()
    rv0 = SoftBuffer()
    full.add(codeword, FULL_CODE_POSITIONS, 3.0, stable_rng(9, 4))
    rv0.add(codeword, RV_POSITIONS[0], 3.0, stable_rng(9, 4))
    assert np.array_equal(full.metric[:59], rv0.metric[:59])
    assert np.array_equal(full.gamma[:59], rv0.gamma[:59])
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


def test_importance_policy() -> None:
    env_a = simpy.Environment()
    env_b = simpy.Environment()
    env_c = simpy.Environment()
    sw = Network(env_a, PROTO_SW_ARQ, 5.0, 10.0, 7, importance_ratio=0.30)
    ca = Network(env_b, PROTO_CA, 5.0, 10.0, 7, importance_ratio=0.30)
    ca_base = Network(
        env_c, PROTO_CA_BASE, 5.0, 10.0, 7, importance_ratio=0.30
    )
    sequence_a = [sw.packet_importance(1, pid) for pid in range(50)]
    sequence_b = [ca.packet_importance(1, pid) for pid in range(50)]
    assert sequence_a == sequence_b
    assert IMPORTANCE_NORMAL in sequence_a
    assert IMPORTANCE_HIGH in sequence_a

    assert sw._initial_positions(IMPORTANCE_HIGH) == UNCODED_POSITIONS
    assert ca_base._initial_positions(IMPORTANCE_HIGH) == RV_POSITIONS[0]
    assert ca._initial_positions(IMPORTANCE_NORMAL) == RV_POSITIONS[0]
    assert ca._initial_positions(IMPORTANCE_HIGH) == FULL_CODE_POSITIONS
    empty = SoftBuffer()
    assert ca._ca_positions(empty, 3, IMPORTANCE_HIGH) == FULL_CODE_POSITIONS
    assert ca._ca_positions(empty, 3, IMPORTANCE_NORMAL) == RV_POSITIONS[1]


def test_radio_priority() -> None:
    env = simpy.Environment()
    node = Node(env, 77, 0.0, 0.0, "TEST")
    order: List[str] = []

    def transmit(name: str, priority: int, start: float, duration: float):
        yield env.timeout(start)
        with node.radio.request(priority=priority) as request:
            yield request
            order.append(name)
            yield env.timeout(duration)

    env.process(transmit("active-normal", 1, 0.0, 0.2))
    env.process(transmit("queued-normal", 1, 0.01, 0.01))
    env.process(transmit("queued-important", 0, 0.02, 0.01))
    env.run(until=0.5)
    assert order == ["active-normal", "queued-important", "queued-normal"]


def test_importance_statistics() -> None:
    stats = Stats()
    stats.packet_generated(IMPORTANCE_NORMAL)
    stats.packet_generated(IMPORTANCE_HIGH)
    stats.record_tx(IMPORTANCE_NORMAL, 100, 2.0)
    stats.record_tx(IMPORTANCE_HIGH, 200, 4.0)
    stats.packet_success(IMPORTANCE_NORMAL, 20.0, IMPORTANT_DEADLINE_S)
    stats.packet_drop(IMPORTANCE_HIGH)
    summary = stats.summary()
    assert stats.tx_bits == 300
    assert stats.energy_j == 6.0
    assert summary["normal_pdr"] == 1.0
    assert summary["important_pdr"] == 0.0
    assert summary["important_deadline_miss_rate"] == 1.0


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


def test_topology_configurations() -> None:
    scenarios = topology_scenarios()
    assert len(scenarios) == 21
    for scenario in scenarios:
        env = simpy.Environment()
        network = Network(
            env, PROTO_CA_BASE, 5.0, 10.0, 13,
            topology=scenario.config,
        )
        assert len(network.nodes_by_id) == scenario.config.total_nodes
        assert len(network.routers) == scenario.config.route_node_count
        assert len(network.helpers) == scenario.config.cooperative_node_count
        assert len(network.link_candidates) == (
            scenario.config.num_chains * scenario.config.num_hops
        )
        assert all(
            len(candidates) == scenario.config.candidates_per_link
            for candidates in network.link_candidates.values()
        )
        assert all(
            source.node_id not in {
                helper.node.node_id for helper in candidates
            }
            and destination.node_id not in {
                helper.node.node_id for helper in candidates
            }
            for (chain_id, hop), candidates in network.link_candidates.items()
            for source, destination in [(
                network.routers[(chain_id, hop)],
                network._destination(chain_id, hop),
            )]
        )
    config = replace(
        BASE_TOPOLOGY,
        formation=FORMATION_RANDOM,
        num_chains=4,
        num_hops=6,
        deployment_chains=4,
        deployment_hops=6,
        total_nodes=31,
    )
    env_a = simpy.Environment()
    env_b = simpy.Environment()
    network_a = Network(
        env_a, PROTO_SW_ARQ, 5.0, 10.0, 7, topology=config
    )
    network_b = Network(
        env_b, PROTO_CA, 5.0, 10.0, 7, topology=config
    )
    positions_a = sorted(
        (node.node_id, node.x, node.y)
        for node_id, node in network_a.nodes_by_id.items()
        if node_id != SINK_ID
    )
    positions_b = sorted(
        (node.node_id, node.x, node.y)
        for node_id, node in network_b.nodes_by_id.items()
        if node_id != SINK_ID
    )
    assert positions_a == positions_b

    # Activating more paths or a longer route must not move any physical node.
    for factor in ("path_count", "hop_count"):
        factor_scenarios = [
            scenario for scenario in scenarios if scenario.factor == factor
        ]
        deployments = []
        for scenario in factor_scenarios:
            env = simpy.Environment()
            network = Network(
                env, PROTO_SW_ARQ, 5.0, 10.0, 19,
                topology=scenario.config,
            )
            deployments.append(sorted(
                (node_id, node.x, node.y)
                for node_id, node in network.nodes_by_id.items()
            ))
        assert all(item == deployments[0] for item in deployments[1:])


def run_self_tests() -> None:
    test_rs_codec()
    test_soft_buffer_and_keys()
    test_charq_fixed_schedule()
    test_importance_policy()
    test_radio_priority()
    test_importance_statistics()
    test_scheduler_cancellation()
    test_topology_configurations()


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
    parser.add_argument(
        "--self-test", action="store_true",
        help="run codec/state/importance tests and exit",
    )
    parser.add_argument("--quick", action="store_true", help="3 SNR x 2 seeds x 600 s pilot")
    parser.add_argument(
        "--topology-sweep", action="store_true",
        help=(
            "run node-scale, spacing, path-count and hop-count "
            "sensitivity experiments instead of the SNR sweep"
        ),
    )
    parser.add_argument(
        "--topology-factor", choices=TOPOLOGY_FACTORS, nargs="*", default=None,
        help="limit --topology-sweep to one or more sensitivity factors",
    )
    parser.add_argument(
        "--topology-snr", type=float, default=5.0,
        help="reference SNR at 600 m for topology sensitivity (default: 5 dB)",
    )
    parser.add_argument("--sim-time", type=float, default=None)
    parser.add_argument("--runs", type=int, default=None)
    parser.add_argument("--snr", type=float, nargs="*", default=None)
    parser.add_argument("--protocol", choices=PROTOCOLS, nargs="*", default=None)
    parser.add_argument(
        "--importance-ratio", type=float, default=DEFAULT_IMPORTANCE_RATIO,
        help="probability that a generated packet is important (default: 0.20)",
    )
    parser.add_argument(
        "--important-deadline", type=float, default=IMPORTANT_DEADLINE_S,
        help="important-packet end-to-end deadline in seconds",
    )
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=Path("output") / "v14")
    parser.add_argument(
        "--no-plots", action="store_true",
        help="write numeric results without generating figures",
    )
    parser.add_argument(
        "--plot-only", type=Path, default=None, metavar="SUMMARY_CSV",
        help="skip simulation and regenerate figures from summary_results.csv",
    )
    parser.add_argument(
        "--topology-plot-only", type=Path, default=None,
        metavar="TOPOLOGY_SUMMARY_CSV",
        help=(
            "skip simulation and regenerate topology figures from "
            "topology_summary_results.csv"
        ),
    )
    parser.add_argument(
        "--paper-figures", action="store_true",
        help="also create standalone one-metric figures for paper layout",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.self_test:
        run_self_tests()
        print("importance-aware CA-CHARQ self-tests: PASS")
        return
    if not 0.0 <= args.importance_ratio <= 1.0:
        raise SystemExit("--importance-ratio must be between 0 and 1")
    if args.important_deadline <= 0.0:
        raise SystemExit("--important-deadline must be positive")
    if args.topology_plot_only is not None:
        summary = read_summary_csv(args.topology_plot_only)
        robustness_path = (
            args.topology_plot_only.parent
            / "topology_robustness_summary.csv"
        )
        robustness = (
            read_summary_csv(robustness_path)
            if robustness_path.exists()
            else None
        )
        figures = create_topology_plots(
            summary, args.output, robustness
        )
        if args.paper_figures:
            figures.extend(create_paper_topology_plots(summary, args.output))
        print(
            f"Created {len(figures)} topology figure files in "
            f"{(args.output / 'figures').resolve()}"
        )
        return
    if args.plot_only is not None:
        summary = read_summary_csv(args.plot_only)
        figures = create_plots(summary, args.output)
        if args.paper_figures:
            figures.extend(create_paper_plots(summary, args.output))
        print(f"Created {len(figures)} figure files in {(args.output / 'figures').resolve()}")
        return

    if args.topology_sweep:
        if args.quick:
            sim_time = args.sim_time or 600.0
            runs = args.runs or 2
        else:
            sim_time = args.sim_time or 3000.0
            runs = args.runs or 5
        protocols = args.protocol or list(PAPER_PROTOCOLS)
        seeds = list(range(runs))
        scenarios = topology_scenarios(
            args.topology_factor or PAPER_TOPOLOGY_FACTORS
        )
        print(
            f"Topology sensitivity: {len(scenarios)} scenarios x "
            f"{len(protocols)} protocols x {runs} seeds = "
            f"{len(scenarios) * len(protocols) * runs} runs, "
            f"sim_time={sim_time:g}s, SNR@600m={args.topology_snr:g}dB, "
            f"important={args.importance_ratio:.0%}, jobs={args.jobs}"
        )
        started = time.perf_counter()
        raw = run_topology_sweep(
            scenarios, protocols, args.topology_snr, sim_time, seeds,
            args.importance_ratio, args.important_deadline,
            max(1, args.jobs),
        )
        summary = aggregate_topology_results(raw)
        robustness = write_topology_results(
            raw, summary, args.output
        )
        figures = (
            [] if args.no_plots
            else create_topology_plots(
                summary, args.output, robustness
            )
        )
        if args.paper_figures and not args.no_plots:
            figures.extend(create_paper_topology_plots(summary, args.output))
        print(f"\nElapsed: {time.perf_counter() - started:.2f}s")
        print(f"Results: {args.output.resolve()}")
        if figures:
            print(f"Figures: {(args.output / 'figures').resolve()}")
        return

    if args.quick:
        snrs = args.snr or [2.0, 5.0, 8.0]
        sim_time = args.sim_time or 600.0
        runs = args.runs or 2
    else:
        snrs = args.snr or [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        sim_time = args.sim_time or 3000.0
        runs = args.runs or 5
    protocols = args.protocol or list(PAPER_PROTOCOLS)
    seeds = list(range(runs))
    print(
        f"Importance-aware CA-CHARQ: {len(protocols)} protocols x "
        f"{len(snrs)} SNR x {runs} seeds, sim_time={sim_time:g}s, "
        f"important={args.importance_ratio:.0%}, jobs={args.jobs}"
    )
    started = time.perf_counter()
    raw = run_sweep(
        snrs, protocols, sim_time, seeds,
        args.importance_ratio, args.important_deadline,
        max(1, args.jobs),
    )
    summary = aggregate_results(raw)
    write_results(raw, summary, args.output)
    figures = [] if args.no_plots else create_plots(summary, args.output)
    if args.paper_figures and not args.no_plots:
        figures.extend(create_paper_plots(summary, args.output))
    print_summary(summary)
    print(f"\nElapsed: {time.perf_counter() - started:.2f}s")
    print(f"Results: {args.output.resolve()}")
    if figures:
        print(f"Figures: {(args.output / 'figures').resolve()}")


if __name__ == "__main__":
    main()
