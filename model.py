# The general functional model of the app
# TODO implement base64 conversions on the database side?

import web, scrypt, random, magic, hashlib
import config

# Connection to database
db = web.database(  dbn='postgres', 
                    db=config.db, 
                    user=config.user, 
                    pw=config.pw)

def get_documents(user):
    '''Retrieve relevant info from documents to display'''
    try:
        return db.select('agreements', what='title,description,landlord,posted_on', where='user_id=$user', order='id ASC', vars=locals())
    except IndexError:
        return None

def get_document(user,id):
    '''Get full document info, including binary data; relative id
    TODO really ugly way to update encoding scheme'''
    try:
        return db.query("SELECT title,landlord,description,file_name,data_type,posted_on,decode(data,'base64') AS data FROM agreements WHERE user_id=$user ORDER BY id ASC LIMIT 1 OFFSET $os", vars={'user': user, 'os': int(id)-1})[0]
        #info['data']=info['data'].decode('base64')
        #return info
    except IndexError:
        return None

def save_document(user, data_type, filename, data, landlord=None, title=None, description=None):
    '''Save rental agreement'''
    try:
        return db.insert( 'agreements',
                data_type=data_type,
                data=data.encode('base64'),
                file_name=filename,
                user_id=user,
                landlord=landlord,
                title=title,
                description=description)
    except:
        return None

def delete_document(user, id):
    '''Delete document, relative id'''
    return db.query("DELETE FROM agreements WHERE id IN (SELECT id FROM agreements WHERE user_id=$user ORDER BY id ASC LIMIT 1 OFFSET $os)", vars={'user': user, 'os': int(id)-1})

def hash_password(password, maxtime=0.5, datalength=128):
    '''Scrypt, use password to encrypt random data'''
    r = lambda x: [chr(random.SystemRandom().randint(0,255)) for i in range(x)]
    return scrypt.encrypt(''.join(r(datalength)), str(password), maxtime).encode('base64')

def save_user(email, password):
    '''Insert new user'''
    db.insert( 'users',
                email=email,
                password=hash_password(password))

def verify_password(password, email, maxtime=0.5):
    '''Verify pw/email combo and return user id, or False'''
    try:
        user=db.select('users', what='password,id', where='email=$email', limit=1, vars=locals())[0]
        hpw=user['password'].decode('base64')
        scrypt.decrypt(hpw, str(password), maxtime)
        return user['id']
    except (scrypt.error, IndexError):
        return False

def verify_email(id, code):
    '''verify email through email/code combo'''
    try:
        db_code=db.select('users', what='email_code', where='id=$id', limit=1, vars=locals())[0]['email_code']
        if code == db_code:
            db.update('users', where='id=$id', verified=True, email_code=None, vars=locals())
            return True
        else:
            return False
    except:
        return False

def is_verified(id):
    '''is email verified'''
    try:
        if db.select('users', what='verified', where='id=$id', limit=1, vars=locals())[0]['verified']:
            return True
        else:
            return False
    except IndexError:
        return False

def get_email_code(email):
    '''generate random id for email code, update db'''
    try:
        if is_verified(get_id(email)):
            return False
        else:
            id=web.to36(random.SystemRandom().getrandbits(256))
            db.update('users', where='email=$email', email_code=id, vars=locals())
            return id
    except:
        return False

def get_id(email):
    '''get id from email'''
    try:
        return db.select('users', what='id', where='email=$email', limit=1, vars=locals())[0]['id']
    except IndexError:
        return False

def get_file_type(fobject, mime=True):
    '''file object, retrieve type'''
    return magic.from_buffer(fobject.read(1024), mime)
