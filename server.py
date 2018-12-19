from flask import Flask, render_template, request, redirect, session, flash
from flask_bcrypt import Bcrypt
from mysqlconnection import connectToMySQL
import helpers 
import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
app = Flask(__name__)
app.secret_key = 'fdgfdgfhiouoiuiokj' 
bcrypt = Bcrypt(app)
SCHEMA = 'ninja_gold' 

@app.route('/')         
def index():
    if 'user_id' not in session:
        return redirect('/users/new')

    db = connectToMySQL(SCHEMA)
    query = 'SELECT * FROM locations;'
    location_list = db.query_db(query)

    db = connectToMySQL(SCHEMA)
    query = 'SELECT gold_amount, locations.name AS location from activities JOIN locations ON activities.location_id = locations.id WHERE activities.user_id = %(user_id)s ORDER BY activities.created_at DESC;'
    data = {
        'user_id': session['user_id']
    }
    activity_list = db.query_db(query, data)

    db = connectToMySQL(SCHEMA)
    query = 'SELECT gold FROM users WHERE id = %(user_id)s;'
    data ={
        'user_id': session['user_id']
    }
    user_list = db.query_db(query, data)
    total_gold = user_list[0]['gold']
  
 
    return render_template('index.html', locations = location_list, activities = activity_list, gold=total_gold)
   
@app.route('/process', methods=['POST'])
def process():
    gold = helpers.calculate_gold(request.form['location']) 
 
    helpers.create_activity(session['user_id'], request.form['location'], gold)
    user_gold = helpers.get_current_gold(session['user_id'])
    user_gold = int(user_gold)
   # print(type(user_gold))
    updated_gold = user_gold + gold
    helpers.update_user_gold(session['user_id'], updated_gold)
    return redirect('/')

@app.route('/users/new')
def login_page():
    return render_template('login_reg.html')

@app.route('/users/create', methods=['POST'])
def create_user():
    errors = False

    if len(request.form['username']) < 3:
        flash('Username must be three characters long')
        errors = True
    else:
        db = connectToMySQL(SCHEMA)
        query = 'SELECT username FROM users WHERE username = %(username)s' 
        data = {
            'username' : request.form['username']
        }
        matching_users = db.query_db(query, data)
        if len(matching_users) > 0:
            flash("Username already in use.")
            errors = True
        
    if not EMAIL_REGEX.match(request.form['email']):
        flash('Email must be valid')
        errors = True
    else:
        db = connectToMySQL(SCHEMA)
        query = 'SELECT id FROM users WHERE email = %(email)s' 
        data = {
            'email' : request.form['email']
        }
        matching_users = db.query_db(query, data)
        if len(matching_users) > 0:
            flash("Email already in use.")
            errors = True

    if len(request.form['password']) < 8:
        flash('Password must be more than 8 characters')        
        errors = True

    if request.form['password'] != request.form['confirm']:
        flash('Password and confirm password must match')
        errors = True

    if errors == True:
        return redirect('/users/new')
    else:
        db = connectToMySQL(SCHEMA)
        query = 'INSERT INTO users (username, email, pw_hash, gold, created_at, updated_at) VALUES(%(username)s, %(email)s, %(pw_hash)s, 0, NOW(), NOW())'
        data = {
            'username': request.form['username'],
            'email': request.form['email'],
            'pw_hash': bcrypt.generate_password_hash(request.form['password'])
        }
        user_id = db.query_db(query, data)
        session['user_id'] = user_id
        return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    db = connectToMySQL(SCHEMA)
    query = 'SELECT id, email, pw_hash FROM users WHERE email = %(email)s;'
    data = {
        'email': request.form['email']
    }
    matching_users = db.query_db(query, data)
    if not matching_users:
        flash("Email or password incorrect")
        return redirect('/users/new')

    user = matching_users[0]
    if not bcrypt.check_password_hash(user['pw_hash'], request.form['password']):
        flash("Email or password incorrect")
        return redirect('/users/new')

    session['user_id'] = user['id']
    return redirect('/')

@app.route('/locations/new')
def new_location():
    return render_template('new_location.html')

@app.route('/locations/create', methods=['POST'])
def create_location():
    errors = helpers.validate_location(request.form)
    if errors:
        for error in errors:
            flash(error)
            return redirect('/locations/new')

    helpers.create_location(request.form)
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('users/new')

if __name__ == "__main__":
    app.run(debug = True)