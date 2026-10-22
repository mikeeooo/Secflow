"""FastAPI boundary: the service supplies time and builds its own features."""

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4
import json
import os
import shutil
import tempfile

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select

from mia_demo.features.transactions import build_transaction_features
from mia_demo.ml.bundle import load_bundle
from mia_demo.risk.engine import assess
from mia_demo.schemas import PaymentEvent, PaymentRequest, RiskResult
from mia_demo.storage import Account, AccountEvent, Assessment, BatchFinding, DeviceSession, Event, Repository, ReviewAction, as_utc


class SessionInput(BaseModel):
    local_account_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)


class AccountEventInput(BaseModel):
    local_account_id: str = Field(min_length=1)
    event_type: str = Field(pattern="^password_reset$")


class DemoContextInput(BaseModel):
    local_account_id: str = Field(min_length=1)
    attempt_count: int = Field(default=5, ge=1, le=5)


class ReviewInput(BaseModel):
    action: Literal["approve", "reject"]
    note: str = Field(default="", max_length=500)


def _assessment_view(item: Assessment) -> dict:
    payment_status = "completed" if item.mock_submitted else ("awaiting_review" if item.review_status == "pending" else "blocked" if item.result["decision"] == "Block" or item.review_status == "rejected" else "pending")
    return dict(transaction_id=item.transaction_id, scored_at=as_utc(item.scored_at).isoformat(), request=item.request, feature_snapshot=item.feature_snapshot, result=item.result, processing_ms=item.processing_ms, mock_submitted=item.mock_submitted, payment_status=payment_status, review_status=item.review_status)


def _event_view(item: Event) -> dict:
    return {"transaction_id": item.transaction_id, "event_type": item.event_type, "observed_at": as_utc(item.observed_at).isoformat(), "sender_account_id": item.sender_account_id, "receiver_account_id": item.receiver_account_id, "receiver_psp": item.receiver_psp, "amount_bani": item.amount_bani, "currency": item.currency, "session_id": item.session_id}


def create_app(db_path: str | Path = "data/demo.sqlite3", model_path: str | Path = "artifacts/model.joblib", report_path: str | Path = "reports/evaluation.json", verify_threshold: float = 60, block_threshold: float = 85) -> FastAPI:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    repo = Repository(db_path)
    model_path = Path(model_path)
    try:
        bundle = load_bundle(model_path) if model_path.exists() else None
        model_error = None
    except Exception as error:
        bundle = None
        model_error = str(error)
    app = FastAPI(title="SecFlow MIA Demo", description="Simulated PSP decision service; no banking integration", version="0.1.0")
    app.state.repo = repo
    app.state.bundle = bundle

    @app.get("/health")
    def health():
        return {"status": "ok" if bundle else "model_unavailable", "model_version": bundle.version if bundle else None, "model_error": model_error, "simulation": True}

    @app.post("/sessions")
    def create_session(payload: SessionInput):
        with repo.Session() as db:
            if db.get(Account, payload.local_account_id) is None:
                raise HTTPException(404, "Contul local nu există")
        session_id = "SIM-" + uuid4().hex[:12]
        repo.insert_session(session_id, payload.local_account_id, payload.device_id, datetime.now(timezone.utc))
        return {"session_id": session_id, "local_account_id": payload.local_account_id, "device_id": payload.device_id}

    @app.post("/account-events")
    def create_account_event(payload: AccountEventInput):
        with repo.Session() as db:
            if db.get(Account, payload.local_account_id) is None:
                raise HTTPException(404, "Contul local nu există")
        repo.insert_account_event(payload.local_account_id, payload.event_type, datetime.now(timezone.utc))
        return {"status": "recorded", "event_type": payload.event_type}

    @app.post("/demo/context")
    def create_demo_context(payload: DemoContextInput):
        from datetime import timedelta

        with repo.Session() as db:
            if db.get(Account, payload.local_account_id) is None:
                raise HTTPException(404, "Contul local nu există")
        now = datetime.now(timezone.utc)
        with repo.lock:
            for index in range(payload.attempt_count):
                transaction_id = "CTX-" + uuid4().hex[:12]
                observed = now - timedelta(seconds=(payload.attempt_count - index) * 30)
                repo.insert_event(PaymentEvent(event_id=f"context-{transaction_id}", transaction_id=transaction_id, occurred_at=observed, observed_at=observed, event_type="attempt", sender_account_id=payload.local_account_id, receiver_account_id=f"DEMO-RECIPIENT-{index}", sender_psp="LOCAL", receiver_psp="PSP-1", amount_bani=1000, session_id="DEMO-CONTEXT"))
        return {"attempts_created": payload.attempt_count, "simulation": True, "payment_submitted": False}

    @app.post("/assessments")
    def create_assessment(request: PaymentRequest):
        with repo.lock:
            existing = repo.assessment(request.transaction_id)
            if existing is not None:
                return _assessment_view(existing)
            started = perf_counter()
            now = datetime.now(timezone.utc)
            with repo.Session() as db:
                sender = db.get(Account, request.sender_account_id)
                session = db.get(DeviceSession, request.session_id)
                if sender is None or sender.psp_id != "LOCAL":
                    raise HTTPException(422, "Expeditorul trebuie să fie un cont local existent")
                if session is None or session.local_account_id != request.sender_account_id or session.device_id != request.device_id:
                    raise HTTPException(422, "Sesiunea nu aparține contului sau dispozitivului")
                if request.receiver_psp == "LOCAL" and db.get(Account, request.receiver_account_id) is None:
                    raise HTTPException(422, "Destinatarul local nu există")
                if request.receiver_psp == "LOCAL" and request.receiver_account_id == request.sender_account_id:
                    raise HTTPException(422, "Transferul către același cont nu este permis")
                if sender.balance_bani < request.amount_bani:
                    raise HTTPException(422, "Sold insuficient în portofelul simulat")
            history = repo.history_for_account(request.sender_account_id)
            try:
                features = build_transaction_features(request, now, history, bundle.peer_median_bani if bundle else 10000)
                result = assess(features, bundle, verify_threshold, block_threshold) if bundle else RiskResult(score=0, decision="Pending", reasons=[{"code": "MODEL_UNAVAILABLE", "detail": "Modelul local nu este încă disponibil"}])
            except Exception:
                features = None
                result = RiskResult(score=0, decision="Pending", reasons=[{"code": "SCORING_ERROR", "detail": "Evaluarea a eșuat; cererea necesită verificare manuală"}])
            duration_ms = (perf_counter() - started) * 1000
            repo.save_assessment(request.transaction_id, now, request.model_dump(), features.model_dump() if features else {}, result.model_dump(), duration_ms)
            repo.insert_event(PaymentEvent(event_id=f"live-attempt-{request.transaction_id}", transaction_id=request.transaction_id, occurred_at=now, observed_at=now, event_type="attempt", sender_account_id=request.sender_account_id, receiver_account_id=request.receiver_account_id, sender_psp="LOCAL", receiver_psp=request.receiver_psp, amount_bani=request.amount_bani, session_id=request.session_id, initiation_method=request.initiation_method))
            if result.decision == "Permit":
                repo.submit_mock_payment(request.transaction_id, now)
            return _assessment_view(repo.assessment(request.transaction_id))

    @app.post("/assessments/{transaction_id}/reviews")
    def review(transaction_id: str, payload: ReviewInput):
        with repo.lock:
            item = repo.assessment(transaction_id)
            if item is None:
                raise HTTPException(404, "Evaluarea nu există")
            if item.result["decision"] != "Verify":
                raise HTTPException(409, "Doar deciziile Verify pot fi revizuite")
            desired = "approved" if payload.action == "approve" else "rejected"
            if item.review_status == desired:
                return _assessment_view(item)
            if item.review_status != "pending":
                raise HTTPException(409, "Evaluarea a fost deja revizuită")
            if payload.action == "approve" and not repo.submit_mock_payment(transaction_id, datetime.now(timezone.utc)):
                raise HTTPException(409, "Sold insuficient pentru transferul simulat")
            with repo.Session.begin() as db:
                db.get(Assessment, transaction_id).review_status = desired
                db.add(ReviewAction(transaction_id=transaction_id, action=desired, acted_at=datetime.now(timezone.utc), actor="demo_analyst", note=payload.note))
            return _assessment_view(repo.assessment(transaction_id))

    @app.post("/assessments/{transaction_id}/approve")
    def approve_legacy(transaction_id: str):
        return review(transaction_id, ReviewInput(action="approve"))

    @app.get("/assessments/{transaction_id}")
    def get_assessment(transaction_id: str):
        item = repo.assessment(transaction_id)
        if item is None:
            raise HTTPException(404, "Evaluarea nu există")
        result = _assessment_view(item)
        with repo.Session() as db:
            rows = db.scalars(select(ReviewAction).where(ReviewAction.transaction_id == transaction_id).order_by(ReviewAction.acted_at)).all()
            result["review_actions"] = [{"action": row.action, "note": row.note, "actor": row.actor, "acted_at": as_utc(row.acted_at).isoformat()} for row in rows]
        return result

    @app.get("/accounts")
    def accounts(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), search: str = ""):
        condition = Account.psp_id == "LOCAL"
        if search:
            condition = and_(condition, Account.account_id.contains(search.strip()))
        with repo.Session() as db:
            total = db.scalar(select(func.count()).select_from(Account).where(condition)) or 0
            rows = db.scalars(select(Account).where(condition).order_by(Account.account_id).offset((page - 1) * page_size).limit(page_size)).all()
            return {"total": total, "page": page, "page_size": page_size, "items": [{"account_id": row.account_id, "balance_bani": row.balance_bani, "opened_at": as_utc(row.opened_at).isoformat()} for row in rows]}

    @app.get("/accounts/{account_id}")
    def account_profile(account_id: str):
        with repo.Session() as db:
            account = db.get(Account, account_id)
            if account is None or account.psp_id != "LOCAL":
                raise HTTPException(404, "Contul local nu există")
            completed = Event.event_type == "completed"
            outgoing = db.scalar(select(func.coalesce(func.sum(Event.amount_bani), 0)).where(completed, Event.sender_account_id == account_id, Event.sender_psp == "LOCAL")) or 0
            incoming = db.scalar(select(func.coalesce(func.sum(Event.amount_bani), 0)).where(completed, Event.receiver_account_id == account_id, Event.receiver_psp == "LOCAL")) or 0
            counterparties = db.scalars(select(Event.receiver_account_id).where(completed, Event.sender_account_id == account_id).distinct().limit(20)).all()
            findings = db.scalars(select(BatchFinding).where(BatchFinding.local_account_id == account_id, BatchFinding.available_at <= datetime.now(timezone.utc)).order_by(BatchFinding.available_at.desc()).limit(10)).all()
            return {"account_id": account_id, "balance_bani": account.balance_bani, "opened_at": as_utc(account.opened_at).isoformat(), "incoming_bani": incoming, "outgoing_bani": outgoing, "counterparties": counterparties, "findings": [{"window_end": as_utc(row.window_end).isoformat(), "available_at": as_utc(row.available_at).isoformat(), "noise_flag": row.noise_flag, "cluster_label": row.cluster_label, "contextual_rule_flags": row.contextual_rule_flags} for row in findings]}

    @app.get("/accounts/{account_id}/activity")
    def account_activity(account_id: str, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
        with repo.Session() as db:
            account = db.get(Account, account_id)
            if account is None or account.psp_id != "LOCAL":
                raise HTTPException(404, "Contul local nu există")
            condition = or_(and_(Event.sender_account_id == account_id, Event.sender_psp == "LOCAL"), and_(Event.receiver_account_id == account_id, Event.receiver_psp == "LOCAL"))
            total = db.scalar(select(func.count()).select_from(Event).where(condition)) or 0
            rows = db.scalars(select(Event).where(condition).order_by(Event.observed_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
            return {"total": total, "page": page, "page_size": page_size, "items": [_event_view(row) for row in rows]}

    @app.get("/transactions")
    def transactions(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), search: str = "", decision: str = "", min_amount_bani: int | None = Query(default=None, ge=0), max_amount_bani: int | None = Query(default=None, ge=0), from_date: datetime | None = None, to_date: datetime | None = None, sort_by: Literal["time", "amount", "score"] = "time", sort_dir: Literal["asc", "desc"] = "desc"):
        condition = and_(Event.event_type == "attempt", Event.session_id != "", Event.session_id != "DEMO-CONTEXT")
        if search.strip():
            term = f"%{search.strip()}%"
            condition = and_(condition, or_(Event.transaction_id.ilike(term), Event.sender_account_id.ilike(term), Event.receiver_account_id.ilike(term)))
        if decision:
            condition = and_(condition, Assessment.result["decision"].as_string() == decision)
        if min_amount_bani is not None:
            condition = and_(condition, Event.amount_bani >= min_amount_bani)
        if max_amount_bani is not None:
            condition = and_(condition, Event.amount_bani <= max_amount_bani)
        if from_date is not None:
            condition = and_(condition, Event.observed_at >= from_date)
        if to_date is not None:
            condition = and_(condition, Event.observed_at <= to_date)
        sort_column = {"time": Event.observed_at, "amount": Event.amount_bani, "score": Assessment.result["score"].as_float()}[sort_by]
        order = sort_column.asc() if sort_dir == "asc" else sort_column.desc()
        with repo.Session() as db:
            base = select(Event, Assessment).outerjoin(Assessment, Assessment.transaction_id == Event.transaction_id).where(condition)
            total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
            rows = db.execute(base.order_by(order, Event.event_id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
            ids = [event.transaction_id for event, _ in rows]
            completed = set(db.scalars(select(Event.transaction_id).where(Event.transaction_id.in_(ids), Event.event_type == "completed")).all()) if ids else set()
            items = []
            for event, assessment in rows:
                status = "completed" if event.transaction_id in completed else "awaiting_review" if assessment and assessment.review_status == "pending" else "blocked" if assessment and (assessment.result["decision"] == "Block" or assessment.review_status == "rejected") else "attempt_only"
                items.append({**_event_view(event), "decision": assessment.result["decision"] if assessment else None, "score": assessment.result["score"] if assessment else None, "historical": assessment is None, "payment_status": status, "review_status": assessment.review_status if assessment else "not_applicable"})
            return {"total": total, "page": page, "page_size": page_size, "items": items}

    @app.get("/transactions/{transaction_id}")
    def transaction_detail(transaction_id: str):
        with repo.Session() as db:
            attempt = db.scalar(select(Event).where(Event.transaction_id == transaction_id, Event.event_type == "attempt").order_by(Event.observed_at).limit(1))
            if attempt is None:
                raise HTTPException(404, "Tranzacția nu există")
            account_id = attempt.sender_account_id
            timeline = db.scalars(select(Event).where(Event.observed_at <= attempt.observed_at, or_(Event.sender_account_id == account_id, Event.receiver_account_id == account_id)).order_by(Event.observed_at.desc()).limit(20)).all()
            assessment = db.get(Assessment, transaction_id)
            reviews = db.scalars(select(ReviewAction).where(ReviewAction.transaction_id == transaction_id).order_by(ReviewAction.acted_at)).all()
            finding = db.scalar(select(BatchFinding).where(BatchFinding.local_account_id == account_id, BatchFinding.available_at <= attempt.observed_at).order_by(BatchFinding.available_at.desc()).limit(1))
            return {"transaction": _event_view(attempt), "assessment": _assessment_view(assessment) if assessment else None, "timeline": [_event_view(row) for row in timeline], "review_actions": [{"action": row.action, "note": row.note, "acted_at": as_utc(row.acted_at).isoformat()} for row in reviews], "batch_finding": {"window_end": as_utc(finding.window_end).isoformat(), "available_at": as_utc(finding.available_at).isoformat(), "noise_flag": finding.noise_flag, "contextual_rule_flags": finding.contextual_rule_flags} if finding else None}

    @app.get("/activity")
    def activity():
        with repo.Session() as db:
            rows = db.execute(select(func.date(Event.observed_at), func.count()).where(Event.event_type == "attempt", Event.session_id != "", Event.session_id != "DEMO-CONTEXT").group_by(func.date(Event.observed_at)).order_by(func.date(Event.observed_at))).all()
            return [{"day": day, "attempts": count} for day, count in rows]

    @app.get("/overview")
    def overview(from_date: datetime | None = None, to_date: datetime | None = None):
        with repo.Session() as db:
            account_count = db.scalar(select(func.count()).select_from(Account)) or 0
            event_condition = and_(Event.event_type == "attempt", Event.session_id != "", Event.session_id != "DEMO-CONTEXT")
            assessment_condition = True
            if from_date is not None:
                event_condition = and_(event_condition, Event.observed_at >= from_date)
                assessment_condition = and_(assessment_condition, Assessment.scored_at >= from_date)
            if to_date is not None:
                event_condition = and_(event_condition, Event.observed_at <= to_date)
                assessment_condition = and_(assessment_condition, Assessment.scored_at <= to_date)
            request_count = db.scalar(select(func.count()).select_from(Event).where(event_condition)) or 0
            all_assessments = db.scalars(select(Assessment).where(assessment_condition)).all()
            recent = db.scalars(select(Assessment).where(assessment_condition).order_by(Assessment.scored_at.desc()).limit(8)).all()
            counts = {name: sum(a.result["decision"] == name for a in all_assessments) for name in ("Permit", "Verify", "Block", "Pending")}
            pending = sum(a.review_status == "pending" for a in all_assessments)
            daily = db.execute(select(func.date(Event.observed_at), func.count()).where(event_condition).group_by(func.date(Event.observed_at)).order_by(func.date(Event.observed_at))).all()
            return {"simulation": True, "accounts": account_count, "historical_requests": request_count, "assessments": len(all_assessments), "decision_counts": counts, "pending_reviews": pending, "daily_attempts": [{"day": day, "count": count} for day, count in daily], "recent": [_assessment_view(item) for item in recent], "model_version": bundle.version if bundle else None, "updated_at": datetime.now(timezone.utc).isoformat()}

    @app.get("/batch-findings")
    def batch_findings(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), account_id: str = "", noise_only: bool = False, sort_dir: Literal["asc", "desc"] = "desc"):
        now = datetime.now(timezone.utc)
        with repo.Session() as db:
            query = select(BatchFinding).where(BatchFinding.available_at <= now)
            if account_id:
                query = query.where(BatchFinding.local_account_id == account_id)
            if noise_only:
                query = query.where(BatchFinding.noise_flag == True)
            total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
            order = BatchFinding.available_at.asc() if sort_dir == "asc" else BatchFinding.available_at.desc()
            rows = db.scalars(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
            return {"total": total, "page": page, "page_size": page_size, "items": [{"run_id": row.run_id, "account_id": row.local_account_id, "window_end": as_utc(row.window_end).isoformat(), "available_at": as_utc(row.available_at).isoformat(), "cluster_label": row.cluster_label, "noise_flag": row.noise_flag, "contextual_rule_flags": row.contextual_rule_flags} for row in rows]}

    @app.get("/experiments")
    def experiments():
        path = Path(report_path)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "not_run", "simulation": True}

    return app


def _deployment_db_path() -> Path:
    """Give each Vercel instance a writable copy of the bundled synthetic demo."""
    source = Path(__file__).resolve().parents[2] / "data" / "demo.sqlite3"
    destination = Path(tempfile.gettempdir()) / "secflow-mia-demo.sqlite3"
    if not destination.exists():
        shutil.copyfile(source, destination)
    return destination


if os.environ.get("VERCEL"):
    _project_root = Path(__file__).resolve().parents[2]
    app = create_app(
        db_path=_deployment_db_path(),
        model_path=_project_root / "artifacts" / "model.joblib",
        report_path=_project_root / "reports" / "evaluation.json",
    )
else:
    app = create_app()
