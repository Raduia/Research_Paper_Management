# Generated manually to add missing Profile fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('research_portfolio', '0004_auto_20260601_2106'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='research_score',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='profile',
            name='reputation_level',
            field=models.CharField(default='Beginner', max_length=50),
        ),
    ]
