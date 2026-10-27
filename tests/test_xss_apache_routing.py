"""Real XAMPP Apache fixture: no production PHP, Render or database access."""
import argparse
import base64
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--php',default='C:/xampp/php/php.exe')
p.add_argument('--httpd',default='C:/xampp/apache/bin/httpd.exe')
p.add_argument('--apache-root',default='C:/xampp/apache')
args=p.parse_args()


def generated(enabled):
    return subprocess.check_output([args.php,'-r',"require 'docker/xss-demo-config.php';echo xss_demo_apache_config("+('true' if enabled else 'false')+");"],cwd=ROOT,text=True)


def check(ok,label):
    if not ok: raise AssertionError(label)
    print('PASS:',label,flush=True)


with tempfile.TemporaryDirectory(prefix='pcforge-apache-xss-') as directory:
    work=Path(directory);doc=work/'public';doc.mkdir();demo=work/'isolated';demo.mkdir()
    (doc/'index.html').write_text('synthetic-storefront')
    (demo/'index.php').write_text('synthetic-authorized-adapter')
    auth=work/'testers'
    hashed=subprocess.check_output([args.php,'-r',"echo password_hash('synthetic-tester-password',PASSWORD_BCRYPT,['cost'=>8]);"],text=True)
    auth.write_text('tester:'+hashed+'\n')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    modules=['authn_core','authz_core','authz_user','auth_basic','authn_file','headers','alias','dir','mime']
    header=f'ServerRoot "{args.apache_root}"\nServerName localhost\nListen 127.0.0.1:{port}\nPidFile "{work.as_posix()}/apache.pid"\nErrorLog "{work.as_posix()}/error.log"\n'
    header+=''.join(f'LoadModule {m}_module modules/mod_{m}.so\n' for m in modules)
    header+='TypesConfig conf/mime.types\n<Directory />\nRequire all denied\n</Directory>\n'
    header+=f'<VirtualHost 127.0.0.1:{port}>\nDocumentRoot "{doc.as_posix()}"\n<Directory "{doc.as_posix()}">\nDirectoryIndex index.html\nRequire all granted\n</Directory>\n'
    old='<LocationMatch "^/xss-demo(?:/|$)">\nRequire all denied\n</LocationMatch>\n'
    token='Basic '+base64.b64encode(b'tester:synthetic-tester-password').decode()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(path,authorization=None,https=True):
        headers={}
        if https: headers['X-Forwarded-Proto']='https'
        if authorization: headers['Authorization']=authorization
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,headers=headers)
        try: result=opener.open(req,timeout=5)
        except urllib.error.HTTPError as e: result=e
        with result: return result.code,result.read().decode(),result.headers
    for stage,config in [('old-disabled',old),('enabled',generated(True)),('new-disabled',generated(False))]:
        config=config.replace('/opt/pc-forge-xss',demo.as_posix()).replace('/run/pc-forge-xss-auth/testers',auth.as_posix())
        file=work/'httpd.conf';file.write_text(header+config+'\n</VirtualHost>\n')
        command=[args.httpd,'-f',str(file)]
        validation=subprocess.run(command+['-t'],capture_output=True,text=True)
        if validation.returncode: raise RuntimeError('Apache fixture syntax/startup: '+validation.stderr)
        check(True,stage+' Apache Syntax OK')
        with (work/'process.log').open('w') as log:
            proc=subprocess.Popen(command,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                for _ in range(50):
                    if proc.poll() is not None: raise RuntimeError('Apache fixture exited')
                    try: status,body,_=request('/');break
                    except OSError: time.sleep(.1)
                else: raise RuntimeError('Apache readiness failed')
                check(status==200 and body=='synthetic-storefront',stage+' public root unchanged')
                if stage=='enabled':
                    check(request('/xss-demo/?version=vulnerable')[0]==401,'anonymous blocked by Basic authentication')
                    wrong='Basic '+base64.b64encode(b'tester:wrong').decode()
                    check(request('/xss-demo/?version=fixed',wrong)[0]==401,'wrong credentials rejected')
                    for version in ('vulnerable','fixed'):
                        status,body,_=request('/xss-demo/?version='+version,token)
                        check(status==200 and body=='synthetic-authorized-adapter','authorized '+version+' reaches Alias target')
                    check(request('/xss-demo/',token,https=False)[0]==403,'correct credentials still require forwarded HTTPS')
                    check(request('/xss-demo',token)[0]==403,'slashless route cannot bypass route policy')
                else:
                    check(request('/xss-demo/?version=vulnerable',token)[0]==403,stage+' stays denied even with credentials')
            finally:
                subprocess.run(command+['-k','shutdown'],capture_output=True)
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired: proc.terminate();proc.wait(timeout=5)
    errors=(work/'error.log').read_text(errors='replace').replace('\\','/')
    check('AH01630' in errors and str(doc).replace('\\','/')+'/xss-demo' in errors,'old disabled policy reproduces document-root AH01630 path')
print('Apache routing checks complete. PHP expiry/browser sandbox remain separate checks.')
