import os
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

#os.getenv("DATABASE_URL")
engine = create_engine("postgres://xcpjp--')#EDITED FOR SUBMISSION
db = scoped_session(sessionmaker(bind=engine))

def main():
    count = db.execute("SELECT COUNT(*) FROM books")

    if count ==  0 :
        f = open("books.csv")
        reader = csv.reader(f)
        for isbn, title, author, year in reader:
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn,:title,:author,:year)", {"isbn":isbn, "title":title, "author":author,"year":year})
            db.commit()
            print("Complete")
        else:
            print("Already completed")

main()
