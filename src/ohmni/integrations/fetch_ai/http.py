"""Narrow public gateway: signed ACP transport and expiring artifact capabilities."""
from __future__ import annotations

import asyncio


async def start_gateway(bridge, public_port=8080, sdk_port=8081):
    from aiohttp import ClientSession, ClientTimeout, web

    app = web.Application(client_max_size=256 * 1024)
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
