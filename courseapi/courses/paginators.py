from rest_framework import pagination


class ItemPagination(pagination.PageNumberPagination):
    page_size = 10