"""Private main-UI sessions over the same project store and engineering services.

The loopback application is never public. Every forwarded path is classified and
owned project/job/plan access is checked before it reaches existing handlers.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
from urllib.parse import urlsplit

COOKIE = 'ohmni_workspace'
ID = r'[0-9a-f]{16}'
JOB = r'[0-9a-f]{12}'


class AccessDenied(ValueError):
    pass


class ConnectedWorkspace:
    def __init__(self, bridge):
        self.bridge = bridge
        self.server = None
        self.thread = None
        self.lock = threading.RLock()
        self.main_url = os.environ.get('OHMNI_MAIN_UI_URL', 'https://ohmni-yvnd.vercel.app').rstrip('/')
        with bridge.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS ui_sessions(digest TEXT PRIMARY KEY, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS ui_members(session TEXT, project TEXT, PRIMARY KEY(session,project));
                CREATE TABLE IF NOT EXISTS ui_claims(digest TEXT PRIMARY KEY, project TEXT NOT NULL, expires REAL NOT NULL, claimed_by TEXT);
                CREATE TABLE IF NOT EXISTS ui_imported_teaching(digest TEXT, component TEXT, PRIMARY KEY(digest,component));
                CREATE TABLE IF NOT EXISTS ui_plans(id TEXT PRIMARY KEY, session TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS project_chat(id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL,
                    revision TEXT NOT NULL, channel TEXT NOT NULL, content TEXT NOT NULL, created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS project_chat_lookup ON project_chat(project,revision,channel,id);
            ''')

    @staticmethod
    def digest(token):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            raise AccessDenied('Open Ohmni again from your Fetch conversation to reconnect.')
        return hashlib.sha256(token.encode()).hexdigest()

    def session(self, token):
        key = self.digest(token)
        with self.bridge.db() as db:
            row = db.execute('SELECT expires FROM ui_sessions WHERE digest=?', (key,)).fetchone()
        if not row or row[0] <= self.bridge.clock():
            raise AccessDenied('Your workspace session expired. Send OPEN in Fetch to reconnect your saved projects.')
        return key

    def connect(self, token=None, claim=None):
        # A valid browser can link another of its projects without losing earlier ones.
        try:
            key = self.session(token)
        except AccessDenied:
            token = secrets.token_urlsafe(32)
            key = self.digest(token)
        with self.bridge.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = None
            if claim is not None:
                row = db.execute('SELECT project,expires,claimed_by FROM ui_claims WHERE digest=?', (self.digest(claim),)).fetchone()
                if not row or row[1] <= self.bridge.clock() or row[2] not in (None, key):
                    raise AccessDenied('That connection link expired or was already used. Send OPEN in Fetch for a fresh link.')
            db.execute('INSERT OR REPLACE INTO ui_sessions VALUES(?,?)', (key, self.bridge.clock() + 180 * 86400))
            if row:
                db.execute('INSERT OR IGNORE INTO ui_members VALUES(?,?)', (key, row[0]))
                db.execute('UPDATE ui_claims SET claimed_by=? WHERE digest=?', (key, self.digest(claim)))
                # Bring conversations from the earlier read-only viewer into the
                # same durable revision history, once, without widening old links.
                old = db.execute('SELECT t.digest,t.component,t.messages,w.revision FROM teaching t JOIN workspaces w ON w.digest=t.digest WHERE w.project=? ORDER BY w.expires', (row[0],)).fetchall()
                for digest, component, messages, revision in old:
                    if db.execute('SELECT 1 FROM ui_imported_teaching WHERE digest=? AND component=?', (digest,component)).fetchone():
                        continue
                    turns = json.loads(messages)
                    stable = f'{row[0]}:{revision}'
                    recent = db.execute('SELECT messages FROM teaching WHERE digest=? AND component=?', (stable,component)).fetchone()
                    combined = [*(json.loads(recent[0]) if recent else []), *turns]
                    db.execute('INSERT OR REPLACE INTO teaching VALUES(?,?,?)', (stable,component,json.dumps(combined[-8:])))
                    for index in range(0, len(turns)-1, 2):
                        content = {'message': turns[index]['text'], 'answer': {'explanation': turns[index+1]['text'], 'sources': [], 'unknowns': []}}
                        db.execute('INSERT INTO project_chat(project,revision,channel,content,created) VALUES(?,?,?,?,?)', (row[0],revision,'component:'+component,json.dumps(content),self.bridge.clock()))
                    db.execute('INSERT INTO ui_imported_teaching VALUES(?,?)', (digest,component))
        if row:
            self.seed_project(row[0])
        return token, row[0] if row else None

    def issue(self, owner, state):
        # Only the bridge's signed conversation can mint a new edit-capable claim.
        with self.bridge.db() as db:
            saved = self.bridge._load(db, owner)
            if saved.get('project_id') != state.get('project_id'):
                raise AccessDenied('Project association unavailable.')
            token = secrets.token_urlsafe(32)
            db.execute('DELETE FROM ui_claims WHERE expires<=?', (self.bridge.clock(),))
            db.execute('INSERT INTO ui_claims VALUES(?,?,?,NULL)', (self.digest(token), state['project_id'], self.bridge.clock() + 1800))
        return f'{self.main_url}/#connect={token}'

    def owns(self, session, project):
        with self.bridge.db() as db:
            owned = db.execute('SELECT 1 FROM ui_members WHERE session=? AND project=?', (session, project)).fetchone()
        if not owned:
            raise AccessDenied('This project is not connected to your workspace.')

    def add_project(self, session, project):
        with self.bridge.db() as db:
            db.execute('INSERT OR IGNORE INTO ui_members VALUES(?,?)', (session, project))

    def record(self, project, revision, channel, value):
        with self.bridge.db() as db:
            db.execute('INSERT INTO project_chat(project,revision,channel,content,created) VALUES(?,?,?,?,?)',
                       (project, revision, channel, json.dumps(value), self.bridge.clock()))

    def history(self, project, revision, channel, before=None):
        with self.bridge.db() as db:
            rows = db.execute('SELECT id,content FROM project_chat WHERE project=? AND revision=? AND channel=? AND id<? ORDER BY id DESC LIMIT 51',
                              (project, revision, channel, before or 2**63-1)).fetchall()
        page = rows[:50]
        return {'messages': [{'id': n, **json.loads(content)} for n, content in reversed(page)],
                'before': page[-1][0] if len(rows) > 50 else None}

    def seed_project(self, project_id):
        project = self.bridge.projects.get(project_id)
        for revision in (project or {}).get('revisions', []):
            messages = revision.get('planning_receipt', {}).get('messages', [])
            with self.bridge.db() as db:
                if db.execute('SELECT 1 FROM project_chat WHERE project=? AND revision=? AND channel=?', (project_id, revision['revision_id'], 'board')).fetchone():
                    continue
                for message in messages:
                    if not isinstance(message, str):
                        continue
                    value = {'source': 'Saved plan', 'message': message,
                             'reply': f"Planning request retained with revision {revision['number']}. Its saved brief records the confirmed choices."}
                    db.execute('INSERT INTO project_chat(project,revision,channel,content,created) VALUES(?,?,?,?,?)', (project_id,revision['revision_id'],'board',json.dumps(value),self.bridge.clock()))

    def record_fetch(self, owner, state, message, reply):
        if not state.get('project_id') or not state.get('revision_id'):
            return
        self.seed_project(state['project_id'])
        # Never persist bearer credentials in chat history returned to browsers.
        reply = re.sub(r'https?://[^\s)]+(?:#connect=|#access=|/downloads/)[^\s)]+', '[private link omitted]', reply)
        self.record(state['project_id'], state['revision_id'], 'board', {'source': 'Fetch', 'message': message, 'reply': reply})

    def start_server(self):
        with self.lock:
            if self.server is not None:
                return self.server
            from scripts.demo_server import DemoHandler, DemoHTTPServer
            self.server = DemoHTTPServer(('127.0.0.1', 0), DemoHandler, store=self.bridge.jobs,
                                         ai_budget=self.bridge.budget, shared_bridge=self.bridge)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return self.server

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=5)

    def authorize(self, session, method, path, payload):
        """Exhaustive route classification; IDs in bodies cannot bypass ownership."""
        if method == 'GET' and path in {'/api/health', '/api/project-options', '/api/projects', '/api/components', '/api/behavior', '/api/exercises/sensor-rail'}:
            return
        if method == 'POST' and path == '/api/projects':
            return
        if method == 'POST' and path == '/api/project-plans':
            parent = payload.get('parent_id')
            if parent:
                self.owns_plan(session, parent)
            return
        match = re.fullmatch(rf'/api/project-plans/({ID})/confirm', path)
        if method == 'POST' and match:
            self.owns_plan(session, match[1])
            return
        match = re.fullmatch(rf'/api/projects/({ID})(?:/revisions(?:/({ID})/(assistant(?:/{ID}/apply)?|run|history|teach))?)?', path)
        if match:
            self.owns(session, match[1])
            if method == 'GET' and (not match[3] or match[3] == 'history'):
                return
            if method == 'POST' and (path.endswith('/revisions') or match[3] in {'assistant', 'run', 'teach'} or (match[3] or '').endswith('/apply')):
                return
        match = re.fullmatch(rf'/api/(?:jobs/({JOB})(?:/circuit)?|artifacts/({JOB})/[^/]+)', path)
        if method == 'GET' and match:
            lineage = self.bridge.projects.job_revision(match[1] or match[2])
            if not lineage:
                raise AccessDenied('Build unavailable.')
            self.owns(session, lineage['project_id'])
            return
        if (method == 'GET' and re.fullmatch(r'/api/behavior/OHM-[0-9]{3}', path)) or (
            method == 'POST' and (re.fullmatch(r'/api/behavior/OHM-[0-9]{3}/run', path) or path in {'/api/behavior/design/run', '/api/exercises/sensor-rail'})):
            return
        raise AccessDenied('This operation is not available in the connected workspace.')

    def owns_plan(self, session, plan):
        with self.bridge.db() as db:
            row = db.execute('SELECT session FROM ui_plans WHERE id=?', (plan,)).fetchone()
        if not row or row[0] != session:
            raise AccessDenied('That draft belongs to another workspace.')


async def register_connected(app, bridge, client):
    import asyncio

    from aiohttp import web

    connected = bridge.connected

    def mutation_guard(request):
        if request.method != 'POST':
            return
        if request.headers.get('X-Ohmni-Client') != 'main-ui' or request.content_type != 'application/json':
            raise AccessDenied('Open this action in Ohmni.')
        configured = urlsplit(connected.main_url)
        allowed_origin = f'{configured.scheme}://{configured.netloc}'
        origin = request.headers.get('Origin')
        local_origin = f'{request.scheme}://{request.host}'
        if origin and origin not in {allowed_origin, local_origin}:
            raise AccessDenied('This origin cannot change your workspace.')

    async def route(request):
        mutation_guard(request)
        path = request.path.removeprefix('/connected')
        payload = await request.json() if request.method == 'POST' else {}
        if not isinstance(payload, dict):
            raise TypeError('Expected an object')
        if path == '/session' and request.method == 'POST':
            if set(payload) - {'claim'}:
                raise ValueError('Unexpected session fields')
            token, project = await asyncio.to_thread(connected.connect, request.cookies.get(COOKIE), payload.get('claim'))
            response = web.json_response({'connected': True, 'project_id': project})
            response.set_cookie(COOKIE, token, httponly=True, secure=request.host not in {'localhost', '127.0.0.1'} and not request.host.startswith(('localhost:', '127.0.0.1:')), samesite='Lax', max_age=180*86400, path='/')
            return response
        session = connected.session(request.cookies.get(COOKIE))
        connected.authorize(session, request.method, path, payload)
        server = await asyncio.to_thread(connected.start_server)
        identity = server._identity()
        history_match = re.fullmatch(rf'/api/projects/({ID})/revisions/({ID})/(history|teach)', path)
        if history_match:
            project, revision, action = history_match.groups()
            if not bridge.projects.revision(project, revision):
                raise AccessDenied('Revision unavailable.')
            if action == 'history' and request.method == 'GET':
                channel = request.query.get('channel', 'board')
                before = int(request.query['before']) if 'before' in request.query else None
                data = connected.history(project, revision, channel, before)
                # Old proposals remain visible but cannot be re-applied after expiration/restart.
                for item in data['messages']:
                    if 'turn' in item:
                        item['turn']['ready'] = False
                return web.json_response({**data, **identity})
            if action == 'teach' and request.method == 'POST':
                if set(payload) != {'component', 'question', *identity} or any(payload[k] != v for k, v in identity.items()):
                    raise ValueError('Stale or invalid request')
                answer = await asyncio.to_thread(bridge.board_workspace.teach, None, payload['component'], payload['question'], project_revision=(project, revision))
                connected.record(project, revision, 'component:' + payload['component'], {'message': payload['question'], 'answer': answer})
                return web.json_response({'answer': answer, **identity})
        # The existing app handlers remain the sole implementation of edits,
        # generation, release gates, supported options and simulation contracts.
        headers = {key: value for key, value in request.headers.items() if key.lower() in {
            'content-type', 'x-ohmni-server-instance', 'x-ohmni-api-version', 'x-ohmni-ui-version'}}
        async with client.request(request.method, f'http://127.0.0.1:{server.server_port}{path}' + ('?' + request.query_string if request.query_string else ''),
                                  headers=headers, json=payload if request.method == 'POST' else None,
                                  timeout=__import__('aiohttp').ClientTimeout(total=120)) as response:
            raw = await response.read()
            response_headers = {k: v for k, v in response.headers.items() if k.lower() in {'content-type', 'content-disposition'}}
            if response.status < 300 and 'application/json' in response.headers.get('Content-Type', ''):
                data = json.loads(raw)
                if path == '/api/projects' and request.method == 'GET':
                    with bridge.db() as db:
                        projects = {r[0] for r in db.execute('SELECT project FROM ui_members WHERE session=?', (session,))}
                    data['projects'] = [p for p in data['projects'] if p['project_id'] in projects]
                if 'project' in data and request.method == 'POST':
                    connected.add_project(session, data['project']['project_id'])
                    connected.seed_project(data['project']['project_id'])
                if 'plan' in data:
                    with bridge.db() as db:
                        db.execute('INSERT OR REPLACE INTO ui_plans VALUES(?,?)', (data['plan']['plan_id'], session))
                match = re.fullmatch(rf'/api/projects/({ID})/revisions/({ID})/assistant', path)
                if match and 'turn' in data:
                    connected.record(match[1], match[2], 'board', {'source': 'Ohmni', 'message': payload['message'], 'turn': data['turn']})
                raw = json.dumps(data).encode()
            return web.Response(status=response.status, body=raw, headers=response_headers)

    app.router.add_route('*', '/connected/{tail:.*}', route)
    async def cleanup(_app):
        await asyncio.to_thread(connected.close)
    app.on_cleanup.append(cleanup)
