
# A very simple Flask Hello World app for you to get started with...
from flask import Flask, render_template, redirect, request, url_for, json, session
from flask_mail import Mail, Message
import mysql.connector, random,os, hashlib, jwt
from time import time
comments = []
app = Flask(__name__)
app.secret_key = "blabla"
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'leonidkp2007@gmail.com'
app.config['MAIL_PASSWORD'] = 'tpii opao coqb jtzu'
app.config['MAIL_USE_TLS'] = True
app.config["MAIL_USE_SSL"] = False
mail= Mail(app)
@app.route('/b_profils/<int:child_id>')
def profils(child_id):
    if not session.get("loggedin") or session.get("user_type") != "parent":
        return redirect(url_for("login_plan"))
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    mycursor = mydb.cursor(dictionary=True)
    try:
        mycursor.execute("""
            SELECT id, name, points
            FROM children
            WHERE id = %s
        """, (child_id,))
        child = mycursor.fetchone()
        if not child:
            return redirect(url_for("parsk"))
        mycursor.execute("""
            SELECT priority, COUNT(*) as count
            FROM tasks
            WHERE assigned_to = %s
            GROUP BY priority
        """, (child_id,))
        counts_raw = mycursor.fetchall()
        task_counts = {
            "urgent_important": 0,
            "urgent_not_important": 0,
            "not_urgent_important": 0,
            "not_urgent_not_important": 0
        }
        for row in counts_raw:
            task_counts[row["priority"]] = row["count"]
        return render_template(
            "b_profils.html",
            child=child,
            task_counts=task_counts
        )
    finally:
        mycursor.close()
        mydb.close()
def get_tasks(child_id, priority, template):
    if not session.get("loggedin") or session.get("user_type") != "parent":
        return redirect(url_for("login_plan"))

    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    mycursor = mydb.cursor(dictionary=True)

    try:
        mycursor.execute("""
            SELECT id, name
            FROM children
            WHERE id = %s
        """, (child_id,))
        child = mycursor.fetchone()

        if not child:
            return redirect(url_for("profils"))
        mycursor.execute("""
            SELECT id, title, deadline
            FROM tasks
            WHERE assigned_to = %s AND priority = %s
        """, (child_id, priority))

        tasks_raw = mycursor.fetchall()

        tasks = [{
            "id": t["id"],
            "nosaukums": t["title"],
            "deadline": t["deadline"].strftime("%d.%m.%Y") if t["deadline"] else None
        } for t in tasks_raw]

        return render_template(
            template,
            tasks=tasks,
            task_count=len(tasks),
            child=child,
            child_id=child_id
        )

    finally:
        mycursor.close()
        mydb.close()
@app.route('/SS/<int:child_id>')
def SS(child_id):
    return get_tasks(child_id, "urgent_important", "S&S.html")
@app.route('/SnS/<int:child_id>')
def SnS(child_id):
    return get_tasks(child_id, "urgent_not_important", "S&nS.html")
@app.route('/nSS/<int:child_id>')
def nSS(child_id):
    return get_tasks(child_id, "not_urgent_important", "nS&S.html")
@app.route('/nSnS/<int:child_id>')
def nSnS(child_id):
    return get_tasks(child_id, "not_urgent_not_important", "nSnS.html")
from datetime import datetime
@app.route('/uzd_piev/<int:child_id>', methods=["GET", "POST"])
def uzd_piev(child_id):
    if not session.get("loggedin") or session.get("user_type") != "parent":
        return redirect(url_for("login_plan"))
    if request.method == "POST":
        mydb = mysql.connector.connect(
            host="lkupelis.mysql.pythonanywhere-services.com",
            user="lkupelis",
            passwd="Databases2024!",
            database="lkupelis$default"
        )
        mycursor = mydb.cursor()
        nosaukums = request.form["nosaukums"]
        punkti = int(request.form["punkti"])
        datums = request.form["datums"]
        priority = request.form["priority"]
        parent_id = session["user_id"]
        mycursor.execute("SELECT family_id FROM parents WHERE id=%s", (parent_id,))
        family_id = mycursor.fetchone()[0]
        mycursor.execute("""
            INSERT INTO tasks
            (family_id, title, points, assigned_to, deadline, priority, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (family_id, nosaukums, punkti, child_id, datums, priority, parent_id,))
        mydb.commit()
        mydb.close()
        return redirect(url_for('profils', child_id=child_id))
    return render_template("uzd_piev.html", child_id=child_id)
@app.route('/login_plan', methods=["GET", "POST"])
def login_plan():
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    mycursor = mydb.cursor(dictionary=True)
    if request.method == "GET":
        return render_template('Login_plan.html')
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return render_template("Login_plan.html", error="Aizpildiet visus laukus")
    try:
        mycursor.execute("SELECT * FROM parents WHERE username = %s", (username,))
        user = mycursor.fetchone()
        user_type = "parent"
        if not user:
            mycursor.execute("SELECT * FROM children WHERE username = %s", (username,))
            user = mycursor.fetchone()
            user_type = "child"
        if not user:
            return render_template("Login_plan.html", error="Nepareizs lietotājvārds vai parole")
        salt = "q&%$jhgflkj )*"
        hashed_input = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        if hashed_input == user["password_hash"]:
            session['loggedin'] = True
            session['username'] = username
            session['user_type'] = user_type
            session['user_id'] = user["id"]
            session['family_id'] = user["family_id"]
            if user_type=="child":
                return redirect(url_for('b_profils'))
            if user_type=="parent":
                return redirect(url_for('parsk'))
        else:
            return render_template("Login_plan.html", error="Nepareizs lietotājvārds vai parole")
    except Exception as e:
        print(f"Login error: {e}")
        return render_template("Login_plan.html", error="Radās kļūda")
    finally:
        mycursor.close()
        mydb.close()
@app.route('/signup_plan', methods=["GET", "POST"])
def signup_plan():
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    mycursor = mydb.cursor(dictionary=True)
    if request.method == "GET":
        return render_template('SignUp_plan.html')
    username = request.form.get("username")
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    password1 = request.form.get("password1")
    family_id = request.form.get("family_id")
    is_parent = request.form.get("vecaks") == "on"
    if not (username and name and email and password and password1):
        return render_template("SignUp_plan.html", error="Nav aizpildīti visi lauki")
    if password != password1:
        return render_template("SignUp_plan.html", error="Paroles nesakrīt")
    try:
        mycursor.execute("SELECT id FROM parents WHERE username = %s", (username,))
        if mycursor.fetchone():
            return render_template("SignUp_plan.html", error="Username jau eksistē")
        mycursor.execute("SELECT id FROM children WHERE username = %s", (username,))
        if mycursor.fetchone():
            return render_template("SignUp_plan.html", error="Username jau eksistē")
        mycursor.execute("SELECT id FROM parents WHERE Email = %s", (email,))
        if mycursor.fetchone():
            return render_template("SignUp_plan.html", error="Email jau tiek izmantots")
        mycursor.execute("SELECT id FROM children WHERE Email = %s", (email,))
        if mycursor.fetchone():
            return render_template("SignUp_plan.html", error="Email jau tiek izmantots")
        if not family_id:
            mycursor.execute("INSERT INTO families () VALUES ()")
            mydb.commit()
            family_id = mycursor.lastrowid
        else:
            mycursor.execute("SELECT id FROM families WHERE id = %s", (family_id,))
            if not mycursor.fetchone():
                return render_template("SignUp_plan.html", error="Ģimene neeksistē")
        salt = "q&%$jhgflkj )*"
        hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        if is_parent:
            sql = """
                INSERT INTO parents (family_id, username, name, Email, password_hash)
                VALUES (%s, %s, %s, %s, %s)
            """
        else:
            sql = """
                INSERT INTO children (family_id, username, name, Email, password_hash)
                VALUES (%s, %s, %s, %s, %s)
            """
        mycursor.execute(sql, (family_id, username, name, email, hashed_password))
        mydb.commit()
        try:
            msg = Message(
                "Reģistrācija veiksmīga",
                sender="leonidskup2007@gmail.com",
                recipients=[email]
            )

            msg.body = f"""
Sveiki!

Jūs veiksmīgi reģistrējāties.

Ģimenes ID: {family_id}
Lietotājvārds: {username}
"""
            mail.send(msg)
        except Exception as e:
            print(f"E-pasta kļūda: {e}")
        return redirect(url_for('login_plan'))
    except Exception as e:
        mydb.rollback()
        print(f"Error: {e}")
        return render_template("SignUp_plan.html", error="Kļūda reģistrācijā")

    finally:
        mycursor.close()
        mydb.close()
@app.route('/re_pass_plan', methods=["GET", "POST"])
def re_pass_plan():
    if request.method == "GET":
        return render_template("re_pass_plan.html")
    username = request.form.get("username")
    if not username:
        return render_template("re_pass_plan.html", error="Ievadiet lietotājvārdu")
    mydb = None
    mycursor = None
    try:
        mydb = mysql.connector.connect(
            host="lkupelis.mysql.pythonanywhere-services.com",
            user="lkupelis",
            passwd="Databases2024!",
            database="lkupelis$default"
        )
        mycursor = mydb.cursor(dictionary=True)
        mycursor.execute("SELECT Email FROM parents WHERE username = %s", (username,))
        user = mycursor.fetchone()
        if not user:
            mycursor.execute("SELECT Email FROM children WHERE username = %s", (username,))
            user = mycursor.fetchone()
        if not user:
            return render_template("re_pass_plan.html", error="Tāds lietotājvārds neeksistē")
        email = user.get("Email") or user.get("email")
        if not email:
            return render_template("re_pass_plan.html", error="Lietotājam nav e-pasta")
        tok = jwt.encode(
            {'reset_password': username, 'exp': time() + 500},
            key=app.secret_key,
            algorithm='HS256'
        )
        try:
            msg = Message(
                subject="Password Reset",
                sender="leonidskup2007@gmail.com",
                recipients=[email]
            )
            msg.html = render_template('resetPwdEmail_plan.html', token=tok, username=username)
            mail.send(msg)
        except Exception as e:
            print("EMAIL ERROR:", e)
            return render_template("re_pass_plan.html", error="Neizdevās nosūtīt e-pastu")
        return render_template("re_pass_plan.html", error="E-pasts aizsūtīts!")
    except Exception as e:
        print("DB ERROR:", e)
        return render_template("re_pass_plan.html", error="Datubāzes kļūda")
    finally:
        if mycursor:
            mycursor.close()
        if mydb:
            mydb.close()
@app.route('/resetPwd_plan', methods=["GET", "POST"])
def resetPwd_plan():
    if request.method == "GET":
        try:
            token = request.args.get("token")
            tok = jwt.decode(token, key=app.secret_key, algorithms=['HS256'])
            username = tok['reset_password']
            expTime = tok['exp']
            if time() > expTime:
                return "Tokena laiks ir beidzies"
            return render_template("resetPwd_plan.html", username=username)
        except Exception:
            return "Nederīgs tokens"
    username = request.form.get("username")
    password = request.form.get("password")
    if not password:
        return render_template("resetPwd_plan.html", error="Ievadiet jaunu paroli", username=username)
    salt = "q&%$jhgflkj )*"
    hashed_password = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    mydb = None
    mycursor = None
    try:
        mydb = mysql.connector.connect(
            host="lkupelis.mysql.pythonanywhere-services.com",
            user="lkupelis",
            passwd="Databases2024!",
            database="lkupelis$default"
        )
        mycursor = mydb.cursor()
        mycursor.execute("SELECT id FROM parents WHERE username = %s", (username,))
        if mycursor.fetchone():
            mycursor.execute(
                "UPDATE parents SET password_hash = %s WHERE username = %s",
                (hashed_password, username)
            )
        else:
            mycursor.execute(
                "UPDATE children SET password_hash = %s WHERE username = %s",
                (hashed_password, username)
            )
        mydb.commit()
        return redirect(url_for('login_plan'))
    except Exception as e:
        print("RESET ERROR:", e)
        return render_template("resetPwd_plan.html", error="Radās kļūda", username=username)
    finally:
        if mycursor:
            mycursor.close()
        if mydb:
            mydb.close()
@app.route('/berni_parskats')
def parsk():
    if not session.get("loggedin") or session.get("user_type") != "parent":
        return redirect(url_for("login_plan"))
    print("SESSION:", session)
    parent_id = session["user_id"]
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    mycursor = mydb.cursor(dictionary=True)
    try:
        mycursor.execute("SELECT family_id FROM parents WHERE id = %s", (parent_id,))
        parent = mycursor.fetchone()
        family_id = parent["family_id"]
        mycursor.execute("""
            SELECT id, name, points
            FROM children
            WHERE family_id = %s
        """, (family_id,))
        children = mycursor.fetchall()

        return render_template("berni_parskats.html", children=children)
    finally:
        mycursor.close()
        mydb.close()
@app.route('/child/<int:child_id>')
def child_profile_parent(child_id):
    if not session.get("loggedin") or session.get("user_type") != "parent":
        return redirect(url_for("login_plan"))
    return redirect(url_for("profils", child_id=child_id))
@app.route('/balvas')
def balvas():
    print("SESSION:", session)
    if 'user_id' not in session:
        return redirect(url_for('login_plan'))
    user_id = session['user_id']
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    cursor = mydb.cursor(dictionary=True)
    try:
        if session.get("user_type") == "parent":
            cursor.execute("SELECT family_id FROM parents WHERE id=%s", (user_id,))
        else:
            cursor.execute("SELECT family_id FROM children WHERE id=%s", (user_id,))
        family = cursor.fetchone()
        family_id = family["family_id"]
        cursor.execute("""
            SELECT id, title, cost
            FROM rewards
            WHERE family_id = %s
        """, (family_id,))
        rewards = cursor.fetchall()
        return render_template("balvas.html", rewards=rewards)
    finally:
        cursor.close()
        mydb.close()
@app.route('/delete_reward/<int:reward_id>', methods=['POST'])
def delete_reward(reward_id):
    if 'user_id' not in session or session.get("user_type") != "parent":
        return redirect(url_for('login_plan'))
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    cursor = mydb.cursor()
    try:
        cursor.execute("DELETE FROM rewards WHERE id = %s", (reward_id,))
        mydb.commit()
    finally:
        cursor.close()
        mydb.close()
    return redirect(url_for('balvas'))
@app.route('/balvas_piev', methods=['GET', 'POST'])
def balvas_piev():
    if 'user_id' not in session or session.get("user_type") != "parent":
        return redirect(url_for('login_plan'))
    user_id = session['user_id']
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    cursor = mydb.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            title = request.form.get('title')
            cost = request.form.get('cost')
            if not title or not cost:
                return "Kļūda: aizpildi visus laukus"
            cursor.execute("""
                SELECT family_id
                FROM parents
                WHERE id = %s
            """, (user_id,))
            parent = cursor.fetchone()
            family_id = parent["family_id"]
            cursor.execute("""
                INSERT INTO rewards (family_id, title, cost)
                VALUES (%s, %s, %s)
            """, (family_id, title, cost))
            mydb.commit()
            return redirect(url_for('balvas'))
        return render_template("balvas_piev.html")
    finally:
        cursor.close()
        mydb.close()
@app.route('/profils_b')
def b_profils():
    if not session.get("loggedin") or session.get("user_type") != "child":
        return redirect(url_for("login_plan"))
    user_id = session["user_id"]
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    mycursor = mydb.cursor(dictionary=True)
    try:
        mycursor.execute("""
            SELECT id, name, points
            FROM children
            WHERE id = %s
        """, (user_id,))
        child = mycursor.fetchone()
        mycursor.execute("""
            SELECT priority, COUNT(*) as count
            FROM tasks
            WHERE assigned_to = %s
            GROUP BY priority
        """, (user_id,))
        counts_raw = mycursor.fetchall()
        counts = {
            "urgent_important": 0,
            "urgent_not_important": 0,
            "not_urgent_important": 0,
            "not_urgent_not_important": 0
        }
        for row in counts_raw:
            counts[row["priority"]] = row["count"]
        return render_template(
            "profils_b.html",
            child=child,
            counts=counts
        )
    finally:
        mycursor.close()
        mydb.close()
@app.route('/balvas_sar')
def balvas_sar():
    next_page = request.args.get("next")
    if 'user_id' not in session or session.get("user_type") != "child":
        return redirect(url_for('login_plan'))
    user_id = session['user_id']
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    cursor = mydb.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT points, family_id
            FROM children
            WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()
        user_points = user["points"]
        family_id = user["family_id"]
        cursor.execute("""
            SELECT id, title, cost
            FROM rewards
            WHERE family_id = %s
        """, (family_id,))
        rewards = cursor.fetchall()
        return render_template(
        "balvas_sar.html",
        rewards=rewards,
        user_points=user_points,
        next_page=next_page
        )
    finally:
        cursor.close()
        mydb.close()
def send_email(to_email, subject, body):
    msg = Message(
        subject,
        sender="leonidskup2007@gmail.com",
        recipients=[to_email]
    )
    msg.body = body
    mail.send(msg)
@app.route('/take_reward', methods=['POST'])
def take_reward():
    if 'user_id' not in session or session.get("user_type") != "child":
        return redirect(url_for('login_plan'))
    user_id = session['user_id']
    reward_id = request.form.get("reward_id")
    next_page = request.form.get("next")
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    cursor = mydb.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT title, cost
            FROM rewards
            WHERE id = %s
        """, (reward_id,))
        reward = cursor.fetchone()
        cursor.execute("""
            SELECT name, points, family_id
            FROM children
            WHERE id = %s
        """, (user_id,))
        child = cursor.fetchone()
        if reward and child and child["points"] >= reward["cost"]:
            cursor.execute("""
                UPDATE children
                SET points = points - %s
                WHERE id = %s
            """, (reward["cost"], user_id))
            mydb.commit()
            cursor.execute("""
                SELECT Email
                FROM parents
                WHERE family_id = %s
            """, (child["family_id"],))
            parents = cursor.fetchall()
            subject = "Bērns paņēma balvu"
            body = f"""
Sveiki!

Bērns {child['name']} ir paņēmis balvu:

🎁 {reward['title']}
💰 {reward['cost']} punkti

-- Sistēma
"""
            for parent in parents:
                email = parent.get("Email") or parent.get("email")
                if email:
                    try:
                        send_email(email, subject, body)
                    except Exception as e:
                        print("EMAIL ERROR:", e)
    finally:
        cursor.close()
        mydb.close()
    return redirect(url_for('balvas_sar', next=next_page))
@app.route('/logout_plan')
def logout_plan():
    session.clear()
    return redirect(url_for('login_plan'))
from datetime import datetime

def get_tasks_b(priority, template):
    if not session.get("loggedin") or session.get("user_type") != "child":
        return redirect(url_for("login_plan"))

    user_id = session["user_id"]

    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    mycursor = mydb.cursor(dictionary=True)

    try:
        mycursor.execute("""
            SELECT id, name
            FROM children
            WHERE id = %s
        """, (user_id,))
        child = mycursor.fetchone()

        if not child:
            return redirect(url_for("login_plan"))

        mycursor.execute("""
            SELECT id, title, deadline
            FROM tasks
            WHERE assigned_to = %s
            AND priority = %s
        """, (user_id, priority))

        tasks_raw = mycursor.fetchall()

        tasks = [{
            "id": t["id"],
            "nosaukums": t["title"],
            "deadline": t["deadline"]
        } for t in tasks_raw]

        return render_template(
            template,
            tasks=tasks,
            task_count=len(tasks),
            child=child,
            child_id=user_id,
            now=datetime.now()
        )

    finally:
        mycursor.close()
        mydb.close()
@app.route('/SS_b')
def SS_b():
    return get_tasks_b("urgent_important", "S&S_b.html")
@app.route('/SnS_b')
def SnS_b():
    return get_tasks_b("urgent_not_important", "S&nS_b.html")
@app.route('/nSS_b')
def nSS_b():
    return get_tasks_b("not_urgent_important", "nS&S_b.html")
@app.route('/nSnS_b')
def nSnS_b():
    return get_tasks_b("not_urgent_not_important", "nS&nS_b.html")
@app.route('/update_task_status', methods=['POST'])
def update_task_status():
    if not session.get("loggedin"):
        return redirect(url_for("login_plan"))
    task_id = request.form.get("task_id")
    mydb = mysql.connector.connect(
        host="lkupelis.mysql.pythonanywhere-services.com",
        user="lkupelis",
        passwd="Databases2024!",
        database="lkupelis$default"
    )
    mycursor = mydb.cursor(dictionary=True)
    try:
        mycursor.execute("""
            SELECT assigned_to, points
            FROM tasks
            WHERE id = %s
        """, (task_id,))
        task = mycursor.fetchone()
        if not task:
            return redirect(request.referrer)
        mycursor.execute("""
            UPDATE children
            SET points = points + %s
            WHERE id = %s
        """, (task["points"], task["assigned_to"]))
        mycursor.execute("""
            DELETE FROM tasks
            WHERE id = %s
        """, (task_id,))
        mydb.commit()
    finally:
        mycursor.close()
        mydb.close()
    return redirect(request.referrer)
