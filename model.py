# The general functional model of the app

import web, scrypt, random, magic
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
    '''Get full document info, including binary data; relative id'''
    try:
        return db.query("SELECT title,description,landlord,posted_on FROM agreements WHERE user_id=$user ORDER BY id ASC LIMIT 1 OFFSET $os", vars={'user': user, 'os': int(id)-1})[0]
    except IndexError:
        return None

def save_document(user, data_type, filename, data, landlord=None, title=None, description=None):
    '''Save rental agreement'''
    db.insert( 'agreements',
                data_type=data_type,
                data=data.encode('base64'),
                file_name=filename,
                user_id=user,
                landlord=landlord,
                title=title,
                description=description)

def delete_document(user, id):
    '''Delete document, relative id'''
    return db.query("DELETE FROM agreements WHERE id IN (SELECT id FROM agreements WHERE user_id=$user ORDER BY id ASC LIMIT 1 OFFSET $os)", vars={'user': user, 'os': int(id)-1})

def hash_password(password, maxtime=0.5, datalength=64):
    '''Scrypt, use password to encrypt random data'''
    r = lambda x: [chr(random.randint(0,255)) for i in range(x)]
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

def get_file_type(fobject, mime=True):
    '''file object, retrieve type'''
    return magic.from_buffer(fobject.read(1024), mime)
