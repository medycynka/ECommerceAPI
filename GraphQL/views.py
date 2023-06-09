from django.contrib.auth.mixins import LoginRequiredMixin

from graphene_django.views import GraphQLView

from API.mixins import AdminAndSellerOnlyMixin


class PrivateGraphQLView(AdminAndSellerOnlyMixin, GraphQLView):
    pass
