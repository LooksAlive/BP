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


"""

View funkcie (zobrazovacie funkcie) sú kľúčovou súčasťou Django frameworku a slúžia na pripojenie logiky spracovania požiadaviek k šablónam HTML.

Základný princíp:

    URL vzor: V súbore urls.py definujete URL vzor, ktorý spája konkrétnu URL adresu s view funkciou. Napríklad URL vzor / by mohol smerovať na view funkciu index.
    Požiadavka: Keď užívateľ navštívi URL adresu, ktorá zodpovedá URL vzoru, Django odošle HTTP požiadavku do príslušnej view funkcie.
    Spracovanie požiadavky: View funkcia prijme objekt request, ktorý obsahuje informácie o požiadavke, ako napríklad metóda požiadavky (GET, POST), hlavičky, parametre URL a telo požiadavky.
    Logika: View funkcia spracuje požiadavku a vykoná požadovanú akciu. Môže to zahŕňať načítanie dát z databázy, spracovanie formulárových dát, generovanie HTML kódu alebo presmerovanie na inú URL adresu.
    Vrátenie odpovede: View funkcia vráti objekt HttpResponse, ktorý obsahuje HTML kód, ktorý sa odošle späť prehliadaču užívateľa.

"""





""" vyčistíme všetky správy """
def clear_messages(request):
    storage = messages.get_messages(request)
    storage.used = True


from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.serializers.json import DjangoJSONEncoder
import json


"""  zobrazovacia funkcia (view) pre úvodnú stránku vašej Django aplikácie. Zodpovedá URL vzoru, ktorý by mal smerovať na hlavnú stránku """
def index(request):
    # 6 záznamov zobrazíme v zozname
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

    # Súhrnné záznamy podľa dátumu (počet záznamov vytvorených za deň)
    records_per_day = (
        recent_records
        .values('vytvoreny')
        .annotate(num_records=models.Count('id'))
    )

    # Pre každý posledný záznam načítame súvisiaci Formular_Atribut_Udaje
    recent_records_data = []
    for record in recent_records:
        form_data = Formular_Atribut_Udaje.objects.filter(zaznam=record)
        # Zhromažďujeme iba potrebné podrobnosti na zobrazenie, ako sú obrázky a hodnoty atribútov
        image_attribute = form_data.filter(formular_atribut__atribut__typ='obrazok_url').first()
        # Zistite, či je pre tento záznam k dispozícii obrázok
        image_available = bool(image_attribute)
        #print("image_available: ", image_available)
        
        # základne detaili o zázname
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
            'image_available': image_available
        }
        recent_records_data.append(record_details)

    # len 4 galérie sa zobrazia na hlavnej stránke
    featured_galleries = Galeria.objects.order_by('-vytvoreny')[:4]
    
    # údaje o galérií
    gallery_data = []
    for gallery in featured_galleries:
        # Get the associated formular for the gallery
        formular = gallery.formular
        if formular:
            formular_nazov = formular.formular_nazov
            # Získame všetky atribúty formulára označené na zobrazenie v galérii
            attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)
            # Získame všetky položky údajov atribútov prepojené s vybranými atribútmi a formulárom galérie
            attributes_data = Formular_Atribut_Udaje.objects.filter(formular_atribut__in=attributes_to_display)
            # Filtrume položky s údajmi atribútov pre vzorec aktuálnej galérie
            record_attributes = attributes_data
            # Nájdite prvú položku s údajmi atribútu URL obrázka pre aktuálnu galériu
            image_url_attribute = record_attributes.filter(formular_atribut__atribut__typ='obrazok_url').first()
            # Získame hodnotu adresy URL obrázka, ak existuje
            obrazok_url = image_url_attribute.hodnota if image_url_attribute else None
        else:
            formular_nazov = "Unknown Form"
            obrazok_url = None

        # vytvoríme zoznam
        gallery_info = {
            'id': gallery.id,
            'nazov': gallery.galeria_nazov,
            'formular_nazov': formular_nazov,
            'vytvoreny': gallery.vytvoreny.strftime('%Y-%m-%d'),
            'obrazok_url': obrazok_url
        }
        gallery_data.append(gallery_info)


    # počty do štatistík
    num_records = Zaznam.objects.count()
    num_users = User.objects.count()
    num_galleries = Galeria.objects.count()
    num_forms = Formular.objects.count()

    # údaje pre grafy
    chart_labels = [item['vytvoreny'].strftime('%Y-%m-%d') for item in records_per_day]
    chart_data = [item['num_records'] for item in records_per_day]

    # finálna premenná
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
        'data': json.dumps(data, cls=DjangoJSONEncoder),  # konvertujeme na JSON, aby sme mohli použiť v grafoch v javascripte.
        'username': request.user.username if request.user.is_authenticated else ''
    }

    return render(request, 'index.html', context)

""" Prihlásenie """
def login_view(request):
    clear_messages(request)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Načítame skupiny užívateľa
            user_groups = user.groups.all()
            #for group in user_groups:
                #print("group: ", group)

            # rôzne presmerovania pre rôzne skupiny užívateľov
            # používame premenné v relácií pre indikáciu skupiny užívateľa
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

""" Odhlásenie """
def logout_user(request):
    logout(request)
    messages.success(request, "Boli ste odhlásený...")
    request.session["admin_view"] = False
    return redirect('index')

""" Registrácia """
def registration_view(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        email = request.POST.get('email')
        username = request.POST.get('username')
        
        # nastavíme skupinu užívateľa
        group = Group.objects.get(name="prihlásený použivateľ")

        if password != confirm_password:
            messages.error(request, "Heslá sa nezhodujú.")
            return render(request, 'registration.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "užívateľské meno už je obsadené.")
            return render(request, 'registration.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email už je registrovaný.")
            clear_messages(request)  # vyčistíme správy a presmerujeme
            return render(request, 'registration.html')

        # vytvorenie nového užívateľa
        user = User.objects.create_user(username=username, email=email, password=password)
        user.groups.add(group)
        user.save()
        messages.success(request, "Registrácia úspešná. Teraz sa môžete prihlásiť.")
        return redirect('login')

    return render(request, 'registration.html')



""" Všetky typy, ktoré registrujeme v aplikácií """
attribute_types = ['int', 'float', 'str', 'bool', 'obrazok_url', 'date']


def admin_attributes(request):
    attributes = Atribut.objects.all()
    return render(request, 'admin_attributes.html', {'attributes': attributes, 'attribute_types': attribute_types})

""" Nový atribút """
def admin_create_attribute(request):
    if request.method == 'POST':
        nazov = request.POST.get('nazov')
        a_type = request.POST.get('typ')
        
        # vytvoríme nová atribút
        attr = Atribut(nazov=nazov, typ=a_type)
        attr.save()
        return redirect('admin_attributes')
    
    attr = Atribut()  # predvolené hodnoty sú v models.py

    return render(request, 'admin_attributes.html', {'attributes': Atribut.objects.all()})

""" Vymaž atribút """
def admin_delete_attribute(request, attribute_id):
    atribut = get_object_or_404(Atribut, pk=attribute_id)

    if request.method == 'POST':
        atribut.delete()
        return redirect('admin_attributes')  # presmerujeme na zoznam atribútov

    return render(request, 'admin_delete_attribute.html', {'atribut': atribut})

""" Úprava atribútu """
def admin_edit_attribute(request, attribute_id):
    atribut = get_object_or_404(Atribut, pk=attribute_id)

    if request.method == 'GET':
        # get metóda, jedoducho renderujeme atribút ktorý upravujeme
        return render(request, 'admin_edit_attribute.html', {'atribut': atribut, 'attribute_types': attribute_types})

    # aktualizujeme atribút
    if request.method == 'POST':
        nazov = request.POST.get('nazov')
        a_type = request.POST.get('typ')

        atribut.nazov = nazov
        atribut.typ = a_type
        atribut.save()

        return redirect('admin_attributes')  # presmerujeme na zoznam atribútov

""" Všetky formuláre """
def admin_forms(request):
    forms = Formular.objects.all()
    return render(request, 'admin_forms.html', {'forms': forms})

""" Vytvorenie nového formulára, ak form_id != None tak upravujeme/editujeme formulár """
def admin_create_form(request, form_id=None):
    # Zistite, či ide o akciu vytvorenia alebo úpravy
    if form_id:
        formular = get_object_or_404(Formular, pk=form_id)
        form_attributes = Formular_Atribut.objects.filter(formular=formular)
    else:
        # Vytvárame nový formulár
        formular = Formular()
        form_attributes = None
    
    if request.method == 'POST':
        formular_nazov = request.POST.get('formular_nazov')
        formular.formular_nazov = formular_nazov
        formular.save()
        
        # Vytvorte FormAttributes množinu pre atribúty ktore dostaneme v POST metóde
        processed_attribute_ids = set()
        # spracujeme vsetky POST udaje
        for key, hodnota in request.POST.items():
            if key.startswith('attribute_'):
                attribute_id = hodnota
                req = request.POST.get('attr_req_'+str(attribute_id))
                povinny = bool(req)  # Je zadaný alebo nie 

                processed_attribute_ids.add(int(attribute_id))

                # Skontrolume, či už existuje atribút Formular_Atribut pre tento vzorec a atribút
                try:
                    formular_attribute = Formular_Atribut.objects.get(formular=formular, atribut_id=int(attribute_id))
                    #print(f"Found existing Formular_Atribut for formular {formular.id} and attribute {attribute_id}: {formular_attribute}")
                    formular_attribute.povinny = povinny
                    formular_attribute.save()
                except Formular_Atribut.DoesNotExist:
                    #print(f"Creating new Formular_Atribut for formular {formular.id} and attribute {attribute_id} with povinny={povinny}")
                    try:
                        atribut = Atribut.objects.get(id=int(attribute_id))
                        new_formular_attribute = Formular_Atribut.objects.create(
                            formular=formular,
                            atribut=atribut,
                            povinny=povinny
                        )
                        
                        # Vytvoriť Formular_Atribut_Udaje prepojené so Zaznamom (záznamom)
                        existing_zaznams = Zaznam.objects.filter(formular=formular)
                        for record in existing_zaznams:
                            Formular_Atribut_Udaje.objects.create(
                                zaznam=record,
                                formular_atribut=new_formular_attribute,
                                hodnota=''  # hodnota je predvolená v models.py ale môžeme ju nastaviť aj tu.
                            )
                    except Atribut.DoesNotExist:
                        print(f"Atribut with ID {attribute_id} does not exist.")

        # Odstránime všetky inštancie Formular_Atribut, ktoré nie sú v spracovanej sade, teda admin niektoré vymazal
        formular_attributes_to_delete = Formular_Atribut.objects.filter(formular=formular)
        formular_attributes_to_delete.exclude(atribut_id__in=processed_attribute_ids).delete()
                    
        # presmerovanie na zoznam formularov
        return redirect('admin_forms')
    
    else:
        attributes = Atribut.objects.all()
        return render(request, 'admin_create_form.html', {
            'formular': formular,
            'form_id': form_id,
            'attributes': attributes,
            'form_attributes': form_attributes,
        })

""" Vymazanie formulára """
def admin_delete_form(request, form_id):
    f = get_object_or_404(Formular, id=form_id)
    records = Zaznam.objects.filter(formular=f)
    # musíme odstrániť aj obrázok, vymazanie databázy odstráni databázové údaje, obrázky sa uložia staticky v /media/.
    # user_record_delete odstráni aj obrázky
    for record in records:
        user_record_delete(request, record.id)
    
    f.delete()
    messages.success(request, f'Formulár {f.formular_nazov} bol vymazaný úspešne.')
    return redirect('admin_forms')

""" Používatelia pre admina """
def admin_users(request):
    users = User.objects.all().prefetch_related('groups').order_by("id")
    groups = Group.objects.all()
    return render(request, 'admin_users.html', {'users': users, 'groups': groups})

""" Admin vytvrára používatelov """
def admin_create_user(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        group_name = request.POST.get('group')

        # Overte skupinu nazov a získame zodpovedajúci objekt skupiny
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            group = None
        
        if not group:
            messages.error(request, "Neplatný výber skupiny.")
            return redirect('admin_users')

        # Check if username or email already exist
        if User.objects.filter(username=username).exists():
            messages.error(request, "užívateľské meno už je obsadené.")
            return redirect('admin_users')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "E-mail je už zaregistrovaný.")
            return redirect('admin_users')

        # Vytvorte a uložte nového užívateľa
        try:
            user2 = User.objects.create_user(username=username, email=email, password=password)
            user2.groups.add(group)  # Pridáme ho do skupiny
            messages.success(request, "užívateľ bol úspešne vytvorený.")
            return redirect('admin_users')
        except Exception as e:
            error_message = str(e)
            messages.error(request, f'Chyba pri vytváraní užívateľa: {error_message}')

    return redirect('admin_users')

# pre vytvorenie nového hesla
from django.contrib.auth.hashers import make_password

""" Úprava užívateľa """
def admin_edit_user(request, user_id):
    # user1, pretože user premenná je už v request-e a v indexe
    user1 = get_object_or_404(User, pk=user_id)
    groups = Group.objects.all()  # všetky skupiny užívateľa

    if request.method == 'POST':
        # user1 details update
        user1.email = request.POST.get('email')
        user1.username = request.POST.get('username')
    
        new_password = request.POST.get('password')
        if new_password:
            user1.password = make_password(new_password)  # hešovanie hesla užívateľa

        # spracovanie skupiny
        selected_group_name = request.POST.get('role')
        selected_group = Group.objects.get(name=selected_group_name)
        user1.groups.clear()  # vymazanie skupín
        user1.groups.add(selected_group)  # pridane skupiny
        
        try:
            user1.save()
            messages.success(request, 'užívateľ bol úspešne aktualizovaný.')
        except Exception as e:
            messages.error(request, f'Chyba pri aktualizácii užívateľa: {str(e)}')

        return redirect('admin_users')
    else:
        # Pass existing group names to the template
        existing_group = user1.groups.first() if user1.groups.exists() else None
        return render(request, 'admin_edit_user.html', {'user1': user1, 'groups': groups, 'existing_group': existing_group})

""" Vymazanie užívateľa """
def admin_delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        records = Zaznam.objects.filter(user=user)
        for record in records:
            user_record_delete(request, record.id)
        user.delete()
        messages.success(request, f'užívateľ {user.username} bol úspešne odstránený.')
        return redirect('admin_users')

    return render(request, 'admin_delete_user.html', {'user': user})




""" Všetky galerie """
def admin_galeries(request):
    galleries = Galeria.objects.all().order_by('-vytvoreny') # zoradíme podla datumu vytvorenia/pridania
    return render(request, 'admin_galeries.html', {'galleries': galleries})


""" Vytvorenie novej galerie, ak je gallery_id != None, tak bude editovat danú galeriu """
def admin_create_galery(request, gallery_id=None):
    # názov galérie
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
        # Požiadavka AJAX na získanie atribútov pre konkrétny formulár
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
        return JsonResponse({'attributes': attributes_data})

    if request.method == 'POST':
        form_id = request.POST.get('form')
        g_name = request.POST.get('galeria_nazov')
        try:
            formular = Formular.objects.get(id=form_id)
        except Formular.DoesNotExist:
            # chyba, nie je nastavený žiadny vzorec pre galériu
            messages.error(request, 'Formulár pre galériu sa nenašiel.')    
            return redirect('admin_galeries')
        
        # Ak vytvárame novú galériu, vytvorte jej inštanciu
        if not gallery_id:
            gallery = Galeria(formular=formular)
        
        formular.zobrazit_v_galerii = True
        formular.save()
        
        gallery.galeria_nazov = g_name

        gallery.save()

        # Aktualizume nastavenia zobrazit_v_galerii pre každý atribút
        # Najprv všetky resetujeme na hodnotu False a potom nastavíme tie vybrané na hodnotu False
        Formular_Atribut.objects.filter(formular=formular).update(zobrazit_v_galerii=False)
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

    # Ak ide o požiadavku GET, vykreslíme stránku s výberom formulára
    if not g_name:
        if selected_form:
            g_name = selected_form.formular_nazov
    
    forms = Formular.objects.filter(zobrazit_v_galerii=False)
    # ak editujeme tak vložíme selected_form do listu ktorej patrí galéria, a zobrazí sa len jeden formulár.
    if forms.exists():
        if selected_form != None:
            forms = []
            forms.append(selected_form)
    else:
        if gallery_id != None and selected_form != None:
            forms = []
            forms.append(selected_form)
    #print("forms: ", forms, "\n")
    #print("selected_form: ", selected_form, "\n")
    #print("gallery_id: ", gallery_id, "\n")
    
    return render(request, 'admin_create_galery.html', {
        'gallery': gallery,
        'selected_form': selected_form,
        'forms': forms,
        'form_attributes': form_attributes,
        'galeria_nazov' : g_name
    })


""" Vymaženie galerie """    
@require_POST  # Zabezpečte, aby bolo toto zobrazenie z bezpečnostných dôvodov prístupné iba prostredníctvom metódy POST
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

""" Adminovy zobrazíme všetky záznamy """
@login_required
def admin_all_records(request):
    records_with_details = []

    records = Zaznam.objects.all()
    for record in records:
        if record.user == None:
            print("ERROR, rec not exists")
            continue
        # Získame prvú inštanciu atribútu vzorca Udaje súvisiacu so záznamom na určenie vzorca
        first_attribute_data = Formular_Atribut_Udaje.objects.filter(zaznam=record).first()
        formular = first_attribute_data.formular_atribut.formular if first_attribute_data else None
        formular_nazov = None
        if formular: formular_nazov = formular.formular_nazov

        # Skontrolujeme, či je k formuláru priradená galéria
        gallery = Galeria.objects.filter(formular=formular).first() if formular else None
        galeria_nazov = gallery.galeria_nazov if gallery else None
        
        attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)
        if not attributes_to_display:
            attributes_to_display = Formular_Atribut.objects.filter(formular=formular)
        # Získame všetky položky Formular_Atribut_Udaje prepojené s vybranými atribútmi
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
        
    # Stránkovanie údajov galérie
    page = request.GET.get('page')
    paginator = Paginator(records_with_details, 6)  # 3 karty v rade, 2 riadky na strane
    records_with_details = paginator.get_page(page)

    return render(request, 'admin_all_records.html', {'records_with_details': records_with_details})





""" Pomocné funkcie pre ladenie """
def user_collection_formular(request):
    attributes = Atribut.objects.all()
    return render(request, 'user_collection_formular.html', {'attributes': attributes})

def user_forms(request):
    forms = Formular.objects.all()
    return render(request, 'user_forms.html', {'forms': forms})


""" Formuláre """
@login_required
def user_forms_view(request, form_id):
    # zistíme všetky atribúty vo formulári
    form_data = Formular_Atribut.objects.filter(formular=form_id)
    formular_nazov = get_object_or_404(Formular, id=form_id).formular_nazov
    form_attrs = []
    for x in form_data:
        form_attrs.append({'attr': x.atribut, 'req': x.povinny})

    return render(request, 'user_forms_view.html', {
        'form_attrs': form_attrs,
        'formular_nazov': formular_nazov,
        'form_id': form_id
    })

""" Vytvorenie nového záznamu """
@login_required
def user_forms_record_add(request, form_id):
    if request.method == 'POST':
        user = request.user
        f = Formular.objects.get(id=form_id)
        record = Zaznam.objects.create(user=user, formular=f)
        
        # Opis
        desc = request.POST.get('description', '')
        if desc:
            record.opis = desc
            record.save()
        
        for key, hodnota in request.POST.items():
            if key.startswith("attr_"):
                attr_id = key.split("_")[1]
                atribut = get_object_or_404(Atribut, id=attr_id)
                # tu skontrolume atribút.typ a daný reťazec na otestovanie správneho typu, napr. int(...)
                
                if atribut.typ != "obrazok_url":  # Tu spracovávame iba polia, ktoré nie sú obrázkom
            
                    if atribut.typ == "date" and not re.match(r"^\d{4}-\d{2}-\d{2}$", hodnota): # formát dátumu
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
                
        # Spracovať polia súboru (obrázky)
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
                # vytvoriť nový zaznam s prazdnou hodnotou
                Formular_Atribut_Udaje.objects.create(zaznam=record, formular_atribut=form_attr, hodnota="")
            except Formular_Atribut.DoesNotExist:
                pass
        
        # spracujeme prvý komentár od vlastníka v zázname
        comment = request.POST.get('comment', '')
        if comment:
            Zaznam_Komentar.objects.create(user=user, zaznam=record, komentar=comment)
    
    return redirect("user_forms")


""" Všetky záznamy ktoré vlastní prihlásený pooužívateľ. """
@login_required
def user_records(request):
    # výsledná premenná pre údaje
    records_with_details = []

    records = Zaznam.objects.filter(user=request.user)
    for record in records:
        # Získame prvú inštanciu atribútu vzorca Udaje súvisiacu so záznamom na určenie vzorca
        first_attribute_data = Formular_Atribut_Udaje.objects.filter(zaznam=record).first()
        formular = first_attribute_data.formular_atribut.formular if first_attribute_data else None
        formular_nazov = formular.formular_nazov if formular else "Unknown Form"

        # Skontrolume, či je k formuláru priradená galéria
        gallery = Galeria.objects.filter(formular=formular).first() if formular else None
        galeria_nazov = gallery.galeria_nazov if gallery else None
        
        attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)
        if not attributes_to_display:
            attributes_to_display = Formular_Atribut.objects.filter(formular=formular)
        #attributes_to_display = FormAttribute.objects.filter(formular=formular, zobrazit_v_galerii=True)
        # Získame všetky položky Formular_Atribut_Udaje prepojené s vybranými atribútmi
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


""" vymazanie zaznamu """
@login_required
def user_record_delete(request, record_id):
    record = get_object_or_404(Zaznam, id=record_id) #, user=request.user

    # Nájdite a odstráňte súbor obrázka priradený k záznamu
    image_attribute_data = Formular_Atribut_Udaje.objects.filter(zaznam=record, formular_atribut__atribut__typ='obrazok_url')
    for image_data in image_attribute_data:
        image_path = image_data.hodnota
        if image_path:
            # Odstráňte úvodný znak „/media“ z cesty k obrázku
            if image_path.startswith('/media'):
                image_path = image_path[6:]  # Upravíme to na základe presnej štruktúry vašich ciest
            full_image_path = settings.MEDIA_ROOT +  image_path
            if os.path.exists(full_image_path):
                os.remove(full_image_path)

    record.delete()
    messages.success(request, 'Zoznam bol úspešne odstránený.')
    if request.session['admin_view'] == True:
        return redirect('admin_all_records')
    return redirect('user_records')


""" Zobrazenie údajov daného záznamu """
def user_record_detail(request, record_id, for_user):
    if for_user == 1:
        record = get_object_or_404(Zaznam, pk=record_id, user=request.user)
    else:
        record = get_object_or_404(Zaznam, pk=record_id)
        
    if record.user == request.user: # request.user.is_authenticated or 
        for_user = 1
    
    fa = Formular_Atribut_Udaje.objects.filter(zaznam=record)
    # filter, ktoré sú zobrazit_v_galerii
    form_attributes = []
    # pomocník na získanie všetkých atribútov
    attributes_to_display = Formular_Atribut.objects.filter(formular=record.formular, zobrazit_v_galerii=True)

    for f in fa:
        if not attributes_to_display:
            form_attributes.append(f)
        elif f.formular_atribut.zobrazit_v_galerii == True:
                form_attributes.append(f)
        else:
            pass
    record_comments = Zaznam_Komentar.objects.filter(zaznam=record).order_by('vytvoreny')

    return render(request, 'user_record_detail.html', {
        'record': record,
        'form_attributes': form_attributes,
        'record_comments': record_comments,
        'for_user' : for_user
    })

from pathlib import Path
import re

""" Aktualizácia/úprava záznamu """
def user_record_update(request, record_id, for_user):
    #clear_messages(request)
    record = get_object_or_404(Zaznam, pk=record_id)

    if request.method == 'POST':
        for key, hodnota in request.POST.items():
            if key.startswith('attribute_'):
                attr_id = key.split('_')[1]
                attribute_data = Formular_Atribut_Udaje.objects.get(id=attr_id)
                # získame skutočný atribút a jeho typ:
                atribut = attribute_data.formular_atribut.atribut
                # skontrolume správnosť typu:
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
        
        # ak začína názvom comment_ tak je komentár a zvyšok je jeho id
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
                    
                    # Získame súbor nazov z nahraného súboru
                    file_name = Path(image_file.name).name
                    
                    # Uložte nový obrazový súbor do systému súborov v rámci MEDIA_ROOT
                    fs = FileSystemStorage(location=settings.MEDIA_ROOT)
                    new_image_path = fs.save(file_name, image_file)
                    new_image_url = fs.url(new_image_path)

                    # Aktualizume Formular_Atribut_Udaje s novou adresou URL obrázka
                    if attr_data.hodnota:
                        #print("HERE: ", attr_data.hodnota)
                        image_path = attr_data.hodnota
                        if image_path:
                            # Odstráňte úvodný znak „/media“ z cesty k obrázku
                            if image_path.startswith('/media'):
                                image_path = image_path[6:]  # Upravte to na základe presnej štruktúry vašich ciest
                            full_image_path = settings.MEDIA_ROOT +  image_path
                            #print("FULL: ", full_image_path)
                            if os.path.exists(full_image_path):
                                os.remove(full_image_path)
                                #print("REMOVED: ", full_image_path)

                    attr_data.hodnota = new_image_url
                    attr_data.save()
                
                
        messages.success(request, "Zaznam bol aktualizovaný.")
        
        descr = request.POST.get('record_description')
        if descr != None:
            record.opis = descr
            record.save()
    
        comment = request.POST.get('comment')
        if comment:
            Zaznam_Komentar.objects.create(zaznam=record, user=request.user, komentar=comment)
            messages.success(request, 'Váš komentár bol pridaný.')
        

        # komentár ktorý nie je schválený adminom (povoleny_adminom=False), neprihlásený užívateľ (user=None)
        commentU = request.POST.get('commentU')
        if commentU:
            """  user = None"""
            Zaznam_Komentar.objects.create(zaznam=record, user=None, komentar=commentU, povoleny_adminom=False)
            messages.success(request, 'Váš komentár bol pridaný.')

        return redirect('user_record_detail', record_id=record_id, for_user=for_user)

    else:
        return redirect('user_record_detail', record_id=record_id, for_user=for_user)
    

""" Vymazanie komentára """
def remove_comment(request, comment_id, for_user):
    comment = get_object_or_404(Zaznam_Komentar, pk=comment_id)
    # komentár patrí danému užívateľovi
    if request.session.get('admin_view', False) or for_user or (request.user.is_authenticated and comment.user == request.user):
        comment.delete()
        messages.success(request, 'Komentár bol úspešne odstránený.')
    return redirect('user_record_detail', record_id=comment.zaznam.id, for_user=for_user)

""" Potvrdenie/schválenie komentára adminom aby sa zobrazoval """
def aprove_comment(request, comment_id, for_user):
    comment = get_object_or_404(Zaznam_Komentar, pk=comment_id)
    comment.povoleny_adminom = True
    comment.save()
    messages.success(request, 'Komentár schválený.')
    return redirect('user_record_detail', record_id=comment.zaznam.id, for_user=for_user)


""" Zobrazenie všetkých galérií, nie ich záznamov ale galérií """
def user_galeries(request):
    
    featured_galleries = Galeria.objects.order_by('-vytvoreny')#[:4]
    gallery_data = []
    for gallery in featured_galleries:
        # Získame príslušný formulár pre galériu
        formular = gallery.formular
        if formular:
            formular_nazov = formular.formular_nazov
            # Získame všetky atribúty formulára označené na zobrazenie v galérii
            attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)
            # Získame všetky položky údajov o atribútoch prepojené s vybranými atribútmi a formulárom galérie
            attributes_data = Formular_Atribut_Udaje.objects.filter(formular_atribut__in=attributes_to_display)
            # Filtrume položky s údajmi atribútov pre vzorec aktuálnej galérie
            record_attributes = attributes_data
            # Nájdite prvú položku s údajmi atribútu URL obrázka pre aktuálnu galériu
            image_url_attribute = record_attributes.filter(formular_atribut__atribut__typ='obrazok_url').first()
            # Získame hodnotu adresy URL obrázka, ak existuje
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
        
    # Stránkovanie údajov galérie
    page = request.GET.get('page')
    paginator = Paginator(gallery_data, 4)  # 3 karty v rade, 2 riadky na strane
    gallery_page = paginator.get_page(page)
    
    
    #galleries = Galeria.objects.all()
    return render(request, 'user_galery.html', {'gallery_data': gallery_data, 'gallery_page': gallery_page})

""" zobrazenie galérie, jej záznamov """
def user_galery_view(request, gallery_id):
    gallery = get_object_or_404(Galeria, id=gallery_id)
    formular = gallery.formular

    # Získame atribúty, ktoré sú označené na zobrazenie v galérii
    attributes_to_display = Formular_Atribut.objects.filter(formular=formular, zobrazit_v_galerii=True)

    # Získame všetky položky Formular_Atribut_Udaje prepojené s vybranými atribútmi
    attributes_data = Formular_Atribut_Udaje.objects.filter(formular_atribut__in=attributes_to_display)

    # Extrahovanie jedinečných ID záznamov z údajov atribútov
    unique_record_ids = set(attributes_data.values_list('zaznam_id', flat=True))

    # Príprava údajov pre každý jedinečný záznam
    gallery_data = []
    for record_id in unique_record_ids:
        record = Zaznam.objects.get(id=record_id)
        record_attributes = attributes_data.filter(zaznam_id=record_id)

        # Extrahume adresu URL obrázka, ak je k dispozícii
        obrazok_url = record_attributes.filter(formular_atribut__atribut__typ='obrazok_url').first()
        obrazok_url = obrazok_url.hodnota if obrazok_url else None

        # Skontrolume existujúce hlasovanie užívateľa
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
        
    # Stránkovanie údajov galérie
    page = request.GET.get('page')
    paginator = Paginator(gallery_data, 6)  # 3 karty v rade, 2 riadky na strane
    gallery_page = paginator.get_page(page)
        
    return render(request, 'user_galery_view.html', {
        'gallery': gallery,
        'gallery_data': gallery_data,
        'gallery_page': gallery_page
    })


""" Hlasovanie používatelov """
@require_POST
def vote(request, record_id, typ_hlasu):
    #print("------------------------Voting on record", record_id, "with", typ_hlasu)
    record = get_object_or_404(Zaznam, pk=record_id)
    user = request.user
    
    # Skontrolume, či užívateľ už o tomto zázname hlasoval
    existing_vote = Hlas.objects.filter(user=user, zaznam=record).first()

    # Aktualizume alebo vytvorte hlasovanie
    if existing_vote:
        if existing_vote.typ_hlasu != typ_hlasu:
            existing_vote.typ_hlasu = typ_hlasu
            existing_vote.save()
    else:
        Hlas.objects.create(user=user, zaznam=record, typ_hlasu=typ_hlasu)

    # Vráti aktualizované počty hlasov
    return JsonResponse({'thumb_up': Hlas.objects.filter(zaznam = record_id, typ_hlasu="up").count(), 'thumb_down': Hlas.objects.filter(zaznam = record_id, typ_hlasu="down").count()})
