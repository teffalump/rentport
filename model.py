# The general functional model of the app

import web, datetime, scrypt, random, magic, base64

# Connection to database
db = web.database(dbn='postgres', db='rentport', user='blar')

def get_documents():
    return db.select('agreements', order='id DESC')

def get_document(id):
    try:
        return db.select('agreements', limit=1, where='id=$id', vars=locals())
    except IndexError:
        return None

def save_document(user, data_type, filename, data, landlord=None, title=None, description=None):
    db.insert('agreements', user=user, landlord=landlord, title=title, data=data, data_type=data_type, description=description)

def delete_document(id):
    db.delete('agreements', where="id=$id", vars=locals())

def hash_password(password, maxtime=0.5, datalength=64):
    r = lambda x: [chr(random.randint(0,255)) for i in range(x)]
    return scrypt.encrypt(''.join(r(datalength)), password, maxtime)

def verify_password(foreign_password, email, maxtime=0.5):
    try:
        hpw=db.select('users', what='password', where='email=$email', limit=1)
        scrypt.decrypt(hpw, foreign_password, maxtime)
        return True
    except scrypt.error:
        return False

def get_file_type(fobject, mime=True):
    return magic.from_buffer(fobject.read(1024), mime)

def encode(text):
    return base64.b64encode(text)

def decode(text):
    return base64.b64decode(text)
