# The general functional model of the app

import web, scrypt, random, magic, base64
import config

# Connection to database
db = web.database(  dbn='postgres', 
                    db=config.db, 
                    user=config.user, 
                    pw=config.pw)

def get_documents(user):
    try:
        return db.select('agreements', where='user_id=$user', order='id DESC', vars=locals())
    except IndexError:
        return None

def get_document(id):
    try:
        return db.select('agreements', limit=1, where='id=$id', vars=locals())[0]
    except IndexError:
        return None

def save_document(user, data_type, filename, data, landlord=None, title=None, description=None):
    db.insert( 'agreements',
                data_type=data_type,
                data=data,
                file_name=filename,
                user_id=user,
                landlord=landlord,
                title=title,
                description=description)

def delete_document(id):
    db.delete('agreements', where="id=$id", vars=locals())

def hash_password(password, maxtime=0.5, datalength=64):
    r = lambda x: [chr(random.randint(0,255)) for i in range(x)]
    return scrypt.encrypt(''.join(r(datalength)), str(password), maxtime).encode('base64')

def save_user(email, password):
    db.insert( 'users',
                email=email,
                password=hash_password(password))

def verify_password(password, email, maxtime=0.5):
    try:
        user=db.select('users', what='password,id', where='email=$email', limit=1, vars=locals())[0]
        hpw=user['password'].decode('base64')
        scrypt.decrypt(hpw, str(password), maxtime)
        return user['id']
    except (scrypt.error, IndexError):
        return False

def get_file_type(fobject, mime=True):
    return magic.from_buffer(fobject.read(1024), mime)
