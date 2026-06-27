"""Verificación temporal: enviar informe por email."""
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from home.models import Users, Informe

PDF = b'%PDF-1.4 fake'


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@test.com',
)
class InformeEmailCheck(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create(usuario='u1', email='u1@t.com', nombre='Juan', is_active=True)
        cls.user.set_password('Xq7!vmZ2pLk'); cls.user.save()
        cls.otro = Users.objects.create(usuario='u2', email='u2@t.com', nombre='Otro', is_active=True)
        cls.otro.set_password('Xq7!vmZ2pLk'); cls.otro.save()
        cls.inf = Informe.objects.create(
            usuario=cls.user, tipo='informe',
            archivo_pdf=SimpleUploadedFile('a.pdf', PDF, content_type='application/pdf'))

    def _url(self, i):
        return f'/api/informes/{i}/enviar-email/'

    def test_envia_al_email_del_usuario_por_defecto(self):
        c = APIClient(); c.force_authenticate(self.user)
        mail.outbox = []
        r = c.post(self._url(self.inf.id), {}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['enviado_a'], 'u1@t.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['u1@t.com'])
        self.assertEqual(len(mail.outbox[0].attachments), 1)  # PDF adjunto

    def test_envia_a_email_indicado(self):
        c = APIClient(); c.force_authenticate(self.user)
        mail.outbox = []
        r = c.post(self._url(self.inf.id), {'email': 'cliente@dominio.com'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(mail.outbox[0].to, ['cliente@dominio.com'])

    def test_no_envia_informe_ajeno(self):
        c = APIClient(); c.force_authenticate(self.otro)
        r = c.post(self._url(self.inf.id), {}, format='json')
        self.assertEqual(r.status_code, 404)

    def test_requiere_auth(self):
        r = APIClient().post(self._url(self.inf.id), {}, format='json')
        self.assertIn(r.status_code, (401, 403))
