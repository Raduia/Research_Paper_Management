from django.db import migrations


def copy_user_to_student(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute('UPDATE research_portfolio_paper SET student_id = user_id')


class Migration(migrations.Migration):

    dependencies = [
        ('research_portfolio', '0005_add_profile_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE research_portfolio_paper ADD COLUMN student_id INTEGER',
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunPython(copy_user_to_student, migrations.RunPython.noop),
            ],
            state_operations=[],
        ),
    ]
