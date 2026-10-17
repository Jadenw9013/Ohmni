"""Owned, bounded chat orchestration over the existing planner and job runner.

No HTTP demo server is started. JobStore is reused from the repository runtime
so report lineage, restart recovery and artifact checks have one implementation.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from ohmni.application.conversation import ConversationPlanner
from ohmni.application.iteration import ProjectAssistant
from ohmni.application.project_store import ProjectWorkspaceLock
from ohmni.application.projects import preview_project
from ohmni.application.request_budget import (
    BudgetConfig,
    BudgetExceeded,
    BudgetUnavailable,
    RequestBudget,
)
from ohmni.synthesis import SynthesisBrief

from .service import supported_options_reply

LIMITATIONS = (
    "These are design files for human engineering/manufacturing review, not a physically tested device. "
    "Firmware is not included. USB-C supplies power only. Costs and catalog evidence have limitations."
)


def owner_key(sender: str, session: str) -> str:
    # Both come from the SDK's verified envelope, never message text or IDs.
    if not sender or len(sender) > 100 or UUID(str(session)).int == 0:
        raise ValueError("A signed sender and valid conversation session are required.")
    return hashlib.sha256(json.dumps([sender, str(session)]).encode()).hexdigest()


def review_plan(plan: dict) -> str:
    brief = plan['brief']
    sensors = ', '.join(x['part_id'] for x in brief['sensors']) or 'none'
    spi = ', '.join(x['part_id'] for x in brief['spi_devices']) or 'none'
    lines = [f"Proposed board: {brief['project_name']}", brief['description'],
             f"USB-C {brief['input_voltage_v']} V power; {brief['mcu_part_id']}; {brief['logic_voltage_v']} V logic.",
             f"Sensors: {sensors}. SPI devices: {spi}.",
             (f"Buttons: {brief['button_count']}; indicator LEDs: {brief['status_led_count']}; "
             f"programming header: {'included' if brief['include_programming_header'] else 'omitted'}."),
             f"Board: {brief['board_width_mm']} × {brief['board_height_mm']} mm, up to {brief['max_board_layers']} layers.",
             f"Hand soldering preferred: {'yes' if brief['hand_solderable_preferred'] else 'no'}; budget target: {brief['budget_usd']} USD (actual total unknown)."]
    if plan['stated']:
        lines += ['Your stated choices:'] + [f"- {x['field'].replace('_', ' ')}: {x['quote']}" for x in plan['stated']]
    lines += plan.get('design_notes', [])
    lines += ['AI/default choices to review: ' + ', '.join(field.replace('_', ' ') for field in plan['assumed_fields']), LIMITATIONS]
    if not plan['ready'] and not plan['questions']:
        lines += ['There are no actionable changes to confirm. Describe a specific change, or reply STATUS.']
    elif plan['questions']:
        lines += ['Before building, please answer:'] + [f"- {x}" for x in plan['questions']]
        lines += ['Reply with your answers or changes. No project has been saved and no build has started.']
    else:
        lines += [f"To save exactly this plan and generate its board, reply CONFIRM {plan['plan_id']}",
                  'Or reply with changes. Confirmation expires after 30 minutes.']
    return '\n\n'.join(lines)


def describe_result(job: dict) -> str:
    status = job['status']
    if status in {'queued', 'running'}:
        progress = job.get('progress', [])
        latest = progress[-1] if progress else {}
        return f"Build {job['job_id']}: {status}. Latest step: {latest.get('message', latest.get('stage', 'waiting for worker'))}. Reply STATUS for a fresh check; this does not rebuild."
    if status == 'failed':
        return f"Build {job['job_id']} failed ({job.get('error_code') or 'pipeline_failed'}). No current manufacturing package is available. Reply RETRY to explicitly retry the same confirmed revision, or describe a changed design."
    report = job.get('report') or {}
    lines = [f"Build {job['job_id']} finished. Engineering outcome: {report.get('project', {}).get('status', 'UNKNOWN')}."]
    requirements = report.get('requirements', [])
    for verdict in ('VIOLATED', 'UNKNOWN'):
        items = [x for x in requirements if x.get('status') == verdict]
        lines.append(f"Requirements {verdict}: {len(items)}.")
        lines += [f"- {x['label']}: {x.get('display_value', '')}. {x.get('detail', 'No supporting result available.')}" for x in items]
    lines += ['Verification:'] + [f"- {x['stage']}: {x['status']}. {x.get('detail', '')}" for x in report.get('verification_ladder', [])]
    lines += [LIMITATIONS, 'Reply FINDINGS to inspect these results again, or describe a change to prepare a new plan. Changes always need a new confirmation.']
    return '\n\n'.join(lines)


def fact_text(value) -> str:
    """Project only supplied report fields into readable text; invent no claims."""
    if isinstance(value, dict):
        keys = ('label', 'stage', 'status', 'display_value', 'detail', 'description', 'part', 'references', 'quantity')
        parts = [fact_text(value[key]) for key in keys if key in value]
        return '; '.join(parts) if parts else '; '.join(f"{key.replace('_', ' ')}: {fact_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return '; '.join(fact_text(item) for item in value)
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    return str(value)


class ChatProjectAssistant(ProjectAssistant):
    """Give the existing grounded selector individual report facts, not JSON blobs."""
    def _context(self, project_id, revision_id):
        context, _ = super()._context(project_id, revision_id)
        facts = []
        for fact in context['facts']:
            if fact['id'].startswith('report.') and isinstance(fact['value'], list):
                for index, item in enumerate(fact['value']):
                    facts.append({**fact, 'id': fact['id'] + '.' + str(index), 'value': fact_text(item)})
                if fact['id'] == 'report.requirements':
                    counts = {status: sum(row.get('status') == status for row in fact['value'])
                              for status in ('MET', 'VIOLATED', 'UNKNOWN')}
                    facts.append({**fact, 'id': 'report.requirements.summary', 'value': fact_text(counts)})
            else:
                facts.append(fact)
        context['facts'] = facts
        fingerprint = hashlib.sha256(json.dumps(context, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return context, fingerprint


class ChatBridge:
    def __init__(self, root: Path, provider, public_url: str, *, jobs=None, clock=time.time):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.public_url = public_url.rstrip('/')
        self.lock = threading.Lock()
        self.workspace = ProjectWorkspaceLock(self.root)
        self.path = self.root / 'fetch-sessions.sqlite3'
        self.jobs = jobs
        try:
            if jobs is None:
                from scripts.demo_server import JobStore
                self.jobs = JobStore(self.root, max_active_jobs=1)
                self.jobs.enable_persistence()
            self.projects = self.jobs.project_store
            self.planner = ConversationPlanner(provider, self.projects)
            self.assistant = ChatProjectAssistant(provider, self.projects, self.jobs)
            self.instance_id = secrets.token_hex(16)
            self.budget = RequestBudget(self.root / 'fetch-budget.sqlite3', BudgetConfig(daily_limit=50, max_in_flight=1))
            with self.db() as db:
                db.executescript('''
                    CREATE TABLE IF NOT EXISTS sessions(owner TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS messages(owner TEXT, id TEXT, reply TEXT, created REAL, PRIMARY KEY(owner,id));
                    CREATE TABLE IF NOT EXISTS downloads(digest TEXT PRIMARY KEY, job TEXT, expires REAL);
                ''')
            from .workspace import BoardWorkspace
            self.board_workspace = BoardWorkspace(self, provider)
            self.path.chmod(0o600)
        except Exception:
            self.workspace.close()
            raise

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def close(self):
        self.jobs.stop()
        self.workspace.close()

    def _load(self, db, owner):
        row = db.execute('SELECT data FROM sessions WHERE owner=?', (owner,)).fetchone()
        return json.loads(row[0]) if row else {}

    def _save(self, db, owner, state):
        db.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)', (owner, json.dumps(state), self.clock()))

    def handle(self, sender, session, message_id, text):
        owner = owner_key(sender, session)
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 2000:
            return 'Please send 1–2,000 characters. No plan or build was started.'
        if not self.lock.acquire(blocking=False):
            return 'Another chat operation is in progress. Please retry shortly; this message did not start a build.'
        try:
            with self.db() as db:
                db.execute('DELETE FROM messages WHERE created<?', (self.clock() - 86400,))
                existing = db.execute('SELECT reply FROM messages WHERE owner=? AND id=?', (owner, str(message_id))).fetchone()
                if existing:
                    return existing[0] or 'This message was interrupted. Send a new message; no duplicate operation will be launched.'
                count = db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
                if count >= 128 and not db.execute('SELECT 1 FROM sessions WHERE owner=?', (owner,)).fetchone():
                    return 'Conversation capacity reached. Please contact the presenter.'
                if db.execute('SELECT COUNT(*) FROM messages').fetchone()[0] >= 4096:
                    return 'Message capacity reached. Try again tomorrow; no operation started.'
                db.execute('INSERT INTO messages VALUES(?,?,NULL,?)', (owner, str(message_id), self.clock()))
                state = self._load(db, owner)
                self._save(db, owner, state)
            try:
                reply = self._operate(owner, state, text.strip())
            except (BudgetExceeded, BudgetUnavailable):
                reply = 'The AI planning budget is busy or exhausted. No new plan/build was started. STATUS still works without model charges.'
            except Exception:  # noqa: BLE001 - public boundary never reflects provider or private failures
                # Never reflect provider exceptions, credentials, paths or raw message data.
                reply = 'This operation could not finish. No unreviewed design will be built. Try STATUS for an existing job, or send your requirements again.'
            with self.db() as db:
                self._save(db, owner, state)
                db.execute('UPDATE messages SET reply=? WHERE owner=? AND id=?', (reply, owner, str(message_id)))
            return reply
        finally:
            self.lock.release()

    def _operate(self, owner, state, text):
        command = text.casefold()
        if command in {'help', 'options', 'supported options'}:
            return supported_options_reply(text).replace(
                'This first connectivity release lists options only: it has not saved a plan or started a build. Planning, explicit confirmation and build tools are the next integration step.',
                'Describe your idea to prepare a plan. Review it, answer questions, then use its exact CONFIRM code to save and build. STATUS and FINDINGS inspect your latest build without model charges.')
        if command in {'status', 'findings', 'files', 'download', 'open', 'view', 'workspace'}:
            return self.result(owner)
        if command == 'retry':
            if not state.get('job_id') or self.jobs.get(state['job_id'])['status'] != 'failed':
                return 'There is no failed build in this conversation to retry. Reply STATUS.'
            return self._start(state)
        match = re.fullmatch(r'confirm\s+([0-9a-f]{16})', command)
        if match:
            plan = state.get('plan')
            if not plan or match[1] != plan['plan_id']:
                return 'That confirmation does not match the latest plan in this conversation. Describe your idea or request changes to review a new plan.'
            if state.get('project_id') and not state.get('pending_change'):
                return self.result(owner) if state.get('job_id') else self._start(state)
            if state.get('plan_expires', 0) <= self.clock():
                return 'That draft expired. Describe your idea again to prepare a new plan; no build was started.'
            if state.get('pending_change') and state.get('assistant_epoch') != self.instance_id:
                return 'That change proposal expired when the service restarted. Ask for your changes again to review a fresh proposal.'
            if not plan['ready'] or plan['questions']:
                return 'Please answer the unresolved questions first. No build was started.'
            brief = SynthesisBrief.model_validate_json(json.dumps(plan['brief']), strict=True)
            if brief.fingerprint != plan['brief_fingerprint']:
                raise ValueError('Draft changed')
            preview = preview_project(brief).model_dump(mode='json')
            if state.get('pending_change'):
                project = self.assistant.apply(state['project_id'], state['revision_id'], plan['plan_id'])
            else:
                project = self.projects.save_revision(brief.model_dump(mode='json'), brief.fingerprint, preview, planning_receipt=plan)
            state.pop('job_id', None)
            state.pop('assistant_turn_id', None)
            state['pending_change'] = False
            state.update(project_id=project['project_id'], revision_id=project['revisions'][-1]['revision_id'])
            # Persist the confirmed association BEFORE launching the worker. A crash
            # can leave a saved revision, never an unowned running build.
            with self.db() as db:
                self._save(db, owner, state)
            return self._start(state)
        if command.startswith('confirm') or command in {'yes', 'build', 'generate', 'generate board'}:
            return 'Review the latest plan and reply with its exact CONFIRM code. A general yes cannot start a build.'
        if state.get('project_id') and not command.startswith('new '):
            with self.budget.admit('assistant'):
                turn = self.assistant.ask(state['project_id'], state['revision_id'], text,
                                          state.get('assistant_turn_id') if state.get('assistant_epoch') == self.instance_id and state.get('assistant_expires', 0) > self.clock() else None)
            state['assistant_turn_id'] = turn['turn_id']
            state['assistant_epoch'] = self.instance_id
            state['assistant_expires'] = self.clock() + 1800
            if turn['kind'] != 'change':
                state['pending_change'] = False
                facts = ['- ' + fact['label'] + ': ' + fact_text(fact['value'])
                         for fact in turn['facts']]
                return '\n\n'.join(['Recorded engineering facts relevant to your question:', *facts,
                    'These facts come from the saved brief and actual run, not new measurements. No new build started.']
                    if facts else ['The existing evidence cannot answer that question. No new build started.'])
            brief = SynthesisBrief.model_validate_json(json.dumps(turn['brief']), strict=True)
            plan = {'plan_id': turn['turn_id'], 'brief': turn['brief'], 'brief_fingerprint': brief.fingerprint,
                    'messages': turn['messages'], 'stated': [], 'assumed_fields': sorted(SynthesisBrief.model_fields),
                    'questions': turn['questions'], 'ready': turn['ready']}
            state.update(plan=plan, pending_change=True, plan_expires=self.clock() + 1800)
            changes = '\n'.join(f"- {change['field']}: {change['before']} → {change['after']}" for change in turn['changes'])
            return 'Changes proposed to your existing revision:\n' + changes + '\n\n' + review_plan(plan)
        parent = state.get('plan') if not command.startswith('new ') else None
        # A bounded transcript is reconstructed into a new proposal. Draft state
        # survives restart without depending on the planner\'s ephemeral ID cache.
        messages = [*(parent['messages'] if parent else []), text]
        combined = '\n'.join(messages)
        if len(messages) > 8 or len(combined) > 2000:
            return 'This planning conversation is full. Send NEW followed by your combined requirements (up to 2,000 characters).'
        if command.startswith('new '):
            combined = text[4:]
        with self.budget.admit('planner'):
            plan = self.planner.propose(combined)
        plan['messages'] = messages if not command.startswith('new ') else [combined]
        # Invalidate any former confirmation as soon as a new plan is displayed.
        state.clear()
        state.update(plan=plan, plan_expires=self.clock() + 1800)
        return review_plan(plan)

    def _start(self, state):
        revision = self.projects.revision(state['project_id'], state['revision_id'])
        previous = revision.get('job_id')
        if previous and self.jobs.get(previous)['status'] != 'failed':
            state['job_id'] = previous
            return describe_result(self.jobs.get(previous))
        with self.budget.admit('generation'):
            job_id = self.jobs.start_revision(state['project_id'], state['revision_id'])
        state['job_id'] = job_id
        return f"Confirmed the reviewed plan. Build {job_id} is queued/running. I will send the result here; reply STATUS at any time. No firmware or physical testing is included."

    def latest_job(self, owner):
        with self.db() as db:
            return self._load(db, owner).get('job_id')

    def result(self, owner):
        with self.db() as db:
            state = self._load(db, owner)
        job_id = state.get('job_id')
        # Recover a worker launched immediately before a process interruption.
        if not job_id and state.get('project_id'):
            revision = self.projects.revision(state['project_id'], state['revision_id'])
            job_id = revision.get('job_id') if revision else None
            if job_id:
                state['job_id'] = job_id
                with self.db() as db:
                    self._save(db, owner, state)
        if not job_id:
            return 'This conversation has no generated board yet. Describe your idea, review the plan and use its CONFIRM code.'
        job = self.jobs.get(job_id)
        if job is None:
            return 'The recorded job is unavailable. No replacement build was started.'
        reply = describe_result(job)
        if job['status'] == 'complete':
            if state.get('project_id') and state.get('revision_id'):
                workspace_url = self.board_workspace.issue(owner, state)
                reply += (f'\n\n[Open your board in Ohmni — 3D view and component tutor]({workspace_url})'
                          '\nSelect a component to learn about it. This private workspace link lasts 24 hours; '
                          'anyone with it can view the board and use its tutor. Ask OPEN for a fresh link.')
            check, _ = self.jobs.read_build_package(job_id)
            if check == 'current':
                token = secrets.token_urlsafe(32)
                with self.db() as db:
                    db.execute('DELETE FROM downloads WHERE expires<?', (self.clock(),))
                    db.execute('INSERT INTO downloads VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), job_id, self.clock() + 3600))
                reply += (f'\n\n[Download all design and fabrication files (ZIP)]({self.public_url}/downloads/{token}/build-package.zip)'
                          '\n\nThis private bearer link expires in one hour. Anyone you share it with can download these files.')
            else:
                reply += '\n\nDownloads withheld: the artifact package is missing, stale, or does not pass release checks.'
        return reply

    def download(self, token):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            return None
        with self.db() as db:
            row = db.execute('SELECT job,expires FROM downloads WHERE digest=?', (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row or row[1] <= self.clock():
            return None
        status, data = self.jobs.read_build_package(row[0])
        return data if status == 'current' else None
