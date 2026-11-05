"""Backend-owned simulated transfer stream.

One producer task per backend process starts with the server. Browser tabs only read the feed
and call start/stop; they never run their own timers, so opening several tabs cannot multiply
submissions. The input generator builds payment *inputs* from observable history (recent
recipients, devices, amounts) plus a few unusual patterns; decisions always come from the
assessment policy, never from the generator.
"""

from __future__ import annotations

import asyncio
import logging
import math
import uuid
from collections import deque
from typing import Any

import numpy as np

from backend.schemas import SimulationRequest
from backend.service import SecFlowService
from storage.identities import FIRST_NAMES, LAST_NAMES
from storage.memory import utc_now_iso

log = logging.getLogger("secflow.stream")
BATCH_SIZES = {"continuous": 1, "batch_5": 5, "batch_10": 10, "batch_20": 20}
FOREIGN = ("US", "GB", "AE", "TR", "UA")


class InputGenerator:
    """Creates plausible payment inputs from what the service has observed so far."""

    def __init__(self, service: SecFlowService, seed: int = 7) -> None:
        self.service = service
        self.rng = np.random.default_rng(seed)
        history = service.state.history
        self.senders = [a for a in service.accounts if a in history.sender]
        weights = np.array([len(history.sender[a].keys) for a in self.senders], dtype=float)
        self.weights = weights / weights.sum()
        self.queue: deque[dict[str, Any]] = deque()

    def _sender(self) -> str:
        return str(self.senders[int(self.rng.choice(len(self.senders), p=self.weights))])

    def _typical_amount(self, sender: str) -> float:
        series = self.service.state.history.sender.get(sender)
        recent = sorted(series.amounts[-25:]) if series else [40.0]
        return recent[len(recent) // 2]

    def _known_recipient(self, sender: str) -> str:
        series = self.service.state.history.sender.get(sender)
        options = [r for r in (series.recipients[-30:] if series else []) if r != sender]
        return str(options[int(self.rng.integers(len(options)))]) if options else "CP-00001"

    def _new_name(self) -> str:
        return f"{FIRST_NAMES[int(self.rng.integers(len(FIRST_NAMES)))]} {LAST_NAMES[int(self.rng.integers(len(LAST_NAMES)))]}"

    def _amount(self, base: float, low: float, high: float) -> float:
        return round(max(1.0, base * float(self.rng.uniform(low, high)) * math.exp(self.rng.normal(0, 0.2))), 2)

    def next_payload(self) -> tuple[SimulationRequest, str | None]:
        """Return the next input and, for burst items, a token linking them to one beneficiary."""
        spec = self.queue.popleft() if self.queue else self._fresh()
        token = spec.pop("_burst", None)
        return SimulationRequest(request_id=f"LIVE-{uuid.uuid4().hex[:12]}", **spec), token

    def _fresh(self) -> dict[str, Any]:
        sender = self._sender()
        home = self.service.accounts[sender].home_country
        device = self.service.last_device(sender)
        base = self._typical_amount(sender)
        roll = float(self.rng.random())
        spec: dict[str, Any] = {
            "sender_id": sender, "device_id": device, "ip_country": home,
            "auth_method": str(self.rng.choice(["biometric", "biometric", "password", "password_otp"])),
            "failed_login_attempts": 1 if self.rng.random() < 0.03 else 0, "channel": "mobile_app",
        }
        if roll < 0.80:  # ordinary payment to a known recipient
            spec.update(recipient_id=self._known_recipient(sender), amount=self._amount(base, 0.7, 1.3))
        elif roll < 0.86:  # ordinary amount to someone new
            spec.update(new_recipient_name=self._new_name(), amount=self._amount(base, 0.8, 2.0))
        elif roll < 0.90:  # large planned purchase with strong authentication
            spec.update(recipient_id=self._known_recipient(sender), amount=self._amount(base, 6, 14),
                        auth_method="password_otp")
        elif roll < 0.94:  # takeover-like access pattern
            spec.update(new_recipient_name=self._new_name(), amount=self._amount(base, 3, 9), device_id=None,
                        failed_login_attempts=int(self.rng.integers(2, 5)), auth_method="password",
                        ip_country=str(self.rng.choice(FOREIGN)) if self.rng.random() < 0.5 else home)
        elif roll < 0.97:  # rapid burst to one new beneficiary
            name, token = self._new_name(), uuid.uuid4().hex
            for _ in range(int(self.rng.integers(3, 6))):  # later items pay the beneficiary the first one created
                self.queue.append({**spec, "new_recipient_name": name, "amount": self._amount(base, 0.8, 1.6),
                                   "_burst": token})
            spec = {**spec, "new_recipient_name": name, "amount": self._amount(base, 0.8, 1.6), "_burst": token}
        else:  # payment to a beneficiary with active trusted evidence, when one exists
            flagged = self.service.simulator_options(None)["flagged_beneficiaries"]
            if flagged:
                target = flagged[int(self.rng.integers(len(flagged)))]
                spec.update(recipient_id=target["id"], amount=self._amount(base, 0.6, 1.4))
            else:
                spec.update(recipient_id=self._known_recipient(sender), amount=self._amount(base, 0.7, 1.3))
        return spec


class StreamController:
    def __init__(self, service: SecFlowService, interval: float, batch_interval: float) -> None:
        self.service = service
        self.generator = InputGenerator(service)
        self.interval = interval
        self.batch_interval = batch_interval
        self.mode = "continuous"
        self.running = False
        self.produced = 0
        self.failures = 0
        self.last_error: str | None = None
        self.started_at: str | None = None
        self.last_tick_at: str | None = None
        self._task: asyncio.Task[None] | None = None
        self._wake = asyncio.Event()
        self._burst_recipients: dict[str, str] = {}

    def status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "mode": self.mode,
            "interval_seconds": self.interval if self.mode == "continuous" else self.batch_interval,
            "produced": self.produced,
            "failures": self.failures,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "last_tick_at": self.last_tick_at,
            "owner": "backend",
        }

    def ensure_task(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="secflow-stream")

    def start(self) -> dict[str, Any]:
        if not self.running:
            self.running = True
            self.started_at = utc_now_iso()
        self.ensure_task()
        self._wake.set()
        return self.status()

    def stop(self) -> dict[str, Any]:
        self.running = False  # checked before every single submission
        return self.status()

    def set_mode(self, mode: str) -> dict[str, Any]:
        self.mode = mode
        self._wake.set()
        return self.status()

    async def shutdown(self) -> None:
        self.running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def tick(self) -> int:
        """Submit one tick's worth of simulated requests; returns how many were committed."""
        committed = 0
        for _ in range(BATCH_SIZES[self.mode]):
            if not self.running:
                break
            payload, token = self.generator.next_payload()
            payload = self._resolve_burst(payload, token)
            try:
                detail, _ = await asyncio.to_thread(self.service.simulate, payload, "stream")
                if token is not None:
                    self._burst_recipients.setdefault(token, detail.recipient.id)
                self.produced += 1
                committed += 1
            except Exception as error:  # noqa: BLE001 - keep producing; surface the error in status
                self.failures += 1
                self.last_error = f"{type(error).__name__}: {error}"
                log.warning("Stream submission failed: %s", self.last_error)
        self.last_tick_at = utc_now_iso()
        return committed

    def _resolve_burst(self, payload: SimulationRequest, token: str | None) -> SimulationRequest:
        """Later items of a burst pay the beneficiary created by the first item."""
        if token is not None and token in self._burst_recipients:
            data = payload.model_dump()
            data.update(recipient_id=self._burst_recipients[token], new_recipient_name=None)
            return SimulationRequest(**data)
        return payload

    async def _loop(self) -> None:
        while True:
            if self.running:
                await self.tick()
                delay = self.interval if self.mode == "continuous" else self.batch_interval
            else:
                delay = 3600.0
            self._wake.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=delay)
            except TimeoutError:
                pass
