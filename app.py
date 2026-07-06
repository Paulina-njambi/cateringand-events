import os, sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, flash, session, g, abort, Response, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,'catering_dispatch.db')
app=Flask(__name__); app.config['SECRET_KEY']=os.environ.get('SECRET_KEY','paulina-catering-dispatch-2026')
CSS='''body{margin:0;font-family:Inter,Arial,sans-serif;background:#f5f7fb;color:#172033}.shell{display:grid;grid-template-columns:280px 1fr;min-height:100vh}.side{background:#111827;color:white;padding:26px}.brand{font-size:20px;font-weight:900;margin-bottom:28px}.brand span{display:block;color:#9ca3af;font-size:13px}nav a{display:block;color:white;text-decoration:none;padding:12px;border-radius:12px;margin:7px 0}nav a:hover{background:#1f2937}.main{padding:30px}h1{margin:0;font-size:32px;letter-spacing:-.04em}.sub{color:#667085}.top{display:flex;justify-content:space-between;margin-bottom:20px}.pill{background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;border-radius:999px;padding:10px 14px;font-weight:800}.card,.kpi{background:white;border:1px solid #e5e7eb;border-radius:22px;box-shadow:0 18px 45px rgba(23,32,51,.08);padding:22px}.grid{display:grid;gap:20px}.two{grid-template-columns:1fr 1fr}.three{grid-template-columns:repeat(3,1fr)}table{width:100%;border-collapse:collapse}th,td{padding:12px 8px;border-bottom:1px solid #e5e7eb;text-align:left}th{font-size:12px;text-transform:uppercase;color:#667085}input,select,textarea{width:100%;height:44px;border:1px solid #d0d5dd;border-radius:12px;padding:0 12px}textarea{height:80px;padding-top:10px}label{display:grid;gap:6px;font-weight:700;margin-bottom:12px}.btn,button{border:0;border-radius:12px;background:#eef2f7;padding:11px 15px;font-weight:800;color:#172033;text-decoration:none;cursor:pointer}.primary{background:linear-gradient(135deg,#7c2d12,#ea580c)!important;color:white}.danger{color:#b42318;font-weight:900}.success{color:#047857;font-weight:900}.flash{padding:12px;border-radius:12px;background:#fff7ed;margin-bottom:10px}.login{min-height:100vh;display:grid;place-items:center;background:linear-gradient(rgba(5,12,22,.55),rgba(5,12,22,.72)),url('/static/project_reference.jpg') center/cover no-repeat fixed}.login .card{width:min(440px,92vw);background:rgba(255,255,255,.94);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.45)}.actions{display:flex;gap:7px;flex-wrap:wrap}.big{font-size:30px;font-weight:900}.system-photo{width:100%;height:220px;object-fit:cover;border-radius:18px;border:1px solid #e5e7eb;box-shadow:0 14px 34px rgba(23,32,51,.12);margin:0 0 18px}.login-photo{width:100%;height:190px;object-fit:cover;border-radius:20px;margin:0 0 18px;border:1px solid rgba(255,255,255,.35)}.hero-card{overflow:hidden}.hero-card p{margin-top:0}@media(max-width:900px){.shell,.two,.three{grid-template-columns:1fr}}'''
def conn():
    if 'db' not in g: g.db=sqlite3.connect(DB); g.db.row_factory=sqlite3.Row
    return g.db
@app.teardown_appcontext
def close(e):
    d=g.pop('db',None)
    if d: d.close()
def q(s,a=(),one=False):
    c=conn().execute(s,a); r=c.fetchall(); c.close(); return (r[0] if r else None) if one else r
def ex(s,a=()):
    c=conn().execute(s,a); conn().commit(); return c.lastrowid
def user(): return q('select * from users where id=?',(session.get('uid'),),one=True) if session.get('uid') else None
def need(fn):
    @wraps(fn)
    def w(*a,**k):
        if not user(): flash('Please log in first.'); return redirect(url_for('login'))
        return fn(*a,**k)
    return w
def admin(fn):
    @wraps(fn)
    def w(*a,**k):
        u=user()
        if not u: return redirect(url_for('login'))
        if u['role']!='Admin': abort(403)
        return fn(*a,**k)
    return w
def log(t): ex('insert into audit(user_id,action,created_at) values(?,?,?)',(session.get('uid'),t,datetime.now().isoformat(timespec='seconds')))
def init_db():
    db=sqlite3.connect(DB); c=db.cursor(); c.executescript('''
    create table if not exists users(id integer primary key,username text unique,password_hash text,full_name text,role text);
    create table if not exists items(id integer primary key,name text,category text,total_qty integer,available_qty integer,replacement_cost real);
    create table if not exists events(id integer primary key,client_name text,event_type text,venue text,event_date text,team_leader text,status text default 'Draft',created_at text,dispatch_signed_at text,return_signed_at text);
    create table if not exists dispatch_items(id integer primary key,event_id integer,item_id integer,qty_dispatched integer,qty_returned integer default 0,last_seen text,loss_value real default 0);
    create table if not exists audit(id integer primary key,user_id integer,action text,created_at text);
    ''')
    if c.execute('select count(*) from users').fetchone()[0]==0:
        c.executemany('insert into users(username,password_hash,full_name,role) values(?,?,?,?)',[('admin',generate_password_hash('Admin@2026'),'Operations Admin','Admin'),('leader',generate_password_hash('Leader@2026'),'Team Leader','Team Leader')])
    if c.execute('select count(*) from items').fetchone()[0]==0:
        c.executemany('insert into items(name,category,total_qty,available_qty,replacement_cost) values(?,?,?,?,?)',[('Plastic Chairs','Seating',1200,1200,750),('Tents 100-Seater','Shelter',30,30,25000),('Dinner Plates','Crockery',2000,2000,250),('Tablecloths','Linen',400,400,900),('Folding Tables','Furniture',150,150,3500)])
    db.commit(); db.close()
def flashes():
    from flask import get_flashed_messages
    return ''.join([f'<div class="flash">{m}</div>' for m in get_flashed_messages()])
def layout(title,sub,body):
    u=user(); nav=''; who=''
    if u:
        if u['role']=='Admin':
            nav=f'<nav><a href="{url_for("dashboard")}">Admin Dashboard</a><a href="{url_for("events")}">All Dispatch Jobs</a><a href="{url_for("new_event")}">Prepare Dispatch</a><a href="{url_for("inventory")}">Inventory</a><a href="{url_for("reports")}">Reports</a><a href="{url_for("logout")}">Logout</a></nav>'
        else:
            nav=f'<nav><a href="{url_for("dashboard")}">Leader Dashboard</a><a href="{url_for("events")}">My Dispatches</a><a href="{url_for("logout")}">Logout</a></nav>'
        who=f'<p>{u["full_name"]}<br><span>{u["role"]}</span></p>'
    return render_template_string(f'<!doctype html><html><head><title>{title}</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet"><style>{CSS}</style></head><body><div class="shell"><aside class="side"><div class="brand">Catering Dispatch<span>Quantity verification & returns</span></div>{nav}{who}</aside><main class="main"><div class="top"><div><h1>{title}</h1><p class="sub">{sub}</p></div><div class="pill">Two-way dispatch/return checks</div></div>{flashes()}{body}</main></div></body></html>')
@app.route('/')
def index(): return redirect(url_for('dashboard') if user() else url_for('login'))
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=q('select * from users where username=?',(request.form['username'],),one=True)
        if u and check_password_hash(u['password_hash'],request.form['password']): session.clear(); session['uid']=u['id']; log(f'{u["username"]} logged in'); return redirect(url_for('dashboard'))
        flash('Invalid username or password.')
    return render_template_string(f'<html><head><title>Login</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap" rel="stylesheet"><style>{CSS}</style></head><body class="login"><div class="card"><h1>Catering Dispatch Login</h1><p class="sub">Prevent equipment loss through signed dispatch and return reconciliation.</p><form method="post"><label>Username<input name="username"></label><label>Password<input type="password" name="password"></label><button class="btn primary">Login</button></form><p class="sub">admin/Admin@2026 · leader/Leader@2026</p></div></body></html>')
@app.route('/logout')
@need
def logout(): log('User logged out'); session.clear(); return redirect(url_for('login'))
@app.route('/dashboard')
@need
def dashboard():
    active=q('select count(*) c from events where status in ("Dispatched","Returned With Loss")',one=True)['c']; losses=q('select coalesce(sum(loss_value),0) total from dispatch_items',one=True)['total']; missing=q('select coalesce(sum(qty_dispatched-qty_returned),0) m from dispatch_items where qty_returned<qty_dispatched',one=True)['m']
    recent=q('select * from events order by id desc limit 8'); rows=''.join([f'<tr><td>{r["client_name"]}</td><td>{r["event_type"]}</td><td>{r["team_leader"]}</td><td>{r["status"]}</td><td><a class="btn" href="{url_for("event_detail",eid=r["id"])}">Open</a></td></tr>' for r in recent])
    u=user(); is_admin=u and u['role']=='Admin'
    title='Admin Dashboard' if is_admin else 'Team Leader Dashboard'
    sub='Admin prepares dispatch jobs, controls inventory and checks reports.' if is_admin else 'Team leader confirms pickup and records returned items.'
    role_note='<div class="flash">Admin: prepare jobs, manage inventory, and review reports. You do not sign items out in the field.</div>' if is_admin else '<div class="flash">Leader: open your dispatches, confirm pickup, then record what returned. No inventory or reports access.</div>'
    return layout(title,sub,role_note+f'<section class="grid three"><div class="kpi"><span>Active / Loss Events</span><div class="big">{active}</div></div><div class="kpi"><span>Missing Units</span><div class="big danger">{missing}</div></div><div class="kpi"><span>Loss Value</span><div class="big">KSh {losses:,.0f}</div></div></section><section class="grid two"><div class="card hero-card"><img class="system-photo" src="/static/project_reference.jpg" alt="Catering event equipment reference"><h2>Catering event equipment reference</h2><p class="sub">Visual reference for events equipment that must be dispatched, signed out and reconciled on return.</p></div><div class="card"><h2>Recent Events</h2><table><tr><th>Client</th><th>Type</th><th>Leader</th><th>Status</th><th></th></tr>{rows}</table></div>')
@app.route('/inventory')
@admin
def inventory():
    rows=''.join([f'<tr><td>{i["name"]}</td><td>{i["category"]}</td><td>{i["total_qty"]}</td><td>{i["available_qty"]}</td><td>KSh {i["replacement_cost"]:,.0f}</td><td><a class="btn" href="{url_for("edit_inventory",iid=i["id"])}">Edit</a></td></tr>' for i in q('select * from items order by category,name')])
    form=f'''<div class="card"><h2>Add Inventory Item</h2><form method="post" action="{url_for('add_inventory')}"><label>Item Name<input name="name" placeholder="Example: Dinner Plates" required></label><label>Category<input name="category" placeholder="Example: Crockery" required></label><label>Total Quantity<input type="number" min="0" name="total_qty" required></label><label>Available Quantity<input type="number" min="0" name="available_qty" required></label><label>Replacement Cost (KSh)<input type="number" min="0" step="0.01" name="replacement_cost" required></label><button class="btn primary">Add Item</button></form></div>'''
    table=f'''<div class="card"><h2>Inventory List</h2><table><tr><th>Item</th><th>Category</th><th>Total</th><th>Available</th><th>Replacement Cost</th><th>Action</th></tr>{rows}</table></div>'''
    return layout('Inventory','Add, view and update catering items before dispatching them to events.',f'<section class="grid two">{form}{table}</section>')

@app.route('/inventory/add',methods=['POST'])
@admin
def add_inventory():
    name=request.form.get('name','').strip()
    category=request.form.get('category','').strip()
    total=max(0,int(request.form.get('total_qty',0) or 0))
    available=max(0,int(request.form.get('available_qty',0) or 0))
    cost=max(0,float(request.form.get('replacement_cost',0) or 0))
    if available>total:
        flash('Available quantity cannot be more than total quantity.')
        return redirect(url_for('inventory'))
    ex('insert into items(name,category,total_qty,available_qty,replacement_cost) values(?,?,?,?,?)',(name,category,total,available,cost))
    log(f'Added inventory item: {name} ({available}/{total})')
    flash('Inventory item added successfully.')
    return redirect(url_for('inventory'))

@app.route('/inventory/<int:iid>/edit',methods=['GET','POST'])
@admin
def edit_inventory(iid):
    item=q('select * from items where id=?',(iid,),one=True)
    if not item: abort(404)
    if request.method=='POST':
        name=request.form.get('name','').strip()
        category=request.form.get('category','').strip()
        total=max(0,int(request.form.get('total_qty',0) or 0))
        available=max(0,int(request.form.get('available_qty',0) or 0))
        cost=max(0,float(request.form.get('replacement_cost',0) or 0))
        if available>total:
            flash('Available quantity cannot be more than total quantity.')
            return redirect(url_for('edit_inventory',iid=iid))
        ex('update items set name=?,category=?,total_qty=?,available_qty=?,replacement_cost=? where id=?',(name,category,total,available,cost,iid))
        log(f'Updated inventory item: {name} ({available}/{total})')
        flash('Inventory item updated successfully.')
        return redirect(url_for('inventory'))
    form=f'''<div class="card"><form method="post"><label>Item Name<input name="name" value="{item["name"]}" required></label><label>Category<input name="category" value="{item["category"]}" required></label><label>Total Quantity<input type="number" min="0" name="total_qty" value="{item["total_qty"]}" required></label><label>Available Quantity<input type="number" min="0" name="available_qty" value="{item["available_qty"]}" required></label><label>Replacement Cost (KSh)<input type="number" min="0" step="0.01" name="replacement_cost" value="{item["replacement_cost"]}" required></label><button class="btn primary">Save Changes</button><a class="btn" href="{url_for('inventory')}">Cancel</a></form></div>'''
    return layout('Edit Inventory Item','Update stock quantity and replacement value for this catering item.',form)
@app.route('/events')
@need
def events():
    rows=''.join([f'<tr><td>{e["client_name"]}</td><td>{e["venue"]}</td><td>{e["event_date"]}</td><td>{e["team_leader"]}</td><td>{e["status"]}</td><td><a class="btn" href="{url_for("event_detail",eid=e["id"])}">Open</a></td></tr>' for e in q('select * from events order by id desc')])
    
    u=user(); is_admin=u and u['role']=='Admin'
    create=f'<p><a class="btn primary" href="{url_for("new_event") }">Prepare Dispatch</a></p>' if is_admin else '<p class="sub">These are the dispatch jobs you confirm and return after the event.</p>'
    title='All Dispatch Jobs' if is_admin else 'My Dispatches'
    sub='Admin views prepared jobs and their status.' if is_admin else 'Leader confirms pickup and records returns.'
    return layout(title,sub,f'{create}<div class="card"><table><tr><th>Client</th><th>Venue</th><th>Date</th><th>Leader</th><th>Status</th><th></th></tr>{rows}</table></div>')
@app.route('/events/new',methods=['GET','POST'])
@admin
def new_event():
    items=q('select * from items order by name')
    if request.method=='POST':
        eid=ex('insert into events(client_name,event_type,venue,event_date,team_leader,created_at) values(?,?,?,?,?,?)',(request.form['client_name'],request.form['event_type'],request.form['venue'],request.form['event_date'],request.form['team_leader'],datetime.now().isoformat(timespec='seconds')))
        for i in items:
            qty=int(request.form.get(f'qty_{i["id"]}',0) or 0)
            if qty>0:
                ex('insert into dispatch_items(event_id,item_id,qty_dispatched,last_seen) values(?,?,?,?)',(eid,i['id'],qty,'Store loading bay before dispatch'))
        log(f'Admin prepared dispatch job #{eid} for {request.form["client_name"]}'); flash('Dispatch job prepared. Team leader must confirm pickup before items leave.'); return redirect(url_for('event_detail',eid=eid))
    qtys=''.join([f'<label>{i["name"]} available {i["available_qty"]}<input type="number" min="0" max="{i["available_qty"]}" name="qty_{i["id"]}" value="0"></label>' for i in items])
    return layout('Prepare Dispatch','Admin prepares the event job and the items expected to leave the store.',f'<div class="card"><form method="post"><label>Client Name<input name="client_name" required></label><label>Event Type<select name="event_type"><option>Wedding</option><option>Funeral</option><option>Corporate Event</option><option>Private Party</option></select></label><label>Venue<input name="venue" required></label><label>Event Date<input type="date" name="event_date" required></label><label>Team Leader<input name="team_leader" required></label><h3>Dispatch Quantities</h3>{qtys}<button class="btn primary">Prepare Dispatch Job</button></form></div>')
@app.route('/event/<int:eid>')
@need
def event_detail(eid):
    e=q('select * from events where id=?',(eid,),one=True); rows=q('select di.*,i.name,i.replacement_cost from dispatch_items di join items i on i.id=di.item_id where di.event_id=?',(eid,))
    trs=''.join([f'<tr><td>{r["name"]}</td><td>{r["qty_dispatched"]}</td><td>{r["qty_returned"]}</td><td>{r["qty_dispatched"]-r["qty_returned"]}</td><td>{r["last_seen"]}</td><td>KSh {r["loss_value"]:,.0f}</td></tr>' for r in rows])
    forms=''.join([f'<label>{r["name"]} returned<input type="number" min="0" max="{r["qty_dispatched"]}" name="ret_{r["id"]}" value="{r["qty_dispatched"]}"></label>' for r in rows])
    u=user(); is_admin=u and u['role']=='Admin'
    base=f'<div class="card"><h2>{e["client_name"]} — {e["event_type"]}</h2><p>{e["venue"]} · {e["event_date"]} · Leader: {e["team_leader"]}</p><p>Status: <b>{e["status"]}</b></p><a class="btn" href="{url_for("events")}">Back</a><table><tr><th>Item</th><th>Prepared</th><th>Returned</th><th>Missing</th><th>Last Seen</th><th>Loss</th></tr>{trs}</table></div>'
    if is_admin:
        html=base+'<div class="card"><h2>Admin View</h2><p class="sub">Admin prepares the dispatch and checks progress. The team leader must confirm pickup and record returns.</p></div>'
    else:
        sign_btn=f'<a class="btn primary" href="{url_for("sign_dispatch",eid=eid)}">Confirm Pickup / Sign Dispatch</a>' if e['status']=='Draft' else ''
        return_form=f'<div class="card"><h2>Record Returned Items</h2><form method="post" action="{url_for("reconcile",eid=eid)}">{forms}<label>Last Seen / Notes<textarea name="last_seen">Event venue return count / truck loading point</textarea></label><button class="btn primary">Save Return Record</button></form></div>' if e['status']!='Draft' else '<div class="card"><p class="sub">First confirm pickup before recording returns.</p></div>'
        html=base+f'<div class="card"><h2>Leader Action</h2>{sign_btn}<p class="sub">Confirm the items when they leave the store. After the event, record what came back.</p></div>'+return_form
    return layout('Dispatch Detail','Prepared quantity versus returned quantity.',html)
@app.route('/event/<int:eid>/sign')
@need
def sign_dispatch(eid):
    if user()['role']!='Team Leader': abort(403)
    e=q('select * from events where id=?',(eid,),one=True)
    if e['status']=='Draft':
        for r in q('select * from dispatch_items where event_id=?',(eid,)): ex('update items set available_qty=available_qty-? where id=?',(r['qty_dispatched'],r['item_id']))
        ex('update events set status="Dispatched",dispatch_signed_at=? where id=?',(datetime.now().isoformat(timespec='seconds'),eid)); log(f'Team leader signed dispatch #{eid} before truck left'); flash('Pickup confirmed. Items have officially left the store.')
    return redirect(url_for('event_detail',eid=eid))
@app.route('/event/<int:eid>/reconcile',methods=['POST'])
@need
def reconcile(eid):
    if user()['role']!='Team Leader': abort(403)
    loss_total=0; missing_total=0; note=request.form.get('last_seen','Return checkpoint')
    for r in q('select di.*,i.replacement_cost from dispatch_items di join items i on i.id=di.item_id where di.event_id=?',(eid,)):
        ret=int(request.form.get(f'ret_{r["id"]}',0)); missing=max(0,r['qty_dispatched']-ret); loss=missing*r['replacement_cost']; loss_total+=loss; missing_total+=missing
        ex('update dispatch_items set qty_returned=?,last_seen=?,loss_value=? where id=?',(ret,note,loss,r['id'])); ex('update items set available_qty=available_qty+? where id=?',(ret,r['item_id']))
    status='Returned Clear' if missing_total==0 else 'Returned With Loss'
    ex('update events set status=?,return_signed_at=? where id=?',(status,datetime.now().isoformat(timespec='seconds'),eid)); log(f'Reconciled event #{eid}: missing {missing_total}, loss KSh {loss_total:,.0f}'); flash(f'Return reconciled. Missing: {missing_total}; Loss: KSh {loss_total:,.0f}.'); return redirect(url_for('event_detail',eid=eid))
@app.route('/reports')
@admin
def reports():
    rows=q('select e.client_name,e.event_type,e.venue,e.status,i.name,di.qty_dispatched,di.qty_returned,(di.qty_dispatched-di.qty_returned) missing,di.last_seen,di.loss_value from dispatch_items di join events e on e.id=di.event_id join items i on i.id=di.item_id order by e.id desc')
    trs=''.join([f'<tr><td>{r["client_name"]}</td><td>{r["name"]}</td><td>{r["qty_dispatched"]}</td><td>{r["qty_returned"]}</td><td class="danger">{r["missing"]}</td><td>{r["last_seen"]}</td><td>KSh {r["loss_value"]:,.0f}</td></tr>' for r in rows])
    return layout('Loss & Reconciliation Reports','Shows exactly where missing items were last seen and the value of leakage.',f'<p><a class="btn ghost" href="{url_for("export_csv")}">Export CSV</a></p><div class="card"><table><tr><th>Client</th><th>Item</th><th>Sent</th><th>Returned</th><th>Missing</th><th>Last Seen</th><th>Loss</th></tr>{trs}</table></div>')
@app.route('/export.csv')
@admin
def export_csv():
    rows=q('select e.client_name,i.name,di.qty_dispatched,di.qty_returned,(di.qty_dispatched-di.qty_returned) missing,di.last_seen,di.loss_value from dispatch_items di join events e on e.id=di.event_id join items i on i.id=di.item_id')
    lines=['Client,Item,Sent,Returned,Missing,LastSeen,LossValue']+[f'{r["client_name"]},{r["name"]},{r["qty_dispatched"]},{r["qty_returned"]},{r["missing"]},{r["last_seen"]},{r["loss_value"]}' for r in rows]
    return Response('\n'.join(lines),mimetype='text/csv')
# Initialize the SQLite database when the module is imported by Gunicorn/Render.
init_db()

if __name__=='__main__':
    debug_mode = os.environ.get('FLASK_DEBUG') == '1'
    bind_host = '0.0.0.0'
    bind_port = int(os.environ.get('PORT', 5053))
    app.run(debug=debug_mode, host=bind_host, port=bind_port)
