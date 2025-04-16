from django.urls import path

from lost_ark import views

app_name = 'lost_ark'

urlpatterns = [
    path('', views.home, name='home'),

    # --------------CHARACTER VIEWS----------------------------#

    path('characters/', views.CharacterListView.as_view(), name='character_list'),
    path('characters/add/', views.CharacterCreateView.as_view(), name='character_create'),
    path('characters/<int:pk>/edit/', views.CharacterUpdateView.as_view(), name='character_update'),
    path('characters/<int:pk>/delete/', views.CharacterDeleteView.as_view(), name='character_delete'),

    # --------------WEEKLY CONTENT VIEWS------------------------#

    path('weekly_content/', views.WeeklyContentTableView.as_view(), name='weekly_content_table'),
    path('update_weekly_status/', views.update_weekly_status.as_view(), name='update_weekly_status'),
    # This needs to be as_view() for CBV
]
