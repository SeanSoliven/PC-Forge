"""Exercise real container HTTP against synthetic MySQL; called only by Docker gate."""
import http.cookiejar
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

base=sys.argv[1]
if not re.fullmatch(r'http://127\.0\.0\.1:\d+/',base):
    raise SystemExit('Only disposable loopback endpoints are permitted')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*unused): return None

class Browser:
    def __init__(self):
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),NoRedirect())
    def request(self,path,data=None):
        try:
            response=self.opener.open(base+path,urllib.parse.urlencode(data).encode() if data is not None else None,timeout=10)
        except urllib.error.HTTPError as error: response=error
        return response.code,response.read().decode(),response.headers
    def login(self,email,password):
        status,body,_=self.request('login.php')
        assert status==200
        csrf=re.search(r'name="csrf" value="([^"]+)"',body).group(1)
        return self.request('login.php',dict(csrf=csrf,email=email,password=password))

def check(ok,label):
    if not ok: raise AssertionError(label)
    print('PASS:',label,flush=True)

customer=Browser()
status,body,_=customer.request('index.php')
check(status==200 and 'Ryzen 5 7600' in body,'HTTP homepage reads synthetic MySQL through verified TLS')
check(customer.request('admin/index.php')[0]==302,'HTTP anonymous admin request redirects')
check(customer.login('customer@fixture.test','wrong')[0]==422,'HTTP invalid password rejected')
status,_,headers=customer.login('customer@fixture.test','lab-customer-123')
check(status==302 and headers['Location']=='index.php','HTTP customer login and redirect')
check(customer.request('orders.php')[0]==200,'HTTP production session persists')
check(customer.request('admin/index.php')[0]==403,'HTTP customer cannot access admin')
admin=Browser()
status,_,headers=admin.login('admin@fixture.test','lab-admin-123')
check(status==302 and headers['Location']=='admin/index.php','HTTP synthetic administrator login and redirect')
check(admin.request('admin/index.php')[0]==200,'HTTP protected admin dashboard renders')
