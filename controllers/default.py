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
	sitsit=db().select(db.party.ALL)
	import uuid
	fb_token=uuid.uuid4()
	db(db.fb_state_tokens.expires > datetime.datetime.now()).delete()
	db.fb_state_tokens.insert(token=fb_token)
	form=auth.login()
	return dict(message=T('Hello World'),parties=sitsit,fb_token=fb_token,form=form)


def sitsit(): 
	if len(request.args) == 0:
		response.view = "%s/%s.%s" % (request.controller, request.function+"new", request.extension)
		form = SQLFORM(db.party)
		if form.process().accepted:
			return redirect(URL(args=form.vars.id))
		return dict(form=form)
	if len(request.args):
		sitsiID = request.args[0]
		sitsi = db.party[sitsiID]
		people = db(db.guest_party_attending.party == sitsiID).select().as_dict()
		owner=False
		if auth.is_logged_in():
			if auth.user.id == sitsi.owner:
				owner=True
		if user_attending(request.args[0],auth.user.id):
			attending=True
		else:
			attending=False
		if sitsit:
			return dict(sitsi=sitsi.as_dict(),found=True,people=people,owner=owner,attending=attending)
		else:
			return dict(found=False,attending=attending)
			
def joinAJAX():
	if auth.is_logged_in() and request.vars.id:
		if db((db.guest_party_attending.party==request.vars.id) & (db.guest_party_attending.guest==auth.user.id)).select().first():
			return "Already attending"
		db.guest_party_attending.insert(party=request.vars.id,guest=auth.user.id)
		return "Successfully joined "+ auth.user.first_name + " on sitsi nro: "+request.vars.id
	return "False"
	
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
	questions = db(db.party_question.party==sitsi.id).select()
	question_list_for_form = l =[]
	for q in questions:
		tmp = []
		if q.type == "question":
			if q.required:
				tmp.append(INPUT(_name=q.id,requires=IS_NOT_EMPTY(),_class="question_text_required",required=True))
			else:
				tmp.append(INPUT(_name=q.id,_class="question_text",required=False))
		if q.type == "select":
			for c in q.choises:
				if q.required:
					tmp.append(INPUT(_name=q.id,_type='radio',_value=c,value="test",_class="question_radio_required"))
				else:
					tmp.append(INPUT(_name=q.id,_type='radio',_value=c,value="test",_class="question_radio"))
				tmp.append(c)
			#s = INPUT(_name=q.id,*[OPTION(c,_value=c) for c in q.choises])
			#l.append(s)
		div = DIV(q.question,_class="questiondiv",*tmp)
		l.append(div)
	l.append(INPUT(_type="submit",value="Join"))
	form = FORM(*l)
	if user_attending(request.args[0],auth.user.id):
		form = None
	def check_user(form):
		if not auth.is_logged_in():
			form.errors.user = "Not logged in"
	if form and form.validate(onvalidation=check_user):
		for q in form.vars.keys():
			db.party_answer.insert(question=q,answer=form.vars[q],guest=auth.user.id)
		db.guest_party_attending.insert(party=request.args[0],guest=auth.user.id)
	return dict(form=form)
	
def user_attending(partyid,userid):
	if db((db.guest_party_attending.party==partyid) & (db.guest_party_attending.guest==userid)).select().first():
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
    return dict(form=auth())


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

