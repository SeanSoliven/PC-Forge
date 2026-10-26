"""Optional XAMPP Apache proxy-boundary test with disposable local fixtures."""
import argparse
import base64
import http.server
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--php',default='php')
p.add_argument('--httpd',default='C:/xampp/apache/bin/httpd.exe')
p.add_argument('--apache-root',default='C:/xampp/apache')
args=p.parse_args()
seen=[]
class Backend(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        seen.append(dict(self.headers))
        self.send_response(200)
        self.send_header('Set-Cookie','PHPSESSID=forbidden; Path=/')
        self.end_headers();self.wfile.write(b'fixture')
    def log_message(self,*unused): pass
backend=http.server.HTTPServer(('127.0.0.1',0),Backend)
thread=threading.Thread(target=backend.serve_forever,daemon=True);thread.start()
try:
    with tempfile.TemporaryDirectory(prefix='pc-forge-apache-check-') as directory:
        work=Path(directory);doc=work/'public';doc.mkdir()
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        code="<?php require 'docker/training-config.php';echo training_apache_config(str_repeat('a',64));"
        config=subprocess.check_output([args.php],input=code,text=True,cwd=root)
        auth=work/'instructors'
        password_hash=subprocess.check_output([args.php],input="<?php echo password_hash('fixture-password',PASSWORD_BCRYPT);",text=True)
        auth.write_text('instructor:'+password_hash+'\n')
        config=config.replace('/run/pc-forge-training-auth/instructors',auth.as_posix()).replace('127.0.0.1:9081',f'127.0.0.1:{backend.server_port}')
        modules=['authn_core','authz_core','authz_user','auth_basic','authn_file','proxy','proxy_http','headers','alias','dir']
        header=f'ServerRoot "{args.apache_root}"\nServerName localhost\nListen 127.0.0.1:{port}\nPidFile "{work.as_posix()}/httpd.pid"\nErrorLog "{work.as_posix()}/error.log"\nDocumentRoot "{doc.as_posix()}"\n'
        header+=''.join(f'LoadModule {m}_module modules/mod_{m}.so\n' for m in modules)
        header+=f'<Directory "{doc.as_posix()}">\nRequire all granted\n</Directory>\n'
        file=work/'httpd.conf';file.write_text(header+config)
        command=[args.httpd,'-f',file.as_posix()]
        result=subprocess.run(command+['-t'],capture_output=True,text=True)
        if result.returncode: raise RuntimeError(result.stderr)
        print('PASS: generated Apache proxy configuration syntax',flush=True)
        log=open(work/'process.log','w');flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        process=subprocess.Popen(command,stdout=log,stderr=log,creationflags=flags)
        def request(headers):
            req=urllib.request.Request(f'http://127.0.0.1:{port}/training/',headers=headers)
            try:r=urllib.request.urlopen(req,timeout=5)
            except urllib.error.HTTPError as e:r=e
            r.read();return r
        try:
            for unused in range(50):
                try:
                    result=request({'X-Forwarded-Proto':'https'});break
                except OSError:time.sleep(.1)
            assert result.code==401 and not seen
            print('PASS: instructor credentials required before proxy',flush=True)
            assert request({'X-Forwarded-Proto':'https','Authorization':'Basic '+base64.b64encode(b'instructor:wrong').decode()}).code==401
            assert not seen
            print('PASS: incorrect instructor credentials do not reach backend',flush=True)
            auth_header='Basic '+base64.b64encode(b'instructor:fixture-password').decode()
            result=request({'X-Forwarded-Proto':'https','Authorization':auth_header,'Cookie':'PHPSESSID=production-fixture'})
            assert result.code==200 and len(seen)==1
            lower={key.lower():value for key,value in seen[0].items()}
            assert 'authorization' not in lower and 'cookie' not in lower
            assert lower['x-pc-forge-training']=='a'*64
            assert result.headers.get('Set-Cookie') is None
            print('PASS: actual proxy strips inbound credentials/cookies and outbound cookies',flush=True)
            assert request({'Authorization':auth_header}).code==403
            print('PASS: instructor access also requires forwarded HTTPS',flush=True)
        finally:
            subprocess.run(command+['-k','shutdown'],capture_output=True)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
            log.close()
finally:
    backend.shutdown();backend.server_close();thread.join(timeout=5)
