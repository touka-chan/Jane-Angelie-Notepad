# main.py
import os
import json
import re
import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app

main = Blueprint('main', __name__, template_folder="templates")

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
NOTES_FILE = os.path.join(os.path.dirname(__file__), "notes.json")
OTP_STORAGE_FILE = "otp_sessions.json"

def ensure_file(path):
   if not os.path.exists(path):
       with open(path, 'w', encoding='utf-8') as f:
           json.dump([], f)

def load_data(path):
   ensure_file(path)
   try:
       with open(path, 'r', encoding='utf-8') as f:
           data = json.load(f)
           if isinstance(data, list):
               return data
           else:
               return []
   except (json.JSONDecodeError, PermissionError, TypeError):
       return []

def atomic_save(path, data):
   tmp = path + ".tmp"
   with open(tmp, "w", encoding='utf-8') as f:
       json.dump(data, f, indent=2, ensure_ascii=False)
   os.replace(tmp, path)

def login_required(f):
   from functools import wraps
   @wraps(f)
   def wrapped(*args, **kwargs):
       if 'username' not in session:
           flash("Please log in first.", "error")
           return redirect(url_for('auth.login'))
       return f(*args, **kwargs)
   return wrapped

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

def gen_otp():
   return str(random.randint(100000, 999999))

@main.route('/home')
@login_required
def home():
   username = session['username']
   notes = load_data(NOTES_FILE)
   
   active_notes = []
   archived_notes = []
   
   for note in notes:
       if isinstance(note, dict):
           if note.get('username') == username:
               if note.get('status') == 'active':
                   active_notes.append(note)
               elif note.get('status') == 'archived':
                   archived_notes.append(note)
   
   return render_template('home.html', active_notes=active_notes, archived_notes=archived_notes)

@main.route('/add_note', methods=['POST'])
@login_required
def add_note():
   if not request.form:
       flash("Invalid request.", "error")
       return redirect(url_for('main.home'))
   title = request.form.get('title','').strip()
   content = request.form.get('content','').strip()
   if not title:
       flash("Title is required.", "error")
       return redirect(url_for('main.home'))
   notes = load_data(NOTES_FILE)
   new_id = max((n.get('id',0) for n in notes if isinstance(n, dict)), default=0) + 1
   note = {
       "id": new_id,
       "username": session['username'],
       "title": title,
       "content": content,
       "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
       "status": "active"
   }
   notes.append(note)
   try:
       atomic_save(NOTES_FILE, notes)
   except Exception:
       current_app.logger.exception("Failed to save note")
       flash("Failed to save note.", "error")
       return redirect(url_for('main.home'))
   flash("Note added.", "success")
   return redirect(url_for('main.home'))

@main.route('/edit_note/<int:note_id>', methods=['GET','POST'])
@login_required
def edit_note(note_id):
   notes = load_data(NOTES_FILE)
   note = next((n for n in notes if isinstance(n, dict) and n.get('id') == note_id and n.get('username') == session['username']), None)
   if not note:
       flash("Note not found.", "error")
       return redirect(url_for('main.home'))
   if request.method == 'POST':
       title = request.form.get('title','').strip()
       content = request.form.get('content','').strip()
       if not title:
           flash("Title required.", "error")
           return redirect(url_for('main.edit_note', note_id=note_id))
       note['title'] = title
       note['content'] = content
       note['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
       try:
           atomic_save(NOTES_FILE, notes)
       except Exception:
           current_app.logger.exception("Failed saving notes")
           flash("Failed to save changes.", "error")
           return redirect(url_for('main.edit_note', note_id=note_id))
       flash("Note updated.", "success")
       return redirect(url_for('main.home'))
   active_notes = [n for n in notes if isinstance(n, dict) and n.get('username') == session['username'] and n.get('status') == 'active']
   archived_notes = [n for n in notes if isinstance(n, dict) and n.get('username') == session['username'] and n.get('status') == 'archived']
   return render_template('home.html', active_notes=active_notes, archived_notes=archived_notes, edit_note=note)

@main.route('/delete_note/<int:note_id>')
@login_required
def delete_note(note_id):
   notes = load_data(NOTES_FILE)
   changed = False
   for n in notes:
       if isinstance(n, dict) and n.get('id') == note_id and n.get('username') == session['username']:
           n['status'] = 'archived'
           changed = True
   if changed:
       try:
           atomic_save(NOTES_FILE, notes)
       except Exception:
           current_app.logger.exception("Failed to archive note")
           flash("Failed to archive note.", "error")
           return redirect(url_for('main.home'))
       flash("Note archived.", "info")
   else:
       flash("Note not found.", "error")
   return redirect(url_for('main.home'))

@main.route('/restore_note/<int:note_id>')
@login_required
def restore_note(note_id):
   notes = load_data(NOTES_FILE)
   changed = False
   for n in notes:
       if isinstance(n, dict) and n.get('id') == note_id and n.get('username') == session['username']:
           n['status'] = 'active'
           changed = True
   if changed:
       try:
           atomic_save(NOTES_FILE, notes)
       except Exception:
           current_app.logger.exception("Failed to restore note")
           flash("Failed to restore note.", "error")
           return redirect(url_for('main.home'))
       flash("Note restored.", "success")
   else:
       flash("Note not found.", "error")
   return redirect(url_for('main.home'))

@main.route('/permanent_delete/<int:note_id>')
@login_required
def permanent_delete(note_id):
   notes = load_data(NOTES_FILE)
   new_notes = [n for n in notes if not (isinstance(n, dict) and n.get('id') == note_id and n.get('username') == session['username'])]
   if len(new_notes) < len(notes):
       try:
           atomic_save(NOTES_FILE, new_notes)
       except Exception:
           current_app.logger.exception("Failed deleting note")
           flash("Failed to delete note.", "error")
           return redirect(url_for('main.home'))
       flash("Note permanently deleted.", "error")
   else:
       flash("Note not found.", "error")
   return redirect(url_for('main.home'))

@main.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    users = load_data(USERS_FILE)
    username = session['username']
    user = next((u for u in users if isinstance(u, dict) and u.get('username') == username), None)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('auth.logout'))

    if request.method == 'POST':
        first_name = request.form.get('first_name','').strip()
        middle_name = request.form.get('middle_name','').strip()
        last_name = request.form.get('last_name','').strip()
        dob = request.form.get('dob','').strip()
        contact = re.sub(r'\D','', request.form.get('contact',''))
        province = request.form.get('province','').strip()
        city = request.form.get('city','').strip()
        barangay = request.form.get('barangay','').strip()
        zipcode = request.form.get('zipcode','').strip()
        email = request.form.get('email','').strip().lower()
        street = request.form.get('street','').strip()

        if not all([first_name, last_name, dob, contact, province, city, barangay, email]):
            flash("All required fields must be filled.", "error")
            return render_template('profile.html', user=user)

        if not (2 <= len(first_name) <= 30) or not re.match(r'^[A-Z][a-zA-Z ]{1,29}$', first_name):
            flash("First name must be 2-30 characters and capitalized.", "error")
            return render_template('profile.html', user=user)
        
        if middle_name and not re.match(r'^[A-Z][a-zA-Z ]{1,29}$', middle_name):
            flash("Middle name (if provided) must be capitalized.", "error")
            return render_template('profile.html', user=user)
            
        if not (2 <= len(last_name) <= 30) or not re.match(r'^[A-Z][a-zA-Z ]{1,29}$', last_name):
            flash("Last name must be 2-30 characters and capitalized.", "error")
            return render_template('profile.html', user=user)

        try:
            birth_date = datetime.strptime(dob, "%Y-%m-%d")
            today = datetime.now()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            
            if age < 13:
                flash("You must be at least 13 years old.", "error")
                return render_template('profile.html', user=user)
            if age > 80:
                flash("Maximum age limit is 80 years.", "error")
                return render_template('profile.html', user=user)
                
            if birth_date > today:
                flash("Date of birth cannot be in the future.", "error")
                return render_template('profile.html', user=user)
                
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "error")
            return render_template('profile.html', user=user)

        if not re.match(r'^09\d{9}$', contact):
            flash("Contact number must be 11 digits starting with 09.", "error")
            return render_template('profile.html', user=user)

        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash("Invalid email format.", "error")
            return render_template('profile.html', user=user)

        users = load_data(USERS_FILE)
        if any(u.get('email') == email and u.get('username') != username for u in users):
            flash("Email already registered by another user.", "error")
            return render_template('profile.html', user=user)

        if any(u.get('contact') == contact and u.get('username') != username for u in users):
            flash("Contact number already registered by another user.", "error")
            return render_template('profile.html', user=user)

        session['profile_update_data'] = {
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'dob': dob,
            'contact': contact,
            'province': province,
            'city': city,
            'barangay': barangay,
            'zipcode': zipcode,
            'email': email,
            'street': street,
            'age': age
        }

        return redirect(url_for('main.verify_profile_update'))

    return render_template('profile.html', user=user)

@main.route('/verify_profile_update', methods=['GET','POST'])
@login_required
def verify_profile_update():
    if 'profile_update_data' not in session:
        flash("No pending profile update. Please fill out the profile form first.", "error")
        return redirect(url_for('main.profile'))

    profile_data = session.get('profile_update_data')
    username = session['username']
    
    existing_session = get_otp_session(username)

    if not existing_session:
        otp = gen_otp()
        new_session = {
            "username": username,
            "otp": otp,
            "expires_at": (datetime.utcnow() + timedelta(minutes=3)).isoformat(),
            "sent_at": datetime.utcnow().isoformat(),
            "time_consumed": "0:00",
            "purpose": "profile_update"
        }
        save_otp_session(username, new_session)
        existing_session = new_session
        flash(f"OTP sent for verification: {otp} (Expires in 3 minutes)", "info")

    expires_at = existing_session["expires_at"]
    current_time = datetime.utcnow().isoformat()

    if expires_at <= current_time:
        delete_otp_session(username)
        session.pop('profile_update_data', None)
        flash("OTP expired. Please try updating your profile again.", "error")
        return redirect(url_for('main.profile'))

    expires_dt = datetime.fromisoformat(expires_at)
    current_dt = datetime.utcnow()
    remaining_seconds = int((expires_dt - current_dt).total_seconds())
    
    total_seconds_used = 180 - remaining_seconds
    minutes_used = total_seconds_used // 60
    seconds_used = total_seconds_used % 60
    time_consumed = f"{minutes_used}:{seconds_used:02d}"
    
    existing_session["time_consumed"] = time_consumed
    save_otp_session(username, existing_session)
    
    otp_display = existing_session["otp"]
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    time_remaining = f"{minutes}:{seconds:02d}"

    if request.method == 'POST':
        otp_entered = request.form.get('otp','').strip()
        
        current_time_check = datetime.utcnow().isoformat()
        if expires_at <= current_time_check:
            delete_otp_session(username)
            session.pop('profile_update_data', None)
            flash("OTP expired. Please try updating your profile again.", "error")
            return redirect(url_for('main.profile'))
        
        if not otp_entered:
            flash("OTP is required.", "error")
            return render_template('verify_profile_update.html',
                                current_username=username,
                                otp_display=otp_display,
                                time_remaining=time_remaining,
                                time_consumed=time_consumed)
        
        if otp_entered != existing_session["otp"]:
            flash("Incorrect OTP. Please try again.", "error")
            return render_template('verify_profile_update.html',
                                current_username=username,
                                otp_display=otp_display,
                                time_remaining=time_remaining,
                                time_consumed=time_consumed)

        users = load_data(USERS_FILE)
        user_updated = False
        
        for user in users:
            if isinstance(user, dict) and user.get('username') == username:
                user.update({
                    "first_name": profile_data['first_name'],
                    "middle_name": profile_data['middle_name'],
                    "last_name": profile_data['last_name'],
                    "dob": profile_data['dob'],
                    "age": profile_data['age'],
                    "contact": profile_data['contact'],
                    "province": profile_data['province'],
                    "city": profile_data['city'],
                    "barangay": profile_data['barangay'],
                    "zipcode": profile_data['zipcode'],
                    "street": profile_data['street'],
                    "email": profile_data['email'],
                    "updated_at": datetime.now().isoformat()
                })
                user_updated = True
                break

        if user_updated:
            try:
                atomic_save(USERS_FILE, users)
                session['display_name'] = profile_data['first_name']
                delete_otp_session(username)
                session.pop('profile_update_data', None)
                flash("Profile updated successfully!", "success")
                return redirect(url_for('main.profile'))
                
            except Exception as e:
                current_app.logger.exception("Failed to save user profile")
                flash("Failed to save profile changes. Please try again.", "error")
                return render_template('verify_profile_update.html',
                                    current_username=username,
                                    otp_display=otp_display,
                                    time_remaining=time_remaining,
                                    time_consumed=time_consumed)
        else:
            flash("User not found in database.", "error")
            return redirect(url_for('main.profile'))

    return render_template('verify_profile_update.html',
                         current_username=username,
                         otp_display=otp_display,
                         time_remaining=time_remaining,
                         time_consumed=time_consumed)