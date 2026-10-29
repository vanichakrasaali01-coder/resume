import json, sqlite3, hashlib
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parent
DB=ROOT/'bank.db'
TABLES={
'customers':['customer_id','name','phone','email','address','registered_at','kyc_status','status'],
'accounts':['account_number','customer_id','account_type','balance','branch','status'],
'employees':['employee_id','name','email','phone','role','branch','status'],
'branches':['branch_code','name','address','phone','manager','status'],
'beneficiaries':['name','account_number','bank_name','ifsc','customer_id','status'],
'deposits':['account_id','amount','method','reference','status','created_at'],
'withdrawals':['account_id','amount','reason','reference','status','created_at'],
'transfers':['from_account_id','to_account_id','amount','reference','status','created_at'],
'repayments':['loan_id','amount','method','reference','status','created_at'],
'loans':['customer_id','loan_type','amount','tenure_months','interest_rate','status','created_at'],
'fixed_deposits':['account_id','customer_id','principal','tenure_months','interest_rate','status','created_at'],
'recurring_deposits':['account_id','customer_id','monthly_amount','tenure_months','status','created_at'],
'cheques':['account_id','cheque_number','amount','payee','status','created_at'],
'cards':['account_id','customer_id','card_type','masked_number','status'],
'kyc':['customer_id','document_type','document_number','status','reason'],
'reports':['report_type','period','status','created_at'],
'users':['name','email','role','permissions','status'],
'notifications':['title','message','recipient','status','created_at'],
'audit':['actor','action','record_type','record_id','created_at']}

def con():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def init():
 c=con(); c.execute('CREATE TABLE IF NOT EXISTS auth_users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password_hash TEXT,role TEXT,status TEXT DEFAULT "Active")')
 for table,cols in TABLES.items():
  defs=['id INTEGER PRIMARY KEY AUTOINCREMENT']+[x+' TEXT' if x not in ('balance','amount','principal','monthly_amount','interest_rate') else (x+' REAL DEFAULT 0') for x in cols]
  # numeric integers
  for i,d in enumerate(defs):
   if d.startswith('tenure_months '): defs[i]='tenure_months INTEGER DEFAULT 0'
  c.execute('CREATE TABLE IF NOT EXISTS '+table+'('+','.join(defs)+')')
 if c.execute('SELECT COUNT(*) FROM auth_users').fetchone()[0]==0:
  c.execute('INSERT INTO auth_users(name,email,password_hash,role) VALUES(?,?,?,?)',('Riya Ahuja','admin@novabank.test',hashlib.sha256(b'admin123').hexdigest(),'Admin'))
 if c.execute('SELECT COUNT(*) FROM customers').fetchone()[0]==0:
  seed=c;
  seed.executemany('INSERT INTO customers(customer_id,name,phone,email,address,registered_at,kyc_status,status) VALUES(?,?,?,?,?,?,?,?)',[('CUST-1001','Aarav Mehta','9876543210','aarav@example.com','12 Residency Road, Bengaluru','2026-10-01','Verified','Active'),('CUST-1002','Diya Shah','9876543211','diya@example.com','45 Lake View, Pune','2026-10-05','Pending','Active'),('CUST-1003','Kabir Rao','9876543212','kabir@example.com','7 Park Avenue, Delhi','2026-10-12','Verified','Active'),('CUST-1004','Meera Kapoor','9876543213','meera@example.com','22 Civic Centre, Mumbai','2026-10-18','Rejected','Inactive')])
  seed.executemany('INSERT INTO accounts(account_number,customer_id,account_type,balance,branch,status) VALUES(?,?,?,?,?,?)',[('NB0011001','1','Savings',125000,'Central Branch','Active'),('NB0011002','2','Current',87500,'Central Branch','Active'),('NB0011003','1','Salary',45230,'Whitefield Branch','Active'),('NB0011004','3','Savings',231000,'Delhi Branch','Frozen')])
  seed.executemany('INSERT INTO employees(employee_id,name,email,phone,role,branch,status) VALUES(?,?,?,?,?,?,?)',[('EMP-001','Neha Verma','neha@novabank.test','9876500011','Branch Manager','Central Branch','Active'),('EMP-002','Rahul Jain','rahul@novabank.test','9876500012','Loan Officer','Central Branch','Active'),('EMP-003','Priya Singh','priya@novabank.test','9876500013','Cashier','Whitefield Branch','Active')])
  seed.executemany('INSERT INTO branches(branch_code,name,address,phone,manager,status) VALUES(?,?,?,?,?,?)',[('NB-CEN','Central Branch','MG Road, Bengaluru','08040001200','Neha Verma','Active'),('NB-WHT','Whitefield Branch','Whitefield, Bengaluru','08040001300','Arjun Das','Active'),('NB-DEL','Delhi Branch','Connaught Place, Delhi','01140001400','Sanjay Roy','Active')])
  seed.executemany('INSERT INTO loans(customer_id,loan_type,amount,tenure_months,interest_rate,status,created_at) VALUES(?,?,?,?,?,?,?)',[('1','Home Loan',2500000,240,8.4,'Approved','2026-10-10'),('2','Personal Loan',300000,36,11.5,'Pending','2026-10-24')])
 c.commit(); c.close()

def audit(c,action,rtype,rid,actor='admin@novabank.test'):
 c.execute('INSERT INTO audit(actor,action,record_type,record_id,created_at) VALUES(?,?,?,?,?)',(actor,action,rtype,str(rid),datetime.now().isoformat()))

class Api(SimpleHTTPRequestHandler):
 def __init__(self,*a,**k): super().__init__(*a,directory=str(ROOT),**k)
 def send_json(self,obj,status=200):
  data=json.dumps(obj,default=str).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
 def read_json(self):
  try: return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0')) or 0) or '{}')
  except json.JSONDecodeError: return None
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/' : self.path='/bank.html'; return super().do_GET()
  if not path.startswith('/api/'): return super().do_GET()
  c=con()
  if path=='/api/dashboard':
   result={'customers':c.execute('SELECT COUNT(*) FROM customers').fetchone()[0],'accounts':c.execute('SELECT COUNT(*) FROM accounts').fetchone()[0],'balance':c.execute('SELECT COALESCE(SUM(balance),0) FROM accounts').fetchone()[0],'loans':c.execute('SELECT COUNT(*) FROM loans').fetchone()[0],'pending':c.execute("SELECT COUNT(*) FROM loans WHERE status='Pending'").fetchone()[0]}
   self.send_json(result); c.close(); return
  resource=path.split('/')[2]
  if resource not in TABLES: self.send_json({'error':'Unknown resource'},404); return
  row_id=path.split('/')[3] if len(path.split('/'))>3 else None
  q=urlparse(self.path).query
  if row_id:
   row=c.execute(f'SELECT * FROM {resource} WHERE id=?',(row_id,)).fetchone(); self.send_json(dict(row) if row else {'error':'Record not found'},200 if row else 404); c.close(); return
  search=None
  from urllib.parse import parse_qs
  params=parse_qs(q); search=params.get('search',[None])[0]
  sql=f'SELECT * FROM {resource}'; vals=[]
  if search:
   cols=TABLES[resource]
   sql+=' WHERE '+' OR '.join([f'{x} LIKE ?' for x in cols]); vals=['%'+search+'%' for _ in cols]
  sql+=' ORDER BY id DESC'
  rows=c.execute(sql,vals).fetchall(); self.send_json([dict(r) for r in rows]); c.close()
 def do_POST(self):
  path=urlparse(self.path).path
  if path=='/api/login':
   b=self.read_json() or {}; c=con(); u=c.execute('SELECT * FROM auth_users WHERE email=?',(b.get('email',''),)).fetchone()
   if not u or u['password_hash']!=hashlib.sha256((b.get('password','') or '').encode()).hexdigest(): self.send_json({'error':'Invalid email or password'},401); return
   self.send_json({'id':u['id'],'name':u['name'],'role':u['role'],'token':'demo-session-token'}); return
  if not path.startswith('/api/'): return self.send_json({'error':'Not found'},404)
  resource=path.split('/')[2]; b=self.read_json()
  if resource not in TABLES or not isinstance(b,dict): return self.send_json({'error':'Invalid request'},400)
  if resource=='customers':
   required=['name','phone','email','address']; missing=[x for x in required if not str(b.get(x,'')).strip()]
   if missing: return self.send_json({'error':'Required: '+', '.join(missing)},400)
   if not b.get('customer_id'): b['customer_id']='CUST-'+str(int(datetime.now().timestamp()))[-8:]
   b.setdefault('registered_at',datetime.now().strftime('%Y-%m-%d')); b.setdefault('kyc_status','Pending'); b.setdefault('status','Active')
  if resource=='accounts': b.setdefault('status','Active'); b.setdefault('balance','0')
  cols=[x for x in TABLES[resource] if x in b]
  if resource in ('deposits','withdrawals','transfers'):
   return self.transaction(resource,b)
  c=con()
  placeholders=','.join(['?']*len(cols)); sql=f"INSERT INTO {resource}("+','.join(cols)+') VALUES('+placeholders+')'
  try:
   cur=c.execute(sql,[b[x] for x in cols]); audit(c,'create',resource,cur.lastrowid); c.commit(); rid=cur.lastrowid; c.close(); self.send_json({'id':rid},201)
  except sqlite3.Error as e: c.close(); self.send_json({'error':str(e)},400)
 def transaction(self,resource,b):
  c=con()
  try:
   if resource=='transfers':
    amount=float(b['amount']); from_id=b['from_account_id']; to_id=b['to_account_id']
    if from_id==to_id: raise ValueError('Source and destination accounts must differ')
    source=c.execute('SELECT balance,status FROM accounts WHERE id=?',(from_id,)).fetchone(); dest=c.execute('SELECT balance,status FROM accounts WHERE id=?',(to_id,)).fetchone()
    if not source or not dest: raise ValueError('Account not found')
    if source['status']=='Frozen': raise ValueError('Source account is frozen')
    if float(source['balance'])<amount: raise ValueError('Insufficient account balance')
    c.execute('UPDATE accounts SET balance=balance-? WHERE id=?',(amount,from_id)); c.execute('UPDATE accounts SET balance=balance+? WHERE id=?',(amount,to_id))
   else:
    amount=float(b['amount']); account_id=b['account_id']; account=c.execute('SELECT balance,status FROM accounts WHERE id=?',(account_id,)).fetchone()
    if not account: raise ValueError('Account not found')
    if account['status']=='Frozen': raise ValueError('Account is frozen')
    if resource=='withdrawals' and float(account['balance'])<amount: raise ValueError('Insufficient account balance')
    delta=amount if resource=='deposits' else -amount; c.execute('UPDATE accounts SET balance=balance+? WHERE id=?',(delta,account_id))
   cols=[x for x in TABLES[resource] if x in b]; b.setdefault('status','Completed'); b.setdefault('created_at',datetime.now().isoformat()); cols=list(dict.fromkeys(cols+['status','created_at']))
   cur=c.execute(f"INSERT INTO {resource}("+','.join(cols)+') VALUES('+','.join(['?']*len(cols))+')',[b[x] for x in cols]); audit(c,resource,resource,cur.lastrowid); c.commit(); self.send_json({'id':cur.lastrowid},201)
  except (ValueError,sqlite3.Error) as e: c.rollback(); self.send_json({'error':str(e)},400)
  finally: c.close()
 def do_PUT(self):
  parts=urlparse(self.path).path.strip('/').split('/'); b=self.read_json() or {}
  if len(parts)!=3 or parts[0]!='api' or parts[1] not in TABLES: return self.send_json({'error':'Not found'},404)
  resource,rid=parts[1],parts[2]; cols=[x for x in TABLES[resource] if x in b]
  c=con()
  try: c.execute(f"UPDATE {resource} SET "+','.join([x+'=?' for x in cols])+' WHERE id=?',[b[x] for x in cols]+[rid]); audit(c,'update',resource,rid); c.commit(); self.send_json({'success':True})
  except sqlite3.Error as e: c.rollback(); self.send_json({'error':str(e)},400)
  finally: c.close()
 def do_DELETE(self):
  parts=urlparse(self.path).path.strip('/').split('/')
  if len(parts)!=3 or parts[1] not in TABLES: return self.send_json({'error':'Not found'},404)
  resource,rid=parts[1],parts[2]
  if resource in ('deposits','withdrawals','transfers'): return self.send_json({'error':'Financial records cannot be deleted; use a reversal workflow'},409)
  c=con(); c.execute(f'DELETE FROM {resource} WHERE id=?',(rid,)); audit(c,'delete',resource,rid); c.commit(); c.close(); self.send_json({'success':True})

if __name__=='__main__': init(); print('NovaBank running at http://localhost:8080'); ThreadingHTTPServer(('0.0.0.0',8080),Api).serve_forever()
