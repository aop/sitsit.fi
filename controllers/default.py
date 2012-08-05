# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## This is a samples controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
## - call exposes all registered services (none by default)
#########################################################################

def index():
	"""
	example action using the internationalization operator T and flash
	rendered by views/default/index.html or views/generic.html
	"""
	response.flash = "Welcome to web2py!"
	sitsit=db(db.party.secrecy=="public").select()
	layoutvars = getLayoutVars()
	return dict(message=T('Hello World'),parties=sitsit,**layoutvars)


def getLayoutVars():
	if not auth.is_logged_in():
		loginform=auth.login()
		import uuid
		fb_token=uuid.uuid4()
		db(db.fb_state_tokens.expires > datetime.datetime.now()).delete()
		db.fb_state_tokens.insert(token=fb_token)
		return dict(loginform=loginform,fb_token=fb_token)
	else:
		return dict()
	
def sitsit(): 
	layoutvars = getLayoutVars()
	if len(request.args) == 0:
		if auth.is_logged_in():
			response.view = "%s/%s.%s" % (request.controller, request.function+"new", request.extension) #sitsitnew.html
			form = SQLFORM(db.party,_id="partyform")
			request.post_vars.owner = auth.user.id
			request.post_vars.numofattending=0
			form.vars.owner = auth.user.id
			if form.process().accepted:
				return redirect(URL(args=form.vars.id))
			return dict(form=form,**layoutvars)
		return redirect(URL('default','user',args='login'))
	if len(request.args):
		sitsiID = request.args[0]
		sitsi = db.party[sitsiID]
		people = db(db.guest_party_attending.party == sitsiID).select().as_dict()
		for k,v in people.items():
			people[k]['guest'] = db.auth_user[v['guest']]
		owner=False
		if auth.is_logged_in():
			if auth.user.id == sitsi.owner:
				owner=True
		if auth.user and user_attending(request.args[0],auth.user.id):
			attending=True
		else:
			attending=False
		if sitsit:
			return dict(sitsi=sitsi.as_dict(),found=True,people=people,owner=owner,attending=attending,**layoutvars)
		else:
			return dict(found=False,attending=attending,**layoutvars)
			
def joinAJAX():
	if auth.is_logged_in() and request.vars.id:
		if db((db.guest_party_attending.party==request.vars.id) & (db.guest_party_attending.guest==auth.user.id)).select().first():
			return "Already attending"
		db.guest_party_attending.insert(party=request.vars.id,guest=auth.user.id)
		return "Successfully joined "+ auth.user.first_name + " on sitsi nro: "+request.vars.id
	return "False"
	
@auth.requires_login()
def dejoin():
	if not request.args or not request.args[0].isdigit() or not db.party[request.args[0]]:
		raise HTTP(404)
	party = request.args[0]
	db((db.guest_party_attending.party == party) & (db.guest_party_attending.guest == auth.user.id)).delete()
	db(db.party.id == party).update(numofattending=db.party.numofattending-1)
	return dict(msg="Successfully unjoind")
	
def join():
	if not request.args or not request.args[0].isdigit() or not db.party[request.args[0]]:
		raise HTTP(404)
	sitsi = db.party[request.args[0]]
	def user_invited(user):
		if (db((db.invite.party == sitsi.id) & (db.invite.email == user.email)).select().first()):
			return True
		return False
	if sitsi.secrecy == "invite":
		if not auth.is_logged_in():
			redirect(auth.settings.login_url)
		if not user_invited(auth.user):
			raise HTTP(403)
	db.guest_party_attending.party.readable=False
	db.guest_party_attending.guest.readable=False
	form_labels={
	"restrictions":"Allergies or special food",
	"maindishdrink":"Drink for main dish",
	"dessertdishdrink":"Drink for dessert"
	}
	form = SQLFORM(db.guest_party_attending,labels=form_labels)
	
	
	if auth.user:
		form.vars.email = auth.user.email
		form.vars.first_name = auth.user.first_name
		form.vars.last_name = auth.user.last_name
		email_element = TR(LABEL('Email:'), \
							INPUT(_name='email',_disabled=True))
		first_name_element = TR(LABEL('First name:'), \
							INPUT(_name='first_name',_disabled=True))
		last_name_element = TR(LABEL('Last name:'), \
							INPUT(_name='last_name',_disabled=True))
	else:
		email_element = TR(LABEL('Email:'), \
							INPUT(_name='email'))
		first_name_element = TR(LABEL('First name:'), \
							INPUT(_name='first_name'))
		last_name_element = TR(LABEL('Last name:'), \
							INPUT(_name='last_name'))
	form[0].insert(0,email_element)
	form[0].insert(0,last_name_element)
	form[0].insert(0,first_name_element)
	msg=""
	if (auth.user and user_attending(request.args[0],auth.user.id)) or unregistered_user_attending(request.args[0],request.vars.email):
		form = None
		msg ="You already attend."
	def check_user(form):
		#check that isn't already attending
		if not auth.is_logged_in():
			form.errors.user = "Not logged in"
	if form and form.validate():
		#If the user is not logged in. Create user with given email if that already exists connect attendance to that
		if not auth.is_logged_in():
			newuser = auth.get_or_create_user(dict(email=request.vars.email,first_name=form.vars.name))
		if auth.is_logged_in():
			db.guest_party_attending.insert(party=request.args[0],guest=auth.user.id,**db.guest_party_attending._filter_fields(form.vars))
		else:
			db.guest_party_attending.insert(party=request.args[0],guest=newuser.id,**db.guest_party_attending._filter_fields(form.vars))
		db(db.party.id==request.args[0]).update(numofattending=db.party.numofattending+1)
		return dict(form=None,msg="Successfully joined.",**getLayoutVars())
	return dict(form=form,msg=msg,**getLayoutVars())
	
def user_attending(partyid,userid):
	if db((db.guest_party_attending.party==partyid) & (db.guest_party_attending.guest==userid)).select().first():
		return True
	return False
	
def unregistered_user_attending(partyid,email):
	user = db(db.auth_user.email == email).select().first()
	if not user:
		return False
	if db((db.guest_party_attending.party==partyid) & (db.guest_party_attending.guest==user.id)).select().first():
		return True
	return False
	
def fbregister():
	state = request.vars.state
	#check state for hacking
	if db(db.fb_state_tokens.token == state).select().first() == None:
		raise HTTP(403, "Hacking attempt")

	#for error:
	# YOUR_REDIRECT_URI?
	# error_reason=user_denied
	# &error=access_denied
	# &error_description=The+user+denied+your+request.
	# &state=YOUR_STATE_VALUE
	if 'error' in request.vars:
		redirect(URL('default','index',args='error'))

	#for success:
	#state=YOUR_STATE_VALUE
	#&code=CODE_GENERATED_BY_FACEBOOK

	code=request.vars.code
	#access then https://graph.facebook.com/oauth/access_token?
	# client_id=YOUR_APP_ID
	# &redirect_uri=YOUR_REDIRECT_URI
	# &client_secret=YOUR_APP_SECRET
	# &code=CODE_GENERATED_BY_FACEBOOK
	oauthURL = "https://graph.facebook.com/oauth/access_token?client_id="+str(FB_APP_ID)+"&redirect_uri="+URL('default','fbregister',host=True)+"&client_secret="+FB_APP_SECRET+"&code="+code
	if not request.env.web2py_runtime_gae:
		import urllib2
		resp = urllib2.urlopen(oauthURL).read()
	else:
		from google.appengine.api import urlfetch
		result = urlfetch.fetch(oauthURL)
		if result.status_code == 200:
			resp = result.content
		else:
			raise HTTP(500,"FB register problem")
	import urlparse
	resp_decoded=urlparse.parse_qs(resp)
	try:
		access_token=resp_decoded['access_token'][0]
	except:
		return str(resp)+" -> "+str(resp_decoded)
	# Load data from fb and register if not yet registered
	fbGraphURL = "https://graph.facebook.com/me?access_token="+access_token
	if not request.env.web2py_runtime_gae:
		fb_resp_raw = urllib2.urlopen(fbGraphURL).read()
	else:
		result = urlfetch.fetch(fbGraphURL)
		if result.status_code == 200:
			fb_resp_raw = result.content
		else:
			raise HTTP(500,"FB register problem")
	import json
	fb_resp=json.loads(fb_resp_raw)
	email = fb_resp['email']
	first_name = fb_resp['first_name']
	last_name = fb_resp['last_name']
	fb_id = fb_resp['id']
	fb_resp['registration_id'] = fb_resp['id']
	fb_resp['password'] = ""
	auth.get_or_create_user(fb_resp)
	# from storage import Storage
	# user = Storage(table_user._filter_fields(user, id=True)) 
	# session.auth = Storage(user=user, last_visit=request.now, 
		# expiration=self.settings.expiration, 
		# hmac_key = web2py_uuid()) 
	# self.user = user
	#return str(db(db.auth_user.email == email).select().first())
	auth.login_bare(email,"")
	#return "User:" + str(auth.login_bare(email,""))
	redirect(URL('default','index'))
   
   

def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth(),**getLayoutVars())


def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request,db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())

