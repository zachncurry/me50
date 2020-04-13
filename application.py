import os

from flask import Flask, session, render_template, request, flash, jsonify, redirect, url_for
from flask_session import Session
from tempfile import mkdtemp
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import requests


app = Flask(__name__)

#REFERENCE: Was receiving error to start project 1: https://github.com/Azure-Samples/ms-identity-python-webapp/issues/16
#REFERENCE: Evaluated UI/Usability: https://www.youtube.com/watch?v=-cXN6xnwVtU
#REFERENCE: Classes: https://cs50.harvard.edu/web/notes/4/
#REFERENCE: SQL Formatting: https://cs50.harvard.edu/web/notes/3/

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
#engine="postgres://xcpjplgohgmiab:1f7d202941ab720dedf70f3234f4ee5f2c14122efe0bfae0f25d39c7aded956b@ec2-34-200-116-132.compute-1.amazonaws.com:5432/d7gp28ah8vfks0"
db = scoped_session(sessionmaker(bind=engine))


class Book:
    def __init__(self, isbn, title, author, year, book_id):
        self.isbn = isbn
        self.title = title
        self.author = author
        self.year = year
        self.book_id = book_id

    def trim_author(self):
        author_len = len(self.author)
        if author_len > 2:
            del self.author[2:]
        self.author = ", ".join(self.author)
        if author_len > 2:
            self.author = self.author + " and more"

class Review:
    def __init__(self, id_review, id_user, comment, rating, book_id):
        self.id_review = id_review
        self.id_user = id_user
        self.comment = comment
        self.rating = rating
        self.book_id = book_id

class GoodRd:
    def __init__(self,id, isbn, isbn13, ratings_count, reviews_count, text_reviews_count, work_ratings_count, work_reviews_count, average_rating):
        self.id = id
        self.isbn = isbn
        self.isbn13 = isbn13
        self.ratings_count = ratings_count
        self.reviews_count = reviews_count
        self.text_reviews_count = text_reviews_count
        self.work_ratings_count = work_ratings_count
        self.work_reviews_count = work_reviews_count
        self.average_rating = average_rating

#--------------------------------------------MAIN PAGE WHEN VISITING THE SITE PROVIDING FOR A LOG IN OPTION
@app.route("/", methods = ["GET", "POST"])
def index():
    # Forget any user_id
    session.clear()

    if request.method == "GET":
        return render_template("login.html")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Invalid User Name")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Invalid Password")
            return render_template("login.html")

        # Query database for username
        username = request.form.get("username")
        password = request.form.get("password")
        rows = db.execute("SELECT id_user, hash FROM users WHERE username = :username", {"username":username}).fetchone()
        hash_pass = rows.hash
        id_user = rows.id_user

        if not rows:
            flash("User not found")
            return render_template("login.html")

        if check_password_hash(hash_pass,password):
            #session["logged_in"] = true
            session["user_id"] = id_user
            #session["username"] = username
            flash("Logged In, Welcome to Book Selector!")
            return render_template("search.html")

        else:
            flash("Incorrect password")
            return render_template("login.html")

#-------------------------------------------ALLOW END USERS TO LOG OUT/ END SESSION
@app.route("/logout")
def logout():
    #"""Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

#-------------------------------------------------ALLOW END USERS TO REGISTER/ CREATE AN ACCOUNT
@app.route("/register", methods = ["GET", "POST"])
def register():
#REFERENCE: Generate Hash Parameters: https://werkzeug.palletsprojects.com/en/1.0.x/utils/
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Please provide username")
            return render_template("register.html", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Please provide a password")
            return render_template("register.html", 403)

        name = request.form.get("username")
        password_var = request.form.get("password")
        hash_pass = generate_password_hash(password_var, method='pbkdf2:sha256',salt_length=8)
        db.execute("INSERT INTO users (username, hash) VALUES (:name, :password)", {"name" : name, "password" : hash_pass});
        db.commit()
        flash("Registered!")
        return render_template("login.html")

    if request.method == "GET":
        return render_template("register.html")

#-----------------------------------ALLOW END USERS TO SEARCH THE DATABASE IF LOGGED IN OTHERWISE SHOW MEMBERSHIP BENEFITS DETAILS
@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return render_template("search.html")
    else:
        return render_template("search.html")

#------------------------------------------RETURN THE RESULTS OF THE SEARCH
@app.route("/results", methods = ["POST"])
def results():
    if request.method == "POST":
        book_search = request.form.get("book_search")
        input = f"%{book_search}%".lower()
        look_up = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn OR LOWER(title) LIKE :title OR LOWER(author) LIKE :author OR year LIKE :year",{"isbn":input,"title":input,"author":input,"year":input}).fetchall()
        books= []
        for isbn, title, author, year, book_id in look_up:
            new_book = Book(isbn, title, author.split(', '), year, book_id)
            new_book.trim_author()
            books.append(new_book)

        return render_template("results.html",results = books)

#-------------------------------------------RETURN THE DETAILS, COMMENTS, AND RATINGS OF THE BOOK ONCE SELECTED FROM THE RESULTS PAGE
@app.route("/infopage/<int:book_id>")
def infopage(book_id):

    search = db.execute("SELECT * FROM books WHERE book_id = :book_id", {"book_id":book_id}).fetchone()
    isbn, title, author, year, book_id = search
    cur_book = Book(isbn, title, author, year, book_id)

    reviews = db.execute("SELECT id_review, id_user, comment, rating FROM reviews JOIN books ON books.book_id = reviews.book_id WHERE books.book_id = :book_id", {"book_id" : book_id}).fetchall()
    comments=[]
    for id_review, id_user, comment, rating, in reviews:
        new_comment = Review(id_review, id_user, comment, rating, book_id)
        comments.append(new_comment)

#--------------------------GET RESULTS FROM GOOD READS API
#--------------------------REFERENCE: How to access an api and return results: https://www.youtube.com/watch?v=1lxrb_ezP-g
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "SSwseOhlqnjAQ2LId6Lw", "isbns": cur_book.isbn})
    if res.status_code != 200:
        raise Exception("ERROR: API request unsuccessful.")
    good_read = res.json()
    GoodRd_average_rating = float(good_read['books'][0]['average_rating'])
    GoodRd_work_ratings_count = float(good_read['books'][0]['work_ratings_count'])

    return render_template("infopage.html", book = cur_book, comments = comments, GoodRd_average_rating = GoodRd_average_rating, GoodRd_work_ratings_count = GoodRd_work_ratings_count)

#--------------------------------------------------ALLOW USER TO CREATE COMMENT & RATING OF AN INDIVIDUAL BOOK
@app.route("/post_comment", methods=["POST"])
def post_comment():
    if request.method=="POST":
        id_user = session["user_id"]
        book_id = request.form.get("book_id")
        new_comment=request.form.get("book_comment")
        rating = float(request.form.get("rating"))
        #----------------------------------------CHECK TO ENSURE ONLY ONE REVIEW PER USER FOR EACH BOOK
        check = db.execute("SELECT * FROM reviews WHERE id_user = :id_user AND book_id = :book_id",{"id_user":id_user, "book_id":book_id}).fetchone()
        if check==None:
            db.execute("INSERT INTO reviews (id_user, comment, rating, book_id) VALUES (:id_user, :comment, :rating, :book_id)",{"id_user":id_user, "comment":new_comment, "rating":rating, "book_id":book_id})
            db.commit()
        else:
            flash("Multiple Reviews Are Not Allowed")

        return redirect(url_for("infopage", book_id = book_id), "303")

#----------------------------------API DOCUMENATION FOR EXTERNAL API AND GOODREADS INFORMATION
@app.route("/apidoc")
def apidoc():
    return render_template("apidoc.html")

#-----------------------------------EXTERNAL API
@app.route("/api/isbn/<int:ex_isbn>")
def externalapi(ex_isbn):
    ex_isbn=f"%{ex_isbn}%".lower()
    res = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn",{"isbn":ex_isbn}).fetchone()
    if res is None:
        return josonify({
        "error_code":404,
        "error_message": "Not Found"
        }), 404

    isbn, title, author, year, book_id = res
    book = Book(isbn, title, author, year, book_id)
    result = {
    "title": book.title,
    "author": book.author,
    "year": book.year,
    "isbn": book.isbn
    }
    return jsonify(result)
