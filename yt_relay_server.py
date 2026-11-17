#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ════════════════════════════════════════════════════════════════════
# yt_relay_server.py — کمکی محلی دانلود یوتیوب برای صفحهٔ PWA (BA-171)
#
# چرا این فایل؟ مرورگر ذاتاً واکشی cross-origin بدون CORS را مسدود می‌کند
# (استاندارد امنیتی، دورزدن از داخل مرورگر غیرممکن است). همهٔ راه‌حل‌های
# واقعی دنیا (yt-dlp، اپ پایتونی، NewPipe، سرورهای Piped/cobalt) بیرون از
# مرورگر اجرا می‌شوند. این اسکریپت همان کار اپ پایتونی شما را می‌کند ولی
# به‌صورت سرویس محلی کنار صفحه — صفحه بایت‌ها را از 127.0.0.1 می‌گیرد و
# CORS اصلاً در میان نیست.
#
# اجرا:
#   python3 yt_relay_server.py          # پورت پیش‌فرض 8790
#   python3 yt_relay_server.py 8791     # پورت دلخواه
# سپس صفحه را رفرش کنید — پیام «🚀 کمکی محلی فعال» می‌بینید.
#
# امنیت: فقط روی 127.0.0.1 گوش می‌دهد (از LAN/اینترنت در دسترس نیست).
# ════════════════════════════════════════════════════════════════════
import json
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8790
# مثل کلاینت موبایل یوتیوب — همان ترفند yt-dlp برای گرفتن استریم
UA = 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip'


class RelayHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self._cors()
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == '/ping':
            self._json({'ok': True, 'name': 'yt-local-relay', 'port': PORT})
            return
        if path == '/dl':
            qs = urllib.parse.parse_qs(parsed.query)
            url = (qs.get('url') or [''])[0]
            if not url.startswith(('http://', 'https://')):
                self._json({'ok': False, 'error': 'bad url'}, 400)
                return
            try:
                req = urllib.request.Request(url, headers={'User-Agent': UA})
                up = urllib.request.urlopen(req, timeout=180)
            except Exception as e:
                self._json({'ok': False, 'error': 'upstream: %s' % e}, 502)
                return
            try:
                self.send_response(200)
                ct = up.headers.get('Content-Type') or 'application/octet-stream'
                cl = up.headers.get('Content-Length')
                self.send_header('Content-Type', ct)
                if cl:
                    self.send_header('Content-Length', cl)
                self._cors()
                self.end_headers()
                total = 0
                while True:
                    chunk = up.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    total += len(chunk)
                print('[dl] %s -> %d bytes' % (url[:90], total), flush=True)
            except Exception as e:
                print('[dl] stream error: %s' % e, flush=True)
            finally:
                try:
                    up.close()
                except Exception:
                    pass
            return
        self._json({'ok': False, 'error': 'not found'}, 404)

    def log_message(self, *a):
        pass  # لاگ کم — فقط خطاهای /dl چاپ می‌شوند


print('🚀 yt-local-relay روی http://127.0.0.1:%d — این پنجره را باز نگه دارید و صفحه را رفرش کنید.' % PORT, flush=True)
print('   خروج: Ctrl+C', flush=True)
ThreadingHTTPServer(('127.0.0.1', PORT), RelayHandler).serve_forever()
