# /frontend/app.py

from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
from typing import Optional

from flask import flash

app = Flask(__name__)

# Obtén la URL del API Gateway desde las variables de entorno.
# Esta variable debe estar configurada en el docker-compose.yml.
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")

# Secret key for session (only for dev). In production set a strong secret via env.
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-change-me")

@app.route("/")
def index():
    """Ruta de la página de inicio."""
    
    # TODO: Haz una llamada al API Gateway para obtener datos, si es necesario.
    # Por ejemplo, para obtener la lista de items de un servicio:
    # try:
    #     response = requests.get(f"{API_GATEWAY_URL}/api/v1/[recurso]")
    #     response.raise_for_status()  # Lanza un error para códigos de estado 4xx/5xx
    #     items = response.json()
    # except requests.exceptions.RequestException as e:
    #     print(f"Error al conectar con el API Gateway: {e}")
    #     items = []

    # Pasa los datos a la plantilla para renderizarlos.
    return render_template("index.html", title="Inicio")


@app.route("/home")
def home():
    """Página que muestra el estado rápido de los microservicios mediante el API Gateway."""
    # Require login to view the home dashboard
    token = session.get("access_token")
    if not token:
        flash("Inicia sesión para ver el estado de los microservicios.")
        return redirect(url_for("login"))
    # Construye los endpoints de health usando la URL del API Gateway
    services = [
        {"name": "Autenticación", "key": "auth", "health": f"{API_GATEWAY_URL}/api/v1/auth/health"},
        {"name": "Restaurantes", "key": "restaurantes", "health": f"{API_GATEWAY_URL}/api/v1/restaurantes/health"},
        {"name": "Pedidos", "key": "pedidos", "health": f"{API_GATEWAY_URL}/api/v1/pedidos/health"},
        {"name": "Repartidores", "key": "repartidores", "health": f"{API_GATEWAY_URL}/api/v1/repartidores/health"},
    ]

    # Consulta cada endpoint desde el servidor (evita CORS). Usa timeout corto.
    for s in services:
        try:
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

    return render_template("home.html", title="Home", services=services)


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
                    return redirect(url_for("home"))
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

@app.route("/new-user", methods=["GET", "POST"])
def new_user():
    """Ruta para crear un nuevo usuario."""
    if request.method == "POST":
        # Recoge los datos del formulario de registro
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role") or "cliente"
        # Do not allow creating admin users via the frontend
        if role == 'admin':
            flash('No está permitido crear usuarios con rol administrador desde esta interfaz.')
            return render_template("new_user.html", title="Nuevo Usuario")

        if not email or not password:
            flash("Email y contraseña son requeridos para registrar un usuario.")
            return render_template("new_user.html", title="Nuevo Usuario")

        # server-side password length check (defensive)
        if len(password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.")
            return render_template("new_user.html", title="Nuevo Usuario")

        payload = {"email": email, "password": password, "role": role}
        try:
            resp = requests.post(f"{API_GATEWAY_URL}/api/v1/auth/register", json=payload, timeout=5)
            if resp.status_code in (200, 201):
                # Autologin: intentar iniciar sesión inmediatamente después del registro
                try:
                    login_resp = requests.post(f"{API_GATEWAY_URL}/api/v1/auth/login", json={"email": email, "password": password}, timeout=5)
                    if login_resp.status_code == 200:
                            token = login_resp.json().get("access_token")
                            if token:
                                # verify role before setting session
                                try:
                                    me = requests.get(f"{API_GATEWAY_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                                    if me.status_code == 200:
                                        u = me.json()
                                        if u.get('role') == 'admin':
                                            flash('No está permitido iniciar sesión como admin desde esta interfaz.')
                                            return redirect(url_for('login'))
                                        session["access_token"] = token
                                        session["user_email"] = u.get("email")
                                        session["user_role"] = u.get("role")
                                except requests.exceptions.RequestException:
                                    pass
                                flash("Registro correcto. Sesión iniciada.")
                                return redirect(url_for("home"))
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

        return render_template("new_user.html", title="Nuevo Usuario")

    return render_template("new_user.html", title="Nuevo Usuario")


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
        return (resp.content, resp.status_code, {'Content-Type': resp.headers.get('content-type','application/json')})
    except requests.exceptions.RequestException as e:
        return ({"detail": str(e)}, 500)


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
            return ({"detail": str(e)}, 500)


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
