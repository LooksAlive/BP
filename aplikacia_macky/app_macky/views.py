from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.conf import settings
from django.core.paginator import Paginator

import os

from .models import *

def clear_messages(request):
    """
    Clears all messages from the request.
    """
    storage = messages.get_messages(request)
    storage.used = True


from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.serializers.json import DjangoJSONEncoder
import json

def index(request):
    # Fetch recent records
    recent_records = Record.objects.order_by('-created_at')[:6]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Display data for the last 30 days
    
    data = []
    dates = []
    labels = ['Records', 'Users', 'Forms', 'Galleries']
    
    current_date = start_date
    while current_date <= end_date:
        num_records = Record.objects.filter(created_at__date=current_date).count()
        num_users = User.objects.filter(date_joined__date=current_date).count()
        num_forms = Form.objects.filter(created_at__date=current_date).count()
        num_galleries = Gallery.objects.filter(created_at__date=current_date).count()

        data.append([num_records, num_users, num_forms, num_galleries])
        dates.append(current_date.strftime('%Y-%m-%d'))

        current_date += timedelta(days=1)

    # Aggregate records by date (count records created per day)
    records_per_day = (
        recent_records
        .values('created_at')
        .annotate(num_records=models.Count('id'))
    )

    # For each recent record, fetch related FormAttributeData
    recent_records_data = []
    for record in recent_records:
        form_data = FormAttributeData.objects.filter(record=record)
        # Collecting only necessary details for display, such as images and attribute values
        record_details = {
            'id': record.id,
            'description': record.description,
            'thumb_up': Vote.objects.filter(record=record, vote_type="up").count(),
            'thumb_down': Vote.objects.filter(record=record, vote_type="down").count(),
            'created_at': record.created_at,
            'updated_at': record.updated_at,
            'username': record.user.username if record.user else "Unknown",
            'attributes': [{
                'name': data.form_attribute.attribute.name,
                'value': data.value,
                'type': data.form_attribute.attribute.type,
                'display_in_gallery': data.form_attribute.display_in_gallery
            } for data in form_data],
            'image': form_data.filter(form_attribute__attribute__type='image_url').first().value if form_data.filter(form_attribute__attribute__type='image_url').exists() else None
        }
        recent_records_data.append(record_details)

    # Fetch galleries to be highlighted
    featured_galleries = Gallery.objects.order_by('-created_at')[:5]
    
    gallery_data = []
    for gallery in featured_galleries:
        # Get the associated form for the gallery
        form = gallery.form
        if form:
            form_name = form.form_name
            # Get all form attributes marked to be displayed in the gallery
            attributes_to_display = FormAttribute.objects.filter(form=form, display_in_gallery=True)
            # Get all attribute data entries linked to the selected attributes and the gallery's form
            attributes_data = FormAttributeData.objects.filter(form_attribute__in=attributes_to_display)
            # Filter attribute data entries for the current gallery's form
            record_attributes = attributes_data
            # Find the first image URL attribute data entry for the current gallery
            image_url_attribute = record_attributes.filter(form_attribute__attribute__type='image_url').first()
            # Get the image URL value if it exists
            image_url = image_url_attribute.value if image_url_attribute else None
        else:
            form_name = "Unknown Form"
            image_url = None

        gallery_info = {
            'id': gallery.id,
            'name': gallery.gallery_name,
            'form_name': form_name,
            'created_at': gallery.created_at.strftime('%Y-%m-%d'),
            'image_url': image_url
        }
        gallery_data.append(gallery_info)


    # Get counts for statistics
    num_records = Record.objects.count()
    num_users = User.objects.count()
    num_galleries = Gallery.objects.count()
    num_forms = Form.objects.count()

    # Prepare chart data
    chart_labels = [item['created_at'].strftime('%Y-%m-%d') for item in records_per_day]
    chart_data = [item['num_records'] for item in records_per_day]

    # Pass the data to the template
    context = {
        'recent_records': recent_records_data,
        'featured_galleries': featured_galleries,
        'gallery_data': gallery_data,
        'num_records': num_records,
        'num_users': num_users,
        'num_forms': num_forms,
        'num_galleries': num_galleries,
        'labels': labels,
        'dates': dates,
        'data': json.dumps(data, cls=DjangoJSONEncoder),  # Convert data to JSON
        'username': request.user.username if request.user.is_authenticated else 'Guest'
    }

    return render(request, 'index.html', context)


def login_view(request):
    clear_messages(request)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Retrieve user's groups
            user_groups = user.groups.all()  # Retrieve all groups the user belongs to
            for group in user_groups:
                    print("group: ", group)
                    
            if any(group.name == "admin" for group in user_groups):
                request.session['admin_view'] = True
                user.is_superuser = True
                messages.success(request, f"Welcome back, {username}!")
                return redirect('index')
            elif any(group.name == "posudzovateľ" for group in user_groups):
                    request.session['admin_view'] = False
                    user.is_superuser = False
                    messages.success(request, f"Welcome back, {username}!")
                    return redirect('user_galeries')
            elif any(group.name == "prihlásený použivateľ" for group in user_groups):
                    request.session['admin_view'] = False
                    user.is_superuser = False
                    messages.success(request, f"Welcome back, {username}!")
                    return redirect('user_forms')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')

def logout_user(request):
    logout(request)
    messages.success(request, "You Have Been Logged Out...")
    request.session["admin_view"] = False
    return redirect('index')

def registration_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        email = request.POST.get('email')
        username = request.POST.get('username')
        
        group = Group.objects.get(name="prihlásený použivateľ")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'registration.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return render(request, 'registration.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            clear_messages(request)  # Clear messages before redirecting
            return render(request, 'registration.html')

        user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
        user.groups.add(group)
        user.save()
        messages.success(request, "Registration successful. You can now log in.")
        return redirect('login')

    return render(request, 'registration.html')




attribute_types = ['int', 'float', 'str', 'bool', 'image_url', 'date', 'datetime', 'time']

def admin_attributes(request):
    attributes = Attribute.objects.all()
    return render(request, 'admin_attributes.html', {'attributes': attributes, 'attribute_types': attribute_types})

def admin_create_attribute(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        a_type = request.POST.get('type')
        
        # Create a new Attribute record
        attr = Attribute(name=name, type=a_type)
        attr.save()
        return redirect('admin_attributes')
    
    # Define attr as an empty instance (you can set default values if needed)
    attr = Attribute()  # or attr = Attribute(name='', type='')

    return render(request, 'admin_attributes.html', {'attributes': Attribute.objects.all()})

def admin_delete_attribute(request, attribute_id):
    attribute = get_object_or_404(Attribute, pk=attribute_id)

    if request.method == 'POST':
        attribute.delete()
        return redirect('admin_attributes')  # Redirect to the attribute list page

    return render(request, 'admin_delete_attribute.html', {'attribute': attribute})

def admin_edit_attribute(request, attribute_id):
    attribute = get_object_or_404(Attribute, pk=attribute_id)

    if request.method == 'GET':
        # Here, you should render the form for editing the attribute
        return render(request, 'admin_edit_attribute.html', {'attribute': attribute, 'attribute_types': attribute_types})

    # Handle POST request for updating the attribute
    if request.method == 'POST':
        name = request.POST.get('name')
        a_type = request.POST.get('type')

        attribute.name = name
        attribute.type = a_type
        attribute.save()

        return redirect('admin_attributes')  # Redirect to the attribute list page




def admin_forms(request):
    forms = Form.objects.all()
    return render(request, 'admin_forms.html', {'forms': forms})

def admin_create_form(request, form_id=None):
    # Determine if this is a create or edit action
    if form_id:
        # We are editing an existing form
        form = get_object_or_404(Form, pk=form_id)
        form_attributes = FormAttribute.objects.filter(form=form)
    else:
        # We are creating a new form
        form = Form()
        form_attributes = None
    
    if request.method == 'POST':
        form_name = request.POST.get('form_name')
        form.form_name = form_name
        form.save()
        
        # If editing, remove existing FormAttributes
        if form_id:
            FormAttribute.objects.filter(form=form).delete()
        
        # Create FormAttributes for the new or updated form
        for key, value in request.POST.items():
            if key.startswith('attribute_'):
                attribute_id = value
                req = request.POST.get('attr_req_'+str(attribute_id))
                if not req:
                    req = False
                else:
                    req = True
                try:
                    attribute = Attribute.objects.get(id=int(attribute_id))
                    FormAttribute.objects.create(
                        form=form,
                        attribute=attribute,
                        required=req
                    )
                except (Attribute.DoesNotExist, ValueError):
                    print("ERROR ", attribute)
                    pass
        # Redirect after POST
        return redirect('admin_forms')
    
    else:
        attributes = Attribute.objects.all()
        return render(request, 'admin_create_form.html', {
            'form': form,
            'form_id': form_id,
            'attributes': attributes,
            'form_attributes': form_attributes,
        })

def admin_delete_form(request, form_id):
    # Handle form deletion logic
    form = Form.objects.get(id=form_id)
    form.delete()
    return redirect('admin_forms')  # Redirect to the form list page


def admin_users(request):
    users = User.objects.all().prefetch_related('groups').order_by("id")
    groups = Group.objects.all()
    return render(request, 'admin_users.html', {'users': users, 'groups': groups})

def admin_create_user(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        group_name = request.POST.get('group')  # Get selected group name from form

        # Validate group name and retrieve corresponding Group object
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            group = None
        
        if not group:
            messages.error(request, "Invalid group selection.")
            return redirect('admin_users')

        # Check if username or email already exist
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('admin_users')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect('admin_users')

        # Create and save the new user
        try:
            user2 = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, email=email, password=password)
            user2.groups.add(group)  # Add user to the selected group
            messages.success(request, "User created successfully.")
            return redirect('admin_users')
        except Exception as e:
            error_message = str(e)
            messages.error(request, f'Error creating user: {error_message}')

    return redirect('admin_users')

from django.contrib.auth.hashers import make_password

def admin_edit_user(request, user_id):
    user1 = get_object_or_404(User, pk=user_id)
    groups = Group.objects.all()  # Fetch all available groups

    if request.method == 'POST':
        # user1 details update
        user1.first_name = request.POST.get('first_name')
        user1.last_name = request.POST.get('last_name')
        user1.email = request.POST.get('email')
        user1.username = request.POST.get('username')
        # FIXME: 
        #if request.POST.get('password'):
        #    user.set_password(request.POST.get('password'))  # Securely set password
        new_password = request.POST.get('password')
        if new_password:
            user1.password = make_password(new_password)  # Hash the password securely

        # Handling role (group) assignment
        selected_group_name = request.POST.get('role')
        selected_group = Group.objects.get(name=selected_group_name)
        user1.groups.clear()  # Remove the user from any existing groups
        user1.groups.add(selected_group)  # Add the user to the selected group
        
        try:
            user1.save()
            messages.success(request, 'User updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')

        return redirect('admin_users')
    else:
        # Pass existing group names to the template
        existing_group = user1.groups.first() if user1.groups.exists() else None
        return render(request, 'admin_edit_user.html', {'user1': user1, 'groups': groups, 'existing_group': existing_group})

 
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        user.delete()
        return redirect('admin_users')  # Redirect to the user list page

    return render(request, 'admin_delete_user.html', {'user': user})





'''
# for admin make a view for all records with pagination and other stuff like in other functions
def admin_records(request):
    records = Record.objects.all().order_by('-created_at')
    paginator = Paginator(records, 20)  # Show 20 records per page

    page = request.GET.get('page')
    records = paginator.get_page(page)

    records_with_details = []

    for record in records:
        # Fetch the first FormAttributeData instance related to the record to determine the form
        first_attribute_data = FormAttributeData.objects.filter(record=record).first()
        form = first_attribute_data.form_attribute.form if first_attribute_data else None
        form_name = form.form_name if form else "Unknown Form"

        # Check if there is a gallery associated with the form
        gallery = Gallery.objects.filter(form=form).first() if form else None
        gallery_name = gallery.gallery_name if gallery else None

        attributes_to_display = FormAttribute.objects.filter(form=form, display_in_gallery=True) # TODO: when in user records could be false
        # Get all FormAttributeData entries linked to the selected attributes
        attributes_data = FormAttributeData.objects.filter(form_attribute__in=attributes_to_display)
        record_attributes = attributes_data.filter(record_id=record.id)
        image_url = record_attributes.filter(form_attribute__attribute__type='image_url').first()
        image_url = image_url.value if image_url else None

        records_with_details.append({
            'record': record,
            'image' : image_url, 
            'form_name': form_name,
            'gallery_name': gallery_name, 
            'description' : record.description
        })

    return render(request, 'admin_records.html', {'records_with_details': records_with_details})
'''

def admin_galeries(request):
    galleries = Gallery.objects.all().order_by('-created_at')
    return render(request, 'admin_galeries.html', {'galleries': galleries})


def admin_create_galery(request, gallery_id=None):
    # If editing an existing gallery, we need to fetch it and its attributes
    g_name = ""
    if gallery_id:
        gallery = get_object_or_404(Gallery, pk=gallery_id)
        selected_form = gallery.form
        form_attributes = FormAttribute.objects.filter(form=selected_form).order_by('id')
        g_name = gallery.gallery_name
    else:
        gallery = None
        selected_form = None
        form_attributes = None

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'GET':
        # AJAX request to get attributes for a specific form
        form_id = request.GET.get('form_id')
        attributes = FormAttribute.objects.filter(form=form_id).order_by('id')
        attributes_data = [
            {
                'id': attr.id,
                'name': attr.attribute.name,
                'display_in_gallery': attr.display_in_gallery
            }
            for attr in attributes
        ]
        #print("returning here -----------------------------")
        return JsonResponse({'attributes': attributes_data})

    if request.method == 'POST':
        form_id = request.POST.get('form')
        g_name = request.POST.get('gallery_name')
        try:
            form = Form.objects.get(id=form_id)
        except Form.DoesNotExist:
            # error, no form for gallery is set
            messages.error(request, 'A form for the gallery was not found.')    
            return redirect('admin_galeries')
        
        # If we're creating a new gallery, instantiate it
        if not gallery_id:
            gallery = Gallery(form=form)
        
        form.included_in_gallery = True
        form.save()
        
        gallery.gallery_name = g_name

        gallery.save()

        # Update the display_in_gallery settings for each attribute
        # We reset all to False first, then set the selected ones to True
        FormAttribute.objects.filter(form=form).update(display_in_gallery=False)
        # TODO filter, fix
        for key, value in request.POST.items():
            if key.startswith('attribute_'):
                #print(key, value, "--------------------------------------------------------------")
                attr_id = value
                FormAttribute.objects.filter(id=attr_id, form=form).update(display_in_gallery=True)

        if gallery_id:
            messages.success(request, 'Gallery has been updated successfully.')
        else:
            messages.success(request, 'Gallery has been created successfully.')
            
        return redirect('admin_galeries')

    # If it's a GET request, we render the page with the form selection
    if not g_name:
        if selected_form:
            g_name = selected_form.form_name
    forms = Form.objects.filter(included_in_gallery=False)
    #print("forms: ", forms, "\n")
    #print("selected_form: ", selected_form, "\n")
    #print("gallery_id: ", gallery_id, "\n")
    if not forms.exists() and gallery_id != None and selected_form != None:
        forms = []
        forms.append(selected_form)
    return render(request, 'admin_create_galery.html', {
        'gallery': gallery,
        'selected_form': selected_form,
        'forms': forms,
        'form_attributes': form_attributes,
        'gallery_name' : g_name
    })
    
    
@require_POST  # Ensure this view can only be accessed via POST method for security
def admin_delete_galery(request, gallery_id):
    gallery = get_object_or_404(Gallery, pk=gallery_id)
    
    f = gallery.form
    f.included_in_gallery = False
    f.save()
    
    attrs = FormAttribute.objects.filter(display_in_gallery=True, form=f)
    for attr in attrs:
        attr.display_in_gallery = False
        attr.save()
    
    gallery.delete()
    messages.success(request, 'Gallery deleted successfully!')
    return redirect('admin_galeries')

@login_required
def admin_all_records(request):
    records_with_details = []

    records = Record.objects.all()
    for record in records:
        if record.user == None:
            print("ERROR, rec not exists")
            continue
        # Fetch the first FormAttributeData instance related to the record to determine the form
        first_attribute_data = FormAttributeData.objects.filter(record=record).first()
        form = first_attribute_data.form_attribute.form if first_attribute_data else None
        form_name = form.form_name if form else "Unknown Form"

        # Check if there is a gallery associated with the form
        gallery = Gallery.objects.filter(form=form).first() if form else None
        gallery_name = gallery.gallery_name if gallery else None
        
        attributes_to_display = FormAttribute.objects.filter(form=form, display_in_gallery=True) # TODO: when in user records could be false
        # Get all FormAttributeData entries linked to the selected attributes
        attributes_data = FormAttributeData.objects.filter(form_attribute__in=attributes_to_display)
        record_attributes = attributes_data.filter(record_id=record.id)
        image_url = record_attributes.filter(form_attribute__attribute__type='image_url').first()
        #print("image url: ", image_url, "\n")
        image_url = image_url.value if image_url else None
        
        records_with_details.append({
            'record': record,
            'image' : image_url, 
            'form_name': form_name,
            'gallery_name': gallery_name, 
            'description' : record.description
        })
        
    # Paginate the gallery data
    page = request.GET.get('page')
    paginator = Paginator(records_with_details, 6)  # 3 cards in a row, 2 rows on a page
    records_with_details = paginator.get_page(page)

    return render(request, 'admin_all_records.html', {'records_with_details': records_with_details})






def user_collection_formular(request):
    attributes = Attribute.objects.all()
    return render(request, 'user_collection_formular.html', {'attributes': attributes})


def user_forms(request):
    forms = Form.objects.all()
    return render(request, 'user_forms.html', {'forms': forms})



@login_required
def user_forms_view(request, form_id):
    form_data = FormAttribute.objects.filter(form=form_id)
    form_name = get_object_or_404(Form, id=form_id).form_name
    form_attrs = []
    for x in form_data:
        form_attrs.append({'attr': x.attribute, 'req': x.required})
    #form_attrs = [attr.attribute for attr, req in form_data]
    return render(request, 'user_forms_view.html', {
        'form_attrs': form_attrs,
        'form_name': form_name,
        'form_id': form_id
    })

@login_required
def user_forms_record_add(request, form_id):
    if request.method == 'POST':
        user = request.user
        record = Record.objects.create(user=user)
        record.form = Form.objects.get(id=form_id)
        
        # description
        desc = request.POST.get('description', '')
        if desc:
            record.description = desc
            record.save()
            
        # Process text fields
        for key, value in request.POST.items():
            if key.startswith("attr_"):
                attr_id = key.split("_")[1]
                attribute = get_object_or_404(Attribute, id=attr_id)
                if attribute.type != "image_url":  # Only process non-image fields here
                    form_attr = FormAttribute.objects.get(attribute=attribute, form_id=form_id)
                    if form_attr.required:
                        if not value:
                            messages.error(request, f"Required field {attribute.name} is empty")
                            return #redirect("user_forms")
                    FormAttributeData.objects.create(record=record, form_attribute=form_attr, value=value)
                
                    
        # Process file fields (images)
        added_image = False
        for key, image_file in request.FILES.items():
            if key.startswith("attr_"):
                attr_id = key.split("_")[1]
                attribute = get_object_or_404(Attribute, id=attr_id)
                if attribute.type == "image_url":
                    form_attr = FormAttribute.objects.get(attribute=attribute, form_id=form_id)
                    if form_attr.required:
                        if not value:
                            messages.error(request, f"Required field {attribute.name} is empty")
                            return #redirect("user_forms")
                        
                    fs = FileSystemStorage(location=settings.MEDIA_ROOT) # pridane...
                    filename = fs.save(image_file.name, image_file)
                    image_url = fs.url(filename)
                    FormAttributeData.objects.create(record=record, form_attribute=form_attr, value=image_url)
                    added_image = True
                    #logger.info(f"Uploaded file: {image_file.name}")
                    #logger.info(f"File URL: {image_url}")

        if not added_image:
            try:
                attribute = Attribute.objects.get(type="image_url")
                form_attr = FormAttribute.objects.get(attribute=attribute, form_id=form_id)
                #print("------------------no files, but image_url\n")
                FormAttributeData.objects.create(record=record, form_attribute=form_attr, value="")
            except FormAttribute.DoesNotExist:
                pass    # this is OK
        # Process comment
        comment = request.POST.get('comment', '')
        if comment:
            RecordComment.objects.create(user=user, record=record, comment=comment)
    
    return redirect("user_forms")




@login_required
def user_records(request):
    records_with_details = []

    records = Record.objects.filter(user=request.user)
    for record in records:
        # Fetch the first FormAttributeData instance related to the record to determine the form
        first_attribute_data = FormAttributeData.objects.filter(record=record).first()
        form = first_attribute_data.form_attribute.form if first_attribute_data else None
        form_name = form.form_name if form else "Unknown Form"

        # Check if there is a gallery associated with the form
        gallery = Gallery.objects.filter(form=form).first() if form else None
        gallery_name = gallery.gallery_name if gallery else None
        
        attributes_to_display = FormAttribute.objects.filter(form=form, display_in_gallery=True) # TODO: when in user records could be false
        # Get all FormAttributeData entries linked to the selected attributes
        attributes_data = FormAttributeData.objects.filter(form_attribute__in=attributes_to_display)
        record_attributes = attributes_data.filter(record_id=record.id)
        image_url = record_attributes.filter(form_attribute__attribute__type='image_url').first()
        image_url = image_url.value if image_url else None
        
        records_with_details.append({
            'record': record,
            'image' : image_url, 
            'form_name': form_name,
            'gallery_name': gallery_name, 
            'description' : record.description
        })
        
    # Paginate the gallery data
    page = request.GET.get('page')
    paginator = Paginator(records_with_details, 6)  # 3 cards in a row, 2 rows on a page
    records_with_details = paginator.get_page(page)

    return render(request, 'user_records.html', {'records_with_details': records_with_details})


@login_required
def user_record_delete(request, record_id):
    record = get_object_or_404(Record, id=record_id) #, user=request.user

    # Find and delete the image file associated with the record
    image_attribute_data = FormAttributeData.objects.filter(record=record, form_attribute__attribute__type='image_url')
    for image_data in image_attribute_data:
        image_path = image_data.value
        if image_path:
            # Remove the leading '/media' from the image path
            if image_path.startswith('/media'):
                image_path = image_path[6:]  # Adjust this based on the exact structure of your paths
            full_image_path = settings.MEDIA_ROOT +  image_path
            if os.path.exists(full_image_path):
                os.remove(full_image_path)

    record.delete()
    messages.success(request, 'Record deleted successfully.')
    if request.session['admin_view'] == True:
        return redirect('admin_all_records')
    return redirect('user_records')



def user_record_detail(request, record_id, for_user):
    if for_user == 1:
        record = get_object_or_404(Record, pk=record_id, user=request.user)
    else:
        record = get_object_or_404(Record, pk=record_id)
        
    if record.user == request.user: # request.user.is_authenticated or 
        for_user = 1
    
    fa = FormAttributeData.objects.filter(record=record)
    # filter which are display_in_gallery
    form_attributes = []
    for f in fa:
        if f.form_attribute.display_in_gallery == True:
            form_attributes.append(f)
    record_comments = RecordComment.objects.filter(record=record).order_by('updated_at')

    return render(request, 'user_record_detail.html', {
        'record': record,
        'form_attributes': form_attributes,
        'record_comments': record_comments,
        'for_user' : for_user
    })


def user_record_update(request, record_id, for_user):
    #clear_messages(request)
    record = get_object_or_404(Record, pk=record_id)

    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('attribute_'):
                attr_id = key.split('_')[1]
                attribute_data = FormAttributeData.objects.get(id=attr_id)
                attribute_data.value = value
                attribute_data.save()
                
        for key, value in request.POST.items():
            if key.startswith('comment_'):
                comment_id = key.split('_')[1]
                comment_data = RecordComment.objects.get(id=comment_id)
                comment_data.comment = value
                comment_data.save()
                
        messages.success(request, "Record updated successfully.")
        
        descr = request.POST.get('record_description')
        if descr:
            record.description = descr
            record.save()
    
        comment = request.POST.get('comment')
        if comment:
            RecordComment.objects.create(record=record, user=request.user, comment=comment)
            messages.success(request, 'Your comment has been added.')
        
    
        commentU = request.POST.get('commentU')
        if commentU:
            RecordComment.objects.create(record=record, user=None, comment=commentU, aproved_by_admin=False)
            messages.success(request, 'Your comment has been added.')

        return redirect('user_record_detail', record_id=record_id, for_user=for_user)

    else:
        return redirect('user_record_detail', record_id=record_id, for_user=for_user)
    


def remove_comment(request, comment_id, for_user):
    comment = get_object_or_404(RecordComment, pk=comment_id)
    #print("------------------------")
    if request.session.get('admin_view', False) or for_user or (request.user.is_authenticated and comment.user == request.user):
        comment.delete()
        messages.success(request, 'Comment removed successfully.')
    return redirect('user_record_detail', record_id=comment.record.id, for_user=for_user)

def aprove_comment(request, comment_id, for_user):
    comment = get_object_or_404(RecordComment, pk=comment_id)
    comment.aproved_by_admin = True
    comment.save()
    messages.success(request, 'Comment Approved.')
    return redirect('user_record_detail', record_id=comment.record.id, for_user=for_user)



def user_galeries(request):
    galleries = Gallery.objects.all()
    return render(request, 'user_galery.html', {'galleries': galleries})


"""
@login_required
def user_galery_view(request, gallery_id):
    gallery = get_object_or_404(Gallery, id=gallery_id)
    form = gallery.form

    # Get attributes marked to display in the gallery
    attributes_to_display = FormAttribute.objects.filter(form=form, display_in_gallery=True)

    # Get all FormAttributeData entries linked to the selected attributes
    attributes_data = FormAttributeData.objects.filter(form_attribute__in=attributes_to_display)

    # Extracting unique record IDs from attributes_data
    unique_record_ids = set(attributes_data.values_list('record_id', flat=True))
    
    print("-------------- ", unique_record_ids)

    # Preparing data for each unique record
    gallery_data = []
    for record_id in unique_record_ids:
        record = Record.objects.get(id=record_id)
        record_attributes = attributes_data.filter(record_id=record_id)

        # Extract image URL if available
        image_url = record_attributes.filter(form_attribute__attribute__type='image_url').first()
        image_url = image_url.value if image_url else None

        record_details = {
            'id': record.id,
            'thumb_up': record.thumb_up,
            'thumb_down': record.thumb_down,
            'attributes': [{'name': attr.form_attribute.attribute.name, 'value': attr.value} for attr in record_attributes],
            'image': image_url
        }
        gallery_data.append(record_details)

    print("GD-------------- ", gallery_data)
    
    return render(request, 'user_galery_view.html', {
        'gallery': gallery,
        'gallery_data': gallery_data
    })
"""

def user_galery_view(request, gallery_id):
    gallery = get_object_or_404(Gallery, id=gallery_id)
    form = gallery.form

    # Get attributes that are marked to display in gallery
    attributes_to_display = FormAttribute.objects.filter(form=form, display_in_gallery=True)

    # Get all FormAttributeData entries linked to the selected attributes
    attributes_data = FormAttributeData.objects.filter(form_attribute__in=attributes_to_display)

    # Extracting unique record IDs from attributes_data
    unique_record_ids = set(attributes_data.values_list('record_id', flat=True))

    # Preparing data for each unique record
    gallery_data = []
    for record_id in unique_record_ids:
        record = Record.objects.get(id=record_id)
        record_attributes = attributes_data.filter(record_id=record_id)

        # Extract image URL if available
        image_url = record_attributes.filter(form_attribute__attribute__type='image_url').first()
        image_url = image_url.value if image_url else None

        # Check the user's existing vote for the record
        user_vote = None
        if request.user.is_authenticated:
            user_vote_obj = Vote.objects.filter(user=request.user, record=record).first()
            if user_vote_obj:
                user_vote = user_vote_obj.vote_type
                
        record_details = {
            'record': record,
            'thumb_up': Vote.objects.filter(record = record_id, vote_type="up").count(),
            'thumb_down': Vote.objects.filter(record = record_id, vote_type="down").count(),
            'created_at': record.created_at,
            'updated_at': record.updated_at,
            'username': record.user.username if record.user else "Unknown",
            'attributes': [{'name': attr.form_attribute.attribute.name, 'value': attr.value, 'type' : attr.form_attribute.attribute.type} for attr in record_attributes if attr.form_attribute.attribute.type != 'image_url'],
            'image': image_url,
            'user_vote': user_vote
        }
        gallery_data.append(record_details)
        
    # Paginate the gallery data
    page = request.GET.get('page')
    paginator = Paginator(gallery_data, 6)  # 3 cards in a row, 2 rows on a page
    gallery_page = paginator.get_page(page)
        
    return render(request, 'user_galery_view.html', {
        'gallery': gallery,
        'gallery_data': gallery_data,
        'gallery_page': gallery_page
    })






@require_POST
def vote(request, record_id, vote_type):
    record = get_object_or_404(Record, pk=record_id)
    user = request.user

    # Check if the user has already voted on this record
    existing_vote = Vote.objects.filter(user=user, record=record).first()

    # Update or create the vote
    if existing_vote:
        if existing_vote.vote_type != vote_type:
            existing_vote.vote_type = vote_type
            existing_vote.save()
    else:
        Vote.objects.create(user=user, record=record, vote_type=vote_type)

    # Return the updated vote counts
    return JsonResponse({'thumb_up': Vote.objects.filter(record = record_id, vote_type="up").count(), 'thumb_down': Vote.objects.filter(record = record_id, vote_type="down").count()})
