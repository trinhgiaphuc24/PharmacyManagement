from rest_framework.pagination import PageNumberPagination
from rest_framework import pagination
from rest_framework.response import Response


class MedicinePagination(PageNumberPagination):
    page_size = 12

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })
