# auth.py
import os
import json
import re
import time
import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint('auth', __name__, template_folder="templates")

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
OTP_STORAGE_FILE = "otp_sessions.json"

NAME_WORD = r'[A-Z][a-z]{1,29}'
NAME_RE = re.compile(rf'^{NAME_WORD}(?:\s{NAME_WORD})*$')
USERNAME_RE = re.compile(r'^[A-Za-z0-9_.\-@+]{3,30}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
CONTACT_RE = re.compile(r'^09\d{9}$')
PASSWORD_RE = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*\W).{8,}$')
VALID_EMAIL_DOMAINS = {"gmail.com","yahoo.com","outlook.com","hotmail.com","icloud.com"}

OTP_SESSION_KEY = "profile_otp"
OTP_SESSION_EXPIRY = "profile_otp_expiry"

def load_otp_sessions():
    if not os.path.exists(OTP_STORAGE_FILE):
        return {}
    try:
        with open(OTP_STORAGE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_otp_sessions(sessions):
    try:
        with open(OTP_STORAGE_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving OTP sessions: {e}")
        return False

def get_otp_session(username):
    sessions = load_otp_sessions()
    return sessions.get(username)

def save_otp_session(username, otp_data):
    sessions = load_otp_sessions()
    sessions[username] = otp_data
    return save_otp_sessions(sessions)

def delete_otp_session(username):
    sessions = load_otp_sessions()
    if username in sessions:
        del sessions[username]
        return save_otp_sessions(sessions)
    return True

def cleanup_expired_otp_sessions():
    sessions = load_otp_sessions()
    current_time = datetime.utcnow().isoformat()
    
    expired_usernames = []
    for username, session_data in sessions.items():
        expires_at = session_data.get("expires_at")
        if expires_at and expires_at < current_time:
            expired_usernames.append(username)
    
    for username in expired_usernames:
        del sessions[username]
    
    if expired_usernames:
        save_otp_sessions(sessions)
    
    return len(expired_usernames)

def ensure_users_file():
   if not os.path.exists(USERS_FILE):
       with open(USERS_FILE, "w", encoding="utf-8") as f:
           json.dump([], f)

def load_users():
   ensure_users_file()
   try:
       with open(USERS_FILE, "r", encoding="utf-8") as f:
           return json.load(f) or []
   except (json.JSONDecodeError, PermissionError):
       return []

def atomic_save_users(users):
   tmp = USERS_FILE + ".tmp"
   with open(tmp, "w", encoding="utf-8") as f:
       json.dump(users, f, indent=2, ensure_ascii=False)
   os.replace(tmp, USERS_FILE)

def gen_otp():
   return str(random.randint(100000, 999999))

@auth.route('/register', methods=['GET','POST'])
def register():
    form_data = {}
    if request.method == 'POST':
        data = request.form
        form_data = data.to_dict()
        
        first_name = data.get('first_name','').strip()
        middle_name = data.get('middle_name','').strip()
        last_name = data.get('last_name','').strip()
        dob = data.get('dob','').strip()
        contact = data.get('contact','').strip()
        contact_clean = contact.replace(" ", "").replace("-", "")
        province = data.get('province','').strip()
        city = data.get('city','').strip()
        barangay = data.get('barangay','').strip()
        zipcode = data.get('zipcode','').strip()
        street = data.get('street','').strip()
        username_raw = data.get('username','').strip()
        username = username_raw.strip()
        email = data.get('email','').strip().lower()
        password = data.get('password','')
        confirm = data.get('confirm','')

        required_fields = ["first_name", "last_name", "dob", "contact", "username", "email", "password", "confirm", "province", "city", "barangay"]
        for field in required_fields:
            if not data.get(field) or not data.get(field).strip():
                flash(f"{field.replace('_', ' ').title()} is required.", "error")
                return render_template('register.html', form_data=form_data)

        name_fields = {
            "first_name": "First name",
            "last_name": "Last name", 
            "middle_name": "Middle name"
        }
        
        for field, display_name in name_fields.items():
            value = data.get(field, "").strip()
            if value:
                if not value.replace(" ", "").isalpha():
                    flash(f"{display_name} must contain only letters and spaces.", "error")
                    return render_template('register.html', form_data=form_data)
                
                if len(value) > 50:
                    flash(f"{display_name} too long (max 50 characters)", "error")
                    return render_template('register.html', form_data=form_data)
                
                if field in ["first_name", "last_name"] and len(value) < 2:
                    flash(f"{display_name} must be at least 2 characters long.", "error")
                    return render_template('register.html', form_data=form_data)
                
                if re.search(r'(.)\1{3,}', value.replace(" ", "")):
                    flash(f"{display_name} cannot contain repeated characters like 'aaaa' or 'gggg'.", "error")
                    return render_template('register.html', form_data=form_data)
                
                if len(value.replace(" ", "")) == 1:
                    flash(f"{display_name} must be more than one character.", "error")
                    return render_template('register.html', form_data=form_data)
                
                unique_chars = len(set(value.replace(" ", "").lower()))
                if unique_chars < 2:
                    flash(f"{display_name} must contain at least 2 different letters.", "error")
                    return render_template('register.html', form_data=form_data)
                
                if "  " in value:
                    flash(f"{display_name} cannot contain consecutive spaces.", "error")
                    return render_template('register.html', form_data=form_data)
                
                if value != value.strip():
                    flash(f"{display_name} cannot have leading or trailing spaces.", "error")
                    return render_template('register.html', form_data=form_data)

        try:
            datetime.strptime(dob, '%Y-%m-%d')
            def calculate_age(birth_date):
                try:
                    birth = datetime.strptime(birth_date, '%Y-%m-%d')
                    today = datetime.now()
                    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
                    return age
                except:
                    return None
            
            age = calculate_age(dob)
            if age is None:
                flash("Invalid date of birth.", "error")
                return render_template('register.html', form_data=form_data)
            
            if age < 13:
                flash("You must be at least 13 years old to register.", "error")
                return render_template('register.html', form_data=form_data)
            if age > 80:
                flash("Maximum age limit is 80 years.", "error")
                return render_template('register.html', form_data=form_data)
                
            if datetime.strptime(dob, '%Y-%m-%d') > datetime.now():
                flash("Date of birth cannot be in the future.", "error")
                return render_template('register.html', form_data=form_data)
                
        except ValueError as e:
            flash("Invalid date format. Please use YYYY-MM-DD format.", "error")
            return render_template('register.html', form_data=form_data)

        if not contact_clean.isdigit():
            flash("Contact number must contain only digits.", "error")
            return render_template('register.html', form_data=form_data)
        if len(contact_clean) != 11:
            flash("Contact number must be exactly 11 digits (starting with 09).", "error")
            return render_template('register.html', form_data=form_data)
        if not contact_clean.startswith('09'):
            flash("Contact number must start with 09.", "error")
            return render_template('register.html', form_data=form_data)
        
        if re.search(r'(\d)\1{9}', contact_clean):
            flash("Contact number cannot be all the same digit.", "error")
            return render_template('register.html', form_data=form_data)
        
        if contact_clean in ['09123456789', '09987654321', '09111111111', '09000000000']:
            flash("Please enter a valid contact number.", "error")
            return render_template('register.html', form_data=form_data)

        if len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
            return render_template('register.html', form_data=form_data)
        if len(username) > 30:
            flash("Username too long (max 30 characters)", "error")
            return render_template('register.html', form_data=form_data)
        if not re.match(r'^[a-zA-Z0-9_@.+\-]+$', username):
            flash("Username can only contain letters, numbers, underscores, @, ., +, and hyphens.", "error")
            return render_template('register.html', form_data=form_data)
        
        if re.search(r'(.)\1{3,}', username):
            flash("Username cannot contain repeated characters like 'aaaa' or '1111'.", "error")
            return render_template('register.html', form_data=form_data)
        
        if len(username) >= 3:
            if any(
                ord(username[i].lower()) + 1 == ord(username[i+1].lower()) and 
                ord(username[i+1].lower()) + 1 == ord(username[i+2].lower())
                for i in range(len(username) - 2)
                if username[i].isalpha() and username[i+1].isalpha() and username[i+2].isalpha()
            ):
                flash("Username cannot contain sequential letters like 'abc' or 'xyz'.", "error")
                return render_template('register.html', form_data=form_data)
            
            if any(
                username[i].isdigit() and username[i+1].isdigit() and username[i+2].isdigit() and
                int(username[i]) + 1 == int(username[i+1]) and 
                int(username[i+1]) + 1 == int(username[i+2])
                for i in range(len(username) - 2)
            ):
                flash("Username cannot contain sequential numbers like '123' or '456'.", "error")
                return render_template('register.html', form_data=form_data)
        
        generic_usernames = ["user", "admin", "test", "demo", "guest", "username", "account", 
                           "root", "system", "manager", "operator", "support", "help", "info"]
        if username.lower() in generic_usernames:
            flash("Please choose a more unique username.", "error")
            return render_template('register.html', form_data=form_data)
        
        if username.startswith('_') or username.endswith('_'):
            flash("Username cannot start or end with an underscore.", "error")
            return render_template('register.html', form_data=form_data)

        if not EMAIL_RE.match(email):
            flash("Please enter a valid email address.", "error")
            return render_template('register.html', form_data=form_data)
        
        email_parts = email.split('@')
        if len(email_parts) != 2:
            flash("Invalid email format. Please use format: example@domain.com", "error")
            return render_template('register.html', form_data=form_data)
        
        local_part, domain = email_parts
        
        if not local_part or len(local_part) > 64:
            flash("Invalid email local part.", "error")
            return render_template('register.html', form_data=form_data)
        
        if not domain or '.' not in domain or domain.startswith('.') or domain.endswith('.'):
            flash("Invalid email domain.", "error")
            return render_template('register.html', form_data=form_data)
        
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            flash("Invalid email domain. Domain must have a proper extension (e.g., .com, .org).", "error")
            return render_template('register.html', form_data=form_data)
        
        tld = domain_parts[-1]
        if len(tld) < 2:
            flash("Invalid email domain extension. Domain extension must be at least 2 characters (e.g., .com, .org).", "error")
            return render_template('register.html', form_data=form_data)

        if len(email) > 100:
            flash("Email address too long (max 100 characters)", "error")
            return render_template('register.html', form_data=form_data)
        
        if domain not in VALID_EMAIL_DOMAINS:
            flash("Please use a common email domain (gmail, yahoo, outlook, hotmail, icloud).", "error")
            return render_template('register.html', form_data=form_data)

        disposable_domains = [
            "tempmail.com", "throwaway.com", "fake.com", "example.com", "mailinator.com", 
            "guerrillamail.com", "10minutemail.com", "trashmail.com", "yopmail.com",
            "temp-mail.org", "fakeinbox.com", "sharklasers.com", "getairmail.com"
        ]
        email_domain = email.split('@')[1] if '@' in email else ''
        if email_domain in disposable_domains:
            flash("Please use a permanent email address.", "error")
            return render_template('register.html', form_data=form_data)

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template('register.html', form_data=form_data)
        
        def is_strong_password(pwd):
            if len(pwd) < 8:
                return False, "Password must be at least 8 characters long."
            if not re.search(r'[A-Z]', pwd):
                return False, "Password must contain at least one uppercase letter."
            if not re.search(r'[a-z]', pwd):
                return False, "Password must contain at least one lowercase letter."
            if not re.search(r'\d', pwd):
                return False, "Password must contain at least one number."
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', pwd):
                return False, "Password must contain at least one special character."
            return True, "Password is strong."
        
        is_strong, msg = is_strong_password(password)
        if not is_strong:
            flash(msg, "error")
            return render_template('register.html', form_data=form_data)
        
        if len(password) > 128:
            flash("Password too long (max 128 characters)", "error")
            return render_template('register.html', form_data=form_data)
        
        common_passwords = ["password", "12345678", "qwerty", "admin", "welcome", "password123"]
        if password.lower() in common_passwords:
            flash("Password is too common. Please choose a stronger password.", "error")
            return render_template('register.html', form_data=form_data)
        
        if username.lower() in password.lower():
            flash("Password should not contain your username.", "error")
            return render_template('register.html', form_data=form_data)
        
        if email.split('@')[0].lower() in password.lower():
            flash("Password should not contain your email address.", "error")
            return render_template('register.html', form_data=form_data)
        
        if re.search(r'(.)\1{2,}', password):
            flash("Password should not contain repeated characters.", "error")
            return render_template('register.html', form_data=form_data)

        address_fields = {
            "province": "Province",
            "city": "City/Municipality", 
            "barangay": "Barangay"
        }
        
        for field, display_name in address_fields.items():
            value = data.get(field, "").strip()
            if not value:
                flash(f"{display_name} is required.", "error")
                return render_template('register.html', form_data=form_data)
            
            if re.search(r'[^a-zA-Z0-9\s\-\.\(\)]', value):
                flash(f"{display_name} contains invalid characters.", "error")
                return render_template('register.html', form_data=form_data)
            
            if len(value) > 100:
                flash(f"{display_name} too long (max 100 characters)", "error")
                return render_template('register.html', form_data=form_data)
            
            if re.search(r'(.)\1{5,}', value.replace(" ", "")):
                flash(f"{display_name} contains invalid pattern.", "error")
                return render_template('register.html', form_data=form_data)

        if zipcode:
            if not zipcode.isdigit():
                flash("ZIP code must contain only numbers.", "error")
                return render_template('register.html', form_data=form_data)
            if len(zipcode) != 4:
                flash("ZIP code must be exactly 4 digits.", "error")
                return render_template('register.html', form_data=form_data)

        users = load_users()
        if any(u.get('username','').lower() == username.lower() for u in users):
            flash("Username already exists.", "error")
            return render_template('register.html', form_data=form_data)
        if any(u.get('email','').lower() == email for u in users):
            flash("Email already registered.", "error")
            return render_template('register.html', form_data=form_data)
        if any(u.get('contact','') == contact_clean for u in users):
            flash("Contact number already registered.", "error")
            return render_template('register.html', form_data=form_data)

        hashed = generate_password_hash(password)
        new_user = {
            "username": username,
            "display_username": username_raw,
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "dob": dob,
            "age": age,
            "contact": contact_clean,
            "province": province,
            "city": city,
            "barangay": barangay,
            "zipcode": zipcode,
            "street": street,
            "email": email,
            "password": hashed,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "is_active": True,
            "login_attempts": 0
        }
        
        users.append(new_user)
        try:
            atomic_save_users(users)
        except Exception:
            current_app.logger.exception("Failed saving users.json")
            flash("Failed to save user data. Try again.", "error")
            return render_template('register.html', form_data=form_data)

        flash("Registration successful — you may now log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html', form_data=form_data)

@auth.route('/login', methods=['GET','POST'])
def login():
   if request.method == 'POST':
       identifier = request.form.get('username','').strip()
       password = request.form.get('password','')
       if not identifier or not password:
           flash("Please fill in all fields.", "error")
           return redirect(url_for('auth.login'))
       users = load_users()
       user = next((u for u in users if u.get('username','').lower() == identifier.lower() or u.get('email','').lower() == identifier.lower()), None)
       if not user:
           flash("Invalid username/email or password.", "error")
           return redirect(url_for('auth.login'))
       if not check_password_hash(user.get('password',''), password):
           flash("Invalid username/email or password.", "error")
           return redirect(url_for('auth.login'))

       session['username'] = user.get('username')
       session['display_name'] = user.get('first_name') or user.get('display_username') or user.get('username')
       flash("Welcome back!", "success")
       return redirect(url_for('main.home'))
   if session.get('username'):
       return redirect(url_for('main.home'))
   return render_template('login.html')

@auth.route('/forgot', methods=['GET','POST'])
def forgot():
   cleanup_expired_otp_sessions()
   
   if request.method == 'POST':
       identifier = request.form.get('username','').strip()
       if not identifier:
           flash("Username is required.", "error")
           return redirect(url_for('auth.forgot'))
       
       users = load_users()
       user = next((u for u in users if u.get('username','').lower() == identifier.lower() or u.get('email','').lower() == identifier.lower()), None)
       if not user:
           flash("Username/email not found.", "error")
           return redirect(url_for('auth.forgot'))
       
       username = user.get('username')
       
       existing_session = get_otp_session(username)
       otp = None
       
       if existing_session:
           expires_at = existing_session["expires_at"]
           current_time = datetime.utcnow().isoformat()
           
           if expires_at > current_time:
               otp = existing_session["otp"]
               expires_dt = datetime.fromisoformat(expires_at)
               current_dt = datetime.utcnow()
               remaining_seconds = int((expires_dt - current_dt).total_seconds())
               minutes = remaining_seconds // 60
               seconds = remaining_seconds % 60
               flash(f"Using existing OTP. Expires in {minutes}:{seconds:02d}", "info")
           else:
               otp = gen_otp()
               new_session = {
                   "username": username,
                   "otp": otp,
                   "expires_at": (datetime.utcnow() + timedelta(minutes=3)).isoformat(),
                   "sent_at": datetime.utcnow().isoformat(),
                   "time_consumed": "0:00",
                   "purpose": "password_reset"
               }
               save_otp_session(username, new_session)
               flash(f"New OTP sent to your account: {otp} (Expires in 3 minutes)", "info")
       else:
           otp = gen_otp()
           new_session = {
               "username": username,
               "otp": otp,
               "expires_at": (datetime.utcnow() + timedelta(minutes=3)).isoformat(),
               "sent_at": datetime.utcnow().isoformat(),
               "time_consumed": "0:00",
               "purpose": "password_reset"
           }
           save_otp_session(username, new_session)
           flash(f"OTP sent to your account: {otp} (Expires in 3 minutes)", "info")
       
       return redirect(url_for("auth.verify_otp", username=username))
   
   return render_template('forgot.html')

@auth.route('/verify_otp', methods=['GET','POST'])
def verify_otp():
    cleanup_expired_otp_sessions()
    
    current_username = None
    
    if request.method == "POST":
        current_username = request.form.get("current_username", "").strip()
        if not current_username:
            current_username = request.form.get("username", "").strip()
    else:
        current_username = request.args.get("username", "").strip()
    
    if not current_username:
        sessions = load_otp_sessions()
        if sessions:
            latest_username = None
            latest_time = None
            for username, session_data in sessions.items():
                sent_time = session_data.get("sent_at", "")
                if sent_time and (not latest_time or sent_time > latest_time):
                    latest_time = sent_time
                    latest_username = username
            current_username = latest_username
    
    if not current_username:
        flash("No OTP session found. Please request a new OTP.", "error")
        return redirect(url_for("auth.forgot"))
    
    existing_session = get_otp_session(current_username)
    
    if not existing_session:
        flash("No OTP session found. Please request a new OTP.", "error")
        return redirect(url_for("auth.forgot"))
    
    expires_at = existing_session["expires_at"]
    current_time = datetime.utcnow().isoformat()
    
    if expires_at <= current_time:
        delete_otp_session(current_username)
        flash("OTP expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot"))
    
    expires_dt = datetime.fromisoformat(expires_at)
    current_dt = datetime.utcnow()
    remaining_seconds = int((expires_dt - current_dt).total_seconds())
    
    total_seconds_used = 180 - remaining_seconds
    minutes_used = total_seconds_used // 60
    seconds_used = total_seconds_used % 60
    time_consumed = f"{minutes_used}:{seconds_used:02d}"
    
    existing_session["time_consumed"] = time_consumed
    save_otp_session(current_username, existing_session)
    
    otp_display = existing_session["otp"]
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    time_remaining = f"{minutes}:{seconds:02d}"
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp','').strip()
        new_pass = request.form.get('new_password','')
        confirm = request.form.get('confirm','')
        form_username = request.form.get('current_username','').strip()
        
        if form_username and form_username != current_username:
            new_session = get_otp_session(form_username)
            if new_session:
                return redirect(url_for("auth.verify_otp", username=form_username))
            else:
                flash(f"No OTP session found for {form_username}.", "error")
                return redirect(url_for("auth.forgot"))
        
        current_time_check = datetime.utcnow().isoformat()
        if expires_at <= current_time_check:
            delete_otp_session(current_username)
            flash("OTP expired. Please request a new one.", "error")
            return redirect(url_for("auth.forgot"))
        
        if not entered_otp or not new_pass or not confirm:
            flash("All fields are required.", "error")
            return render_template('otp_reset.html',
                                current_username=current_username,
                                otp_display=otp_display,
                                time_remaining=time_remaining,
                                time_consumed=time_consumed)
        
        if entered_otp != existing_session["otp"]:
            flash("Incorrect OTP. Please try again.", "error")
            return render_template('otp_reset.html',
                                current_username=current_username,
                                otp_display=otp_display,
                                time_remaining=time_remaining,
                                time_consumed=time_consumed)
        
        if new_pass != confirm:
            flash("Passwords do not match.", "error")
            return render_template('otp_reset.html',
                                current_username=current_username,
                                otp_display=otp_display,
                                time_remaining=time_remaining,
                                time_consumed=time_consumed)
        
        if not PASSWORD_RE.match(new_pass):
            flash("Password must be at least 8 chars and include uppercase, lowercase, number and symbol.", "error")
            return render_template('otp_reset.html',
                                current_username=current_username,
                                otp_display=otp_display,
                                time_remaining=time_remaining,
                                time_consumed=time_consumed)
        
        users = load_users()
        updated = False
        for u in users:
            if u.get('username') == current_username:
                u['password'] = generate_password_hash(new_pass)
                u['failed_attempts'] = 0
                u['lockout_until'] = 0
                updated = True
                break
        
        if updated:
            try:
                atomic_save_users(users)
            except Exception:
                flash("Failed to save updated password. Try again.", "error")
                return render_template('otp_reset.html',
                                    current_username=current_username,
                                    otp_display=otp_display,
                                    time_remaining=time_remaining,
                                    time_consumed=time_consumed)
            
            delete_otp_session(current_username)
            
            flash("Password updated successfully.", "success")
            return redirect(url_for('auth.login'))
        
        flash("User for password reset not found.", "error")
        return redirect(url_for('auth.forgot'))
    
    return render_template('otp_reset.html',
                         current_username=current_username,
                         otp_display=otp_display,
                         time_remaining=time_remaining,
                         time_consumed=time_consumed)

@auth.route('/reset_password', methods=['GET','POST'])
def reset_password():
   if request.method == 'POST':
       new_pass = request.form.get('new_password','')
       confirm = request.form.get('confirm','')
       if not new_pass or not confirm:
           flash("All fields are required.", "error")
           return redirect(url_for('auth.reset_password'))
       if new_pass != confirm:
           flash("Passwords do not match.", "error")
           return redirect(url_for('auth.reset_password'))
       if not PASSWORD_RE.match(new_pass):
           flash("Password must be at least 8 chars and include uppercase, lowercase, number and symbol.", "error")
           return redirect(url_for('auth.reset_password'))

       username = session.get('reset_user')
       users = load_users()
       updated = False
       for u in users:
           if u.get('username') == username:
               u['password'] = generate_password_hash(new_pass)
               updated = True
               break
       if updated:
           try:
               atomic_save_users(users)
           except Exception:
               flash("Failed to save updated password. Try again.", "error")
               return redirect(url_for('auth.reset_password'))
           session.pop('reset_user', None)
           flash("Password updated successfully.", "success")
           return redirect(url_for('auth.login'))
       flash("User for password reset not found.", "error")
       return redirect(url_for('auth.forgot'))
   return render_template('reset_password.html')

@auth.route('/logout')
def logout():
   session.clear()
   flash("You have been logged out.", "info")
   return redirect(url_for('auth.login'))

@auth.route('/request_profile_otp', methods=['POST'])
def request_profile_otp():
   if 'username' not in session:
       return jsonify({"success": False, "msg": "Not logged in."}), 401
   now = time.time()
   expiry = session.get(OTP_SESSION_EXPIRY, 0)
   if now < expiry:
       remaining = int(expiry - now)
       return jsonify({"success": True, "otp": session.get(OTP_SESSION_KEY), "expiry": remaining})
   otp = gen_otp()
   session[OTP_SESSION_KEY] = otp
   session[OTP_SESSION_EXPIRY] = now + 180
   return jsonify({"success": True, "otp": otp, "expiry": 180})

@auth.route('/verify_profile_otp', methods=['POST'])
def verify_profile_otp():
   if 'username' not in session:
       return jsonify({"success": False, "msg": "Not logged in."}), 401
   otp_entered = (request.form.get('otp') or "").strip()
   new_pass = (request.form.get('new_password') or "").strip()
   confirm = (request.form.get('confirm') or "").strip()
   if not otp_entered or not new_pass or not confirm:
       return jsonify({"success": False, "msg": "All fields required."})
   if time.time() > session.get(OTP_SESSION_EXPIRY, 0):
       session.pop(OTP_SESSION_KEY, None); session.pop(OTP_SESSION_EXPIRY, None)
       return jsonify({"success": False, "msg": "OTP expired. Please request again."})
   if otp_entered != session.get(OTP_SESSION_KEY):
       return jsonify({"success": False, "msg": "Incorrect OTP."})
   if new_pass != confirm:
       return jsonify({"success": False, "msg": "Passwords do not match."})
   if not PASSWORD_RE.match(new_pass):
       return jsonify({"success": False, "msg": "Password does not meet complexity requirements."})
   username = session['username']
   users = load_users()
   updated = False
   for u in users:
       if u.get('username') == username:
           u['password'] = generate_password_hash(new_pass)
           updated = True
           break
   if updated:
       try:
           atomic_save_users(users)
       except Exception:
           current_app.logger.exception("Failed to save users during profile password update")
           return jsonify({"success": False, "msg": "Failed saving password."})
       session.pop(OTP_SESSION_KEY, None); session.pop(OTP_SESSION_EXPIRY, None)
       return jsonify({"success": True})
   return jsonify({"success": False, "msg": "User not found."})