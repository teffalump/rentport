# The general functional model of the app

# Notes: user parameters are ids, unless otherwise indicated
# TODO Usually, I retrieve/update/delete, etc records oldest (id = 1) first, change?
# TODO Implement PENDING status for issues? Way later
# TODO Consolidate comments and issue retrieving
# TODO Do better error report and handling
# TODO Add better landlord/tenant handling

import web,sys, scrypt, random, magic, sendgrid, re, stripe, json
from web import form
from psycopg2 import Error as DBError
import config

# Connection to database
db = web.database(  dbn='postgres', 
                    db=config.db.name, 
                    user=config.db.user, 
                    pw=config.db.pw)

#form validators
vemail = form.regexp(r"^.+@.+$", "must be a valid email address")
vname= form.regexp(r"^[A-Za-z0-9._+-]{3,}$", "must be a valid username (numbers, letters, and . _ - +)")
vpass = form.regexp(r"^.{12,}$", 'must be at least 12 characters')

def get_documents(user, start=1, num=10):
    '''Retrieve relevant info from documents to display'''
    try:
        return db.query("SELECT title,description,landlord,to_char(posted_on, 'YYYY-MM-DD') AS posted \
                        FROM agreements \
                        WHERE user_id=$user \
                        ORDER BY id ASC OFFSET $os LIMIT $lim",
                        vars={'user':user,
                            'os': int(start)-1,
                            'lim': int(num)})
    except:
        return [{'error': 'Error retrieving documents'}]

def get_document(user,id):
    '''Get document info/data for dl; relative id'''
    try:
        f=db.query("SELECT file_name,data_type,decode(data,'base64') AS data \
                        FROM agreements \
                        WHERE user_id=$user \
                        ORDER BY id ASC LIMIT 1 OFFSET $os",
                        vars={'user': user, 'os': int(id)-1})[0]
        web.header('Content-Type', f['data_type'])
        #i'm worried about the security of the following header, how i do it
        web.header('Content-Disposition', 'attachment; filename="{0}"'.format(re.escape(f['file_name'])))
        web.header('Cache-Control', 'no-cache')
        web.header('Pragma', 'no-cache')
        return f['data']
    except IndexError:
        return web.notfound()

def save_document(user, data_type, filename, data, landlord=None, title=None, description=None):
    '''Save rental agreement'''
    try:
        return db.query("INSERT INTO agreements \
                    (data_type, data, file_name, user_id, landlord, title, description) \
                    VALUES ($data_type, $data, $filename, $user, $landlord, $title, $description) \
                    RETURNING title,description,landlord,to_char(posted_on, 'YYYY-MM-DD') AS posted",
                    vars={'data_type': data_type,
                        'data': data.encode('base64'),
                        'filename': filename,
                        'user': user,
                        'landlord': landlord,
                        'title': title,
                        'description': description})[0]
    except:
        return {'error': "Error uploading"}

def delete_document(user, id):
    '''Delete document, relative id'''
    try:
        return db.query("DELETE FROM agreements \
                    WHERE id IN \
                        (SELECT id FROM agreements WHERE user_id=$user \
                        ORDER BY id ASC LIMIT 1 OFFSET $os) \
                    RETURNING $id AS id,$status AS status", 
                    vars={'user': user,
                            'os': int(id)-1,
                            'id': int(id),
                            'status': 'Deleted'})[0]
    except IndexError:
        return {'error': 'No document to delete'}
    except:
        return {'error': ' document'}

def hash_password(password, maxtime=0.5, datalength=128):
    '''Scrypt, use password to encrypt random data'''
    r = lambda x: [chr(random.SystemRandom().randint(0,255)) for i in range(x)]
    return scrypt.encrypt(''.join(r(datalength)), str(password), maxtime=maxtime).encode('base64')

def save_user(email, username, password, category):
    '''Insert new user'''
    try:
        a=db.insert('users',
                email=email,
                username=username,
                password=hash_password(password),
                category=category)
        if a > 0:
            return True
        else:
            return False
    except:
        return False

def update_user(id, **kw):
    '''Update user'''
    #RISK This is a dangerous function, properly secure it
    #TODO Clean up
    try:
        allowed_changes=['email', 'password']
        for key in kw.keys():
            if key not in allowed_changes:
                del kw[key]
            elif key == 'password':
                if not vpass.valid(kw['password']): return {'error': 'Invalid password'}
                kw['password']=hash_password(kw['password'])
            elif key == 'email':
                if not vemail.valid(kw[key]): return {'error': 'Invalid email'}
                #if send_verification_email(kw['email']) == True:
                    #save_sent_email(web.ctx.ip,kw['email'],'verify')
                    #kw['verified']=False
                #else:
                    #return False
            else:
                pass
        a=db.update('users', where='id=$id', vars=locals(), **kw)
        if a>0:
            return dict([(k,'Updated') for k in kw])
        else:
            return {'error': 'No updated info'}
    except:
        return {'error': 'Error updating info'}

def get_user_info(identifier, where='username', **kw):
    '''get user info given key and value, returning whatever is specified'''
    #RISK This is a powerful, potentially dangerous function
    #TODO TUNING
    default=['category', 'username', 'email', 'verified', "to_char(joined,'YYYY-MM-DD') as joined"]
    categories=kw.keys() or default

    categories = ["to_char(joined,'YYYY-MM-DD') as joined" if x == 'joined' else x for x in categories]

    what=web.db.SQLQuery.join(categories, sep=',')

    try:
        if identifier == 'id':
            where_query=web.db.sqlwhere({where: int(identifier)})
        else:
            where_query=web.db.sqlwhere({where: str(identifier)})
    except ValueError:
        #bad identifier and where arguments
        return {}

    try:
        return db.select('users', what=what, where=where_query, limit=1)[0]
    except DBError:
        #column doesn't exist or other driver error
        return {}
    except IndexError:
        #no results
        return {}

def get_landlord_info(username):
    '''return landlord info and properties'''
    try:
        return db.query("SELECT t.username,t.id,t.email,k.location FROM users t \
                            INNER JOIN properties k ON t.id = k.owner \
                            WHERE t.username = $username \
                            AND t.category IN ('Landlord', 'Both')",
                            vars={'username': username})
    except:
        return False

def add_property(landlord_id, property_id, property_text):
    '''add property'''
    #RISK Ask them not to store an actual address, just an identifier
    #dangerous to keep in db
    try:
        a=db.insert('properties',
                        description=property_text,
                        location=property_id,
                        owner=landlord_id)
        if a>0:
            return True
        else:
            return False
    except:
        return False

def search_users(user, **kw):
    '''search for similar usernames given constraints'''
    #RISK CAN GIVE A LOT OF DANGEROUS INFO! Whitelist safe keys!!!
    #TODO TUNING
    try:
        like=web.db.SQLQuery(['username LIKE ', web.db.SQLParam(''.join([user,"%"]))])
        allowed_keys=['accepts_cc', 'category']

        for key in kw.keys():
            if key not in allowed_keys:
                del kw[key]

        if len(kw) == 0:
            where=like
        else:
            base=web.db.sqlwhere(kw)
            where=web.SQLQuery.join([like, base], sep=' AND ')
        return db.select('users', what='username', where=where, limit=10, vars=kw)
    except:
        return [{'error': 'Error retrieving users'}]

def verify_password(password, login_id, maxtime=1):
    '''Verify pw/login_id combo'''
    try:
        user = db.query("SELECT password,id,username \
                            FROM users \
                            WHERE email=$login_id OR username=$login_id \
                            LIMIT 1", vars={'login_id': login_id})[0]
        hpw=user.pop('password').decode('base64')
        scrypt.decrypt(hpw, str(password), maxtime=maxtime)
        user['login']=True
        return user
    except (scrypt.error, IndexError):
        return {'login': False}

def verify_code(user_id, code, type):
    '''verify code from reset or register process'''
    try:
        a=db.query('DELETE FROM codes \
                    WHERE user_id = $user_id AND \
                        type = $type AND \
                        code = $code',
                    vars={'code': code, 'user_id': user_id, 'type': type})
        if a > 0:
            return True
        else:
            return False
    except:
        return False

def send_verification_email(userid, email):
    '''Send email to user with verification code'''
    try:
        code=get_email_code(userid, 'verify')
        subject="Verify please"
        message="Sign in: https://www.rentport.com/login\nGo to: https://www.rentport.com/verify\nEnter code: {0}".format(code)
        s = sendgrid.Sendgrid(config.email.user, config.email.pw, secure=True)
        message = sendgrid.Message(config.email.support, subject, message)
        message.add_to(email)
        s.smtp.send(message)
        return True
    except:
        return False

def send_reset_email(userid, email):
    '''send reset email with reset url'''
    try:
        code=get_email_code(userid, 'reset')
        subject="Reset email"
        message="Go here to reset password: https://www.rentport.com/reset\nEnter email: {0}\nEnter code: {1}".format(email, code)
        s = sendgrid.Sendgrid(config.email.user, config.email.pw, secure=True)
        message = sendgrid.Message(config.email.support, subject, message)
        message.add_to(email)
        s.smtp.send(message)
        return True
    except:
        return False

def save_sent_email(ip, account, type):
    '''save sent email to db'''
    try:
        num=db.query("INSERT INTO sent_emails \
                        (ip,account,type,time) \
                    VALUES ($ip, $account, $type, now())",
                    vars={'ip': ip, 'account': account, 'type': type})
        if num == 1:
            return True
        else:
            return False
    except:
        return False

def is_verified(userid):
    '''is user's email verified?'''
    try:
        return db.select('users', what='verified', where='id=$userid', limit=1, vars=locals())[0]['verified']
    except IndexError:
        return False

def get_email_code(userid, code_type):
    '''generate random id for verify or reset email'''
    try:
        uuid=web.to36(random.SystemRandom().getrandbits(256))
        return db.query("INSERT INTO codes \
                (user_id, type, value) \
                VALUES ($user_id, $type, $uuid) \
                RETURNING value", 
                vars = {'user_id': userid, 'uuid': uuid, 'type': code_type})[0]['value']
    except:
        return None

def get_file_type(fobject, mime=True):
    '''file object, retrieve type'''
    return magic.from_buffer(fobject.read(1024), mime)

def allow_login(account, ip):
    '''Quite complicated sql queries for most recent attempt from/for:
            -originating ip
            -target account (email or username)
       throttle attempts based on account, and ip, and time'''
    try:
        num=db.query("SELECT max(count) \
                        FROM (SELECT count(*) \
                                FROM failed_logins \
                                WHERE ip=$ip \
                                UNION ALL \
                              SELECT count(*) \
                                FROM failed_logins \
                                WHERE account=$account) \
                            as num", 
                    vars={'account': account, 'ip': ip})[0]['max']
        time_delta=db.query("SELECT EXTRACT(EPOCH FROM now()-max) as age \
                                FROM (SELECT max(max) \
                                    FROM \
                                        (SELECT max(time) \
                                            FROM failed_logins \
                                            WHERE ip=$ip \
                                        UNION ALL \
                                        SELECT max(time) \
                                            FROM failed_logins \
                                            WHERE account=$account) \
                                    as t) \
                                as p",
                    vars={'account': account, 'ip': ip})[0]['age']
        if num == 0:
            return True
        elif num == 1:
            '''enforce 5 sec delay'''
            if time_delta <= 5:
                return False 
            else:
                return True
        elif num == 2:
            '''enforce 15 sec delay'''
            if time_delta <= 15:
                return False
            else:
                return True
        else:
            '''enforce 45 sec delay'''
            if time_delta <= 45:
                return False
            else:
                return True
    except:
        '''some sort of error, fail safely'''
        return False

def clear_failed_logins(account, ip):
    '''DEBUG There is a subtle bug here, since someone
     might use both username and email to login,
     it's possible that they could get around the
     throttling behavior and get an extra login
     attempt per throttling level but - unless I'm
     mistaken - they will still be throttled. 

     DEBUG In addition, successful login by email will not
     clear failed login by username. Similarly, 
     successful login from ip x will not clear failed
     logins from ip y. Think about this more.

    clear attempts from account and ip'''
    try:
        num=db.query("DELETE FROM failed_logins \
                        WHERE \
                            ip=$ip \
                            AND \
                            account=$account",
                            vars={'account': account, 'ip': ip})
        if num > 0:
            return True
        else:
            return False
    except:
        return False

def add_failed_login(account, ip):
    '''add failed login to db'''
    try:
        num=db.query("INSERT INTO failed_logins \
                        (account, ip) \
                        VALUES ($account, $ip)",
                    vars={'account': account, 'ip': ip})
        if num == 1:
            return True
        else:
            return False
    except:
        return False

def add_failed_email(ip):
    '''add failed email to db'''
    try:
        num=db.query("INSERT INTO failed_emails \
                        (ip) \
                        VALUES ($ip)",
                    vars={'ip': ip})
        if num == 1:
            return True
        else:
            return False
    except:
        return False

def throttle_email_attempt(ip):
    '''throttle after submitting bad email addresses'''
    try:
        time_delta=db.query("SELECT EXTRACT(EPOCH FROM now()-max(time)) as age \
                                FROM failed_emails \
                                WHERE ip=$ip",
                                vars={'ip': ip})[0]['age']
        if time_delta == None or time_delta > 3600:
            return False
        else:
            return False
    except:
        return False

def allow_email(account, type, ip):
    '''throttle email according to criteria:
            verify: 1 email/min/acct
            reset:  1 email/min/acct && 1 email/min/ip)'''

    if type == 'verify':
        try:
            time_delta=db.query("SELECT EXTRACT(EPOCH FROM now()-max) as age \
                                    FROM (SELECT max(time) \
                                            FROM sent_emails \
                                            WHERE account=$account AND type=$type) \
                                    as p",
                                vars={'account': account, 'type': 'verify'})[0]['age']
        except (KeyError, IndexError):
            return True

        if time_delta > 60 or time_delta == None:
            '''only 1 email per 1 min'''
            return True
        else:
            return False
    elif type == 'reset':
        '''only 1 email per 1 min for acct and ip''' 
        try:
            time_delta=db.query("SELECT EXTRACT(EPOCH FROM now()-max) as age \
                                    FROM (SELECT max(time) \
                                            FROM sent_emails \
                                            WHERE account=$account AND type=$type \
                                        UNION ALL \
                                        SELECT max(time) \
                                                FROM sent_emails \
                                                WHERE ip=$ip AND type=$type) \
                                    as t",
                                    vars={'ip': ip, 'type': 'reset', 'account': account})
            if time_delta[0]['age'] > 60 and time_delta[1]['age'] > 60:
                return True
            else:
                return False
        except (KeyError, IndexError):
            return True
    else:
        return False

def accepts_cc(userid):
    '''accepts cc --> t/f'''
    try:
        return db.select('users', what='accepts_cc', where='id=$userid', limit=1, vars=locals())[0]['accepts_cc']
    except IndexError:
        return False

def get_category(userid):
    try:
        return db.select('users', what='category', where='id=$userid', limit=1, vars=locals())[0]['category']
    except:
        return None

def save_payment(origin,to,charge_id):
    '''save payment to db'''
    try:
        num=db.query("INSERT INTO payments \
                        (from_user,to_user,time,stripe_id) \
                    VALUES ($origin, $to, current_timestamp, $charge_id)",
                    vars={'origin': origin, 'to': to, 'stripe_id': charge_id})
        if num == 1:
            return True
        else:
            return False
    except:
        return False

def get_payments(user, start=1, num=10):
    '''return user related payment info'''
    #TODO Figure out amount retrieving
    try:
        return db.query("SELECT stripe_id,from_user as from,to_user as to, \
                                to_char(time, 'YYYY-MM-DD') as date \
                        FROM payments \
                        WHERE from_user=$user OR to_user=$user \
                        ORDER BY id ASC LIMIT $num OFFSET $os",
                            vars={'user': user,
                                    'os': int(start)-1,
                                    'num': int(num)})
    except:
        return []

def authorize_payment(token, amount, api_key, from_user, from_user_id, to_user_id):
    '''authorize payment, return charge id'''
    try:
        charge = stripe.Charge.create(
            amount=amount, # cents
            currency="usd",
            capture="false",
            api_key=api_key,
            card=token,
            description=from_user,
            metadata={'from': from_user_id,
                        'to': to_user_id})
        return json.loads(charge)['id']

    except stripe.CardError:
        '''declined'''
        return False

def capture_payment(charge_id, api_key):
    '''capture payment using stripe'''
    try:
        ch = stripe.Charge.retrieve(
                id=charge_id,
                api_key=api_key)
        ch.capture()
        return True

    except:
        return False

def get_charge_info(charge_id, userid):
    '''Return charge info'''
    try:
        charge = stripe.Charge.retrieve(
                                id=charge_id,
                                api_key=get_user_sk(userid))
        return json.loads(charge)
    except stripe.InvalidRequestError:
        return False

def get_user_pk(user_id):
    '''retrieve user pk_key from db'''
    try:
        return db.query("SELECT pub_key FROM user_keys \
                        WHERE user_id = $user_id \
                        LIMIT 1", vars={'user_id': user_id})[0]['pub_key']
    except:
        return False

def get_user_sk(user_id):
    '''retrieve user sk_key from db'''
    try:
        return db.query("SELECT sec_key FROM user_keys \
                        WHERE user_id = $user_id \
                        LIMIT 1", vars={'user_id': user_id})[0]['sec_key']
    except:
        return False

def save_user_keys(userid, pub_key, sec_key, refresh_token):
    '''save keys of user from oauth2'''
    try:
        a=db.insert('users',
                    user_id=userid,
                    pub_key=pub_key,
                    sec_key=sec_key,
                    refresh_token=refresh_token)
        if a>0:
            return True
        else:
            return False
    except:
        return False

def get_unconfirmed_requests(userid):
    '''retrieve unconfirmed requests related to given userid'''
    try:
        return db.query("SELECT k.username AS from,kk.username AS to,p.started AS sent,p.location as location \
                        FROM relations AS p \
                        INNER JOIN users k ON p.tenant = k.id \
                        INNER JOIN users kk ON p.landlord = kk.id \
                        WHERE p.confirmed = False \
                        AND (p.landlord = $userid OR p.tenant = $userid) \
                        ORDER BY p.started DESC",vars={'userid': userid})
    except:
       return []

def make_relation_request(tenant_id, landlord_username, location):
    '''relation request, only tenant can'''
    try:
        return db.query("INSERT INTO relations \
                    (tenant, location, landlord) \
                    VALUES ($tenant, $location, \
                        (SELECT id FROM users WHERE username = $landlord \
                        AND category = 'Landlord')) \
                    RETURNING $landlord AS landlord,location,confirmed",
                    vars={'tenant': tenant_id,
                            'landlord': landlord_username,
                            'location': location})[0]
    except:
        return {'error': 'Error making request'}

def confirm_relation_request(tenant_username, landlord):
    '''confirm relation request, only landlord can'''
    try:
        return db.query("UPDATE relations \
                    SET confirmed = $confirmed \
                    WHERE tenant IN \
                        (SELECT id FROM users WHERE username = $tenant \
                        AND category = 'Tenant') \
                    AND landlord = $landlord \
                    AND confirmed = FALSE \
                    RETURNING confirmed,$tenant AS tenant",
                    vars={'confirmed': True,
                        'tenant': tenant_username,
                        'landlord': landlord})[0]
    except IndexError:
        return {'error' : 'No request to confirm'}
    except:
        return {'error': 'Bad request'}

def end_relation(tenant):
    '''end current relation; only tenant can'''
    try:
        return db.query("UPDATE relations \
                    SET stopped = current_timestamp \
                    WHERE tenant = $tenant \
                    AND stopped IS NULL AND confirmed = True \
                    RETURNING $end AS end, \
                        to_char(stopped, 'YYYY-MM-DD HH24:MI:SS') AS stopped",
                    vars={'tenant': tenant,
                            'end': True})[0]
    except:
        return {'error': 'Error completing request'}

def get_relations(userid):
    '''return confirmed tenant-landlord relations in readable and accessible manner'''
    #TODO FUCKING CLEAN THIS UP - SO SLOW I BET
    #TODO Add dates to relations?
    try:
        opaque=db.query("SELECT k.username AS tenant,p.tenant AS tenant_id, \
                kk.username AS landlord,p.started,p.stopped,p.location \
            FROM relations as p \
            INNER JOIN users k ON p.tenant = k.id \
            INNER JOIN users kk ON p.landlord = kk.id \
            WHERE p.confirmed = True \
                AND (p.tenant = $userid OR p.landlord = $userid) \
            ORDER BY started DESC",
                        vars={'userid': userid})
        relations={}
        for row in opaque:
            if row['tenant_id'] == userid:
                #user was/is tenant
                if row['stopped']:
                    #was previous tenant
                    relations.setdefault('prev_landlords', []).append(row['landlord'])
                else:
                    #is current tenant
                    relations['landlord']=row['landlord']
            else:
                #user was/is landlord
                if row['stopped']:
                    #was previous landlord
                    relations.setdefault('prev_tenants', []).append(row['tenant'])
                else:
                    #is current landlord
                    relations.setdefault('tenants', []).append(row['tenant'])
        return relations
    except:
        return {} 

def get_current_landlord_info(userid):
    try:
        return db.query("SELECT k.landlord as landlord_id,p.username,kk.location \
                            FROM relations k \
                            INNER JOIN users p ON k.landlord=p.id \
                            INNER JOIN properties kk ON k.location = kk.id \
                            WHERE k.stopped IS NULL \
                            AND k.tenant = $userid",
                            vars={'userid': userid})[0]
    except:
        return None

def get_current_tenant_info(userid):
    try:
        return db.query("SELECT k.tenant AS tenant_id,p.username,kk.location \
                            FROM relations k \
                            INNER JOIN users p ON k.tenant = p.id \
                            INNER JOIN properties kk ON k.location = kk.id \
                            WHERE k.stopped IS NULL \
                            AND k.landlord = $userid",
                            vars={'userid': userid})
    except:
        return []

def open_issue(tenant_id, severity, description):
    '''tenant function; open issue'''
    #TODO Send email?
    try:
        return db.query("WITH tb AS (SELECT landlord AS owner,location FROM \
                    relations WHERE stopped IS NULL AND tenant = $tenant \
                    AND confirmed = TRUE LIMIT 1) \
            INSERT INTO issues \
                (owner,location,description,status,creator,severity) \
            SELECT *,$description AS description,$status AS status, \
                $creator AS creator,$severity AS severity FROM tb \
            RETURNING description,status,severity, \
                to_char(current_timestamp, 'YYYY-MM-DD') AS opened",
                vars={'description': description,
                    'status': 'Open',
                    'creator': tenant_id,
                    'severity': severity,
                    'tenant': tenant_id})[0]
    except:
        return "Error opening issue"

def close_issue(landlord_id, issue_id, reason=None):
    '''landlord function;close issue (only owner can)'''
    #TODO Send email?
    #TODO Add reason for closing (make last comment?)
    try:
        return db.query("UPDATE issues \
                    SET status = 'Closed', closed = current_timestamp \
                    WHERE id IN (SELECT id FROM issues WHERE owner = $landlord_id \
                        AND status IN ('Open', 'Pending') \
                        ORDER BY id ASC OFFSET $os LIMIT 1) \
                    RETURNING $issue AS issue,status, \
                        to_char(closed, 'YYYY-MM-DD HH24:MI:SS') AS closed",
                    vars={'os': int(issue_id)-1,
                            'landlord_id': landlord_id,
                            'issue': int(issue_id)})[0]
    except IndexError:
        return {'issue': int(issue_id), 'error': "No issue"}
    except:
        return {'error': "Error closing issue", 'issue': int(issue_id)}

def tenant_get_issues(tenant_id, status='Open', start=1, num=None):
    '''tenant function; get issues at current residence'''
    try:
        num = int(num)
    except TypeError:
        num = None
    try:
        return db.query("WITH tb AS (SELECT landlord AS owner,location \
                FROM relations WHERE stopped IS NULL AND tenant = $tenant \
                AND confirmed = TRUE LIMIT 1), \
        iss AS (SELECT k.*,count(c.id) AS num_cms FROM issues k \
            NATURAL INNER JOIN tb LEFT JOIN comments c ON c.issue_id = k.id \
            WHERE k.status = $status GROUP BY k.id) \
        SELECT p.username AS creator,pp.username AS owner,k.status, \
            to_char(k.opened, 'YYYY-MM-DD HH24:MI:SS') AS opened, \
            k.severity,k.num_cms,k.description,ppp.location \
        FROM iss k \
        INNER JOIN users pp ON pp.id = k.owner \
        INNER JOIN users p ON p.id = k.creator \
        INNER JOIN properties ppp ON k.location = ppp.id \
        ORDER BY k.opened ASC OFFSET $os LIMIT $limit",
            vars={'os': int(start)-1,
                'limit': num,
                'tenant': tenant_id,
                'status': status})
    except:
        return [{'error': "Error getting issues"}]

def landlord_get_issues(landlord_id, status='Open', start=1, num=None):
    '''landlord function; get issues'''
    try:
        num = int(num)
    except TypeError:
        num = None
    try:
        return db.query("WITH iss AS \
            (SELECT k.*,count(c.id) AS num_cms FROM issues k \
                LEFT JOIN comments c ON c.issue_id = k.id \
                WHERE k.status = $status AND k.owner = $landlord \
                GROUP BY k.id) \
            SELECT p.username AS creator,k.status,k.severity, \
                to_char(k.opened, 'YYYY-MM-DD HH24:MI:SS') AS opened, \
                k.num_cms,k.description,pp.username AS owner,ppp.location \
            FROM iss k \
            INNER JOIN users p ON p.id = k.creator \
            INNER JOIN users pp ON pp.id = k.owner \
            INNER JOIN properties ppp ON k.location = ppp.id \
            ORDER BY k.opened ASC OFFSET $os LIMIT $limit",
            vars={'os': int(start)-1,
                'limit': num,
                'landlord': landlord_id,
                'status': status})
    except:
        return [{'error': "Error getting issues"}]

def landlord_comment_on_issue(landlord_id, issue_id, comment):
    '''landlord function; comment on issue; relative id'''
    #TODO Send email?
    try:
        return db.query("INSERT INTO comments (text, user_id, issue_id) \
                    VALUES ($comment, $id, \
                    (SELECT id FROM issues WHERE status IN \
                        ('Open', 'Pending') AND owner = $landlord \
                        ORDER BY id ASC OFFSET $os LIMIT 1)) \
                    RETURNING text,to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS') AS posted",
                vars={'comment': comment,
                    'landlord': landlord_id,
                    'id': landlord_id,
                    'os': int(issue_id)-1})[0]
    except KeyError:
        return {'error': "No issue"}
    except:
        return {'error': "Error posting on issue"}

def tenant_comment_on_issue(tenant_id, issue_id, comment):
    '''tenant function; comment on issue; relative id'''
    #TODO Send email?
    try:
        return db.query("WITH tb AS \
            (SELECT landlord AS owner,location FROM relations \
                WHERE stopped IS NULL AND tenant = $tenant \
                AND confirmed = TRUE LIMIT 1) \
            INSERT INTO comments (text,user_id,issue_id) \
            VALUES ($comment, $tenant, \
                (SELECT k.id FROM issues k NATURAL INNER JOIN tb \
                    WHERE k.status in ('Open','Pending') \
                    ORDER BY k.opened ASC OFFSET $os LIMIT 1)) \
            RETURNING text,to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS') AS posted",
                    vars={'comment': comment,
                        'tenant': tenant_id,
                        'os': int(issue_id)-1})[0]
    except IndexError:
        return {'error': "No issue"}
    except:
        return {'error': "Error commenting on issue"}

def tenant_get_comments(tenant_id, issue_id, status='Open', start=1, num=None):
    '''tenant function; get comments from issue'''
    try:
        num = int(num)
    except TypeError:
        num = None
    try:
        return db.query("WITH tb AS (SELECT landlord AS owner,location \
                FROM relations WHERE stopped IS NULL AND tenant = $tenant \
                AND confirmed = TRUE LIMIT 1) \
                SELECT t.username,k.text,\
                    to_char(k.posted, 'YYYY-MM-DD HH24:MI:SS') AS posted \
                FROM comments k \
                INNER JOIN users t ON k.user_id = t.id \
                WHERE k.issue_id IN (SELECT l.id FROM issues l \
                    NATURAL INNER JOIN tb WHERE l.status = $status \
                    ORDER BY l.opened ASC OFFSET $issue_id LIMIT 1) \
                ORDER BY k.posted ASC OFFSET $os LIMIT $lim",
                        vars={'issue_id': int(issue_id)-1,
                            'os': int(start)-1,
                            'tenant': int(tenant_id),
                            'lim': num,
                            'status': status})
    except:
        return [{'error': "Error getting comments"}]

def landlord_get_comments(landlord_id, issue_id, status='Open',start=1, num=None):
    '''landlord function; get comments from issue'''
    try:
        num = int(num)
    except TypeError:
        num = None
    try:
        return db.query("SELECT t.username,k.text, \
                    to_char(k.posted, 'YYYY-MM-DD HH24:MI:SS') AS posted \
                FROM comments k \
                INNER JOIN users t ON k.user_id = t.id \
                WHERE k.issue_id IN (SELECT id FROM issues p \
                    WHERE p.status = $status \
                    AND p.owner = $landlord ORDER BY p.id ASC \
                    OFFSET $issue_id LIMIT 1) \
                ORDER BY k.id ASC OFFSET $os LIMIT $lim",
                vars={'issue_id': int(issue_id)-1,
                    'os': int(start)-1,
                    'landlord': int(landlord_id),
                    'lim': num,
                    'status': status})
    except:
        return [{'error': "Error getting comments"}]

def get_issues(userid, **kw):
    '''wrapper for getting issues'''
    try:
        if get_category(userid) == 'Tenant':
            return tenant_get_issues(userid, **kw)
        else:
            return landlord_get_issues(userid, **kw)
    except:
        return []

def comment_on_issue(userid, issue_id, comment):
    '''wrapper for posting comments'''
    try:
        if get_category(userid) == 'Tenant':
            return tenant_comment_on_issue(userid, issue_id, comment)
        else:
            return landlord_comment_on_issue(userid, issue_id, comment)
    except:
        return None

def get_comments(userid, issue_id, **kw):
    '''wrapper for listing comments'''
    try:
        if get_category(userid) == 'Tenant':
            return tenant_get_comments(userid, issue_id, **kw)
        else:
            return landlord_get_comments(userid, issue_id, **kw)
    except:
        return []
