# The general functional model of the app
# TODO implement base64 conversions on the database side? - mostly done
# TODO validate emails

import web, scrypt, random, magic, hashlib, sendgrid
import config

# Connection to database
db = web.database(  dbn='postgres', 
                    db=config.db.name, 
                    user=config.db.user, 
                    pw=config.db.pw)

def get_documents(user):
    '''Retrieve relevant info from documents to display'''
    try:
        return db.query("SELECT title,description,landlord,to_char(posted_on, 'YYYY-MM-DD') AS posted_on \
                        FROM agreements \
                        WHERE user_id=$user \
                        ORDER BY id ASC",
                        vars={'user':user})
    except:
        return None

def get_document(user,id):
    '''Get document info/data for dl; relative id'''
    try:
        return db.query("SELECT file_name,data_type,decode(data,'base64') AS data \
                        FROM agreements \
                        WHERE user_id=$user \
                        ORDER BY id ASC LIMIT 1 OFFSET $os",
                        vars={'user': user, 'os': int(id)-1})[0]
    except IndexError:
        return None

def save_document(user, data_type, filename, data, landlord=None, title=None, description=None):
    '''Save rental agreement'''
    try:
        a=db.query("INSERT INTO agreements \
                    (data_type, data, file_name, user_id, landlord, title, description) \
                    VALUES ($data_type, $data, $filename, $user, $landlord, $title, $description)",
                    vars={'data_type': data_type,
                        'data': data.encode('base64'),
                        'filename': filename,
                        'user': user,
                        'landlord': landlord,
                        'title': title,
                        'description': description})
        if a > 0:
            return True
        else:
            return False
    except:
        return False

def delete_document(user, id):
    '''Delete document, relative id'''
    try:
        a=db.query("DELETE FROM agreements \
                    WHERE id IN \
                    (SELECT id FROM agreements WHERE user_id=$user ORDER BY id ASC LIMIT 1 OFFSET $os)", 
                    vars={'user': user, 'os': int(id)-1})
        if a > 0:
            return True
        else:
            return False
    except:
        return False

def hash_password(password, maxtime=0.5, datalength=128):
    '''Scrypt, use password to encrypt random data'''
    r = lambda x: [chr(random.SystemRandom().randint(0,255)) for i in range(x)]
    return scrypt.encrypt(''.join(r(datalength)), str(password), maxtime).encode('base64')

def save_user(email, password):
    '''Insert new user'''
    try:
        a=db.insert( 'users',
                email=email,
                password=hash_password(password))
        if a > 0:
            return True
        else:
            return False
    except:
        return False

def update_user(id, email=None, password=None):
    '''Update user; need user id'''
    try:
        if email != None and password != None:
            db.update('users', where='id=$id', email=email, password=hash_password(password), vars=locals())
            return True
        elif password != None:
            db.update('users', where='id=$id', password=hash_password(password), vars=locals())
            return True
        elif email != None:
            db.update('users', where='id=$id', email=email, vars=locals())
            return True
        else:
            return False
    except:
        return False

def get_user_info(id):
    try:
        return db.query("SELECT email,verified,to_char(joined, 'YYYY-MM-DD') AS joined \
                        FROM users \
                        WHERE id=$id \
                        LIMIT 1", vars={'id': id})[0]
    except:
        return False

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
        db_code=db.select('users', what='verify_code', where='id=$id', limit=1, vars=locals())[0]['verify_code']
        if code == db_code:
            db.update('users', where='id=$id', verified=True, verify_code=None, vars=locals())
            return True
        else:
            return False
    except:
        return False

def send_verification_email(email):
    '''Send email to user with verification code'''
    try:
        code=get_verify_code(email)
        subject="Verify please"
        message="Sign in: https://www.rentport.com/login\nGo to: https://www.rentport.com/verify\nEnter code: {0}".format(code)
        s = sendgrid.Sendgrid(config.email.user, config.email.pw, secure=True)
        message = sendgrid.Message(config.email.support, subject, message)
        message.add_to(email)
        s.smtp.send(message)
        return True
    except:
        return False

def send_reset_email(email):
    '''send reset email with reset url'''
    try:
        subject="Reset email"
        code=get_reset_code(email)
        message="Go here to reset password: https://www.rentport.com/reset\nEnter email: {0}\nEnter code: {1}".format(email, code)
        s = sendgrid.Sendgrid(config.email.user, config.email.pw, secure=True)
        message = sendgrid.Message(config.email.support, subject, message)
        message.add_to(email)
        s.smtp.send(message)
        return True
    except:
        return False

def verify_reset(email, code):
    '''verify email/code combo and reset password'''
    #TODO do this in one motion
    try:
        db_code = db.select('users', what='reset_code', where='email=$email', limit=1, vars=locals())[0]['reset_code']
        if code == db_code:
            db.update('users', where='email=$email', reset_code=None, vars=locals())
            return True
        else:
            return False
    except:
        return False

def is_verified(id):
    '''is user's email verified?'''
    try:
        if db.select('users', what='verified', where='id=$id', limit=1, vars=locals())[0]['verified']:
            return True
        else:
            return False
    except IndexError:
        return False

def get_verify_code(email):
    '''generate random id for verify email code, update db'''
    try:
        if is_verified(get_id(email)):
            return False
        else:
            id=web.to36(random.SystemRandom().getrandbits(256))
            db.update('users', where='email=$email', verify_code=id, vars=locals())
            return id
    except:
        return False

def get_reset_code(email):
    '''generate random id for reset email code, update db'''
    try:
        id=web.to36(random.SystemRandom().getrandbits(256))
        db.update('users', where='email=$email', reset_code=id, vars=locals())
        return id
    except:
        return False

def get_id(email):
    '''get id from email'''
    try:
        return db.select('users', what='id', where='email=$email', limit=1, vars=locals())[0]['id']
    except IndexError:
        return False

def get_email(id):
    '''get email from id'''
    try:
        return db.select('users', what='email', where='id=$id', limit=1, vars=locals())[0]['email']
    except IndexError:
        return False

def get_file_type(fobject, mime=True):
    '''file object, retrieve type'''
    return magic.from_buffer(fobject.read(1024), mime)
