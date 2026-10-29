import json, sqlite3, hashlib, secrets
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DB = ROOT / "hospital.db"

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,password TEXT,role TEXT,email TEXT);
    CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT UNIQUE,name TEXT,age INTEGER,gender TEXT,phone TEXT,address TEXT,medical_history TEXT,status TEXT DEFAULT 'Active',created_at TEXT);
    CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,specialization TEXT,department TEXT,phone TEXT,email TEXT,availability TEXT,consultation TEXT,status TEXT DEFAULT 'Available');
    CREATE TABLE IF NOT EXISTS departments(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,head TEXT,doctors INTEGER DEFAULT 0,beds INTEGER DEFAULT 0,status TEXT DEFAULT 'Active');
    CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id INTEGER,doctor_id INTEGER,department TEXT,date TEXT,time TEXT,status TEXT DEFAULT 'Scheduled',FOREIGN KEY(patient_id) REFERENCES patients(id),FOREIGN KEY(doctor_id) REFERENCES doctors(id));
    CREATE TABLE IF NOT EXISTS beds(id INTEGER PRIMARY KEY AUTOINCREMENT,bed_number TEXT,ward TEXT,room TEXT,status TEXT DEFAULT 'Available',patient_id INTEGER);
    CREATE TABLE IF NOT EXISTS admissions(id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id INTEGER,ward TEXT,bed_id INTEGER,admitted_at TEXT,discharged_at TEXT,status TEXT DEFAULT 'Admitted',FOREIGN KEY(patient_id) REFERENCES patients(id));
    CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_no TEXT UNIQUE,patient_id INTEGER,total REAL,status TEXT DEFAULT 'Pending',method TEXT,items TEXT,created_at TEXT,FOREIGN KEY(patient_id) REFERENCES patients(id));
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,user TEXT,action TEXT,record_type TEXT,record_id TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS appointment_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT NOT NULL,department TEXT NOT NULL,status TEXT DEFAULT 'New',created_at TEXT);
    """)
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        con.execute("INSERT INTO users(name,password,role,email) VALUES(?,?,?,?)",("Admin User",hash_password("admin123"),"Admin","admin@medora.local"))
    if con.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0:
        seed(con)
    con.commit(); con.close()

def hash_password(value): return hashlib.sha256(value.encode()).hexdigest()
def seed(con):
    patients=[("PT-1001","Aarav Sharma",34,"Male","9876543210","Bengaluru","Hypertension","2026-10-20"),("PT-1002","Diya Patel",28,"Female","9876501234","Delhi","None","2026-10-21"),("PT-1003","Vivaan Rao",52,"Male","9876512345","Bengaluru","Diabetes","2026-10-22"),("PT-1004","Anika Singh",41,"Female","9876523456","Mysuru","Asthma","2026-10-23")]
    con.executemany("INSERT INTO patients(patient_id,name,age,gender,phone,address,medical_history,created_at) VALUES(?,?,?,?,?,?,?,?)",[(p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7]+" 09:00") for p in patients])
    doctors=[("Dr. Ananya Mehta","Cardiologist","Cardiology","9876541111","08:00 - 16:00"),("Dr. Rahul Verma","Neurologist","Neurology","9876542222","09:00 - 17:00"),("Dr. Kavya Iyer","Orthopedic Surgeon","Orthopedics","9876543333","10:00 - 18:00"),("Dr. Arun Nair","General Physician","General Medicine","9876544444","08:00 - 14:00")]
    con.executemany("INSERT INTO doctors(name,specialization,department,phone,consultation) VALUES(?,?,?,?,?)",[(d[0],d[1],d[2],d[3],d[4]) for d in doctors])
    departments=[("Cardiology","Dr. Ananya Mehta",8,24),("Neurology","Dr. Rahul Verma",5,18),("Orthopedics","Dr. Kavya Iyer",6,20),("Pediatrics","Dr. Meera Shah",9,16),("General Medicine","Dr. Arun Nair",12,32),("Emergency","Dr. Vikram Joshi",14,20),("Radiology","Dr. Priya Das",4,8),("Laboratory","Dr. Sanjay Roy",7,4)]
    con.executemany("INSERT INTO departments(name,head,doctors,beds) VALUES(?,?,?,?)",departments)
    con.executemany("INSERT INTO appointments(patient_id,doctor_id,department,date,time,status) VALUES(?,?,?,?,?,?)",[(1,1,"Cardiology","2026-10-28","09:30","Confirmed"),(2,4,"General Medicine","2026-10-28","10:00","Scheduled"),(3,2,"Neurology","2026-10-28","11:30","Completed"),(4,3,"Orthopedics","2026-10-28","14:00","Scheduled")])
    for n in range(1,21): con.execute("INSERT INTO beds(bed_number,ward,room,status) VALUES(?,?,?,?)",(f"B-{n:03}","General Ward" if n<16 else "ICU",str(100+(n//4)),"Available" if n>14 else "Occupied"))
    con.executemany("INSERT INTO invoices(invoice_no,patient_id,total,status,method,items,created_at) VALUES(?,?,?,?,?,?,?)",[("INV-2026-001",1,12500,"Paid","UPI","Consultation, laboratory","2026-10-25"),("INV-2026-002",2,4800,"Pending","","Consultation, medicines","2026-10-26"),("INV-2026-003",3,28750,"Partially Paid","Card","Treatment, room","2026-10-27")])

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def json(self,data,status=200):
        body=json.dumps(data,default=str).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def body(self):
        length=int(self.headers.get("Content-Length","0")); return json.loads(self.rfile.read(length) or b"{}")
    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith("/api/"): return self.api_get(path,parse_qs(urlparse(self.path).query))
        if path=="/": self.path="/hms.html"
        super().do_GET()
    def api_get(self,path,q):
        con=db()
        if path=="/api/dashboard":
            data={"patients":con.execute("SELECT COUNT(*) c FROM patients").fetchone()[0],"doctors":con.execute("SELECT COUNT(*) c FROM doctors").fetchone()[0],"appointments":con.execute("SELECT COUNT(*) c FROM appointments WHERE date='2026-10-28'").fetchone()[0],"beds":con.execute("SELECT COUNT(*) c FROM beds WHERE status='Available'").fetchone()[0],"admitted":con.execute("SELECT COUNT(*) c FROM beds WHERE status='Occupied'").fetchone()[0],"bills":con.execute("SELECT COALESCE(SUM(total),0) c FROM invoices WHERE status!='Paid'").fetchone()[0]}
            data["recent"]=con.execute("SELECT a.id,a.time,a.status,a.department,p.name patient,d.name doctor FROM appointments a JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id ORDER BY a.id DESC LIMIT 6").fetchall()
            data["notifications"]=[{"title":"Lab report ready","detail":"Patient PT-1003","type":"Lab"},{"title":"Low stock alert","detail":"3 medicines require restock","type":"Stock"},{"title":"Appointment confirmed","detail":"Dr. Ananya Mehta at 09:30","type":"Calendar"}]
            self.json({**data,"recent":[dict(r) for r in data["recent"]]}); return
        table={"/api/patients":"patients","/api/doctors":"doctors","/api/departments":"departments","/api/appointments":"appointments","/api/beds":"beds","/api/invoices":"invoices"}.get(path)
        if table:
            rows=con.execute(f"SELECT * FROM {table}").fetchall(); self.json([dict(r) for r in rows]); return
        self.json({"error":"Not found"},404)
    def do_POST(self):
        path=urlparse(self.path).path
        try:
            body=self.body(); con=db()
            if path=="/api/patients":
                if not body.get("name") or len(str(body.get("phone","")))<10: return self.json({"error":"Name and a valid phone number are required"},400)
                cur=con.execute("INSERT INTO patients(patient_id,name,age,gender,phone,address,medical_history,created_at) VALUES(?,?,?,?,?,?,?,?)",(body.get("patient_id") or f"PT-{datetime.now().strftime('%H%M%S')}",body["name"],int(body.get("age",0)),body.get("gender",""),body.get("phone",""),body.get("address",""),body.get("medical_history",""),datetime.now().isoformat(timespec='seconds')))
                con.commit(); audit(con,"Admin","Created patient",cur.lastrowid); con.commit(); return self.json({"id":cur.lastrowid},201)
            if path=="/api/doctors":
                cur=con.execute("INSERT INTO doctors(name,specialization,department,phone,email,availability,consultation) VALUES(?,?,?,?,?,?,?)",(body["name"],body.get("specialization",""),body.get("department",""),body.get("phone",""),body.get("email",""),body.get("availability","Available"),body.get("consultation",""))); con.commit(); return self.json({"id":cur.lastrowid},201)
            if path=="/api/appointment-requests":
                name=str(body.get("name","")).strip()
                phone=str(body.get("phone","")).strip()
                department=str(body.get("department","")).strip()
                digits=''.join(ch for ch in phone if ch.isdigit())
                if len(name)<2: return self.json({"error":"Please enter your full name"},400)
                if len(digits)<10: return self.json({"error":"Please enter a valid phone number"},400)
                if not department: return self.json({"error":"Please select a department"},400)
                cur=con.execute("INSERT INTO appointment_requests(name,phone,department,created_at) VALUES(?,?,?,?)",(name,phone,department,datetime.now().isoformat(timespec='seconds')))
                con.commit(); audit(con,"Website visitor","Created appointment request",cur.lastrowid); con.commit()
                return self.json({"id":cur.lastrowid,"status":"New"},201)
            if path=="/api/appointments":
                exists=con.execute("SELECT id FROM appointments WHERE doctor_id=? AND date=? AND time=? AND status!='Cancelled'",(body["doctor_id"],body["date"],body["time"])).fetchone()
                if exists: return self.json({"error":"This doctor already has an appointment at the selected time"},409)
                cur=con.execute("INSERT INTO appointments(patient_id,doctor_id,department,date,time,status) VALUES(?,?,?,?,?,?)",(body["patient_id"],body["doctor_id"],body.get("department",""),body["date"],body["time"],body.get("status","Scheduled"))); con.commit(); return self.json({"id":cur.lastrowid},201)
            if path=="/api/departments":
                cur=con.execute("INSERT INTO departments(name,head,doctors,beds,status) VALUES(?,?,?,?,?)",(body["name"],body.get("head",""),int(body.get("doctors",0)),int(body.get("beds",0)),body.get("status","Active"))); con.commit(); return self.json({"id":cur.lastrowid},201)
            if path=="/api/invoices":
                cur=con.execute("INSERT INTO invoices(invoice_no,patient_id,total,status,method,items,created_at) VALUES(?,?,?,?,?,?,?)",(body.get("invoice_no") or f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",body["patient_id"],float(body.get("total",0)),body.get("status","Pending"),body.get("method",""),body.get("items",""),datetime.now().isoformat(timespec='seconds'))); con.commit(); return self.json({"id":cur.lastrowid},201)
            self.json({"error":"Not found"},404)
        except (KeyError,ValueError,sqlite3.IntegrityError) as e: self.json({"error":str(e)},400)
    def do_PUT(self):
        path=urlparse(self.path).path; body=self.body(); parts=path.strip("/").split("/")
        if len(parts)!=3: return self.json({"error":"Invalid request"},400)
        _,resource,id=parts; mapping={"patients":"patients","doctors":"doctors","departments":"departments","appointments":"appointments","beds":"beds","invoices":"invoices"}
        if resource not in mapping: return self.json({"error":"Not found"},404)
        con=db()
        if resource=="appointments" and "status" in body: con.execute("UPDATE appointments SET status=? WHERE id=?",(body["status"],id))
        elif resource=="beds" and "status" in body: con.execute("UPDATE beds SET status=? WHERE id=?",(body["status"],id))
        elif resource=="invoices" and "status" in body: con.execute("UPDATE invoices SET status=?,method=? WHERE id=?",(body["status"],body.get("method",""),id))
        else:
            if resource=="patients": query="UPDATE patients SET name=?,age=?,gender=?,phone=?,address=?,medical_history=?,status=? WHERE id=?"; vals=(body["name"],body.get("age",0),body.get("gender",""),body.get("phone",""),body.get("address",""),body.get("medical_history",""),body.get("status","Active"),id)
            elif resource=="doctors": query="UPDATE doctors SET name=?,specialization=?,department=?,phone=?,email=?,availability=?,consultation=? WHERE id=?"; vals=(body["name"],body.get("specialization",""),body.get("department",""),body.get("phone",""),body.get("email",""),body.get("availability","Available"),body.get("consultation",""),id)
            elif resource=="departments": query="UPDATE departments SET name=?,head=?,doctors=?,beds=?,status=? WHERE id=?"; vals=(body["name"],body.get("head",""),body.get("doctors",0),body.get("beds",0),body.get("status","Active"),id)
            else: return self.json({"error":"Unsupported update"},400)
            con.execute(query,vals)
        con.commit(); audit(con,"Admin",f"Updated {resource}",id); con.commit(); self.json({"success":True})
    def do_DELETE(self):
        parts=urlparse(self.path).path.strip("/").split("/")
        if len(parts)==3:
            _,resource,id=parts
            allowed={"patients":"patients","doctors":"doctors","departments":"departments","appointments":"appointments","invoices":"invoices"}
            if resource in allowed:
                con=db(); con.execute(f"DELETE FROM {allowed[resource]} WHERE id=?",(id,)); con.commit(); con.close(); return self.json({"success":True})
        self.json({"error":"Not found"},404)

def audit(con,user,action,record_id): con.execute("INSERT INTO audit(user,action,record_type,record_id,created_at) VALUES(?,?,?,?,?)",(user,action,"system",record_id,datetime.now().isoformat(timespec='seconds')))

if __name__=="__main__":
    init_db(); port=8080
    print(f"Medora HMS running at http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0",port),Handler).serve_forever()
