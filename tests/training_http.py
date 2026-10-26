"""Safe-preview HTTP tests; a fixture copy changes filesystem paths only."""
import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--php',default='php')
args=p.parse_args()
with tempfile.TemporaryDirectory(prefix='pc-forge-preview-test-') as directory:
    work=Path(directory)
    shutil.copytree(root/'training-src/public',work/'public')
    (work/'public/assets').mkdir()
    shutil.copy2(root/'assets/style.css',work/'public/assets/style.css')
    router=work/'router.php'
    router.write_text((root/'docker/training-router.php').read_text().replace('/opt/pc-forge-training',(work/'public').as_posix()).replace('/run/pc-forge-training/proxy-token',(work/'proxy-token').as_posix()))
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
    token='a'*64
    (work/'proxy-token').write_text(token)
    env={'PATH':os.environ.get('PATH','')}
    if os.name=='nt': env['SystemRoot']=os.environ['SystemRoot']
    log=open(work/'server.log','w')
    process=subprocess.Popen([args.php,'-n','-S',f'127.0.0.1:{port}','-t',str(work/'public'),str(router)],env=env,stdout=log,stderr=log)
    def request(path,headers=None,post=False):
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,headers=headers or {},data=b'email=synthetic%40example.test&password=fixture' if post else None)
        try: response=urllib.request.urlopen(req,timeout=5)
        except urllib.error.HTTPError as error: response=error
        return response.code,response.read().decode(),response.headers
    def check(ok,label):
        if not ok: raise AssertionError(label)
        print('PASS:',label,flush=True)
    try:
        for unused in range(50):
            try:
                result=request('/')
                break
            except OSError: time.sleep(.1)
        check(result[0]==403,'direct backend request denied')
        good={'X-PC-Forge-Training':token}
        status,body,headers=request('/',good)
        check(status==200 and 'Power your next' in body,'safe storefront preview renders')
        check('script-src \'none\'' in headers['Content-Security-Policy'],'preview disables scripts')
        check(request('/login.php',good)[0]==200,'normal login preview renders')
        status,body,headers=request('/login.php',good,True)
        check(status==503 and 'No login was attempted' in body,'authentication remains disabled')
        check(headers.get('Set-Cookie') is None,'no training or production auth cookie emitted')
        check(request('/',dict(good,Cookie='PHPSESSID=production-fixture'))[0]==403,'backend refuses forwarded production cookies')
        check(request('/',dict(good,Authorization='Basic fixture'))[0]==403,'backend refuses forwarded instructor authorization')
        check(request('/../config/db.php',good)[0]==404,'router does not serve production config')
        check(request('/assets/style.css',good)[0]==200,'existing production CSS served in preview')
    finally:
        process.terminate();process.wait(timeout=10);log.close()
    # Even a correctly signed proxy request must not accept an inherited secret.
    polluted=dict(env,DB_PASSWORD='synthetic-unexpected-environment')
    with open(work/'polluted.log','w') as log:
        process=subprocess.Popen([args.php,'-n','-S',f'127.0.0.1:{port}','-t',str(work/'public'),str(router)],env=polluted,stdout=log,stderr=log)
        try:
            for unused in range(50):
                try:
                    status,_,_=request('/',good)
                    break
                except OSError: time.sleep(.1)
            check(status==403,'actual backend fails closed if production environment is inherited')
        finally:
            process.terminate();process.wait(timeout=10)
