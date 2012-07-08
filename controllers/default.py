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
    return dict(message=T('Hello World'))


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
		if sitsit:
			return dict(sitsi=sitsi.as_dict(),found=True,people=people,owner=owner)
		else:
			return dict(found=False)
			
def join():
	if auth.is_logged_in() and request.vars.id:
		if db((db.guest_party_attending.party==request.vars.id) & (db.guest_party_attending.guest==auth.user.id)).select().first():
			return "Already attending"
		db.guest_party_attending.insert(party=request.vars.id,guest=auth.user.id)
		return "Successfully joined "+ auth.user.first_name + " on sitsi nro: "+request.vars.id
	return "False"

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

