"""Small SQLite repository and matching in-memory replay history."""

from datetime import datetime, timezone
from collections import defaultdict
from threading import RLock

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, and_, create_engine, insert, inspect, or_, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .schemas import PaymentEvent


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    account_id: Mapped[str] = mapped_column(String, primary_key=True)
    psp_id: Mapped[str] = mapped_column(String, default="LOCAL")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    balance_bani: Mapped[int] = mapped_column(Integer)


class Event(Base):
    __tablename__ = "payment_events"
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_type: Mapped[str] = mapped_column(String)
    sender_account_id: Mapped[str] = mapped_column(String, index=True)
    receiver_account_id: Mapped[str] = mapped_column(String, index=True)
    sender_psp: Mapped[str] = mapped_column(String)
    receiver_psp: Mapped[str] = mapped_column(String)
    amount_bani: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="MDL")
    session_id: Mapped[str] = mapped_column(String, default="")
    initiation_method: Mapped[str] = mapped_column(String, default="APP")


class DeviceSession(Base):
    __tablename__ = "sessions"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    local_account_id: Mapped[str] = mapped_column(String, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    device_id: Mapped[str] = mapped_column(String)
    authentication_result: Mapped[str] = mapped_column(String, default="success")


class AccountEvent(Base):
    __tablename__ = "account_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    local_account_id: Mapped[str] = mapped_column(String, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_type: Mapped[str] = mapped_column(String)


class Assessment(Base):
    __tablename__ = "assessments"
    transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request: Mapped[dict] = mapped_column(JSON)
    feature_snapshot: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    processing_ms: Mapped[float] = mapped_column(Float)
    mock_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String, default="none")


class BatchFinding(Base):
    __tablename__ = "batch_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    local_account_id: Mapped[str] = mapped_column(String, index=True)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cluster_label: Mapped[int] = mapped_column(Integer)
    noise_flag: Mapped[bool] = mapped_column(Boolean)
    contextual_rule_flags: Mapped[list] = mapped_column(JSON, default=list)


class EvaluationLabel(Base):
    __tablename__ = "evaluation_labels"
    transaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String)
    scenario_type: Mapped[str] = mapped_column(String)
    is_simulated_fraud: Mapped[bool] = mapped_column(Boolean)


class ReviewAction(Base):
    __tablename__ = "review_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    acted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String, default="demo_analyst")
    note: Mapped[str] = mapped_column(String, default="")


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class MemoryHistory:
    """One PSP's observable history; evaluation labels never enter this class."""

    def __init__(self, accounts: dict[str, dict] | None = None):
        self.accounts = accounts or {}
        self.events: list[PaymentEvent] = []
        self.sessions: list[dict] = []
        self.account_events: list[dict] = []
        self._events_by_account = defaultdict(list)
        self._sessions_by_account = defaultdict(list)
        self._account_events_by_account = defaultdict(list)
        self._cycles_cache: dict[datetime, set[str]] = {}

    def add_event(self, event: PaymentEvent):
        self.events.append(event)
        self._cycles_cache.clear()
        if event.sender_psp == "LOCAL":
            self._events_by_account[event.sender_account_id].append(event)
        if event.receiver_psp == "LOCAL" and event.receiver_account_id != event.sender_account_id:
            self._events_by_account[event.receiver_account_id].append(event)

    def add_payment(self, transaction_id, sender, receiver, amount_bani, observed_at, event_type="completed", sender_psp="LOCAL", receiver_psp="LOCAL", session_id=""):
        self.add_event(PaymentEvent(event_id=f"{transaction_id}-{len(self.events)}", transaction_id=transaction_id, occurred_at=observed_at, observed_at=observed_at, event_type=event_type, sender_account_id=sender, receiver_account_id=receiver, sender_psp=sender_psp, receiver_psp=receiver_psp, amount_bani=amount_bani, session_id=session_id))

    def add_session(self, session_id, account_id, device_id, observed_at, authentication_result="success"):
        row = dict(session_id=session_id, local_account_id=account_id, device_id=device_id, observed_at=observed_at, authentication_result=authentication_result)
        self.sessions.append(row)
        self._sessions_by_account[account_id].append(row)

    def add_account_event(self, account_id, event_type, observed_at):
        row = dict(local_account_id=account_id, event_type=event_type, observed_at=observed_at)
        self.account_events.append(row)
        self._account_events_by_account[account_id].append(row)

    def prior_events(self, account_id: str, as_of: datetime) -> list[PaymentEvent]:
        return [e for e in self._events_by_account[account_id] if e.observed_at < as_of]

    def device_seen(self, account_id: str, device_id: str, as_of: datetime, exclude_session_id: str = "") -> bool:
        return any(s["device_id"] == device_id and s["session_id"] != exclude_session_id and s["observed_at"] < as_of for s in self._sessions_by_account[account_id])

    def reset_seen(self, account_id: str, as_of: datetime, hours=24) -> bool:
        from datetime import timedelta
        return any(e["event_type"] == "password_reset" and as_of - timedelta(hours=hours) <= e["observed_at"] < as_of for e in self._account_events_by_account[account_id])

    def account_opened_at(self, account_id: str) -> datetime:
        return self.accounts[account_id]["opened_at"]

    def local_cycle_accounts(self, as_of: datetime) -> set[str]:
        """Accounts on a local directed transfer cycle of length 2-4 within 10 minutes."""
        if as_of in self._cycles_cache:
            return self._cycles_cache[as_of]
        from datetime import timedelta

        edges = defaultdict(list)
        for event in self.events:
            if event.event_type == "completed" and event.sender_psp == event.receiver_psp == "LOCAL" and as_of - timedelta(hours=24) <= event.observed_at < as_of:
                edges[event.sender_account_id].append((event.receiver_account_id, event.observed_at))
        found = set()

        def walk(start, current, path, times):
            if len(path) > 4:
                return
            for next_account, observed in edges.get(current, ()):
                if times and observed <= times[-1]:
                    continue
                if times and observed - times[0] > timedelta(minutes=10):
                    continue
                if next_account == start and len(path) >= 2:
                    found.update(path)
                elif next_account not in path and len(path) < 4:
                    walk(start, next_account, path + [next_account], times + [observed])

        for account_id in edges:
            walk(account_id, account_id, [account_id], [])
        self._cycles_cache[as_of] = found
        return found


class Repository:
    """Serialized local SQLite writes for a single-process university demo."""

    def __init__(self, path):
        self.engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        # The local demo may already have a database created by an earlier build.
        if "note" not in {column["name"] for column in inspect(self.engine).get_columns("review_actions")}:
            with self.engine.begin() as connection:
                connection.execute(text("ALTER TABLE review_actions ADD COLUMN note VARCHAR NOT NULL DEFAULT ''"))
        self.Session = sessionmaker(self.engine, expire_on_commit=False)
        self.lock = RLock()

    def history(self) -> MemoryHistory:
        with self.Session() as db:
            accounts = {a.account_id: dict(opened_at=as_utc(a.opened_at), balance_bani=a.balance_bani, psp_id=a.psp_id) for a in db.scalars(select(Account))}
            history = MemoryHistory(accounts)
            for e in db.scalars(select(Event).order_by(Event.observed_at, Event.event_id)):
                history.add_event(PaymentEvent.model_validate({name: (as_utc(getattr(e, name)) if name in {"occurred_at", "observed_at"} else getattr(e, name)) for name in PaymentEvent.model_fields}))
            for s in db.scalars(select(DeviceSession)):
                history.add_session(s.session_id, s.local_account_id, s.device_id, as_utc(s.observed_at), s.authentication_result)
            for e in db.scalars(select(AccountEvent)):
                history.add_account_event(e.local_account_id, e.event_type, as_utc(e.observed_at))
            return history

    def history_for_account(self, account_id: str) -> MemoryHistory:
        """Load only PSP-visible rows needed to score one local payer."""
        with self.Session() as db:
            account = db.get(Account, account_id)
            if account is None:
                raise ValueError("Unknown local account")
            history = MemoryHistory({account_id: dict(opened_at=as_utc(account.opened_at), balance_bani=account.balance_bani)})
            predicate = or_(and_(Event.sender_psp == "LOCAL", Event.sender_account_id == account_id), and_(Event.receiver_psp == "LOCAL", Event.receiver_account_id == account_id))
            for e in db.scalars(select(Event).where(predicate).order_by(Event.observed_at, Event.event_id)):
                history.add_event(PaymentEvent.model_validate({name: (as_utc(getattr(e, name)) if name in {"occurred_at", "observed_at"} else getattr(e, name)) for name in PaymentEvent.model_fields}))
            for s in db.scalars(select(DeviceSession).where(DeviceSession.local_account_id == account_id)):
                history.add_session(s.session_id, s.local_account_id, s.device_id, as_utc(s.observed_at), s.authentication_result)
            for e in db.scalars(select(AccountEvent).where(AccountEvent.local_account_id == account_id)):
                history.add_account_event(e.local_account_id, e.event_type, as_utc(e.observed_at))
            return history

    def assessment(self, transaction_id: str):
        with self.Session() as db:
            return db.get(Assessment, transaction_id)

    def insert_event(self, event: PaymentEvent):
        with self.lock, self.Session.begin() as db:
            db.add(Event(**event.model_dump()))

    def insert_accounts(self, accounts: dict[str, dict]):
        with self.lock, self.Session.begin() as db:
            for account_id, data in accounts.items():
                db.merge(Account(account_id=account_id, psp_id=data.get("psp_id", "LOCAL"), opened_at=data["opened_at"], balance_bani=data["balance_bani"]))

    def insert_session(self, session_id, account_id, device_id, observed_at):
        with self.lock, self.Session.begin() as db:
            db.add(DeviceSession(session_id=session_id, local_account_id=account_id, device_id=device_id, observed_at=observed_at))

    def insert_account_event(self, account_id, event_type, observed_at):
        with self.lock, self.Session.begin() as db:
            db.add(AccountEvent(local_account_id=account_id, event_type=event_type, observed_at=observed_at))

    def save_assessment(self, transaction_id, scored_at, request, features, result, processing_ms):
        with self.lock, self.Session.begin() as db:
            db.add(Assessment(transaction_id=transaction_id, scored_at=scored_at, request=request, feature_snapshot=features, result=result, processing_ms=processing_ms, review_status="pending" if result["decision"] == "Verify" else "none"))

    def submit_mock_payment(self, transaction_id: str, now: datetime) -> bool:
        """Apply a mock ledger transfer once; false means insufficient funds."""
        with self.lock, self.Session.begin() as db:
            assessment = db.get(Assessment, transaction_id)
            if assessment.mock_submitted:
                return True
            req = assessment.request
            sender = db.get(Account, req["sender_account_id"])
            if sender is None or sender.balance_bani < req["amount_bani"]:
                return False
            sender.balance_bani -= req["amount_bani"]
            if req["receiver_psp"] == "LOCAL":
                receiver = db.get(Account, req["receiver_account_id"])
                if receiver is not None:
                    receiver.balance_bani += req["amount_bani"]
            db.add(Event(event_id=f"live-complete-{transaction_id}", transaction_id=transaction_id, occurred_at=now, observed_at=now, event_type="completed", sender_account_id=req["sender_account_id"], receiver_account_id=req["receiver_account_id"], sender_psp="LOCAL", receiver_psp=req["receiver_psp"], amount_bani=req["amount_bani"], currency="MDL", session_id=req["session_id"], initiation_method=req["initiation_method"]))
            assessment.mock_submitted = True
            return True

    def seed_dataset(self, dataset, findings: list[dict] | None = None) -> bool:
        """Load a generated historical stream once; return false when already seeded."""
        with self.lock, self.Session.begin() as db:
            if db.scalar(select(Account.account_id).limit(1)) is not None:
                return False
            db.execute(insert(Account), [dict(account_id=account_id, psp_id="LOCAL", opened_at=datetime.fromisoformat(data["opened_at"]), balance_bani=dataset.closing_balances[account_id]) for account_id, data in dataset.accounts.items()])
            db.execute(insert(Event), [event.model_dump() for event in dataset.events])
            db.execute(insert(DeviceSession), [dict(session_id=row["session_id"], local_account_id=row["local_account_id"], observed_at=datetime.fromisoformat(row["observed_at"]), device_id=row["device_id"], authentication_result=row["authentication_result"]) for row in dataset.sessions])
            if dataset.account_events:
                db.execute(insert(AccountEvent), [dict(local_account_id=row["local_account_id"], observed_at=datetime.fromisoformat(row["observed_at"]), event_type=row["event_type"]) for row in dataset.account_events])
            if findings:
                db.execute(insert(BatchFinding), findings)
            return True
