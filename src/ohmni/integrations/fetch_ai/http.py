"""Narrow public gateway: signed ACP transport and expiring artifact capabilities."""
from __future__ import annotations

import asyncio
import json
import mimetypes

from ohmni.application.request_budget import BudgetExceeded

from .workspace import WorkspaceUnavailable


async def start_gateway(bridge, public_port=8080, sdk_port=8081):
    from aiohttp import ClientSession, ClientTimeout, web

    private_headers = {'Cache-Control': 'private, no-store', 'Referrer-Policy': 'no-referrer',
                       'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
                       'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"}

    @web.middleware
    async def errors(request, handler):
        try:
            response = await handler(request)
        except WorkspaceUnavailable as exc:
            response = web.json_response({'error': str(exc)}, status=410)
        except BudgetExceeded:
            response = web.json_response({'error': 'The shared AI limit has been reached. Try again later; your board is still available.'}, status=429)
        except web.HTTPException as exc:
            response = web.Response(status=exc.status, text=exc.text, headers=exc.headers)
        except (ValueError, TypeError):
            response = web.json_response({'error': 'The request could not be completed. Check your selection and try again.'}, status=400)
        except Exception:  # noqa: BLE001 - never expose provider or persistence details
            response = web.json_response({'error': 'Teaching is temporarily unavailable. Your board has not changed. Please try again.'}, status=503)
        if request.path.startswith(('/workspace', '/assets/')):
            response.headers.update(private_headers)
        return response

    app = web.Application(client_max_size=256 * 1024, middlewares=[errors])
    client = ClientSession(timeout=ClientTimeout(total=30))

    async def download(request):
        data = await asyncio.to_thread(bridge.download, request.match_info['token'])
        if data is None:
            raise web.HTTPNotFound(text='Download unavailable or expired. Ask the agent for FILES again.')
        return web.Response(body=data, headers={
            'Content-Type': 'application/zip',
            'Content-Disposition': 'attachment; filename="ohmni-build-package.zip"',
            'Cache-Control': 'private, no-store',
            'Referrer-Policy': 'no-referrer',
            'X-Content-Type-Options': 'nosniff',
        })

    async def transport(request):
        # Never proxy /connect, /disconnect, /messages, filesystem paths or the
        # demo HTTP API. Loopback forwarding must not widen inspector access.
        if (request.path == '/submit' and request.method in {'HEAD', 'POST', 'OPTIONS'}) or (
            request.path in {'/agent_info', '/health'} and request.method == 'GET'
        ):
            headers = {key: request.headers[key] for key in ('Content-Type', 'x-uagents-address') if key in request.headers}
            async with client.request(request.method, f'http://127.0.0.1:{sdk_port}{request.path}',
                                      data=await request.read(), headers=headers) as response:
                safe = {key: value for key, value in response.headers.items() if key.lower() in {
                    'content-type', 'x-uagents-status', 'x-uagents-response-time-hint',
                    'access-control-allow-origin', 'access-control-allow-methods', 'access-control-allow-headers'}}
                return web.Response(status=response.status, body=await response.read(), headers=safe)
        raise web.HTTPNotFound()

    def capability(request):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            raise WorkspaceUnavailable('Open the private workspace link from your Fetch conversation.')
        return auth[7:]

    async def workspace_data(request):
        return web.json_response(await asyncio.to_thread(bridge.board_workspace.read, capability(request)))

    async def teach(request):
        token = capability(request)
        await asyncio.to_thread(bridge.board_workspace.resolve, token)
        # Custom authorization header and JSON-only POST prevent cross-site form spending.
        if request.content_type != 'application/json':
            raise web.HTTPUnsupportedMediaType()
        if request.content_length is not None and request.content_length > 16384:
            raise web.HTTPRequestEntityTooLarge(max_size=16384, actual_size=request.content_length)
        raw = await request.read()
        if len(raw) > 16384:
            raise web.HTTPRequestEntityTooLarge(max_size=16384, actual_size=len(raw))
        payload = json.loads(raw)
        if not isinstance(payload, dict) or set(payload) != {'component', 'question'}:
            raise ValueError('Invalid question')
        result = await asyncio.to_thread(bridge.board_workspace.teach, token, payload['component'], payload['question'])
        return web.json_response(result)

    async def workspace_download(request):
        data = await asyncio.to_thread(bridge.board_workspace.download, capability(request))
        return web.Response(body=data, content_type='application/zip', headers={
            'Content-Disposition': 'attachment; filename="ohmni-build-package.zip"'})

    # Serve only explicit repository UI assets, never arbitrary local files or demo APIs.
    from scripts.demo_server import STATIC_ASSETS, WEB_ROOT
    web_root = WEB_ROOT  # Runtime package may live in site-packages; assets live beside scripts/.
    allowed = set(STATIC_ASSETS) | {'fetch-workspace.html', 'fetch-workspace.js', 'fetch-workspace.css'}

    async def asset(request):
        name = request.match_info.get('name', 'fetch-workspace.html')
        if name not in allowed:
            raise web.HTTPNotFound()
        path = web_root / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(web_root.resolve()):
            raise web.HTTPNotFound()
        return web.Response(body=path.read_bytes(), content_type=mimetypes.guess_type(name)[0] or 'application/octet-stream')

    app.router.add_get('/workspace/', asset)
    app.router.add_get('/assets/{name:.*}', asset)
    app.router.add_get('/workspace/api/board', workspace_data)
    app.router.add_post('/workspace/api/teach', teach)
    app.router.add_get('/workspace/api/download', workspace_download)
    app.router.add_get('/downloads/{token}/build-package.zip', download)
    app.router.add_route('*', '/{tail:.*}', transport)
    runner = web.AppRunner(app, access_log=None)  # Capability URLs are credentials; never log them.
    await runner.setup()
    try:
        await web.TCPSite(runner, '0.0.0.0', public_port).start()
    except Exception:
        await runner.cleanup()
        await client.close()
        raise
    return runner, client
