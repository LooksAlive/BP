from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('registration/', views.registration_view, name='registration'),
    
    path('admin_attributes/', views.admin_attributes, name='admin_attributes'),
    path('admin_create_attribute/', views.admin_create_attribute, name='admin_create_attribute'),
    path('admin_delete_attribute/<int:attribute_id>/', views.admin_delete_attribute, name='admin_delete_attribute'),
    path('admin_edit_attribute/<int:attribute_id>/', views.admin_edit_attribute, name='admin_edit_attribute'),


    path('admin_forms/', views.admin_forms, name='admin_forms'),
    path('admin_create_form/', views.admin_create_form, name='admin_create_form'),
    path('admin_create_form/<int:form_id>/', views.admin_create_form, name='admin_create_form'),
    #path('admin_edit_form/<int:form_id>/', views.admin_edit_form, name='admin_edit_form'),
    path('admin_delete_form/<int:form_id>/', views.admin_delete_form, name='admin_delete_form'),


    path('admin_galeries/', views.admin_galeries, name='admin_galeries'),
    path('admin_create_galery/', views.admin_create_galery, name='admin_create_galery'),
    path('admin_create_galery/<int:gallery_id>/', views.admin_create_galery, name='admin_create_galery'),
    path('admin_delete_galery/<int:gallery_id>/', views.admin_delete_galery, name='admin_delete_galery'),


    path('admin_users/', views.admin_users, name='admin_users'),
    path('admin_create_user/', views.admin_create_user, name='admin_create_user'),
    path('admin_delete_user/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    path('admin_edit_user/<int:user_id>/', views.admin_edit_user, name='admin_edit_user'),


    
    # input new cat for a specific form
    path('user_forms/', views.user_forms, name='user_forms'),
    path('user_forms_view/<int:form_id>/', views.user_forms_view, name='user_forms_view'),
    path('user_forms_record_add/<int:form_id>/', views.user_forms_record_add, name='user_forms_record_add'),
    
    
    path('user_collection_formular/', views.user_collection_formular, name='user_collection_formular'),
    
    path('user_records/', views.user_records, name='user_records'),
    path('user_record_delete/<int:record_id>/', views.user_record_delete, name='user_record_delete'),
    path('user_record_detail/<int:record_id>/<int:for_user>/', views.user_record_detail, name='user_record_detail'),
    path('user_record_update/<int:record_id>/<int:for_user>/', views.user_record_update, name='user_record_update'),
    
    path('remove_comment/<int:comment_id>/<int:for_user>/', views.remove_comment, name='remove_comment'),
    
    
    
    # gallery view    
    path('user_galeries/', views.user_galeries, name='user_galeries'),
    path('user_galery_view/<int:gallery_id>/', views.user_galery_view, name='user_galery_view'),
    
    
    path('vote/<int:record_id>/<str:vote_type>/', views.vote, name='vote'),

]
