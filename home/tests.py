"""
Tests mínimos de las APIs admin y pública.

Cobertura:
 - Auth admin (login con/sin is_staff, me, logout)
 - Auth público (register, login, me)
 - Valoraciones: aislamiento por usuario en la API pública
 - Admin: CRUD básico y permisos
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from home.models import Users, Valoracion


class AuthAdminAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create(
            usuario='admin1', email='admin@test.com', nombre='Admin',
            is_staff=True, is_active=True,
        )
        cls.admin.set_password('pass1234')
        cls.admin.save()

        cls.user = Users.objects.create(
            usuario='user1', email='user@test.com', nombre='User',
            is_staff=False, is_active=True,
        )
        cls.user.set_password('pass1234')
        cls.user.save()

    def test_login_admin_ok(self):
        c = APIClient()
        r = c.post('/api/admin/auth/login/', {'usuario': 'admin1', 'password': 'pass1234'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['is_staff'])

    def test_login_admin_rechaza_no_staff(self):
        c = APIClient()
        r = c.post('/api/admin/auth/login/', {'usuario': 'user1', 'password': 'pass1234'}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_login_admin_credenciales_malas(self):
        c = APIClient()
        r = c.post('/api/admin/auth/login/', {'usuario': 'admin1', 'password': 'malo'}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_me_admin_requiere_auth(self):
        c = APIClient()
        r = c.get('/api/admin/auth/me/')
        self.assertIn(r.status_code, (401, 403))

    def test_me_admin_ok(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.get('/api/admin/auth/me/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['usuario'], 'admin1')


class AdminUsersAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Users.objects.create(
            usuario='admin1', email='admin@test.com', nombre='Admin',
            is_staff=True, is_active=True,
        )
        cls.admin.set_password('pass1234')
        cls.admin.save()

    def setUp(self):
        self.c = APIClient()
        self.c.force_authenticate(self.admin)

    def test_list_users_requiere_staff(self):
        anon = APIClient()
        r = anon.get('/api/admin/users/')
        self.assertIn(r.status_code, (401, 403))

    def test_crear_usuario(self):
        r = self.c.post('/api/admin/users/', {
            'usuario': 'nuevo', 'email': 'nuevo@test.com',
            'nombre': 'Nuevo', 'empresa': 'Empresa', 'password': 'secret123',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(Users.objects.filter(usuario='nuevo').exists())

    def test_no_puede_borrarse_a_si_mismo(self):
        r = self.c.delete(f'/api/admin/users/{self.admin.pk}/')
        self.assertEqual(r.status_code, 403)

    def test_set_password(self):
        u = Users.objects.create(usuario='x', email='x@x.com', nombre='X', is_active=True)
        u.set_password('viejo')
        u.save()
        r = self.c.post(f'/api/admin/users/{u.pk}/set-password/', {'password': 'nuevo123'}, format='json')
        self.assertEqual(r.status_code, 200)
        u.refresh_from_db()
        self.assertTrue(u.check_password('nuevo123'))


class PublicAuthAPITests(TestCase):
    def test_register_ok(self):
        c = APIClient()
        r = c.post('/api/auth/register/', {
            'usuario': 'pepito', 'email': 'pepito@test.com', 'password': 'secret123',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(Users.objects.filter(usuario='pepito').exists())

    def test_register_duplicado_da_409(self):
        Users.objects.create(usuario='dup', email='dup@test.com', nombre='Dup')
        c = APIClient()
        r = c.post('/api/auth/register/', {
            'usuario': 'dup', 'email': 'dup@test.com', 'password': 'x',
        }, format='json')
        self.assertEqual(r.status_code, 409)

    def test_login_y_me(self):
        u = Users.objects.create(usuario='login1', email='l@l.com', nombre='L', is_active=True)
        u.set_password('clave1234')
        u.save()
        c = APIClient()
        r = c.post('/api/auth/login/', {'usuario': 'login1', 'password': 'clave1234'}, format='json')
        self.assertEqual(r.status_code, 200)
        r2 = c.get('/api/auth/me/')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data['usuario'], 'login1')


class ValoracionesAislamientoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u1 = Users.objects.create(usuario='a', email='a@a.com', nombre='A', is_active=True)
        cls.u2 = Users.objects.create(usuario='b', email='b@b.com', nombre='B', is_active=True)
        Valoracion.objects.create(
            iduser_id=cls.u1.pk, modo='venta', ciudad='Madrid', distrito='X', barrio='Y',
            calle='Z', tipo_vivienda='1', metros_cuadrados=80, num_habitaciones=2,
            num_banos=1, planta=1, terraza=False, balcon=False, ascensor=True,
            estado_inmueble='1', precio_minimo=100, precio_esperado=120, precio_maximo=140,
            precio_esperado_unico=120,
        )
        Valoracion.objects.create(
            iduser_id=cls.u2.pk, modo='venta', ciudad='Madrid', distrito='X', barrio='Y',
            calle='Z', tipo_vivienda='1', metros_cuadrados=90, num_habitaciones=3,
            num_banos=2, planta=2, terraza=True, balcon=False, ascensor=True,
            estado_inmueble='1', precio_minimo=200, precio_esperado=220, precio_maximo=240,
            precio_esperado_unico=220,
        )

    def test_usuario_solo_ve_sus_valoraciones(self):
        c = APIClient()
        c.force_authenticate(self.u1)
        r = c.get('/api/valoraciones/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)

    def test_admin_ve_todas(self):
        admin = Users.objects.create(
            usuario='adm', email='ad@m.com', nombre='Adm', is_staff=True, is_active=True,
        )
        c = APIClient()
        c.force_authenticate(admin)
        r = c.get('/api/admin/valoraciones/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
