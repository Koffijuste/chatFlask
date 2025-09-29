from models import db, User, Message

for line in db.inspect(User).columns:
    print(line.name, line.type)

for col in User.__table__.columns:
    print(col.name, col.type)