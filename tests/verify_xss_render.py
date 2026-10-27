"""Opt-in verification of the existing Render service; never deploys. No saved credentials/bodies."""
import argparse
import base64
import getpass
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

BASE='https://pc-forge-k68s.onrender.com'
REFLECTED="<script>alert('XSS Demonstration Successful')</script>"
ATTRIBUTE='''" onclick="alert('XSS Demonstration Successful')" data-demo="'''


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args): return None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify-live',action='store_true')
    p.add_argument('--http-only',action='store_true',help='Partial verification only; browser execution remains unverified')
    a=p.parse_args()
    if not a.verify_live: p.error('--verify-live required; no requests sent')
    if not a.http_only:
        from playwright.sync_api import sync_playwright
    user=input('Dedicated demo tester username: ')
    password=getpass.getpass('Dedicated demo password: ')
    authorization='Basic '+base64.b64encode((user+':'+password).encode()).decode()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl.create_default_context()),NoRedirect())
    results=[]
    def request(path,auth=False):
        time.sleep(2)
        headers={'Authorization':authorization} if auth else {}
        req=urllib.request.Request(BASE+path,headers=headers)
        try: response=opener.open(req,timeout=30)
        except urllib.error.HTTPError as e: response=e
        with response:
            body=response.read(524289).decode('utf-8',errors='replace')
            if len(body)>524288 or response.code>=500: raise RuntimeError('Availability/size stop')
            results.append({'path':path.split('?')[0],'authenticated':auth,'status':response.code})
            print('HTTP',response.code,path.split('?')[0],('authorized' if auth else 'anonymous'),flush=True)
            return response.code,body,response.headers
    for path in ('/','/login.php'):
        assert request(path)[0]==200,'Public storefront smoke check failed'
    for version in ('vulnerable','fixed'):
        path='/xss-demo/?version='+version
        assert request(path)[0]==401,'Unauthenticated demonstration not rejected with 401'
        status,body,headers=request(path,True)
        assert status==200 and 'synthetic search' in body,'Authorized demo unavailable'
        assert not headers.get('Set-Cookie'),'Demo emitted cookie'
        csp=headers.get('Content-Security-Policy','')
        assert 'sandbox allow-scripts allow-modals' in csp and 'allow-same-origin' not in csp,'Opaque sandbox missing'
    assert request('/xss-demo/?version=vulnerable&q=unapproved',True)[0]==400,'Payload allowlist failed'
    if not a.http_only:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            try:
                context=browser.new_context(http_credentials={'username':user,'password':password,'origin':BASE})
                for version in ('vulnerable','fixed'):
                    for payload in (REFLECTED,ATTRIBUTE):
                        time.sleep(2)
                        page=context.new_page(); dialogs=[]
                        def handle(d): dialogs.append(d.message); d.dismiss()
                        page.on('dialog',handle)
                        # No other browser destinations or production routes are allowed.
                        page.route('**/*',lambda route: route.continue_() if route.request.url.startswith(BASE+'/xss-demo/') else route.abort())
                        response=page.goto(BASE+'/xss-demo/?'+urllib.parse.urlencode({'version':version,'q':payload}))
                        assert response and response.status==200,'Browser demo unavailable'
                        if payload==ATTRIBUTE: page.locator('input[name=q]').click()
                        page.wait_for_timeout(500)
                        assert dialogs==(['XSS Demonstration Successful'] if version=='vulnerable' else []),'Browser dialog result differs'
                        assert page.evaluate("() => {try {localStorage.getItem('x'); return false;} catch(e) {return e.name === 'SecurityError';}}"),'Opaque storage isolation not established'
                        results.append({'version':version,'case':'attribute' if payload==ATTRIBUTE else 'reflected','dialog_matches':True,'opaque_storage':True})
                        page.close()
            finally: browser.close()
    for path in ('/','/login.php'):
        assert request(path)[0]==200,'Post-test public smoke check failed'
    print(json.dumps({'result':'partial-http-pass' if a.http_only else 'http-and-browser-pass','checks':results,'limits':'Public smoke checks only; no account/cart/checkout verification'},indent=2))


if __name__=='__main__':
    try: main()
    except Exception: raise SystemExit('Verification stopped/failed. Details suppressed; check configuration, deployment and browser prerequisites. No successful exploit claimed.')
