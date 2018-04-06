from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
import random
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bid.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.static_url_path=app.config.get('STATIC_FOLDER')
app.static_folder=app.root_path + app.static_url_path
db = SQLAlchemy(app)

app.secret_key = 'bluhbluh'

# upload file
UPLOAD_FOLDER = 'path/to/the/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


class User(db.Model):
    # user info
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(10))
    balance = db.Column(db.Float, default=0)

    def __init__(self, username):
        self.username = username


class Cat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10))
    price = db.Column(db.Float, default=0)
    owner = db.Column(db.Integer)
    description = db.Column(db.String(255))
    def __init__(self, name, price, owner, description):
        self.name = name
        self.price = price
        self.owner = owner
        self.description = description


    # New bid: change owner, change price
    def changeOwner(self, new_owner, new_price):
        new_price = float(new_price)
        # cant bid on your own cat
        if g.user == self.owner:
            flash('You own the cat!')
            return
        # price restriction: have to bid higher
        if self.price >= float(new_price):
            flash('You have to bid higher!')
            return
        # have to have enough money
        new = User.query.get(new_owner)
        if float(new_price) > new.balance:
            flash("You don't have enough money!")
            return
        old = User.query.get(self.owner)
        new.balance -= new_price
        old.balance += new_price
        self.price = new_price
        self.owner = new_owner
        db.session.commit()

    def changeDescription(self, new_description):
        print type(new_description)
        # new_description = new_description.encode('utf-8')
        print type(new_description)
        self.description = new_description
        db.session.commit()

class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer)
    id_asset = db.Column(db.Integer)
    typeAction = db.Column(db.String(10))
    content = db.Column(db.String(255))
    # when someone likes it, cant like agian
    # too many likes?? for db
    # def like(self):



## before request

@app.before_request
def before_request():
    g.user = None
    if 'user' in session:
        g.user = session["user"]


## login/logout

@app.route('/')
def index():
    users = User.query.all()
    return render_template('index.html', users=users)

@app.route('/login')
def login():
    # check if user exist
    username = request.args.get('username')
    user = User.query.filter_by(username=username).first()
    if user is not None:
        session['user'] = user.id
        return redirect(url_for('index'))
    # if not create new user
    user = User(username)
    db.session.add(user)
    db.session.commit()
    session['user'] = user.id
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


# ## game

# @app.route('/play')
# def new_game():
#     if g.user:
#         user = User.query.get(g.user)
#         user.random_word()
#         db.session.commit()
#         return redirect(url_for('play', user_id=g.user))
#     return redirect(url_for('index'))

# @app.route('/play/<user_id>', methods=['GET', 'POST'])
# def play(user_id):
#     # go to /play when not logged in OR try to play other ppl's game
#     if not g.user or g.user != int(user_id):
#         return redirect(url_for('index'))

#     user = User.query.get(user_id)
#     user.random_word()
#     db.session.commit()
#     if user.finished:
#         user.new_game()
#         db.session.commit()
#     if request.method == 'POST':
#         letter = request.form['letter'].upper()
#         user.try_letter(letter)
#     return render_template('play.html', user=user)


@app.route('/profile')
def profile():
    if not g.user:
        return redirect(url_for('index'))
    user = User.query.get(g.user)
    assets = Cat.query.filter_by(owner=g.user).all()
    return render_template('profile.html', user=user, assets=assets)


@app.route('/market')
def market():
    if not g.user:
        return redirect(url_for('index'))
    cats = Cat.query.all()
    return render_template('market.html', cats=cats)

@app.route('/cat/<cat_id>', methods=['GET', 'POST'])
def cat(cat_id):
    if not g.user:
        return redirect(url_for('index'))
    # get cat from db
    cat = Cat.query.get(cat_id)
    # throw 404 if not found
    if cat == None:
        return render_template('404.html'), 404



    if request.method == 'POST':
        new_bid = request.form['bidprice']
        if new_bid != None:
            # new_owner = request.form['new_owner']
            new_owner = g.user
            cat.changeOwner(new_owner, new_bid)
        # new_description = request.form['newdescription']
        # print(new_description)
        # if new_description != None:
        #     cat.changeDescription(new_description)

    return render_template('cat.html', cat=cat)

@app.route('/createasset', methods=['GET', 'POST'])
def createAsset():
    if not g.user:
        return redirect(url_for('index'))
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        # if file:
        filename = secure_filename(file.filename)
        assetname = request.form['assetname']
        assetprice = request.form['assetprice']
        assetdescription = request.form['assetdescription']
        # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # save file & create asset
        file.save("static/images/"+assetname+".jpg")
        cat = Cat(assetname, assetprice, g.user, assetdescription)
        db.session.add(cat)
        db.session.commit()

        return redirect(url_for('profile'))
    
    cats = Cat.query.all()
    return render_template('createAsset.html', cats=cats)



# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

app.debug = True
if __name__ == '__main__':
    app.run(host = "192.168.1.76", port = 5000)