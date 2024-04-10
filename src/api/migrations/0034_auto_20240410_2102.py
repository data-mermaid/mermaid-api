# Generated by Django 3.2.20 on 2024-04-10 21:02

import api.models.gfcr
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0033_alter_fishattributeview_table'),
    ]

    operations = [
        migrations.CreateModel(
            name='GFCRFinanceSolution',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('sector', models.CharField(choices=[('clean_energy', 'Clean energy'), ('coastal_agriculture', 'Coastal agriculture'), ('coastal_forestry', 'Coastal forestry'), ('coastal_infrastructure', 'Coastal infrastructure'), ('coral_ecosystem Restoration', 'Coral ecosystem restoration'), ('ecotourism', 'Ecotourism'), ('green_shipping_and_cruise_ships', 'Green shipping and cruise ships'), ('invasive_species Management', 'Invasive species management'), ('marine_protected_areas', 'Marine protected areas'), ('other_land_based_pollutants_management', 'Other land-based pollutants management'), ('plastic_waste_management', 'Plastic waste management'), ('sewage_and_waste_water_treatment', 'Sewage and waste-water treatment'), ('sustainable_fisheries', 'Sustainable fisheries'), ('sustainable_mariculture_aquaculture', 'Sustainable mariculture/aquaculture')], max_length=50)),
                ('used_and_incubator', models.BooleanField(default=False)),
                ('local_enterprise', models.BooleanField(default=False)),
                ('sustainable_finance_mechanisms', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('biodiversity_offsets', 'Biodiversity offsets'), ('blue_bonds', 'Blue bonds'), ('blue_carbon', 'Blue carbon'), ('conservation_trust_funds', 'Conservation trust funds'), ('conservation_trust_funds', 'Conservation trust funds'), ('debt_conversion', 'Debt conversion'), ('incubator_tecnical_assistance', 'Incubator / Technical assistance'), ('insurance_products', 'Insurance products'), ('mpa_entry_fees', 'MPA entry fees'), ('pay_for_success', 'Pay for success'), ('sustainable_livelihood_mech', 'Sustainable livelihood mechanisms')], max_length=50), default=list, size=None, validators=[api.models.gfcr.validate_unique_elements])),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gfcrfinancesolution_created_by', to='api.profile')),
            ],
            options={
                'db_table': 'gfcr_finance_solution',
                'ordering': ['created_on'],
            },
        ),
        migrations.CreateModel(
            name='GFCRRevenue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('revenue_type', models.CharField(choices=[('biodiversity_offsets', 'Biodiversity offsets'), ('blue_bonds', 'Blue bonds'), ('business_incubation_and_investment', 'Business incubation and investment'), ('carbon_credits_environmental_services', 'Carbon credits / environmental services'), ('conservation_trust_funds', 'Conservation trust funds'), ('debt_conversion', 'Debt conversion'), ('ecotourism', 'Ecotourism'), ('fees_and_payments', 'Fees and payments'), ('green_tax', 'Green tax'), ('insurance_products', 'Insurance products'), ('interest_investment_returns', 'Interest / investment returns'), ('marine_resources_sales', 'Marine resources sales'), ('misc_revenue_streams', 'Misc. revenue streams'), ('sustainable_livelihood_mechanisms', 'Sustainable livelihood mechanisms'), ('water_tariff', 'Water tariff')], max_length=50)),
                ('sustainable_revenue_stream', models.BooleanField(default=False)),
                ('annual_revenue', models.DecimalField(decimal_places=2, max_digits=11, verbose_name='Annual Revenue in USD')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gfcrrevenue_created_by', to='api.profile')),
                ('finance_solution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.gfcrfinancesolution')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gfcrrevenue_updated_by', to='api.profile')),
            ],
            options={
                'db_table': 'gfcr_revenue',
                'ordering': ['created_on'],
            },
        ),
        migrations.CreateModel(
            name='GFCRInvestmentSource',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('investment_source', models.CharField(choices=[('gfcr', 'GFCR'), ('philanthropy', 'Philanthropy'), ('private', 'Private'), ('public', 'Public')], max_length=50)),
                ('investment_type', models.CharField(choices=[('bond', 'Bond'), ('commercial_loan', 'Commercial loan'), ('concessional_loan', 'Concessional loan'), ('equity', 'Equity'), ('financial_guarantee', 'Financial guarantee'), ('grant', 'Grant'), ('public_budget', 'Public budget'), ('technical assistance', 'Technical assistance')], max_length=50)),
                ('investment_amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Investment amount in USD')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gfcrinvestmentsource_created_by', to='api.profile')),
                ('finance_solution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.gfcrfinancesolution')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gfcrinvestmentsource_updated_by', to='api.profile')),
            ],
            options={
                'db_table': 'gfcr_investment_source',
                'ordering': ['created_on'],
            },
        ),
        migrations.CreateModel(
            name='GFCRIndicatorSet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=100)),
                ('report_date', models.DateField()),
                ('indicator_set_type', models.CharField(choices=[('actual', 'Actual'), ('target', 'Target')], max_length=50)),
                ('f1_1', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Total area of coral reefs in GFCR programming (sq.km)')),
                ('f2_1a', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Area of MPAs and OECMs (as aligned to GBF Target 3) [coralreef] (sq.km)')),
                ('f2_1b', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Area of MPAs and OECMs (as aligned to GBF Target 3) [total] (sq.km)')),
                ('f2_2a', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Area of locally managed areas / co-managed areas [coralreef] (sq.km)')),
                ('f2_2b', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Area of locally managed areas / co-managed areas [total] (sq.km)')),
                ('f2_3a', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Area of fisheries management [coralreef] (sq.km)')),
                ('f2_3b', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Area of fisheries management [total] (sq.km)')),
                ('f2_4', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Area with pollution mitigation (sq.km)')),
                ('f2_opt1', models.DecimalField(blank=True, decimal_places=3, max_digits=9, null=True, verbose_name='Area of non-coral reef ecosystems, e.g., mangroves, seagrass or other associated ecosystems (sq.km)')),
                ('f3_1', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='Area of effective coral reef restoration (sq.km)')),
                ('f3_2', models.PositiveSmallIntegerField(default=0, verbose_name='Number of in situ coral restoration projects')),
                ('f3_3', models.PositiveSmallIntegerField(default=0, verbose_name='Number of coral restoration plans, technologies, strategies or guidelines developed')),
                ('f3_4', models.PositiveSmallIntegerField(default=0, verbose_name='Number of coral restoration trainings')),
                ('f3_5a', models.PositiveSmallIntegerField(default=0, verbose_name='Number of people engaged in coral restoration [men]')),
                ('f3_5b', models.PositiveSmallIntegerField(default=0, verbose_name='Number of people engaged in coral restoration [women]')),
                ('f3_5c', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Number of people engaged in coral restoration [youth]')),
                ('f3_5d', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Number of people engaged in coral restoration [Indigenous]')),
                ('f3_6', models.PositiveSmallIntegerField(default=0, verbose_name='Number of response plans (incl. financial mechanisms, eg., insurance) in place to support coral restoration after severe shocks (e.g,. storms, bleaching)')),
                ('f4_1', models.DecimalField(decimal_places=1, default=0, max_digits=4, verbose_name='Average live hard coral cover (%)')),
                ('f4_2', models.DecimalField(decimal_places=1, default=0, max_digits=4, verbose_name='Average macroalgae (%)')),
                ('f4_3', models.DecimalField(decimal_places=1, default=0, max_digits=5, verbose_name='Average reef fish biomass (kg/ha)')),
                ('f5_1', models.PositiveSmallIntegerField(default=0, verbose_name='Number of local communities engaged in meaningful participation and co-development')),
                ('f5_2', models.PositiveSmallIntegerField(default=0, verbose_name='Number of local organizations engaged in meaningful participation and co-development')),
                ('f5_3', models.PositiveSmallIntegerField(default=0, verbose_name='Number of local scientific/research partners involved in strengthening capacity for participation and co-development (e.g., national universities, regional science organizations)')),
                ('f5_4a', models.PositiveSmallIntegerField(default=0, verbose_name='Number of local practitioners trained / supported in coral reef conservation (e.g. community rangers) [men]')),
                ('f5_4b', models.PositiveSmallIntegerField(default=0, verbose_name='Number of local practitioners trained / supported in coral reef conservation (e.g. community rangers) [women]')),
                ('f5_4c', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Number of local practitioners trained / supported in coral reef conservation (e.g. community rangers) [youth]')),
                ('f5_4d', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Number of local practitioners trained / supported in coral reef conservation (e.g. community rangers) [Indigenous]')),
                ('f5_5', models.PositiveSmallIntegerField(default=0, verbose_name='Number of agreements with local authorities or fishing cooperatives to manage marine resources (e.g., LMMAs, MPAs, OECMs)')),
                ('f5_6', models.PositiveSmallIntegerField(default=0, verbose_name='Number of national policies linked to GFCR engagement, (e.g., NBSAPs, blue economy policies, national MPA declarations)')),
                ('f6_1a', models.PositiveSmallIntegerField(default=0, verbose_name='Number of direct jobs created (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [men]')),
                ('f6_1b', models.PositiveSmallIntegerField(default=0, verbose_name='Number of direct jobs created (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [women]')),
                ('f6_1c', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Number of direct jobs created (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [youth]')),
                ('f6_1d', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Number of direct jobs created (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [Indigenous]')),
                ('f6_2a', models.PositiveSmallIntegerField(default=0, verbose_name='Number of people with increased income and/or nutrition from GFCR support (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [men]')),
                ('f6_2b', models.PositiveSmallIntegerField(default=0, verbose_name='Number of people with increased income and/or nutrition from GFCR support (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [women]')),
                ('f6_2c', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Number of people with increased income and/or nutrition from GFCR support (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [youth]')),
                ('f6_2d', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Number of people with increased income and/or nutrition from GFCR support (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [Indigenous]')),
                ('f7_1a', models.PositiveSmallIntegerField(default=0, verbose_name='Total direct beneficiaries (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [men]')),
                ('f7_1b', models.PositiveSmallIntegerField(default=0, verbose_name='Total direct beneficiaries (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [women]')),
                ('f7_1c', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Total direct beneficiaries (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [youth]')),
                ('f7_1d', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Total direct beneficiaries (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [Indigenous]')),
                ('f7_2a', models.PositiveSmallIntegerField(default=0, verbose_name='Total indirect beneficiaries (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [men]')),
                ('f7_2b', models.PositiveSmallIntegerField(default=0, verbose_name='Total indirect beneficiaries (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [women]')),
                ('f7_2c', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Total indirect beneficiaries (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [youth]')),
                ('f7_2d', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Total indirect beneficiaries (disaggregated by gender, age, disability, Indigenous peoples, small-scale producers) [Indigenous]')),
                ('f7_3', models.PositiveSmallIntegerField(default=0, verbose_name='Number of financial mechanisms/reforms to help coastal communities respond and recover from external shocks (e.g., insurance, loans, village savings, restoration crisis plans, etc)')),
                ('f7_4', models.PositiveSmallIntegerField(default=0, verbose_name='Number of governance reforms/policies to support response and recovery to external shocks (e.g., crisis management plans, reforms for temporary alternative employment)')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gfcrindicatorset_created_by', to='api.profile')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.project')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gfcrindicatorset_updated_by', to='api.profile')),
            ],
            options={
                'db_table': 'gfcr_indicator_set',
                'ordering': ['report_date'],
            },
        ),
        migrations.AddField(
            model_name='gfcrfinancesolution',
            name='indicator_set',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.gfcrindicatorset'),
        ),
        migrations.AddField(
            model_name='gfcrfinancesolution',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gfcrfinancesolution_updated_by', to='api.profile'),
        ),
    ]
