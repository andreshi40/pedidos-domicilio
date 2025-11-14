# /frontend/app.py

from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
from typing import Optional
from flask import flash
import json
import uuid
import threading
from datetime import datetime

app = Flask(__name__)

# Obtén la URL del API Gateway desde las variables de entorno.
# Esta variable debe estar configurada en el docker-compose.yml.
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")

# Secret key for session (only for dev). In production set a strong secret via env.
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-change-me")


# --- Local mock store fallback (used when API Gateway and other services are down) ---
class MockStore:
    def __init__(self, path=None):
        base = os.path.dirname(__file__)
        self.path = path or os.path.join(base, 'mock_data.json')
        self.lock = threading.Lock()
        self._load_or_init()

    def _load_or_init(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
            except Exception:
                self.data = self._default()
                self._save()
        else:
            self.data = self._default()
            self._save()

    def _default(self):
        # minimal seed matching the services' expected shapes
        return {
            "restaurantes": [
                {"id": "rest1", "nombre": "La Pizzeria", "direccion": "Calle 1", "descripcion": "Pizza tradicional"},
                {"id": "rest2", "nombre": "Sushi Bar", "direccion": "Calle 2", "descripcion": "Sushi fresco"}
            ],
            "menus": {
                "rest1": [
                    {"id": "p1", "nombre": "Margarita", "precio": 7.5, "cantidad": 10},
                    {"id": "p2", "nombre": "Cuatro Quesos", "precio": 9.0, "cantidad": 8}
                ],
                "rest2": [
                    {"id": "s1", "nombre": "Sushi Mix", "precio": 12.0, "cantidad": 6}
                ]
            },
            "repartidores": [
                {"id": "r_local_1", "nombre": "Local Repartidor", "telefono": "3000000001", "estado": "disponible"}
            ],
            "orders": {}
        }

    def _save(self):
        tmp = self.path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.data, f, default=str)
        os.replace(tmp, self.path)

    # Restaurants
    def list_restaurantes(self):
        return list(self.data.get('restaurantes', []))

    def get_restaurante(self, rest_id):
        for r in self.data.get('restaurantes', []):
            if r.get('id') == rest_id:
                return r
        return None

    def get_menu(self, rest_id):
        return self.data.get('menus', {}).get(rest_id, [])

    # Orders
    def create_order(self, payload):
        with self.lock:
            order_id = str(uuid.uuid4())
            items_out = []
            # check stock and decrement
            menu = self.data.setdefault('menus', {}).get(payload.get('restaurante_id'), [])
            menu_by_id = {m['id']: m for m in menu}
            for it in payload.get('items', []):
                mi = menu_by_id.get(it.get('item_id'))
                if not mi or mi.get('cantidad', 0) < it.get('cantidad', 0):
                    raise ValueError(f"Sin stock para item {it.get('item_id')}")
            for it in payload.get('items', []):
                mi = menu_by_id.get(it.get('item_id'))
                mi['cantidad'] = mi.get('cantidad', 0) - it.get('cantidad')
                items_out.append({"item_id": mi['id'], "nombre": mi.get('nombre'), "precio": mi.get('precio'), "cantidad": it.get('cantidad')})

            # assign repartidor if available
            rep = None
            for r in self.data.get('repartidores', []):
                if r.get('estado') == 'disponible':
                    rep = r
                    r['estado'] = 'ocupado'
                    break

            estado = 'asignado' if rep else 'creado'
            rep_out = None
            if rep:
                rep_out = {"id": rep['id'], "nombre": rep['nombre'], "telefono": rep.get('telefono')}

            order = {
                "id": order_id,
                "restaurante_id": payload.get('restaurante_id'),
                "cliente_email": payload.get('cliente_email'),
                "direccion": payload.get('direccion'),
                "items": items_out,
                "estado": estado,
                "repartidor": rep_out,
                "created_at": datetime.utcnow().isoformat()
            }
            self.data.setdefault('orders', {})[order_id] = order
            self._save()
            return order

    def get_order(self, order_id):
        return self.data.get('orders', {}).get(order_id)


# instantiate single mock store
mock_store = MockStore()

@app.route("/")
def index():
    """Ruta de la página de inicio."""
    # If user is logged in, make the restaurants search the post-login home.
    token = session.get("access_token")
    if token:
        return redirect(url_for("client_index"))

    # Otherwise show the public landing page.
    return render_template("index.html", title="Inicio")


@app.route("/home")
def home():
    # The microservices health dashboard was removed. Redirect to restaurants search.
    token = session.get("access_token")
    if not token:
        return redirect(url_for("login"))
    return redirect(url_for("client_index"))


@app.route('/_services')
def services_json():
    """Devuelve el mismo listado de servicios en formato JSON para llamadas AJAX."""
    # Require an access token in session (user must be logged in)
    token = session.get("access_token")
    if not token:
        return {"detail": "Authentication required"}, 401

    services = [
        {"name": "Autenticación", "key": "auth", "health": f"{API_GATEWAY_URL}/api/v1/auth/health"},
        {"name": "Restaurantes", "key": "restaurantes", "health": f"{API_GATEWAY_URL}/api/v1/restaurantes/health"},
        {"name": "Pedidos", "key": "pedidos", "health": f"{API_GATEWAY_URL}/api/v1/pedidos/health"},
        {"name": "Repartidores", "key": "repartidores", "health": f"{API_GATEWAY_URL}/api/v1/repartidores/health"},
    ]

    for s in services:
        try:
            # forward the session token to the API Gateway so it can include user headers
            headers = {"Authorization": f"Bearer {token}"}
            r = requests.get(s["health"], timeout=2, headers=headers)
            if r.status_code == 200:
                s["status"] = "up"
                try:
                    s["detail"] = r.json()
                except Exception:
                    s["detail"] = r.text
            else:
                s["status"] = "down"
                s["detail"] = f"HTTP {r.status_code}"
        except Exception as e:
            s["status"] = "down"
            s["detail"] = str(e)

    return {"services": services}


# Admin UI removed: admin user listing is no longer exposed via the frontend.



@app.route('/login', methods=["GET", "POST"])
def login():
    """Formulario de login que solicita un access token al gateway y lo guarda en sesión."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            flash("Email y contraseña son requeridos.")
            return render_template("login.html", title="Login")
        try:
            resp = requests.post(f"{API_GATEWAY_URL}/api/v1/auth/login", json={"email": email, "password": password}, timeout=5)
            # fallback to direct authentication service when gateway login fails
            if resp.status_code != 200:
                try:
                    resp = requests.post("http://authentication-service:8001/login", json={"email": email, "password": password}, timeout=4)
                except requests.exceptions.RequestException:
                    pass
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                if token:
                    # store token only for non-admin users; admin login via frontend is disabled
                    # fetch user info to check role
                    try:
                        me = requests.get(f"{API_GATEWAY_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                        if me.status_code == 200:
                            u = me.json()
                            role = u.get("role")
                            if role == 'admin':
                                flash("El ingreso como administrador no está permitido desde esta interfaz.")
                                return render_template("login.html", title="Login")
                            # not admin: set session
                            session["access_token"] = token
                            session["user_email"] = u.get("email")
                            session["user_role"] = role
                    except requests.exceptions.RequestException:
                        # if we cannot fetch /me, do not allow admin token to be stored
                        flash("No se pudo verificar la información del usuario.")
                        return render_template("login.html", title="Login")
                    flash("Login exitoso.")
                    # Redirect user to the client restaurants search after login
                    return redirect(url_for("client_index"))
            # else show error
            msg = resp.json().get("detail") if resp.headers.get('content-type','').startswith('application/json') else resp.text
            flash(f"Login falló: {msg}")
        except requests.exceptions.RequestException as e:
            flash(f"Error conectando al gateway: {e}")

    return render_template("login.html", title="Login")


@app.route('/logout')
def logout():
    """Clear session and redirect to index."""
    session.pop('access_token', None)
    session.pop('user_email', None)
    session.pop('user_role', None)
    flash('Sesión cerrada.')
    return redirect(url_for('index'))


@app.route('/restaurant/setup', methods=['GET', 'POST'])
def restaurant_setup():
    """Route that shows a simple restaurant onboarding form (name, address, phone, menu items).
    On POST it will call the API Gateway (or direct service) to create the restaurant and its menu items.
    """
    token = session.get('access_token')
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        direccion = request.form.get('direccion')
        telefono = request.form.get('telefono')
        # collect menu items
        nombres = request.form.getlist('item_nombre')
        precios = request.form.getlist('item_precio')
        cantidades = request.form.getlist('item_cantidad')

        # create restaurant payload
        rest_payload = {"nombre": nombre, "direccion": direccion}
        try:
            # try API gateway first
            resp = requests.post(f"{API_GATEWAY_URL}/api/v1/restaurantes", json=rest_payload, headers=headers, timeout=5)
            if resp.status_code not in (200,201):
                # try direct service inside compose network
                direct = requests.post(f"http://restaurantes-service:8002/api/v1/restaurantes", json=rest_payload, timeout=4)
                if direct.status_code not in (200,201):
                    flash('No se pudo crear el restaurante. Comprueba los logs del servicio.')
                    return render_template('new_restaurant.html', title='Registrar restaurante')
                resto = direct.json()
            else:
                resto = resp.json()

            rest_id = resto.get('id')
            # create menu items
            for i, nombre_item in enumerate(nombres or []):
                precio = precios[i] if i < len(precios) else 0
                cantidad = cantidades[i] if i < len(cantidades) else 0
                item_payload = {"nombre": nombre_item, "precio": float(precio or 0), "cantidad": int(cantidad or 0)}
                try:
                    r = requests.post(f"{API_GATEWAY_URL}/api/v1/restaurantes/{rest_id}/menu", json=item_payload, headers=headers, timeout=4)
                    if r.status_code not in (200,201):
                        # fallback
                        requests.post(f"http://restaurantes-service:8002/api/v1/restaurantes/{rest_id}/menu", json=item_payload, timeout=4)
                except requests.exceptions.RequestException:
                    try:
                        requests.post(f"http://restaurantes-service:8002/api/v1/restaurantes/{rest_id}/menu", json=item_payload, timeout=4)
                    except Exception:
                        pass

            flash('Restaurante creado correctamente.')
            return redirect(url_for('client_index'))
        except requests.exceptions.RequestException:
            flash('Error conectando al servicio de restaurantes.')
            return render_template('new_restaurant.html', title='Registrar restaurante')

    return render_template('new_restaurant.html', title='Registrar restaurante')


@app.route('/repartidor/setup', methods=['GET', 'POST'])
def repartidor_setup():
    """Onboarding form for repartidores (delivery riders).

    Collects full name, teléfono and photo. Creates a repartidor record in the
    repartidores service and uploads the photo.
    """
    token = session.get('access_token')
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        foto = request.files.get('foto')

        if not nombre:
            flash('El nombre es requerido.')
            return render_template('new_repartidor.html', title='Registro repartidor')

        # determine user id from auth/me
        user_id = None
        try:
            me = requests.get(f"{API_GATEWAY_URL}/api/v1/auth/me", headers=headers, timeout=4)
            if me.status_code == 200:
                u = me.json()
                # support both {"user": {...}} and direct user object
                if isinstance(u, dict) and 'user' in u:
                    u = u.get('user') or {}
                user_id = u.get('id') or u.get('sub') or u.get('email')
        except Exception:
            user_id = None

        if not user_id:
            # fallback to using email from session
            user_id = session.get('user_email') or str(uuid.uuid4())

        # create repartidor record
        payload = {"id": user_id, "nombre": nombre, "telefono": telefono}
        try:
            resp = requests.post(f"{API_GATEWAY_URL}/api/v1/repartidores", json=payload, headers=headers, timeout=5)
            if resp.status_code not in (200, 201):
                # try direct service in compose network
                direct = requests.post(f"http://repartidores-service:8004/api/v1/repartidores", json=payload, timeout=4)
                if direct.status_code not in (200, 201):
                    flash('No se pudo crear el repartidor en el servicio.')
                    return render_template('new_repartidor.html', title='Registro repartidor')
        except requests.exceptions.RequestException:
            try:
                direct = requests.post(f"http://repartidores-service:8004/api/v1/repartidores", json=payload, timeout=4)
                if direct.status_code not in (200, 201):
                    flash('No se pudo crear el repartidor en el servicio.')
                    return render_template('new_repartidor.html', title='Registro repartidor')
            except Exception:
                flash('Error conectando al servicio de repartidores.')
                return render_template('new_repartidor.html', title='Registro repartidor')

        # upload photo if provided
        if foto and foto.filename:
            try:
                files = {"file": (foto.filename, foto.stream.read(), foto.mimetype or 'application/octet-stream')}
                try:
                    r = requests.post(f"{API_GATEWAY_URL}/api/v1/repartidores/{user_id}/photo", files=files, headers=headers, timeout=5)
                    if r.status_code not in (200, 201):
                        # fallback direct
                        requests.post(f"http://repartidores-service:8004/api/v1/repartidores/{user_id}/photo", files=files, timeout=4)
                except requests.exceptions.RequestException:
                    try:
                        requests.post(f"http://repartidores-service:8004/api/v1/repartidores/{user_id}/photo", files=files, timeout=4)
                    except Exception:
                        pass
            except Exception:
                # ignore photo upload errors but inform user
                flash('Advertencia: no se pudo subir la foto, puedes añadirla después.')

        flash('Registro de repartidor completado.')
        return redirect(url_for('client_index'))

    return render_template('new_repartidor.html', title='Registro repartidor')

@app.route("/new-user", methods=["GET", "POST"])
def new_user():
    """Ruta para crear un nuevo usuario."""
    # allow preselecting the role via querystring (?role=cliente|restaurante|repartidor)
    role_default = request.args.get('role') if request.method == 'GET' else (request.form.get('role') or request.args.get('role'))

    if request.method == "POST":
        # Recoge los datos del formulario de registro
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role") or "cliente"

        # Do not allow creating admin users via the frontend
        if role == 'admin':
            flash('No está permitido crear usuarios con rol administrador desde esta interfaz.')
            return render_template("new_user.html", title="Nuevo Usuario", role_default=role_default)

        if not email or not password:
            flash("Email y contraseña son requeridos para registrar un usuario.")
            return render_template("new_user.html", title="Nuevo Usuario", role_default=role_default)

        # server-side password length check (defensive)
        if len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.")
            return render_template("new_user.html", title="Nuevo Usuario", role_default=role_default)

        payload = {"email": email, "password": password, "role": role}
        try:
            resp = requests.post(f"{API_GATEWAY_URL}/api/v1/auth/register", json=payload, timeout=5)
            # If gateway fails (404/other) try direct auth service in compose network
            if resp.status_code not in (200, 201):
                try:
                    resp = requests.post("http://authentication-service:8001/register", json=payload, timeout=4)
                except requests.exceptions.RequestException:
                    pass

            if resp.status_code in (200, 201):
                # Autologin: intentar iniciar sesión inmediatamente después del registro
                try:
                    login_resp = requests.post(f"{API_GATEWAY_URL}/api/v1/auth/login", json={"email": email, "password": password}, timeout=5)
                    # fallback to direct auth service if gateway login fails or returns 404
                    if login_resp.status_code != 200:
                        try:
                            login_resp = requests.post("http://authentication-service:8001/login", json={"email": email, "password": password}, timeout=4)
                        except requests.exceptions.RequestException:
                            pass

                    if login_resp.status_code == 200:
                        token = login_resp.json().get("access_token")
                        if token:
                            # verify role before setting session
                            try:
                                me = requests.get(f"{API_GATEWAY_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                                if me.status_code == 200:
                                    u = me.json()
                                    # some auth services return {"user": {...}} while others
                                    # return the user object directly; normalize both shapes
                                    if isinstance(u, dict) and 'user' in u:
                                        u = u.get('user') or {}
                                    if u.get('role') == 'admin':
                                        flash('No está permitido iniciar sesión como admin desde esta interfaz.')
                                        return redirect(url_for('login'))
                                    session["access_token"] = token
                                    session["user_email"] = u.get("email")
                                    session["user_role"] = u.get("role")
                            except requests.exceptions.RequestException:
                                pass
                            flash("Registro correcto. Sesión iniciada.")
                            # After successful registration + autologin, if user is a restaurante
                            # redirect them to the restaurant setup page so they can register their menu.
                            if role == 'restaurante' or session.get('user_role') == 'restaurante':
                                return redirect(url_for('restaurant_setup'))
                            # If the user registered as repartidor, redirect to repartidor onboarding
                            if role == 'repartidor' or session.get('user_role') == 'repartidor':
                                return redirect(url_for('repartidor_setup'))
                            return redirect(url_for("client_index"))
                except requests.exceptions.RequestException:
                    # Si falla el autologin, redirigimos al login manual
                    pass

                flash("Usuario creado correctamente. Por favor, inicia sesión.")
                return redirect(url_for("login"))
            # mostrar detalle de error si viene en JSON
            msg = resp.json().get("detail") if resp.headers.get('content-type','').startswith('application/json') else resp.text
            flash(f"Registro falló: {msg}")
        except requests.exceptions.RequestException as e:
            flash(f"Error conectando al gateway: {e}")

        return render_template("new_user.html", title="Nuevo Usuario", role_default=role_default)

    return render_template("new_user.html", title="Nuevo Usuario", role_default=role_default)


# Compatibility redirect: keep the old URL (/new-item) working by redirecting
# clients to the new route (/new-user). This avoids breaking existing links.
@app.route("/new-item", methods=["GET", "POST"])
def new_item_redirect():
    return redirect(url_for('new_user'))

@app.route('/client')
def client_index():
    """Página pública para clientes: buscador de restaurantes.

    Intenta primero usar el API Gateway; si devuelve 404 o falla, hace fallback
    directo al servicio `restaurantes` (útil en entornos de desarrollo docker-compose).
    """
    q = request.args.get('q')
    restos = []
    # Construir rutas
    gw_path = f"/api/v1/restaurantes?q={q}" if q else "/api/v1/restaurantes?limit=20"
    try:
        resp = requests.get(f"{API_GATEWAY_URL}{gw_path}", timeout=5)
        if resp.status_code == 200:
            restos = resp.json().get('restaurantes') or resp.json()
        else:
            # si gateway respondió 404 o similar, intentar acceso directo al servicio restaurantes
            if resp.status_code == 404:
                try:
                    direct_url = f"http://restaurantes-service:8002{gw_path}"
                    dr = requests.get(direct_url, timeout=5)
                    if dr.status_code == 200:
                        restos = dr.json().get('restaurantes') or dr.json()
                except requests.exceptions.RequestException:
                    restos = []
            else:
                restos = []
    except requests.exceptions.RequestException:
        # gateway inaccesible: intento directo
        try:
            direct_url = f"http://restaurantes-service:8002{gw_path}"
            dr = requests.get(direct_url, timeout=5)
            if dr.status_code == 200:
                restos = dr.json().get('restaurantes') or dr.json()
        except requests.exceptions.RequestException:
            restos = []

    return render_template('client_home.html', title='Buscar restaurantes', restaurantes=restos, q=q)


@app.route('/restaurants')
def restaurants_search():
    q = request.args.get('q')
    return redirect(url_for('client_index', q=q))


@app.route('/restaurants/<rest_id>', methods=['GET', 'POST'])
def restaurant_detail(rest_id):
    """Muestra detalle del restaurante y permite crear un pedido (cliente debe estar logueado)."""
    # Obtener info del restaurante y su menú desde el API Gateway
    restaurante = None
    menu = []
    try:
        r = requests.get(f"{API_GATEWAY_URL}/api/v1/restaurantes/{rest_id}", timeout=5)
        if r.status_code == 200:
            restaurante = r.json()
        else:
            # si gateway respondió 404 o similar, intentar acceso directo al servicio restaurantes
            if r.status_code == 404:
                try:
                    direct_r = requests.get(f"http://restaurantes-service:8002/api/v1/restaurantes/{rest_id}", timeout=5)
                    if direct_r.status_code == 200:
                        restaurante = direct_r.json()
                except requests.exceptions.RequestException:
                    restaurante = None
            else:
                restaurante = None
    except requests.exceptions.RequestException:
        # intento directo si el gateway no responde
        try:
            direct_r = requests.get(f"http://restaurantes-service:8002/api/v1/restaurantes/{rest_id}", timeout=5)
            if direct_r.status_code == 200:
                restaurante = direct_r.json()
        except requests.exceptions.RequestException:
            restaurante = None

    if not restaurante:
        flash('No se pudo obtener la información del restaurante.')
        return redirect(url_for('client_index'))

    # Obtener menú (normalized contract: {"menu": [...]}) con fallback al servicio directo
    try:
        m = requests.get(f"{API_GATEWAY_URL}/api/v1/restaurantes/{rest_id}/menu", timeout=5)
        if m.status_code == 200:
            data = m.json()
            if isinstance(data, dict) and 'menu' in data:
                menu = data.get('menu') or []
            elif isinstance(data, list):
                menu = data
            else:
                menu = []
        else:
            if m.status_code == 404:
                try:
                    direct_m = requests.get(f"http://restaurantes-service:8002/api/v1/restaurantes/{rest_id}/menu", timeout=5)
                    if direct_m.status_code == 200:
                        d = direct_m.json()
                        if isinstance(d, dict) and 'menu' in d:
                            menu = d.get('menu') or []
                        elif isinstance(d, list):
                            menu = d
                except requests.exceptions.RequestException:
                    menu = []
            else:
                menu = []
    except requests.exceptions.RequestException:
        try:
            direct_m = requests.get(f"http://restaurantes-service:8002/api/v1/restaurantes/{rest_id}/menu", timeout=5)
            if direct_m.status_code == 200:
                d = direct_m.json()
                if isinstance(d, dict) and 'menu' in d:
                    menu = d.get('menu') or []
                elif isinstance(d, list):
                    menu = d
        except requests.exceptions.RequestException:
            menu = []

    if request.method == 'POST':
        # Crear pedido — requiere token en sesión
        token = session.get('access_token')
        if not token:
            flash('Debes iniciar sesión para hacer un pedido.')
            return redirect(url_for('login'))

        direccion = request.form.get('direccion')
        items = []
        # items esperados como item_<id>=cantidad
        for k, v in request.form.items():
            if k.startswith('item_') and v and int(v) > 0:
                item_id = k.split('_', 1)[1]
                items.append({'item_id': item_id, 'cantidad': int(v)})

        payload = {
            'restaurante_id': rest_id,
            'cliente_email': session.get('user_email'),
            'direccion': direccion,
            'items': items
        }
        try:
            resp = requests.post(f"{API_GATEWAY_URL}/api/v1/pedidos", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if resp.status_code in (200, 201):
                order = resp.json()
                order_id = order.get('id') or order.get('pedido_id') or order.get('order_id')
                try:
                    session['last_order_id'] = order_id
                except Exception:
                    pass
                flash('Pedido creado correctamente.')
                return redirect(url_for('order_status', order_id=order_id))
            else:
                # si gateway devolvió 404 o similar, intentar enviar directamente al servicio de pedidos
                if resp.status_code == 404:
                    try:
                        direct = requests.post("http://pedidos-service:8003/api/v1/pedidos", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=5)
                        if direct.status_code in (200,201):
                            order = direct.json()
                            order_id = order.get('id') or order.get('pedido_id') or order.get('order_id')
                            try:
                                session['last_order_id'] = order_id
                            except Exception:
                                pass
                            flash('Pedido creado correctamente.')
                            return redirect(url_for('order_status', order_id=order_id))
                        else:
                            msg = direct.json().get('detail') if direct.headers.get('content-type','').startswith('application/json') else direct.text
                            flash(f'Error creando pedido (direct): {msg}')
                    except requests.exceptions.RequestException:
                        flash('No se pudo conectar al servicio de pedidos directamente.')
                else:
                    msg = resp.json().get('detail') if resp.headers.get('content-type','').startswith('application/json') else resp.text
                    flash(f'Error creando pedido: {msg}')
        except requests.exceptions.RequestException as e:
            # intento directo si el gateway no responde
            try:
                direct = requests.post("http://pedidos-service:8003/api/v1/pedidos", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=5)
                if direct.status_code in (200,201):
                    order = direct.json()
                    order_id = order.get('id') or order.get('pedido_id') or order.get('order_id')
                    try:
                        session['last_order_id'] = order_id
                    except Exception:
                        pass
                    flash('Pedido creado correctamente.')
                    return redirect(url_for('order_status', order_id=order_id))
                else:
                    msg = direct.json().get('detail') if direct.headers.get('content-type','').startswith('application/json') else direct.text
                    flash(f'Error creando pedido (direct): {msg}')
            except requests.exceptions.RequestException:
                flash('Error conectando al gateway y al servicio de pedidos.')

    # If there's a last_order_id in session, try to fetch it and, if it belongs to this restaurant,
    # pass it to the template so the page can show the order status inline.
    current_order = None
    order_id = session.get('last_order_id')
    if order_id:
        try:
            headers = {"Authorization": f"Bearer {session.get('access_token')}"} if session.get('access_token') else {}
            resp = requests.get(f"{API_GATEWAY_URL}/api/v1/pedidos/{order_id}", headers=headers, timeout=3)
            if resp.status_code == 200:
                pedido = resp.json()
                # only show it on this restaurant page if it belongs to the current restaurant
                if pedido.get('restaurante_id') == rest_id:
                    current_order = pedido
        except requests.exceptions.RequestException:
            current_order = None

    return render_template('restaurant.html', title=restaurante.get('nombre','Restaurante'), restaurante=restaurante, menu=menu, current_order=current_order)


@app.route('/order/<order_id>')
def order_status(order_id):
    """Muestra el estado de un pedido y datos del repartidor si están disponibles."""
    token = session.get('access_token')
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.get(f"{API_GATEWAY_URL}/api/v1/pedidos/{order_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            pedido = resp.json()
        else:
            flash('No se pudo obtener el estado del pedido.')
            return redirect(url_for('client_index'))
    except requests.exceptions.RequestException:
        flash('Error conectando al gateway.')
        return redirect(url_for('client_index'))

    return render_template('order_confirm.html', title='Estado del pedido', pedido=pedido)



@app.route('/api/order/<order_id>')
def api_order_status(order_id):
    """Proxy que devuelve el JSON del pedido llamando al API Gateway.
    Esto permite al frontend hacer polling sin depender de CORS o exponer el gateway al cliente.
    """
    token = session.get('access_token')
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.get(f"{API_GATEWAY_URL}/api/v1/pedidos/{order_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            return (resp.content, resp.status_code, {'Content-Type': resp.headers.get('content-type','application/json')})
        # fallback to direct pedidos service when gateway returns 404 or method routing issues
        if resp.status_code == 404 or resp.status_code == 405:
            try:
                direct = requests.get(f"http://pedidos-service:8003/api/v1/pedidos/{order_id}", headers=headers, timeout=4)
                return (direct.content, direct.status_code, {'Content-Type': direct.headers.get('content-type','application/json')})
            except requests.exceptions.RequestException:
                return (resp.content, resp.status_code, {'Content-Type': resp.headers.get('content-type','application/json')})
        return (resp.content, resp.status_code, {'Content-Type': resp.headers.get('content-type','application/json')})
    except requests.exceptions.RequestException as e:
        # fallback to local mock store if available
        o = mock_store.get_order(order_id)
        if o:
            return (json.dumps(o), 200, {'Content-Type': 'application/json'})
        return ({"detail": "cannot reach gateway and no local mock order"}, 500)


@app.route('/api/restaurantes/<rest_id>/menu')
def api_rest_menu(rest_id):
    """Proxy para obtener el menú de un restaurante desde el servidor (permite polling desde el navegador).
    Intenta API Gateway y si falla, hace fallback al servicio `restaurantes` directo dentro de la red docker-compose.
    """
    try:
        resp = requests.get(f"{API_GATEWAY_URL}/api/v1/restaurantes/{rest_id}/menu", timeout=4)
        if resp.status_code == 200:
            return (resp.content, resp.status_code, {'Content-Type': resp.headers.get('content-type','application/json')})
        else:
            # si gateway devuelve 404 o similar, intentamos el servicio directo
            if resp.status_code == 404:
                try:
                    direct = requests.get(f"http://restaurantes-service:8002/api/v1/restaurantes/{rest_id}/menu", timeout=4)
                    return (direct.content, direct.status_code, {'Content-Type': direct.headers.get('content-type','application/json')})
                except requests.exceptions.RequestException:
                    return ({"menu": []}, 502)
            return (resp.content, resp.status_code, {'Content-Type': resp.headers.get('content-type','application/json')})
    except requests.exceptions.RequestException:
        try:
            direct = requests.get(f"http://restaurantes-service:8002/api/v1/restaurantes/{rest_id}/menu", timeout=4)
            return (direct.content, direct.status_code, {'Content-Type': direct.headers.get('content-type','application/json')})
        except requests.exceptions.RequestException as e:
            # fallback: return mock menu if present
            menu = mock_store.get_menu(rest_id)
            return (json.dumps({"menu": menu}), 200, {'Content-Type': 'application/json'})


@app.route('/api/pedidos', methods=['POST'])
def api_create_pedido():
    """Proxy para crear un pedido desde el frontend mediante AJAX.
    Reenvía la petición al API Gateway y si falla intenta el servicio directo de pedidos.
    Guarda session['last_order_id'] con el id devuelto cuando la creación es exitosa.
    """
    payload = None
    try:
        payload = request.get_json()
    except Exception:
        return ({"detail": "invalid json"}, 400)

    token = session.get('access_token')
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Intentar API Gateway primero
    try:
        resp = requests.post(f"{API_GATEWAY_URL}/api/v1/pedidos", json=payload, headers=headers, timeout=5)
        if resp.status_code in (200, 201):
            # store last order id in session if possible
            try:
                order = resp.json()
                order_id = order.get('id') or order.get('pedido_id') or order.get('order_id')
                if order_id:
                    session['last_order_id'] = order_id
            except Exception:
                pass
            return (resp.content, resp.status_code, {'Content-Type': resp.headers.get('content-type','application/json')})
        else:
            # si gateway devolvió 405 (método no permitido) o devolvió 404/401 y no tenemos token en sesión,
            # intentar enviar directamente al servicio de pedidos (fallback útil en desarrollo)
            if resp.status_code == 405 or (resp.status_code in (404, 401) and not token):
                try:
                    direct = requests.post("http://pedidos-service:8003/api/v1/pedidos", json=payload, headers=headers, timeout=5)
                    if direct.status_code in (200,201):
                        try:
                            order = direct.json()
                            order_id = order.get('id') or order.get('pedido_id') or order.get('order_id')
                            if order_id:
                                session['last_order_id'] = order_id
                        except Exception:
                            pass
                        return (direct.content, direct.status_code, {'Content-Type': direct.headers.get('content-type','application/json')})
                    else:
                        return (direct.content, direct.status_code, {'Content-Type': direct.headers.get('content-type','application/json')})
                except requests.exceptions.RequestException:
                    return ({"detail": "no connection to pedidos service"}, 502)
            # otherwise forward error
            return (resp.content, resp.status_code, {'Content-Type': resp.headers.get('content-type','application/json')})
    except requests.exceptions.RequestException:
        # intento directo si el gateway no responde
        try:
            direct = requests.post("http://pedidos-service:8003/api/v1/pedidos", json=payload, headers=headers, timeout=5)
            if direct.status_code in (200,201):
                try:
                    order = direct.json()
                    order_id = order.get('id') or order.get('pedido_id') or order.get('order_id')
                    if order_id:
                        session['last_order_id'] = order_id
                except Exception:
                    pass
            return (direct.content, direct.status_code, {'Content-Type': direct.headers.get('content-type','application/json')})
        except requests.exceptions.RequestException as e:
            # fallback: create order locally using mock store
            try:
                order = mock_store.create_order(payload)
                order_id = order.get('id')
                if order_id:
                    try:
                        session['last_order_id'] = order_id
                    except Exception:
                        pass
                return (json.dumps(order), 200, {'Content-Type': 'application/json'})
            except ValueError as ve:
                return ({"detail": str(ve)}, 400)
            except Exception as _:
                return ({"detail": "unable to create order (gateway and local mock failed)"}, 500)


@app.route('/_debug/set_last/<order_id>', methods=['GET'])
def _debug_set_last(order_id):
    """Ruta de depuración (solo dev): establece session['last_order_id'] para facilitar pruebas E2E.
    No debe usarse en producción.
    """
    try:
        session['last_order_id'] = order_id
        return {"ok": True, "last_order_id": order_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
