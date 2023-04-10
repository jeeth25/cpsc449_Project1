import os
from functools import wraps

from flask import Flask, render_template, request, \
    redirect, url_for, session, abort, jsonify, request
import pymysql
from flask_cors import CORS
from datetime import timedelta

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=10)

# CORS(app)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

app.secret_key = 'mykey'
# Setup the Flask-JWT-Extended extension
app.config["JWT_SECRET_KEY"] = "super-secret"
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.pdf']
app.config['UPLOAD_PATH'] = 'media'

jwt = JWTManager(app)

# To connect MySQL database
conn = pymysql.connect(
    host='localhost',
    user='root',
    password="admin",
    db='web_backend',
    cursorclass=pymysql.cursors.DictCursor
)
cur = conn.cursor()


@app.route("/")
def home_page():
    return render_template("home.html")


@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(404)
def page_not_found(e):
    return jsonify(error=str(e)), 404


@app.errorhandler(401)
def no_access(e):
    return jsonify(error=str(e)), 401


@app.errorhandler(403)
def bad_request(e):
    return jsonify(error=str(e)), 403


@app.errorhandler(500)
def error_1(e):
    return jsonify(error=str(e)), 500


# Create a route to authenticate your users and return JWTs. The
# create_access_token() function is used to actually generate the JWT.
@app.route("/login", methods=["POST"])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.json.get("username", None)
        password = request.json.get("password", None)
        cur.execute('SELECT * FROM accounts WHERE username = % s AND password = % s', (username, password,))
        conn.commit()
        account = cur.fetchone()
        if account:
            session.permanent = True
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            access_token = create_access_token(identity=username)
            return jsonify(access_token=access_token)

        else:
            return jsonify({"msg": "Incorrect username or password"}), 401


# Protect a route with jwt_required, which will kick out requests
# without a valid JWT present.
@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200



def role_required(role_name):
    def decorator(func):
        @wraps(func)
        def authorize(*args, **kwargs):
            print("  ========= IN DECORATOR ===================", args, kwargs, request.args)
            username = request.json.get("username", None)
            if username != 'admin':
                abort(401) # not authorized
            return func(*args, **kwargs)
        return authorize
    return decorator

@app.route('/admin-protected', methods=["POST"])
@role_required('admin')
def admin_view():
    " this view is for admins only "\

    return jsonify({"msg": "Admin View Accessed !"}), 201



@app.route('/uploadfile', methods=['POST'])
@jwt_required()
def upload_files():
    print(" IN DEF ----------------")
    uploaded_file = request.files['file1']
    filename = secure_filename(uploaded_file.filename)
    file_ext = ""
    if filename != '':
        file_ext = os.path.splitext(filename)[1]
    if file_ext not in app.config['UPLOAD_EXTENSIONS']:
        abort(400, "File Type Not Allowed")
    uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
    return jsonify({"msg": "File Uploaded Successfully !"}), 200


@app.route("/public", methods=['GET'])
def public_route():

    try:
        cur.execute('''SELECT * FROM accounts''')
    except:
        return 'error'
    items = []
    for row in cur.fetchall():
        items.append(row)
    print(items)
    return jsonify(items)


if __name__ == "__main__":
    app.run(debug=True)
