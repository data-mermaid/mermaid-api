from django.core import urlresolvers
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

from .base import BaseAdmin
from ..models.base import *
from ..models.mermaid import *


def get_crs_with_attrib(query, attrib_val):
    cr_filter = {query: [attrib_val]}
    return CollectRecord.objects.filter(**cr_filter)


def get_sus_with_attrib(model_su, query, attrib_id):
    su_filter = {query: attrib_id}
    return model_su.objects.filter(**su_filter).distinct()


class AttributeAdmin(BaseAdmin):

    # For any (protected) attribute assigned to mermaid observations, override
    # default "can't delete" admin behavior with form allowing user to
    # reassign existing observations using this attribute to use another attribute.
    # Requires these definitions on the inherited class:
    # model_attrib =
    # attrib = ''
    # protocols = [
    #     {'model_su': ,
    #      'model_obs': ,
    #      'cr_obs': '',
    #      'cr_sampleunit': '',
    #      'su_obs': '',
    #      'su_sampleunit': ''},
    # ]
    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}

        if not extra_context.get('protected_descendants'):
            # dropdown of other attributes to assign to existing observations before deleting
            other_objs = self.model_attrib.objects.exclude(id=object_id).order_by('name')
            if other_objs.count() > 0:
                extra_context.update({'other_objs': other_objs})

            protocol_crs = CollectRecord.objects.none()
            atleast_one_su = False
            collect_records = []
            sample_units = []
            for p in self.protocols:

                # Collect records that use this attribute, about to be deleted
                crs = get_crs_with_attrib('data__{}__contains'.format(p.get('cr_obs')), {self.attrib: object_id})
                if crs.count() > 0:
                    if not protocol_crs:
                        protocol_crs = crs
                    else:
                        protocol_crs = protocol_crs.union(crs)

                    for cr in crs:
                        project_id = cr.project.id
                        admin_url = reverse(
                            'admin:{}_collectrecord_change'.format(p.get('model_su')._meta.app_label),
                            args=(cr.pk,))
                        crstr = format_html('<a href="{}">{}</a>', admin_url, cr)
                        if project_id is not None:
                            app_url = '{}/#/projects/{}/collect/{}/{}'.format(settings.DEFAULT_DOMAIN_COLLECT,
                                                                              project_id, p.get('cr_sampleunit'), cr.pk)
                            crstr = format_html('<a href="{}">{}</a> [<a href="{}">{}</a>]', admin_url, cr, app_url,
                                                app_url)
                        collect_records.append(crstr)

                # Sample units that use this attribute, about to be deleted
                sus = get_sus_with_attrib(p.get('model_su'), '{}__{}'.format(p.get('su_obs'), self.attrib), object_id)
                if sus.count() > 0:
                    atleast_one_su = True
                    for su in sus:
                        project_id = su.transect.sample_event.site.project.pk
                        admin_url = reverse(
                            'admin:{}_{}_change'.format(p.get('model_su')._meta.app_label,
                                                        p.get('model_su')._meta.model_name),
                            args=(su.pk,))
                        app_url = '{}/#/projects/{}/{}/{}'.format(settings.DEFAULT_DOMAIN_COLLECT,
                                                                  project_id, p.get('su_sampleunit'), su.pk)
                        sustr = format_html('<a href="{}">{}</a> [<a href="{}">{}</a>]', admin_url, su, app_url,
                                            app_url)
                        sample_units.append(sustr)

            if collect_records:
                extra_context.update({'collect_records': collect_records})
            if sample_units:
                extra_context.update({'sample_units': sample_units})

            # process reassignment, then hand back to django for deletion
            if request.method == 'POST':
                replacement_obj = request.POST.get('replacement_obj')
                if (replacement_obj is None or replacement_obj == '') and atleast_one_su:
                    self.message_user(request,
                                      'To delete, you must select a replacement object to assign to all items '
                                      'using this object.',
                                      level=messages.ERROR)
                    return super(AttributeAdmin, self).delete_view(request, object_id, extra_context)

                for cr in protocol_crs:
                    for p in self.protocols:
                        observations = cr.data.get(p.get('cr_obs')) or []
                        for obs in observations:
                            if self.attrib in obs and obs[self.attrib] == object_id:
                                obs[self.attrib] = replacement_obj
                    cr.save()

                for p in self.protocols:
                    p.get('model_obs').objects.filter(
                        **{self.attrib: object_id}
                    ).update(
                        **{self.attrib: replacement_obj}
                    )

        return super(AttributeAdmin, self).delete_view(request, object_id, extra_context)


class FishAttributeAdmin(AttributeAdmin):
    model_attrib = FishAttributeView
    attrib = 'fish_attribute'
    protocols = [
        {'model_su': BeltFish,
         'model_obs': ObsBeltFish,
         'cr_obs': 'obs_belt_fishes',
         'cr_sampleunit': 'fishbelt',
         'su_obs': 'beltfish_observations',
         'su_sampleunit': 'fishbelttransectmethods'},
    ]

    # before using AttributeAdmin reassignment logic, check to see if any descendants are used by observations
    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        protected_descendants = set()

        if self.model == FishGenus or self.model == FishFamily:
            query = 'genus_id'
            if self.model == FishFamily:
                query = 'genus__family_id'

            species = FishSpecies.objects.filter(**{query: object_id})
            for s in species:
                cqry = 'data__{}__contains'.format(self.protocols[0].get('cr_obs'))
                crs = get_crs_with_attrib(cqry, {self.attrib: str(s.pk)})
                sqry = '{}__{}'.format(self.protocols[0].get('su_obs'), self.attrib)
                sus = get_sus_with_attrib(self.protocols[0].get('model_su'), sqry, s.pk)
                if crs.count() > 0 or sus.count() > 0:
                    admin_url = reverse('admin:{}_fishspecies_change'.format(FishSpecies._meta.app_label), args=(s.pk,))
                    sstr = format_html('<a href="{}">{}</a>', admin_url, s)
                    protected_descendants.add(sstr)

            extra_context.update({'protected_descendants': protected_descendants})

        return super(FishAttributeAdmin, self).delete_view(request, object_id, extra_context)


class SiteInline(admin.StackedInline):
    model = Site
    extra = 0


@admin.register(Project)
class ProjectAdmin(BaseAdmin):
    list_display = ('name', 'status', 'admin_list', 'country_list', 'tag_list')
    exportable_fields = ('name', 'status', 'admin_list', 'country_list', 'tag_list',
                         'data_policy_beltfish', 'data_policy_benthiclit',
                         'data_policy_benthicpit', 'data_policy_habitatcomplexity',
                         'data_policy_bleachingqc', 'notes')
    inlines = [SiteInline, ]
    search_fields = ['name', 'pk', ]
    list_filter = ('status',)

    def admin_list(self, obj):
        pps = ProjectProfile.objects.filter(project=obj, role=ProjectProfile.ADMIN).select_related('profile')
        return ", ".join([u'{} <{}>'.format(p.profile.full_name, p.profile.email) for p in pps])

    def country_list(self, obj):
        sites = Site.objects.filter(project=obj).select_related('country')
        countries = []
        for s in sites:
            if s.country not in countries:
                countries.append(s.country)
        return ", ".join([c.name for c in countries])

    def tag_list(self, obj):
        return ", ".join(u"{}".format(t.name) for t in obj.tags.all())
    tag_list.short_description = _(u"organizations")


@admin.register(ProjectProfile)
class ProjectProfileAdmin(BaseAdmin):
    list_display = ('project', 'profile', 'role')
    search_fields = ['project__name', 'profile__first_name', 'profile__last_name', 'profile__email', ]
    list_filter = ('role',)


@admin.register(Region)
class RegionAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(Site)
class SiteAdmin(BaseAdmin):
    list_display = ('country', 'name', 'reef_type', 'reef_zone', 'exposure')
    list_display_links = ('name',)
    search_fields = ['country__name', 'name', ]
    list_filter = ('reef_type', 'reef_zone', 'exposure',)


@admin.register(BeltTransectWidth)
class BeltTransectWidthAdmin(BaseAdmin):
    list_display = ('val',)


@admin.register(Country)
class CountryAdmin(BaseAdmin):
    list_display = ('iso', 'name',)


@admin.register(Current)
class CurrentAdmin(BaseAdmin):
    list_display = ('val', 'name',)


@admin.register(FishSizeBin)
class FishSizeBinAdmin(BaseAdmin):
    list_display = ('val',)


@admin.register(FishSize)
class FishSizenAdmin(BaseAdmin):
    list_display = ('fish_bin_size', 'name', 'val',)


@admin.register(GrowthForm)
class GrowthFormAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(HabitatComplexityScore)
class HabitatComplexityScoreAdmin(BaseAdmin):
    list_display = ('val', 'name',)


@admin.register(ReefExposure)
class ReefExposureAdmin(BaseAdmin):
    list_display = ('val', 'name',)


@admin.register(ReefSlope)
class ReefSlopeAdmin(BaseAdmin):
    list_display = ('val', 'name',)


@admin.register(ReefType)
class ReefTypeAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(ReefZone)
class ReefZoneAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(RelativeDepth)
class RelativeDepthAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(Tide)
class TideAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(Visibility)
class VisibilityAdmin(BaseAdmin):
    list_display = ('val', 'name',)


@admin.register(Management)
class ManagementAdmin(BaseAdmin):
    list_display = ('name', 'name_secondary', 'project', 'est_year')
    readonly_fields = ('area',)
    search_fields = ['name', 'name_secondary', 'project__name', 'est_year']


@admin.register(ManagementCompliance)
class ManagementComplianceAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(ManagementParty)
class ManagementPartyAdmin(BaseAdmin):
    list_display = ('name',)


# TODO: make inline display map when creating (not just editing). Ideally using OSMGeoAdmin.
# https://djangosnippets.org/snippets/2232/
class MPAZoneInline(admin.StackedInline):
    model = MPAZone
    readonly_fields = ('area',)
    extra = 0


@admin.register(MPA)
class MPAAdmin(BaseAdmin):
    list_display = ('name', 'wdpa_link', 'est_year')
    readonly_fields = ('area',)
    inlines = (MPAZoneInline,)

    def wdpa_link(self, obj):
        domain = 'http://www.protectedplanet.net/'
        return format_html('<a href="{}{}" target="_blank">{}</a>',
                           domain,
                           obj.wdpa_id,
                           obj.wdpa_id)

    wdpa_link.allow_tags = True
    wdpa_link.short_description = _(u'WDPA id')


@admin.register(BenthicTransect)
class BenthicTransectAdmin(BaseAdmin):
    list_display = ('name', 'len_surveyed')
    search_fields = ['sample_event__site__name',
                     'sample_event__sample_date', ]

    def name(self, obj):
        return obj.__unicode__()

    name.admin_order_field = 'sample_event'


@admin.register(FishBeltTransect)
class FishTransectAdmin(BaseAdmin):
    list_display = ('name', 'len_surveyed', 'width')
    search_fields = ['sample_event__site__name',
                     'sample_event__sample_date', ]
    readonly_fields = ('cr_id',)

    def name(self, obj):
        return obj.__unicode__()

    name.admin_order_field = 'sample_event'

    def cr_id(self, obj):
        return obj.transect.collect_record_id

    cr_id.short_description = 'CollectRecord ID'


@admin.register(QuadratCollection)
class QuadratCollectionAdmin(BaseAdmin):
    list_display = ('name', 'quadrat_size')
    search_fields = ['sample_event__site__name',
                     'sample_event__sample_date', ]

    def name(self, obj):
        return obj.__unicode__()

    name.admin_order_field = 'sample_event'


@admin.register(SampleEvent)
class SampleEventAdmin(BaseAdmin):
    list_display = ('site', 'sample_date', 'depth')
    list_display_links = ('site', 'sample_date')
    search_fields = ['site__name', 'sample_date', ]


@admin.register(BenthicLifeHistory)
class BenthicLifeHistoryAdmin(BaseAdmin):
    list_display = ('name',)


class BenthicAttributeInline(admin.StackedInline):
    model = BenthicAttribute
    extra = 0


@admin.register(BenthicAttribute)
class BenthicAttributeAdmin(AttributeAdmin):
    model_attrib = BenthicAttribute
    attrib = 'attribute'
    protocols = [
        {'model_su': BenthicPIT,
         'model_obs': ObsBenthicPIT,
         'cr_obs': 'obs_benthic_pits',
         'cr_sampleunit': 'benthicpit',
         'su_obs': 'obsbenthicpit_set',
         'su_sampleunit': 'benthicpittransectmethods'},
        {'model_su': BenthicLIT,
         'model_obs': ObsBenthicLIT,
         'cr_obs': 'obs_benthic_lits',
         'cr_sampleunit': 'benthiclit',
         'su_obs': 'obsbenthiclit_set',
         'su_sampleunit': 'benthiclittransectmethods'},
    ]

    # before using AttributeAdmin reassignment logic, check to see if any descendants are used by observations
    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        protected_descendants = set()
        obj = self.get_object(request, object_id)
        if obj.descendants:
            for d in obj.descendants:
                for p in self.protocols:
                    cqry = 'data__{}__contains'.format(p.get('cr_obs'))
                    crs = get_crs_with_attrib(cqry, {self.attrib: str(d.pk)})
                    sqry = '{}__{}'.format(p.get('su_obs'), self.attrib)
                    sus = get_sus_with_attrib(p.get('model_su'), sqry, d.pk)
                    if crs.count() > 0 or sus.count() > 0:
                        admin_url = reverse(
                            'admin:{}_benthicattribute_change'.format(self.model_attrib._meta.app_label),
                            args=(d.pk,))
                        sstr = format_html('<a href="{}">{}</a>', admin_url, d)
                        protected_descendants.add(sstr)

            extra_context.update({'protected_descendants': protected_descendants})

        return super(BenthicAttributeAdmin, self).delete_view(request, object_id, extra_context)

    list_display = ('name', 'fk_link', 'life_history', 'region_list')
    exportable_fields = ('name', 'parent', 'life_history', 'region_list')
    inlines = [
        BenthicAttributeInline,
    ]
    search_fields = ['name', ]
    list_filter = ('status', 'life_history')

    def fk_link(self, obj):
        if obj.parent:
            link = urlresolvers.reverse("admin:api_benthicattribute_change", args=[obj.parent.pk])
            return u'<a href="%s">%s</a>' % (link, obj.parent.name)
        else:
            return ''

    fk_link.allow_tags = True
    fk_link.admin_order_field = 'parent'
    fk_link.short_description = _(u'Parent')

    def region_list(self, obj):
        return ",".join([r.name for r in obj.regions.all()])

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ('child_life_histories', 'child_regions',)
        return ()

    def child_life_histories(self, obj):
        proportions = {}
        # get all non-null life histories of descendants
        life_histories = [ba.life_history for ba in obj.descendants if ba.life_history]
        total = float(len(life_histories))
        for lh in life_histories:
            if lh.name not in proportions:
                proportions[lh.name] = 0
            proportions[lh.name] += 1 / total

        return proportions

    def child_regions(self, obj):
        proportions = {}
        counts = {}
        total = 0
        # get all m2m sets of regions for each descendant, then add each region to overall count
        region_sets = [ba.regions.all() for ba in obj.descendants]
        for rs in region_sets:
            for r in rs:
                if r.name not in counts:
                    counts[r.name] = 0
                counts[r.name] += 1
                total += 1
        for name in counts:
            proportions[name] = counts[name] / float(total)

        return proportions


class ObserverInline(admin.StackedInline):
    model = Observer
    extra = 0


class ObsBenthicLITInline(admin.StackedInline):
    model = ObsBenthicLIT
    extra = 0


@admin.register(BenthicLIT)
class BenthicLITAdmin(BaseAdmin):
    list_display = ('name',)
    inlines = (ObserverInline, ObsBenthicLITInline,)
    search_fields = ['transect__sample_event__site__name',
                     'transect__sample_event__sample_date', ]
    readonly_fields = ('cr_id',)

    def name(self, obj):
        return obj.__unicode__()

    name.admin_order_field = 'transect'

    def cr_id(self, obj):
        return obj.transect.collect_record_id

    cr_id.short_description = 'CollectRecord ID'


class ObsBenthicPITInline(admin.StackedInline):
    model = ObsBenthicPIT
    extra = 0


@admin.register(BenthicPIT)
class BenthicPITAdmin(BaseAdmin):
    list_display = ('name',)
    inlines = (ObserverInline, ObsBenthicPITInline,)
    search_fields = ['transect__sample_event__site__name',
                     'transect__sample_event__sample_date', ]
    readonly_fields = ('cr_id',)

    def name(self, obj):
        return obj.__unicode__()

    name.admin_order_field = 'transect'

    def cr_id(self, obj):
        return obj.transect.collect_record_id

    cr_id.short_description = 'CollectRecord ID'

    class Media:
        js = (
            'js/admin/admin.js',  # app static folder
        )


class ObsHabitatComplexityInline(admin.StackedInline):
    model = ObsHabitatComplexity
    extra = 0


@admin.register(HabitatComplexity)
class HabitatComplexityAdmin(BaseAdmin):
    list_display = ('name',)
    inlines = (ObserverInline, ObsHabitatComplexityInline,)
    search_fields = ['transect__sample_event__site__name',
                     'transect__sample_event__sample_date', ]
    readonly_fields = ('cr_id',)

    def name(self, obj):
        return obj.__unicode__()

    name.admin_order_field = 'transect'

    def cr_id(self, obj):
        return obj.transect.collect_record_id
    cr_id.short_description = 'CollectRecord ID'

    class Media:
        js = (
            'js/admin/admin.js',  # app static folder
        )


class ObsColoniesBleachedInline(admin.StackedInline):
    model = ObsColoniesBleached
    extra = 0


class ObsQuadratBenthicPercentInline(admin.StackedInline):
    model = ObsQuadratBenthicPercent
    extra = 0


@admin.register(BleachingQuadratCollection)
class BleachingQuadratCollectionAdmin(BaseAdmin):
    list_display = ('name',)
    inlines = (ObsColoniesBleachedInline, ObsQuadratBenthicPercentInline,)
    search_fields = ['quadrat__sample_event__site__name',
                     'quadrat__sample_event__sample_date', ]
    readonly_fields = ('cr_id',)

    def name(self, obj):
        return obj.__unicode__()

    def cr_id(self, obj):
        return obj.transect.collect_record_id

    cr_id.short_description = 'CollectRecord ID'

    name.admin_order_field = 'quadrat'

    class Media:
        js = (
            'js/admin/admin.js',  # app static folder
        )


@admin.register(FishGroupFunction)
class FishGroupFunctionAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(FishGroupTrophic)
class FishGroupTrophicAdmin(BaseAdmin):
    list_display = ('name',)


@admin.register(FishGroupSize)
class FishGroupSizeAdmin(BaseAdmin):
    list_display = ('name',)


class FishGenusInline(admin.StackedInline):
    model = FishGenus
    fk_name = 'family'
    extra = 1


@admin.register(FishFamily)
class FishFamilyAdmin(FishAttributeAdmin):
    list_display = ('name',)
    inlines = (FishGenusInline,)
    search_fields = ['name', ]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ('biomass_constant_a', 'biomass_constant_b',)
        return ()


class FishSpeciesInline(admin.StackedInline):
    model = FishSpecies
    fk_name = 'genus'
    extra = 1


@admin.register(FishGenus)
class FishGenusAdmin(FishAttributeAdmin):
    list_display = ('name', 'fk_link')
    readonly_fields = ('biomass_constant_a', 'biomass_constant_b',)
    inlines = (FishSpeciesInline,)
    search_fields = ['name', 'family__name', ]
    exportable_fields = ('name', 'genus')

    def fk_link(self, obj):
        link = urlresolvers.reverse("admin:api_fishfamily_change", args=[obj.family.pk])
        return u'<a href="%s">%s</a>' % (link, obj.family.name)

    fk_link.allow_tags = True
    fk_link.admin_order_field = 'family'
    fk_link.short_description = _(u'Family')


@admin.register(FishSpecies)
class FishSpeciesAdmin(FishAttributeAdmin):
    list_display = ('name', 'fk_link', 'biomass_constant_a', 'biomass_constant_b', 'biomass_constant_c',
                    'max_length', 'trophic_level', 'vulnerability')
    search_fields = ['name', 'genus__name', ]
    list_filter = ('status', 'group_size', 'trophic_group', 'functional_group')
    exportable_fields = ('name', 'genus', 'biomass_constant_a', 'biomass_constant_b', 'biomass_constant_c',
                         'max_length', 'trophic_level', 'vulnerability')

    def fk_link(self, obj):
        link = urlresolvers.reverse("admin:api_fishgenus_change", args=[obj.genus.pk])
        return u'<a href="%s">%s</a>' % (link, obj.genus.name)

    fk_link.allow_tags = True
    fk_link.admin_order_field = 'genus'
    fk_link.short_description = _(u'Genus')

    def region_list(self, obj):
        return ",".join([r.name for r in obj.regions.all()])


class ObsTransectBeltFishInline(admin.StackedInline):
    model = ObsBeltFish
    fk_name = 'beltfish'
    extra = 0


@admin.register(BeltFish)
class BeltFishAdmin(BaseAdmin):
    list_display = ('name',)
    inlines = (ObserverInline, ObsTransectBeltFishInline,)
    search_fields = ['transect__sample_event__site__name',
                     'transect__sample_event__sample_date', ]

    def name(self, obj):
        return obj.__unicode__()

    name.admin_order_field = 'transect'


@admin.register(Observer)
class ObserverAdmin(BaseAdmin):
    list_display = ('profile', 'transectmethod')
    search_fields = ['profile__first_name', 'profile__last_name', 'profile__email', ]


@admin.register(CollectRecord)
class CollectRecordAdmin(BaseAdmin):
    list_display = ('id', 'protocol', 'profile', 'created_by')
    search_fields = ['id', 'project__name', 'profile__first_name', 'profile__last_name', 'profile__email', ]

    def protocol(self, obj):
        data = obj.data or dict()
        return data.get('protocol')


@admin.register(ArchivedRecord)
class ArchivedRecordAdmin(BaseAdmin):
    list_display = ('app_label', 'model', 'record_pk', 'project_pk',)
    list_filter = ('model', 'project_pk',)


@admin.register(Tag)
class TagAdmin(BaseAdmin):
    list_display = ('name', 'status', 'updated_by')

    def delete_view(self, request, object_id, extra_context=None):
        obj = Tag.objects.get(pk=object_id)
        extra_context = extra_context or {}

        # dropdown of other tags to assign to existing projects before deleting
        other_objs = Tag.objects.exclude(id=object_id).order_by('name')
        if other_objs.count() > 0:
            extra_context.update({'other_objs': other_objs})

        # Projects that use this tag
        projects = []
        ps = Project.objects.filter(tags=obj)
        for p in ps:
            admin_url = reverse(
                'admin:{}_{}_change'.format(Project._meta.app_label, Project._meta.model_name),
                args=(p.pk,))
            app_url = '{}/#/projects/{}/details'.format(settings.DEFAULT_DOMAIN_COLLECT, p.pk)
            pstr = format_html('<a href="{}">{}</a> [<a href="{}" target="_blank">{}</a>]', admin_url, p, app_url,
                               app_url)
            projects.append(pstr)

        if projects:
            extra_context.update({'projects': projects})

        # process reassignment, then hand back to django for deletion
        if request.method == 'POST':
            replacement_obj = request.POST.get('replacement_obj')
            if replacement_obj is not None:
                for p in ps:
                    p.tags.remove(obj)
                    p.tags.add(replacement_obj)

        return super(TagAdmin, self).delete_view(request, object_id, extra_context)
