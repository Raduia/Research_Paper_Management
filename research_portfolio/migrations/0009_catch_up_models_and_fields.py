import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('research_portfolio', '0008_drop_paper_user_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResearchCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Evaluation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('methodology_score', models.IntegerField(default=0)),
                ('innovation_score', models.IntegerField(default=0)),
                ('writing_score', models.IntegerField(default=0)),
                ('technical_score', models.IntegerField(default=0)),
                ('feedback', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations', to='research_portfolio.paper')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='paper',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='research_portfolio.researchcategory'),
        ),
        migrations.AddField(
            model_name='paper',
            name='pdf',
            field=models.FileField(blank=True, null=True, upload_to='papers/'),
        ),
        migrations.AddField(
            model_name='paper',
            name='current_score',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='paper',
            name='previous_score',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='paper',
            name='improvement_bonus',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='paper',
            name='final_score',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='paper',
            name='revision_count',
            field=models.IntegerField(default=0),
        ),
    ]
