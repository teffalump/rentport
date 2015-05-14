from rentport.common.extensions import db
from rentport.common.forms import AddPropertyForm, ModifyPropertyForm
from rentport.common.model import Property, Address
from flask.ext.security import login_required
from flask import Blueprint, request, g, url_for, flash
from sys import exc_info as er
from datetime import datetime as dt
from rentport.common.utils import (get_address, render_xhr_or_normal,
                                    redirect_xhr_or_normal, yelp)

#### Blueprint ####
housing = Blueprint('property', __name__, template_folder = '../templates/property', static_folder='static')
#### /Blueprint ####

##### PROPERTIES #####
@housing.route('/landlord/property', methods=['GET'])
@login_required
def properties():
    '''show properties
        params:     NONE
        returns:    GET: List of properties
    '''
    if g.user.fee_paid():
        form=AddPropertyForm()
    else:
        form=None
    props = g.user.properties.all()
    return render_xhr_or_normal('properties.html', props=props, form=form)

# PAID ENDPOINT
@housing.route('/landlord/property/add', methods=['POST'])
@login_required
def add_property():
    '''add property
        params:     POST: <location> location id
                    POST: <description> property description
        returns:    POST: Redirect
                    GET: Add property form
    '''
    if not g.user.fee_paid():
        flash('You need to pay to access this endpoint')
        return redirect_xhr_or_normal('.properties')
    form=AddPropertyForm()
    if form.validate_on_submit():
        address=request.form['address']
        city=request.form['city']
        state=request.form['state']
        fs=', '.join([address, city, state])
        loc=get_address(fs)
        if not loc:
            flash("Address not found")
            return redirect_xhr_or_normal('.properties')
        if loc.get('house_number') is None or \
                loc.get('road') is None or \
                loc.get('city') is None:
            flash("Non-specific address")
            return redirect_xhr_or_normal('.properties')
        a=Address(lat=loc.get('lat'),
                lon=loc.get('lon'),
                number=loc.get('house_number'),
                street=loc.get('road'),
                neighborhood=loc.get('neighbourhood'),
                city=loc.get('city'),
                county=loc.get('county'),
                state=loc.get('state'),
                postcode=loc.get('postcode'),
                country=loc.get('country'))
        description=request.form['description']

        #Optional unit
        unit=request.form.get('unit')
        if unit:
            p=Property(apt_number=int(unit),
                    description=description)
        else:
            p=Property(description=description)
        p.address=a
        g.user.properties.append(p)
        db.session.add(p)
        db.session.commit()
        flash("Property added")
        return redirect_xhr_or_normal('.properties')
    return render_xhr_or_normal('add_property.html', form=form)

@housing.route('/landlord/property/<int(min=1):prop_id>/modify', methods=['GET', 'POST'])
@login_required
def modify_property(prop_id):
    '''modify existing property
        params:     POST: <description> new property description
                    GET/POST: <prop_id> absolute location id
        returns:    POST: Redirect
                    GET: Modify property form
    '''
    prop=g.user.properties.filter(Property.id==prop_id).first()
    if not prop:
        flash('Not a valid property id')
        return redirect_xhr_or_normal('.properties')
    form=ModifyPropertyForm()
    if form.validate_on_submit():
        prop.description=request.form['description']
        db.session.add(prop)
        db.session.commit()
        flash("Property modified")
        return redirect_xhr_or_normal('.properties')
    form.description.data=prop.description
    return render_xhr_or_normal('modify_location.html', form=form, location=prop)
#### /PROPERTIES ####

__all__=['housing']
