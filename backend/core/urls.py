from django.urls import path
from . import views as v
from . import landing_api as la

urlpatterns = [
    path("admin/members/<str:code>/roles/", v.roles),
    path("members/<str:code>/", v.member_profile), path("rankings/", v.rankings),
    path("session/", v.session), path("login/", v.sign_in), path("logout/", v.sign_out),
    path("password/", v.change_password), path("state/", v.state),
    path("growth/", v.growth), path("posts/", v.posts), path("posts/<str:pid>/", v.delete_post),
    path("posts/<str:pid>/votes/<str:kind>/", v.vote),
    path("posts/<str:pid>/comments/", v.comments), path("comments/<str:cid>/like/", v.comment_like),
    path("follows/<str:code>/", v.follow), path("profile/status/", v.profile_status),
    path("profile/avatar/", v.avatar), path("files/upload/<str:purpose>/", v.upload),
    path("files/<str:fid>/", v.download), path("messages/", v.send_message),
    path("messages/read/", v.read_messages), path("grades/<str:kind>/", v.grade),
    path("notices/read/", v.notices_read), path("oversight/", v.oversight),
    path("assistant/chat/", v.assistant_chat), path("landing/", v.landing),
    path("forms/", v.forms), path("forms/<str:fid>/answers/", v.form_answers),
    path("admin/members/", v.register), path("admin/members/<str:code>/suspend/", v.suspend),
    path("admin/reports/", v.weekly), path("health/", v.health),
    # New landing cards & member titles
    path("landing/cards/", la.landing_cards),
    path("landing/card/", la.manage_landing_card),
    path("landing/titles/", la.landing_titles),
    path("landing/titles/add/", la.add_title),
    path("landing/titles/<str:tid>/", la.remove_title),
]
