from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('research_portfolio', '0007_add_paper_student_db_column'),
    ]

    operations = [
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
