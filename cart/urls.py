from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.CartView.as_view(), name="detail"),
    path("add/<int:product_id>/", views.AddToCartView.as_view(), name="add"),
    path("lines/<int:product_id>/", views.CartLineView.as_view(), name="line"),
]
