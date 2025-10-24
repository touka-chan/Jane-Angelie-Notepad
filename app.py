# app.py
import os
from flask import Flask, redirect, url_for, session


from auth import auth
from main import main


app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "change_this_in_production_please")


app.register_blueprint(main)
app.register_blueprint(auth)


@app.route('/')
def index():
  
   if session.get('username'):
       return redirect(url_for('main.home'))
   return redirect(url_for('auth.login'))


if __name__ == '__main__':
  
   for fname in ['users.json', 'notes.json']:
       if not os.path.exists(fname):
           with open(fname, 'w', encoding='utf-8') as f:
               f.write('[]')
   app.run(debug=True)
