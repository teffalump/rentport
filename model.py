# Basic CRUD functionality and user/pw stuff
#   note: don't need UPDATE

import web, datetime, scrypt, random, magic

# Connection to database
db = web.database(dbn='postgre', db='rentport', user='blar')

def get_documents():
    return db.select('agreements', order='id DESC')

def get_document(id):
    try:
        return db.select('agreements', limit=1, where='id=$id', vars=locals())
    except IndexError:
        return None

def save_document():
    db.insert('agreements')

def delete_document(id):
    db.delete('agreements', where="id=$id", vars=locals())

def hash_password(password, maxtime=0.5, datalength=64):
    r = lambda x: [chr(random.randint(0,255)) for i in range(x)]
    return scrypt.encrypt(''.join(r(datalength)), password, maxtime)

def verify_password(foreign_password, email, maxtime=0.5):
    try:
        hpw=db.select('users', what='password', where='email=$email')
        scrypt.decrypt(hpw, foreign_password, maxtime)
        return True
    except scrypt.error:
            return False

def get_file_type(fobject, mime=True):
    return magic.from_buffer(fobject.read(1024), mime)
