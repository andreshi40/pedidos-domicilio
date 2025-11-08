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


@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    """Página para que un admin vea la lista de usuarios.

    Si existe un access token en la sesión, el servidor lo usará para llamar
    al API Gateway y obtener la lista; también permite hacer logout.
    """
    users = None
    # logout action
    if request.method == "POST" and request.form.get("action") == "logout":
        session.pop("access_token", None)
        flash("Sesión cerrada.")
        return redirect(url_for("admin_users"))

    token = session.get("access_token")
    if token:
        try:
            resp = requests.get(f"{API_GATEWAY_URL}/api/v1/auth/users", headers={"Authorization": f"Bearer {token}"}, timeout=5)
            resp.raise_for_status()
            users = resp.json().get("users", [])
        except requests.exceptions.RequestException as e:
            flash(f"Error llamando al API: {e}")
            users = None

    return render_template("admin_users.html", title="Usuarios (admin)", users=users)



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
                    session["access_token"] = token
                    # fetch user info to store email/role in session
                    try:
                        me = requests.get(f"{API_GATEWAY_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                        if me.status_code == 200:
                            u = me.json()
                            session["user_email"] = u.get("email")
                            session["user_role"] = u.get("role")
                    except requests.exceptions.RequestException:
                        pass
                    flash("Login exitoso.")
                    return redirect(url_for("admin_users"))
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
                            session["access_token"] = token
                            # fetch user info
                            try:
                                me = requests.get(f"{API_GATEWAY_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                                if me.status_code == 200:
                                    u = me.json()
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
    """Página pública para clientes: buscador de restaurantes."""
    q = request.args.get('q')
    try:
        if q:
            resp = requests.get(f"{API_GATEWAY_URL}/api/v1/restaurantes?q={q}", timeout=5)
        else:
            resp = requests.get(f"{API_GATEWAY_URL}/api/v1/restaurantes?limit=20", timeout=5)
        if resp.status_code == 200:
            restos = resp.json().get('restaurantes') or resp.json()
        else:
            restos = []
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
    try:
        r = requests.get(f"{API_GATEWAY_URL}/api/v1/restaurantes/{rest_id}", timeout=5)
        if r.status_code == 200:
            restaurante = r.json()
        else:
            flash('No se pudo obtener la información del restaurante.')
            return redirect(url_for('client_index'))
    except requests.exceptions.RequestException:
        flash('Error conectando al gateway.')
        return redirect(url_for('client_index'))

    # Obtener menú (si existe endpoint)
    try:
        m = requests.get(f"{API_GATEWAY_URL}/api/v1/restaurantes/{rest_id}/menu", timeout=5)
        menu = m.json() if m.status_code == 200 else []
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
                flash('Pedido creado correctamente.')
                return redirect(url_for('order_status', order_id=order_id))
            else:
                msg = resp.json().get('detail') if resp.headers.get('content-type','').startswith('application/json') else resp.text
                flash(f'Error creando pedido: {msg}')
        except requests.exceptions.RequestException as e:
            flash(f'Error conectando al gateway: {e}')

    return render_template('restaurant.html', title=restaurante.get('nombre','Restaurante'), restaurante=restaurante, menu=menu)


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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
