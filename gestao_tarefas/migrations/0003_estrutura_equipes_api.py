from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('gestao_tarefas', '0002_tarefa_urgencia_alter_tarefa_status'),
    ]
    operations = [
        migrations.AddField(
            model_name='perfil', name='papel',
            field=models.CharField(choices=[('SUPREMO', 'Supremo'), ('GERENTE', 'Gerente'), ('FUNCIONARIO', 'Funcionário')], default='FUNCIONARIO', max_length=12),
        ),
        migrations.CreateModel(
            name='Equipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('descricao', models.TextField(blank=True)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('ativa', models.BooleanField(default=True)),
                ('gerente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipes_gerenciadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['nome'], 'verbose_name': 'Equipe', 'verbose_name_plural': 'Equipes'},
        ),
        migrations.CreateModel(
            name='MembroEquipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pode_criar_tarefa', models.BooleanField(default=False)),
                ('pode_editar_tarefa', models.BooleanField(default=False)),
                ('pode_excluir_tarefa', models.BooleanField(default=False)),
                ('entrou_em', models.DateTimeField(auto_now_add=True)),
                ('equipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='membros', to='gestao_tarefas.equipe')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vinculos_equipes', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='membroequipe',
            constraint=models.UniqueConstraint(fields=('equipe', 'usuario'), name='uniq_membro_por_equipe'),
        ),
        migrations.AddField(
            model_name='tarefa', name='equipe',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tarefas', to='gestao_tarefas.equipe'),
        ),
        migrations.AddField(
            model_name='tarefa', name='criada_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tarefas_criadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='tarefa', name='criada_em',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tarefa', name='atualizada_em',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='HistoricoTarefa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(max_length=120)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('detalhes', models.JSONField(blank=True, default=dict)),
                ('autor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('tarefa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico', to='gestao_tarefas.tarefa')),
            ],
            options={'ordering': ['-criado_em']},
        ),
    ]
