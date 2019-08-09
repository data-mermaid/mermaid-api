import django_filters
from rest_framework import serializers, exceptions
from .base import BaseAPIFilterSet, BaseApiViewSet, BaseAPISerializer
from ..models import Profile
from django.contrib.auth import get_user_model
from ..permissions import *
from rest_condition import Or


class ProfileSerializer(BaseAPISerializer):
    class Meta:
        model = Profile
        fields = [
            'id',
            'created_on',
            'updated_on',
            'updated_by',
        ]


class FullProfileSerializer(BaseAPISerializer):
    user = serializers.ReadOnlyField()
    password = serializers.CharField(source='user.password', write_only=True, required=False)

    # don't display (nonserializable) user or (secure/hashed) password
    def to_representation(self, obj):
        ubpk = None
        if obj.updated_by:
            ubpk = obj.updated_by.pk

        return {'id': obj.id,
                'first_name': obj.first_name,
                'last_name': obj.last_name,
                'updated_by': ubpk,
                'created_on': obj.created_on,
                'updated_on': obj.updated_on,
                'email': obj.email
                }

    def create(self, validated_data):
        raise exceptions.MethodNotAllowed('POST')
        # user_data = validated_data.pop('user', None)
        # # password is not required generally, but is required on create
        # if 'password' not in user_data:
        #     raise exceptions.ValidationError('You must supply a password.')

        # user = get_user_model().objects.create_user(username=user_data['username'],
        #                                             email=user_data['email'],
        #                                             password=user_data['password'])
        # validated_data['user'] = user
        # return super(FullProfileSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        raise exceptions.MethodNotAllowed('UPDATE')
        # user_data = validated_data.pop('user', None)
        # user = get_user_model().objects.get(profile=instance)
        # # user.username = user_data.get('username', instance.username)
        # # user.email = user_data.get('email', instance.email)
        # if 'password' in user_data:
        #     user.set_password(user_data['password'])
        # user.save()
        # super(FullProfileSerializer, self).update(instance, validated_data)
        # return self.Meta.model.objects.get(id=instance.id)  # ensure PATCH returns refreshed data

    class Meta:
        model = Profile
        fields = [
            'id',
            'password',
            'email',
            'first_name',
            'last_name',
            'created_on',
            'updated_on',
            'updated_by',
        ]


class ProfileFilterSet(BaseAPIFilterSet):
    organization = django_filters.UUIDFilter(field_name='projects__project__tagged_items__tag_id', distinct=True,
                                             label='Associated with organization associated with at least one project '
                                                   'associated with profile')
    project = django_filters.UUIDFilter(field_name='projects__project', distinct=True,
                                        label='Associated with project')

    class Meta:
        model = Profile
        fields = ['organization', 'project', 'email']


class UnauthenticatedProfileCreatePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return False
        else:
            return request.method == 'POST'


class AuthenticatedProfilePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return request.method != 'POST'
        return False


class ProfileViewSet(BaseApiViewSet):
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = [
        Or(UnauthenticatedReadOnlyPermission,
           UnauthenticatedProfileCreatePermission,
           AuthenticatedProfilePermission
           )
    ]
    filter_class = ProfileFilterSet
    search_fields = ['^email', '^first_name', '^last_name', ]

    def perform_update(self, serializer):
        raise exceptions.MethodNotAllowed('PUT')
        # if self.get_object() != self.request.user.profile:
        #     raise PermissionDenied('You must own this object in order to modify it.')
        # serializer.save()

    def perform_destroy(self, instance):
        raise exceptions.MethodNotAllowed('DELETE')
        # if instance != self.request.user.profile:
        #     raise PermissionDenied('You must own this object in order to delete it.')
        # instance.delete()

    def get_serializer_class(self):
        serializer_class = self.serializer_class

        if self.request.method == 'POST':
            serializer_class = FullProfileSerializer
        elif self.request.method in ['GET', 'PUT', 'PATCH']:
            try:
                obj = self.get_object()  # retrieve, not list
                if obj == self.request.user.profile:
                    serializer_class = FullProfileSerializer
            except:
                pass

        return serializer_class
