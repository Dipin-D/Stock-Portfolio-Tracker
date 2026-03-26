from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0006_appsettings'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedGlidepath',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name', '-updated_at'],
            },
        ),
    ]
