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
    recent_records = Zaznam.objects.order_by('-vytvoreny')[:6]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Display data for the last 30 days
    
    data = []
    dates = []
    labels = ['Records', 'Users', 'Forms', 'Galleries']
    
    current_date = start_date
    while current_date <= end_date:
        num_records = Zaznam.objects.filter(vytvoreny__date=current_date).count()
        num_users = User.objects.filter(date_joined__date=current_date).count()
        num_forms = Formular.objects.filter(vytvoreny__date=current_date).count()
        num_galleries = Galeria.objects.filter(vytvoreny__date=current_date).count()

        data.append([num_records, num_users, num_forms, num_galleries])
        dates.append(current_date.strftime('%Y-%m-%d'))

        current_date += timedelta(days=1)

    # Aggregate records by date (count records created per day)
    records_per_day = (
        recent_records
        .values('vytvoreny')
        .annotate(num_records=models.Count('id'))
    )

    # For each recent record, fetch related Formular_Atribut_Udaje
    recent_records_data = []
    for record in recent_records:
        form_data = Formular_Atribut_Udaje.objects.filter(zaznam=record)
        # Collecting only necessary details for display, such as images and atribut values
        image_attribute = form_data.filter(formular_atribut__atribut__typ='obrazok_url').first()
        # Determine if image is available for this record
        image_available = bool(image_attribute)
        #print("image_available: ", image_available)
        
        record_details = {
            'id': record.id,
            'description': record.opis,
            'thumb_up': Hlas.objects.filter(zaznam=record, typ_hlasu="up").count(),
            'thumb_down': Hlas.objects.filter(zaznam=record, typ_hlasu="down").count(),
            'vytvoreny': record.vytvoreny,
            'aktualizovany': record.aktualizovany,
            'username': record.user.username if record.user else "Neznámy",
            'attributes': [{
                'nazov': data.formular_atribut.atribut.nazov,
                'hodnota': data.hodnota,
                'typ': data.formular_atribut.atribut.typ,
                'zobrazit_v_galerii': data.formular_atribut.zobrazit_v_galerii
            } for data in form_data],
            'image': form_data.filter(formular_atribut__atribut__typ='obrazok_url').first().hodnota if form_data.filter(formular_atribut__atribut__typ='obrazok_url').exists() else None,
            'image_available': image_available  # Include image availability flag
        }
        recent_records_data.append(record_details)

    # Fetch galleries to be highlighted
    featured_galleries = Galeria.objects.order_by('-vytvoreny')[:4]
    
    gallery_data = []
    for gallery in featured_galleries:
        # Get the associated formular for the gallery
        formular = gallery.formular
        if formular:
            formular_nazov = formular.formular_nazov
            # Get all formular attributes marked to be displayed in the gallery
            attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)
            # Get all atribut data entries linked to the selected attributes and the gallery's formular
            attributes_data = Formular_Atribut_Udaje.objects.filter(formular_atribut__in=attributes_to_display)
            # Filter atribut data entries for the current gallery's formular
            record_attributes = attributes_data
            # Find the first image URL atribut data entry for the current gallery
            image_url_attribute = record_attributes.filter(formular_atribut__atribut__typ='obrazok_url').first()
            # Get the image URL hodnota if it exists
            obrazok_url = image_url_attribute.hodnota if image_url_attribute else None
        else:
            formular_nazov = "Unknown Form"
            obrazok_url = None

        gallery_info = {
            'id': gallery.id,
            'nazov': gallery.galeria_nazov,
            'formular_nazov': formular_nazov,
            'vytvoreny': gallery.vytvoreny.strftime('%Y-%m-%d'),
            'obrazok_url': obrazok_url
        }
        gallery_data.append(gallery_info)


    # Get counts for statistics
    num_records = Zaznam.objects.count()
    num_users = User.objects.count()
    num_galleries = Galeria.objects.count()
    num_forms = Formular.objects.count()

    # Prepare chart data
    chart_labels = [item['vytvoreny'].strftime('%Y-%m-%d') for item in records_per_day]
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
        'username': request.user.username if request.user.is_authenticated else ''
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
            #for group in user_groups:
                #print("group: ", group)
                    
            if any(group.name == "admin" for group in user_groups):
                request.session['admin_view'] = True
                request.session['posudzovateľ'] = False
                user.is_superuser = True
                messages.success(request, f"Prihlásenie bolo úspešné")
                return redirect('index')
            elif any(group.name == "posudzovateľ" for group in user_groups):
                    request.session['admin_view'] = False
                    request.session['posudzovateľ'] = True
                    user.is_superuser = False
                    messages.success(request, f"Prihlásenie bolo úspešné")
                    return redirect('user_galeries')
            elif any(group.name == "prihlásený použivateľ" for group in user_groups):
                    request.session['admin_view'] = False
                    request.session['posudzovateľ'] = False
                    user.is_superuser = False
                    messages.success(request, f"Prihlásenie bolo úspešné")
                    return redirect('user_forms')
        else:
            messages.error(request, "Nesprávne užívateľské meno alebo heslo.")

    return render(request, 'login.html')

def logout_user(request):
    logout(request)
    messages.success(request, "Boli ste odhlásený...")
    request.session["admin_view"] = False
    return redirect('index')

def registration_view(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        email = request.POST.get('email')
        username = request.POST.get('username')
        
        group = Group.objects.get(name="prihlásený použivateľ")

        if password != confirm_password:
            messages.error(request, "Heslá sa nezhodujú.")
            return render(request, 'registration.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Používateľské meno už je obsadené.")
            return render(request, 'registration.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email už je registrovaný.")
            clear_messages(request)  # Clear messages before redirecting
            return render(request, 'registration.html')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.groups.add(group)
        user.save()
        messages.success(request, "Registrácia úspešná. Teraz sa môžete prihlásiť.")
        return redirect('login')

    return render(request, 'registration.html')




attribute_types = ['int', 'float', 'str', 'bool', 'obrazok_url', 'date']

def admin_attributes(request):
    attributes = Atribut.objects.all()
    return render(request, 'admin_attributes.html', {'attributes': attributes, 'attribute_types': attribute_types})

def admin_create_attribute(request):
    if request.method == 'POST':
        nazov = request.POST.get('nazov')
        a_type = request.POST.get('typ')
        
        # Create a new Attribute record
        attr = Atribut(nazov=nazov, typ=a_type)
        attr.save()
        return redirect('admin_attributes')
    
    # Define attr as an empty instance (you can set default values if needed)
    attr = Atribut()  # or attr = Attribute(nazov='', typ='')

    return render(request, 'admin_attributes.html', {'attributes': Atribut.objects.all()})

def admin_delete_attribute(request, attribute_id):
    atribut = get_object_or_404(Atribut, pk=attribute_id)

    if request.method == 'POST':
        atribut.delete()
        return redirect('admin_attributes')  # Redirect to the atribut list page

    return render(request, 'admin_delete_attribute.html', {'atribut': atribut})

def admin_edit_attribute(request, attribute_id):
    atribut = get_object_or_404(Atribut, pk=attribute_id)

    if request.method == 'GET':
        # Here, you should render the formular for editing the atribut
        return render(request, 'admin_edit_attribute.html', {'atribut': atribut, 'attribute_types': attribute_types})

    # Handle POST request for updating the atribut
    if request.method == 'POST':
        nazov = request.POST.get('nazov')
        a_type = request.POST.get('typ')

        atribut.nazov = nazov
        atribut.typ = a_type
        atribut.save()

        return redirect('admin_attributes')  # Redirect to the atribut list page




def admin_forms(request):
    forms = Formular.objects.all()
    return render(request, 'admin_forms.html', {'forms': forms})

def admin_create_form(request, form_id=None):
    # Determine if this is a create or edit action
    if form_id:
        # We are editing an existing formular
        formular = get_object_or_404(Formular, pk=form_id)
        form_attributes = Formular_Atribut.objects.filter(formular=formular)
    else:
        # We are creating a new formular
        formular = Formular()
        form_attributes = None
    
    if request.method == 'POST':
        formular_nazov = request.POST.get('formular_nazov')
        formular.formular_nazov = formular_nazov
        formular.save()
        
        # Create FormAttributes for the new or updated formular
        processed_attribute_ids = set()
        # Process attributes
        for key, hodnota in request.POST.items():
            if key.startswith('attribute_'):
                attribute_id = hodnota
                req = request.POST.get('attr_req_'+str(attribute_id))
                povinny = bool(req)  # Convert to boolean

                processed_attribute_ids.add(int(attribute_id))

                # Check if the Formular_Atribut already exists for this formular and attribute
                try:
                    formular_attribute = Formular_Atribut.objects.get(formular=formular, atribut_id=int(attribute_id))
                    print(f"Found existing Formular_Atribut for formular {formular.id} and attribute {attribute_id}: {formular_attribute}")
                    formular_attribute.povinny = povinny
                    formular_attribute.save()
                except Formular_Atribut.DoesNotExist:
                    print(f"Creating new Formular_Atribut for formular {formular.id} and attribute {attribute_id} with povinny={povinny}")
                    try:
                        atribut = Atribut.objects.get(id=int(attribute_id))
                        new_formular_attribute = Formular_Atribut.objects.create(
                            formular=formular,
                            atribut=atribut,
                            povinny=povinny
                        )
                        
                        # Create Formular_Atribut_Udaje linked to a Zaznam (record)
                        existing_zaznams = Zaznam.objects.filter(formular=formular)
                        for record in existing_zaznams:
                            Formular_Atribut_Udaje.objects.create(
                                zaznam=record,
                                formular_atribut=new_formular_attribute,
                                hodnota=''  # You may initialize the value as needed
                            )
                    except Atribut.DoesNotExist:
                        print(f"Atribut with ID {attribute_id} does not exist.")

        # Remove any Formular_Atribut instances not in the processed set
        formular_attributes_to_delete = Formular_Atribut.objects.filter(formular=formular)
        formular_attributes_to_delete.exclude(atribut_id__in=processed_attribute_ids).delete()
                    
        # Redirect after POST
        return redirect('admin_forms')
    
    else:
        attributes = Atribut.objects.all()
        return render(request, 'admin_create_form.html', {
            'formular': formular,
            'form_id': form_id,
            'attributes': attributes,
            'form_attributes': form_attributes,
        })

def admin_delete_form(request, form_id):
    # Handle formular deletion logic
    f = get_object_or_404(Formular, id=form_id)
    records = Zaznam.objects.filter(formular=f)
    # we need to remove image as well, database delete removes database data, images are stored statically in /media/.
    # user_record_delete removes images as well
    for record in records:
        user_record_delete(request, record.id)
    
    f.delete()
    messages.success(request, f'Formulár {f.formular_nazov} bol vymazaný úspešne.')
    return redirect('admin_forms')  # Redirect to the formular list page


def admin_users(request):
    users = User.objects.all().prefetch_related('groups').order_by("id")
    groups = Group.objects.all()
    return render(request, 'admin_users.html', {'users': users, 'groups': groups})

def admin_create_user(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        group_name = request.POST.get('group')  # Get selected group nazov from formular

        # Validate group nazov and retrieve corresponding Group object
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            group = None
        
        if not group:
            messages.error(request, "Neplatný výber skupiny.")
            return redirect('admin_users')

        # Check if username or email already exist
        if User.objects.filter(username=username).exists():
            messages.error(request, "Používateľské meno už je obsadené.")
            return redirect('admin_users')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "E-mail je už zaregistrovaný.")
            return redirect('admin_users')

        # Create and save the new user
        try:
            user2 = User.objects.create_user(username=username, email=email, password=password)
            user2.groups.add(group)  # Add user to the selected group
            messages.success(request, "Používateľ bol úspešne vytvorený.")
            return redirect('admin_users')
        except Exception as e:
            error_message = str(e)
            messages.error(request, f'Chyba pri vytváraní používateľa: {error_message}')

    return redirect('admin_users')

from django.contrib.auth.hashers import make_password

def admin_edit_user(request, user_id):
    user1 = get_object_or_404(User, pk=user_id)
    groups = Group.objects.all()  # Fetch all available groups

    if request.method == 'POST':
        # user1 details update
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
            messages.success(request, 'Používateľ bol úspešne aktualizovaný.')
        except Exception as e:
            messages.error(request, f'Chyba pri aktualizácii používateľa: {str(e)}')

        return redirect('admin_users')
    else:
        # Pass existing group names to the template
        existing_group = user1.groups.first() if user1.groups.exists() else None
        return render(request, 'admin_edit_user.html', {'user1': user1, 'groups': groups, 'existing_group': existing_group})

 
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        records = Zaznam.objects.filter(user=user)
        for record in records:
            user_record_delete(request, record.id)
        user.delete()
        messages.success(request, f'User {user.username} was deleted successfully.')
        return redirect('admin_users')  # Redirect to the user list page

    return render(request, 'admin_delete_user.html', {'user': user})





def admin_galeries(request):
    galleries = Galeria.objects.all().order_by('-vytvoreny')
    return render(request, 'admin_galeries.html', {'galleries': galleries})


def admin_create_galery(request, gallery_id=None):
    # If editing an existing gallery, we need to fetch it and its attributes
    g_name = ""
    if gallery_id:
        gallery = get_object_or_404(Galeria, pk=gallery_id)
        selected_form = gallery.formular
        #print("selected_form: ", selected_form)
        form_attributes = Formular_Atribut.objects.filter(formular=selected_form).order_by('id')
        g_name = gallery.galeria_nazov
    else:
        gallery = None
        selected_form = None
        form_attributes = None

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'GET':
        # AJAX request to get attributes for a specific formular
        form_id = request.GET.get('form_id')
        attributes = Formular_Atribut.objects.filter(formular=form_id).order_by('id')
        attributes_data = [
            {
                'id': attr.id,
                'nazov': attr.atribut.nazov,
                'zobrazit_v_galerii': attr.zobrazit_v_galerii
            }
            for attr in attributes
        ]
        #print("returning here -----------------------------")
        return JsonResponse({'attributes': attributes_data})

    if request.method == 'POST':
        form_id = request.POST.get('form')
        g_name = request.POST.get('galeria_nazov')
        try:
            formular = Formular.objects.get(id=form_id)
        except Formular.DoesNotExist:
            # error, no formular for gallery is set
            messages.error(request, 'Formulár pre galériu sa nenašiel.')    
            return redirect('admin_galeries')
        
        # If we're creating a new gallery, instantiate it
        if not gallery_id:
            gallery = Galeria(formular=formular)
        
        formular.zobrazit_v_galerii = True
        formular.save()
        
        gallery.galeria_nazov = g_name

        gallery.save()

        # Update the zobrazit_v_galerii settings for each atribut
        # We reset all to False first, then set the selected ones to True
        Formular_Atribut.objects.filter(formular=formular).update(zobrazit_v_galerii=False)
        # TODO filter, fix
        for key, hodnota in request.POST.items():
            if key.startswith('attribute_'):
                #print(key, hodnota, "--------------------------------------------------------------")
                attr_id = hodnota
                Formular_Atribut.objects.filter(id=attr_id, formular=formular).update(zobrazit_v_galerii=True)

        if gallery_id:
            messages.success(request, 'Galéria bola úspešne aktualizovaná.')
        else:
            messages.success(request, 'Galéria bola úspešne vytvorená.')
            
        return redirect('admin_galeries')

    # If it's a GET request, we render the page with the formular selection
    if not g_name:
        if selected_form:
            #print("HRERE-------")
            g_name = selected_form.formular_nazov
    
    forms = Formular.objects.filter(zobrazit_v_galerii=False)
    #print("forms: ", forms, "\n")
    if forms.exists():
        if selected_form != None:
            forms = []
            forms.append(selected_form)
    else:
        if gallery_id != None and selected_form != None:
            forms = []
            forms.append(selected_form)
    print("forms: ", forms, "\n")
    print("selected_form: ", selected_form, "\n")
    print("gallery_id: ", gallery_id, "\n")
    """if not forms.exists() and gallery_id != None and selected_form != None:
        print("------HRERE-------")
        forms = []
        forms.append(selected_form)"""
    return render(request, 'admin_create_galery.html', {
        'gallery': gallery,
        'selected_form': selected_form,
        'forms': forms,
        'form_attributes': form_attributes,
        'galeria_nazov' : g_name
    })
    
    
@require_POST  # Ensure this view can only be accessed via POST method for security
def admin_delete_galery(request, gallery_id):
    gallery = get_object_or_404(Galeria, pk=gallery_id)
    
    f = gallery.formular
    f.zobrazit_v_galerii = False
    f.save()
    
    attrs = Formular_Atribut.objects.filter(zobrazit_v_galerii=True, formular=f)
    for attr in attrs:
        attr.zobrazit_v_galerii = False
        attr.save()
    
    gallery.delete()
    messages.success(request, 'Galéria bola úspešne odstránená.')
    return redirect('admin_galeries')

@login_required
def admin_all_records(request):
    records_with_details = []

    records = Zaznam.objects.all()
    for record in records:
        if record.user == None:
            print("ERROR, rec not exists")
            continue
        # Fetch the first Formular_Atribut_Udaje instance related to the record to determine the formular
        first_attribute_data = Formular_Atribut_Udaje.objects.filter(zaznam=record).first()
        formular = first_attribute_data.formular_atribut.formular if first_attribute_data else None
        formular_nazov = None
        if formular: formular_nazov = formular.formular_nazov

        # Check if there is a gallery associated with the formular
        gallery = Galeria.objects.filter(formular=formular).first() if formular else None
        galeria_nazov = gallery.galeria_nazov if gallery else None
        
        attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)
        if not attributes_to_display:
            attributes_to_display = Formular_Atribut.objects.filter(formular=formular)
        # Get all Formular_Atribut_Udaje entries linked to the selected attributes
        attributes_data = Formular_Atribut_Udaje.objects.filter(formular_atribut__in=attributes_to_display)
        record_attributes = attributes_data.filter(zaznam_id=record.id)
        obrazok_url = record_attributes.filter(formular_atribut__atribut__typ='obrazok_url').first()
        #print("image url: ", obrazok_url, "\n")
        obrazok_url = obrazok_url.hodnota if obrazok_url else None
        
        records_with_details.append({
            'record': record,
            'image' : obrazok_url, 
            'formular_nazov': formular_nazov,
            'galeria_nazov': galeria_nazov, 
            'description' : record.opis
        })
        
    # Paginate the gallery data
    page = request.GET.get('page')
    paginator = Paginator(records_with_details, 6)  # 3 cards in a row, 2 rows on a page
    records_with_details = paginator.get_page(page)

    return render(request, 'admin_all_records.html', {'records_with_details': records_with_details})






def user_collection_formular(request):
    attributes = Atribut.objects.all()
    return render(request, 'user_collection_formular.html', {'attributes': attributes})


def user_forms(request):
    forms = Formular.objects.all()
    return render(request, 'user_forms.html', {'forms': forms})



@login_required
def user_forms_view(request, form_id):
    form_data = Formular_Atribut.objects.filter(formular=form_id)
    formular_nazov = get_object_or_404(Formular, id=form_id).formular_nazov
    form_attrs = []
    for x in form_data:
        form_attrs.append({'attr': x.atribut, 'req': x.povinny})
    #form_attrs = [attr.atribut for attr, req in form_data]
    return render(request, 'user_forms_view.html', {
        'form_attrs': form_attrs,
        'formular_nazov': formular_nazov,
        'form_id': form_id
    })

@login_required
def user_forms_record_add(request, form_id):
    if request.method == 'POST':
        user = request.user
        record = Zaznam.objects.create(user=user)
        record.formular = Formular.objects.get(id=form_id)
        
        # description
        desc = request.POST.get('description', '')
        if desc:
            record.opis = desc
            record.save()
                
        # Process text fields
        for key, hodnota in request.POST.items():
            if key.startswith("attr_"):
                attr_id = key.split("_")[1]
                atribut = get_object_or_404(Atribut, id=attr_id)
                # here check for atribut.typ and given string to test correct typ e.g. int(...)
                
                if atribut.typ != "obrazok_url":  # Only process non-image fields here
            
                    if atribut.typ == "date" and not re.match(r"^\d{4}-\d{2}-\d{2}$", hodnota):
                        if Formular_Atribut.objects.get(atribut=atribut, formular_id=form_id).povinny:
                            messages.error(request, f"Hodnota pre '{atribut.nazov}' musí mať formát: YYYY-MM-DD.")
                            record.delete()
                            return redirect('user_forms_view', form_id=form_id)
                    if atribut.typ == "bool" and hodnota.lower() not in ["áno", "nie"]:
                        if Formular_Atribut.objects.get(atribut=atribut, formular_id=form_id).povinny:
                            messages.error(request, f"Hodnota pre'{atribut.nazov}' musí byť: 'áno' or 'nie'.")
                            record.delete()
                            return redirect('user_forms_view', form_id=form_id)

                    if atribut.typ == "int" and not hodnota.isdigit():
                        if Formular_Atribut.objects.get(atribut=atribut, formular_id=form_id).povinny:
                            messages.error(request, f"Hodnota pre '{atribut.nazov}' musí byť: integer.")
                            record.delete()
                            return redirect('user_forms_view', form_id=form_id)
                        
                    form_attr = Formular_Atribut.objects.get(atribut=atribut, formular_id=form_id)
                    Formular_Atribut_Udaje.objects.create(zaznam=record, formular_atribut=form_attr, hodnota=hodnota)
                
        # Process file fields (images)
        added_image = False
        for key, image_file in request.FILES.items():
            if key.startswith("attr_"):
                attr_id = key.split("_")[1]
                atribut = get_object_or_404(Atribut, id=attr_id)
                if atribut.typ == "obrazok_url":
                    form_attr = Formular_Atribut.objects.get(atribut=atribut, formular_id=form_id)                        
                    fs = FileSystemStorage(location=settings.MEDIA_ROOT) # pridane...
                    filename = fs.save(image_file, image_file)
                    obrazok_url = fs.url(filename)
                    Formular_Atribut_Udaje.objects.create(zaznam=record, formular_atribut=form_attr, hodnota=obrazok_url)
                    added_image = True
                    #logger.info(f"Uploaded file: {image_file.nazov}")
                    #logger.info(f"File URL: {obrazok_url}")

        if not added_image:
            try:
                atribut = Atribut.objects.get(typ="obrazok_url")
                form_attr = Formular_Atribut.objects.get(atribut=atribut, formular_id=form_id)
                #print("------------------no files, but obrazok_url\n")
                Formular_Atribut_Udaje.objects.create(zaznam=record, formular_atribut=form_attr, hodnota="")
            except Formular_Atribut.DoesNotExist:
                pass    # this is OK
        # Process comment
        
        comment = request.POST.get('comment', '')
        if comment:
            Zaznam_Komentar.objects.create(user=user, zaznam=record, komentar=comment)
    
    return redirect("user_forms")




@login_required
def user_records(request):
    records_with_details = []

    records = Zaznam.objects.filter(user=request.user)
    for record in records:
        # Fetch the first Formular_Atribut_Udaje instance related to the record to determine the formular
        first_attribute_data = Formular_Atribut_Udaje.objects.filter(zaznam=record).first()
        formular = first_attribute_data.formular_atribut.formular if first_attribute_data else None
        formular_nazov = formular.formular_nazov if formular else "Unknown Form"

        # Check if there is a gallery associated with the formular
        gallery = Galeria.objects.filter(formular=formular).first() if formular else None
        galeria_nazov = gallery.galeria_nazov if gallery else None
        
        attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)
        if not attributes_to_display:
            attributes_to_display = Formular_Atribut.objects.filter(formular=formular)
        #attributes_to_display = FormAttribute.objects.filter(formular=formular, zobrazit_v_galerii=True) # TODO: when in user records could be false
        # Get all Formular_Atribut_Udaje entries linked to the selected attributes
        attributes_data = Formular_Atribut_Udaje.objects.filter(formular_atribut__in=attributes_to_display)
        record_attributes = attributes_data.filter(zaznam_id=record.id)
        obrazok_url = record_attributes.filter(formular_atribut__atribut__typ='obrazok_url').first()
        obrazok_url = obrazok_url.hodnota if obrazok_url else None
        
        records_with_details.append({
            'record': record,
            'image' : obrazok_url, 
            'formular_nazov': formular_nazov,
            'galeria_nazov': galeria_nazov, 
            'description' : record.opis
        })
        
    # Paginate the gallery data
    page = request.GET.get('page')
    paginator = Paginator(records_with_details, 6)  # 3 cards in a row, 2 rows on a page
    records_with_details = paginator.get_page(page)

    return render(request, 'user_records.html', {'records_with_details': records_with_details})


@login_required
def user_record_delete(request, record_id):
    record = get_object_or_404(Zaznam, id=record_id) #, user=request.user

    # Find and delete the image file associated with the record
    image_attribute_data = Formular_Atribut_Udaje.objects.filter(zaznam=record, formular_atribut__atribut__typ='obrazok_url')
    for image_data in image_attribute_data:
        image_path = image_data.hodnota
        if image_path:
            # Remove the leading '/media' from the image path
            if image_path.startswith('/media'):
                image_path = image_path[6:]  # Adjust this based on the exact structure of your paths
            full_image_path = settings.MEDIA_ROOT +  image_path
            if os.path.exists(full_image_path):
                os.remove(full_image_path)

    record.delete()
    messages.success(request, 'Zoznam bol úspešne odstránený.')
    if request.session['admin_view'] == True:
        return redirect('admin_all_records')
    return redirect('user_records')



def user_record_detail(request, record_id, for_user):
    if for_user == 1:
        record = get_object_or_404(Zaznam, pk=record_id, user=request.user)
    else:
        record = get_object_or_404(Zaznam, pk=record_id)
        
    if record.user == request.user: # request.user.is_authenticated or 
        for_user = 1
    
    fa = Formular_Atribut_Udaje.objects.filter(zaznam=record)
    # filter which are zobrazit_v_galerii
    form_attributes = []
    # helper to get all attributes
    attributes_to_display = Formular_Atribut.objects.filter(formular=record.formular, zobrazit_v_galerii=True)

    for f in fa:
        if not attributes_to_display:
            form_attributes.append(f)
        elif f.formular_atribut.zobrazit_v_galerii == True:
                form_attributes.append(f)
        else:
            pass
            #print("NO\n")
    record_comments = Zaznam_Komentar.objects.filter(zaznam=record).order_by('vytvoreny')

    return render(request, 'user_record_detail.html', {
        'record': record,
        'form_attributes': form_attributes,
        'record_comments': record_comments,
        'for_user' : for_user
    })

from pathlib import Path
import re

def user_record_update(request, record_id, for_user):
    #clear_messages(request)
    record = get_object_or_404(Zaznam, pk=record_id)

    if request.method == 'POST':
        for key, hodnota in request.POST.items():
            if key.startswith('attribute_'):
                attr_id = key.split('_')[1]
                attribute_data = Formular_Atribut_Udaje.objects.get(id=attr_id)
                # get actual atribut and its typ:
                atribut = attribute_data.formular_atribut.atribut
                # check the typ correctness:
                if atribut.typ == "date" and not re.match(r"^\d{4}-\d{2}-\d{2}$", hodnota):
                    # povinny
                    if attribute_data.formular_atribut.povinny == True:
                        messages.error(request, f"Hodnota pre '{atribut.nazov}' musí mať formát:  YYYY-MM-DD.")
                        return redirect('user_record_detail', record_id=record_id, for_user=for_user)
                if atribut.typ == "bool" and hodnota.lower() not in ["áno", "nie"]:
                    if attribute_data.formular_atribut.povinny == True:
                        messages.error(request, f"odnota pre '{atribut.nazov}' musí byť: 'áno' alebo 'nie'.")
                        return redirect('user_record_detail', record_id=record_id, for_user=for_user)

                if atribut.typ == "int" and not hodnota.isdigit():
                    if attribute_data.formular_atribut.povinny == True:
                        messages.error(request, f"odnota pre '{atribut.nazov}' musí byt: integer.")
                        return redirect('user_record_detail', record_id=record_id, for_user=for_user)
                
                attribute_data.hodnota = hodnota
                attribute_data.save()
                
        for key, hodnota in request.POST.items():
            if key.startswith('comment_'):
                comment_id = key.split('_')[1]
                comment_data = Zaznam_Komentar.objects.get(id=comment_id)
                comment_data.komentar = hodnota
                comment_data.save()
        
        for key, image_file in request.FILES.items():
            if key.startswith("attrnew_"):
                attr_id = key.split("_")[1]
                atribut = get_object_or_404(Atribut, id=attr_id)
                
                if atribut.typ == "obrazok_url":
                    #print("record.formular: ", record.formular)
                    form_attr = Formular_Atribut.objects.get(atribut=atribut, formular=record.formular)
                    attr_data, _ = Formular_Atribut_Udaje.objects.get_or_create(zaznam=record, formular_atribut=form_attr)
                    
                    # Get file nazov from the uploaded file
                    file_name = Path(image_file.name).name
                    
                    # Save the new image file to the file system within MEDIA_ROOT
                    fs = FileSystemStorage(location=settings.MEDIA_ROOT)
                    new_image_path = fs.save(file_name, image_file)
                    new_image_url = fs.url(new_image_path)

                    # Update the Formular_Atribut_Udaje with the new image URL
                    if attr_data.hodnota:
                        #print("HERE: ", attr_data.hodnota)
                        image_path = attr_data.hodnota
                        if image_path:
                            # Remove the leading '/media' from the image path
                            if image_path.startswith('/media'):
                                image_path = image_path[6:]  # Adjust this based on the exact structure of your paths
                            full_image_path = settings.MEDIA_ROOT +  image_path
                            #print("FULL: ", full_image_path)
                            if os.path.exists(full_image_path):
                                os.remove(full_image_path)
                                #print("REMOVED: ", full_image_path)

                    attr_data.hodnota = new_image_url
                    attr_data.save()
                
                
        messages.success(request, "Zaznam bol aktualizovaný.")
        
        descr = request.POST.get('record_description')
        if descr:
            record.opis = descr
            record.save()
    
        comment = request.POST.get('comment')
        if comment:
            Zaznam_Komentar.objects.create(zaznam=record, user=request.user, komentar=comment)
            messages.success(request, 'Váš komentár bol pridaný.')
        
    
        commentU = request.POST.get('commentU')
        if commentU:
            """  user = None"""
            Zaznam_Komentar.objects.create(zaznam=record, user=None, komentar=commentU, povoleny_adminom=False)
            messages.success(request, 'Váš komentár bol pridaný.')

        return redirect('user_record_detail', record_id=record_id, for_user=for_user)

    else:
        return redirect('user_record_detail', record_id=record_id, for_user=for_user)
    


def remove_comment(request, comment_id, for_user):
    comment = get_object_or_404(Zaznam_Komentar, pk=comment_id)
    #print("------------------------")
    if request.session.get('admin_view', False) or for_user or (request.user.is_authenticated and comment.user == request.user):
        comment.delete()
        messages.success(request, 'Komentár bol úspešne odstránený.')
    return redirect('user_record_detail', record_id=comment.zaznam.id, for_user=for_user)

def aprove_comment(request, comment_id, for_user):
    comment = get_object_or_404(Zaznam_Komentar, pk=comment_id)
    comment.povoleny_adminom = True
    comment.save()
    messages.success(request, 'Komentár schválený.')
    return redirect('user_record_detail', record_id=comment.zaznam.id, for_user=for_user)



def user_galeries(request):
    
    featured_galleries = Galeria.objects.order_by('-vytvoreny')#[:4]
    gallery_data = []
    for gallery in featured_galleries:
        # Get the associated formular for the gallery
        formular = gallery.formular
        if formular:
            formular_nazov = formular.formular_nazov
            # Get all formular attributes marked to be displayed in the gallery
            attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)
            # Get all atribut data entries linked to the selected attributes and the gallery's formular
            attributes_data = Formular_Atribut_Udaje.objects.filter(formular_atribut__in=attributes_to_display)
            # Filter atribut data entries for the current gallery's formular
            record_attributes = attributes_data
            # Find the first image URL atribut data entry for the current gallery
            image_url_attribute = record_attributes.filter(formular_atribut__atribut__typ='obrazok_url').first()
            # Get the image URL hodnota if it exists
            obrazok_url = image_url_attribute.hodnota if image_url_attribute else None
        else:
            formular_nazov = "Unknown Form"
            obrazok_url = None

        gallery_info = {
            'id': gallery.id,
            'nazov': gallery.galeria_nazov,
            'formular_nazov': formular_nazov,
            'vytvoreny': gallery.vytvoreny.strftime('%Y-%m-%d'),
            'obrazok_url': obrazok_url
        }
        gallery_data.append(gallery_info)
        
    # Paginate the gallery data
    page = request.GET.get('page')
    paginator = Paginator(gallery_data, 4)  # 3 cards in a row, 2 rows on a page
    gallery_page = paginator.get_page(page)
    
    
    #galleries = Galeria.objects.all()
    return render(request, 'user_galery.html', {'gallery_data': gallery_data, 'gallery_page': gallery_page})


def user_galery_view(request, gallery_id):
    gallery = get_object_or_404(Galeria, id=gallery_id)
    formular = gallery.formular

    # Get attributes that are marked to display in gallery
    attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)

    # Get all Formular_Atribut_Udaje entries linked to the selected attributes
    attributes_data = Formular_Atribut_Udaje.objects.filter(formular_atribut__in=attributes_to_display)

    # Extracting unique record IDs from attributes_data
    unique_record_ids = set(attributes_data.values_list('zaznam_id', flat=True))

    # Preparing data for each unique record
    gallery_data = []
    for record_id in unique_record_ids:
        record = Zaznam.objects.get(id=record_id)
        record_attributes = attributes_data.filter(zaznam_id=record_id)

        # Extract image URL if available
        obrazok_url = record_attributes.filter(formular_atribut__atribut__typ='obrazok_url').first()
        obrazok_url = obrazok_url.hodnota if obrazok_url else None

        # Check the user's existing vote for the record
        user_vote = None
        if request.user.is_authenticated:
            user_vote_obj = Hlas.objects.filter(user=request.user, zaznam=record).first()
            if user_vote_obj:
                user_vote = user_vote_obj.typ_hlasu
                
        record_details = {
            'record': record,
            'thumb_up': Hlas.objects.filter(zaznam = record_id, typ_hlasu="up").count(),
            'thumb_down': Hlas.objects.filter(zaznam = record_id, typ_hlasu="down").count(),
            'vytvoreny': record.vytvoreny,
            'aktualizovany': record.aktualizovany,
            'username': record.user.username if record.user else "Unknown",
            'attributes': [{'nazov': attr.formular_atribut.atribut.nazov, 'hodnota': attr.hodnota, 'typ' : attr.formular_atribut.atribut.typ} for attr in record_attributes if attr.formular_atribut.atribut.typ != 'obrazok_url'],
            'image': obrazok_url,
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
def vote(request, record_id, typ_hlasu):
    #print("------------------------Voting on record", record_id, "with", typ_hlasu)
    record = get_object_or_404(Zaznam, pk=record_id)
    user = request.user
    
    #print("------------------------Voting on record", record_id, "with", typ_hlasu, "for user", user)

    # Check if the user has already voted on this record
    existing_vote = Hlas.objects.filter(user=user, zaznam=record).first()

    # Update or create the vote
    if existing_vote:
        if existing_vote.typ_hlasu != typ_hlasu:
            existing_vote.typ_hlasu = typ_hlasu
            existing_vote.save()
    else:
        Hlas.objects.create(user=user, zaznam=record, typ_hlasu=typ_hlasu)

    # Return the updated vote counts
    return JsonResponse({'thumb_up': Hlas.objects.filter(zaznam = record_id, typ_hlasu="up").count(), 'thumb_down': Hlas.objects.filter(zaznam = record_id, typ_hlasu="down").count()})
