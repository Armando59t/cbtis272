import os
import traceback
from flask import Flask, request, render_template, redirect, session
from pymongo import MongoClient
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)

# ---------- VARIABLES DE ENTORNO (RENDER) ----------
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave_respaldo")

# Ajustes de cookie para despliegues (Render usa HTTPS)
# Nota: SESSION_COOKIE_SECURE=True requiere HTTPS (ok en Render).
app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8)
)

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError(mongodb+srv://armando59:<armando.59>@cluster0.osxgqoy.mongodb.net/?appName=Cluster0)

client = MongoClient(MONGO_URI)
db = client["cbtis272"]

usuarios = db["usuarios"]
admins = db["admins"]
maestros = db["maestros"]

# ---------- SUBIDA DE ARCHIVOS ----------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {".xls", ".xlsx"}

# ---------- CONFIGURACIÓN DE CORREO (RENDER) ----------
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER")

mail = Mail(app)

# ---------- HELPERS ----------
def archivo_permitido(nombre):
    if not nombre:
        return False
    return os.path.splitext(nombre)[1].lower() in ALLOWED_EXTENSIONS

def solo_maestros(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if not session.get("maestro_logged"):
            # Para depuración, devolver mensaje claro en vez de redirect silencioso
            return render_template(
                "mensaje.html",
                titulo="Acceso restringido",
                mensaje="Debes iniciar sesión como maestro para ver esta sección.",
                link="/maestro/login",
                texto_link="Iniciar sesión"
            )
        return f(*args, **kwargs)
    return decorador

# ---------- RUTAS ----------
@app.route("/")
def inicio():
    return render_template("index.html")

# ---------- REGISTRO ----------
@app.route("/registro")
def mostrar_registro():
    return render_template("registro.html")

@app.route("/registrar", methods=["POST"])
def registrar():
    datos = request.form.to_dict()

    if usuarios.find_one({"curp": datos.get("curp")}):
        return render_template(
            "mensaje.html",
            titulo="Error",
            mensaje="CURP ya registrado",
            link="/login",
            texto_link="Iniciar sesión"
        )

    usuarios.insert_one(datos)
    return render_template(
        "mensaje.html",
        titulo="Registro exitoso",
        mensaje="Datos guardados correctamente",
        link="/login",
        texto_link="Iniciar sesión"
    )

# ---------- LOGIN ALUMNO ----------
@app.route("/login")
def mostrar_login():
    return render_template("login.html")

@app.route("/iniciar_sesion", methods=["POST"])
def iniciar_sesion():
    try:
        usuario = usuarios.find_one({
            "curp": request.form.get("curp"),
            "email": request.form.get("email")
        })

        if usuario:
            session.clear()
            session.permanent = True
            session["alumno"] = usuario["curp"]
            session["nombre"] = usuario.get("nombres", "Alumno")
            return render_template("menu_alumno.html", nombre=usuario.get("nombres", "Alumno"))
        else:
            return render_template(
                "mensaje.html",
                titulo="Error",
                mensaje="Datos incorrectos",
                link="/login",
                texto_link="Intentar de nuevo"
            )
    except Exception:
        app.logger.error("Error en iniciar_sesion:\n" + traceback.format_exc())
        return render_template("mensaje.html", titulo="Error", mensaje="Error interno", link="/", texto_link="Inicio")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- REINSCRIPCIÓN ----------
@app.route("/reinscripcion", methods=["GET", "POST"])
def reinscripcion():
    if not session.get("alumno"):
        return redirect("/login")

    alumno = usuarios.find_one({"curp": session["alumno"]})

    if request.method == "POST":
        nuevos = request.form.to_dict()
        nuevos["fecha_reinscripcion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        usuarios.update_one({"curp": alumno["curp"]}, {"$set": nuevos})
        return render_template(
            "mensaje.html",
            titulo="Éxito",
            mensaje="Reinscripción realizada",
            link="/",
            texto_link="Inicio"
        )

    return render_template("reinscripcion_form.html", alumno=alumno)

# ---------- ADMIN ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        try:
            admin = admins.find_one({
                "usuario": request.form.get("usuario"),
                "password": request.form.get("password")
            })

            if admin:
                session.clear()
                session.permanent = True
                session["admin"] = True
                return redirect("/admin")

            return render_template(
                "mensaje.html",
                titulo="Error",
                mensaje="Acceso denegado",
                link="/admin/login",
                texto_link="Intentar"
            )
        except Exception:
            app.logger.error("Error en admin_login:\n" + traceback.format_exc())
            return render_template("mensaje.html", titulo="Error", mensaje="Error interno", link="/admin/login", texto_link="Volver")

    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin/login")
    return render_template("admin.html", usuarios=list(usuarios.find()))

# ---------- MAESTROS (mejorado y debug-safe) ----------
@app.route("/maestro/login", methods=["GET", "POST"])
def login_maestro():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        password = request.form.get("password")

        try:
            maestro = maestros.find_one({
                "usuario": usuario,
                "password": password
            })
        except Exception:
            app.logger.error("Error consultando maestros:\n" + traceback.format_exc())
            return render_template("mensaje.html", titulo="Error", mensaje="Error al consultar base de datos", link="/maestro/login", texto_link="Volver")

        if maestro:
            # eliminar otras sesiones sin borrar toda la cookie
            session.pop("alumno", None)
            session.pop("admin", None)

            session.permanent = True
            session["maestro_logged"] = True
            session["maestro_nombre"] = maestro.get("nombre", "Maestro")

            # Debug: imprimir sesión en logs (remueve en producción si quieres)
            app.logger.info(f"Sesión maestro creada: {session.get('maestro_nombre')}")

            return redirect("/maestro")

        return render_template(
            "mensaje.html",
            titulo="Error",
            mensaje="Usuario o contraseña incorrectos",
            link="/maestro/login",
            texto_link="Intentar de nuevo"
        )

    return render_template("maestro_login.html")

@app.route("/maestro")
@solo_maestros
def panel_maestro():
    # usar get para evitar KeyError si la sesión no está bien
    nombre = session.get("maestro_nombre", "Maestro")
    return render_template("maestro_menu.html", nombre=nombre)

@app.route("/maestro/subir_excel")
@solo_maestros
def subir_excel():
    return render_template("subir_excel_maestro.html")

@app.route("/maestro/enviar_excel", methods=["POST"])
@solo_maestros
def enviar_excel():
    archivo = request.files.get("excel")
    correo = request.form.get("correo")

    if not archivo or archivo.filename == "" or not archivo_permitido(archivo.filename):
        return render_template(
            "mensaje.html",
            titulo="Error",
            mensaje="Archivo inválido",
            link="/maestro",
            texto_link="Volver"
        )

    nombre_seguro = secure_filename(archivo.filename)
    ruta = os.path.join(UPLOAD_FOLDER, nombre_seguro)
    archivo.save(ruta)

    try:
        msg = Message(
            "Archivo Excel - BWERBUNG",
            recipients=[correo]
        )
        msg.body = f"Archivo enviado desde BWERBUNG por el maestro {session.get('maestro_nombre', 'Maestro')}."

        with open(ruta, "rb") as f:
            msg.attach(
                nombre_seguro,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f.read()
            )

        mail.send(msg)

    except Exception:
        app.logger.error("Error enviando correo:\n" + traceback.format_exc())
        if os.path.exists(ruta):
            os.remove(ruta)
        return render_template(
            "mensaje.html",
            titulo="Error",
            mensaje="No se pudo enviar el correo (revisa logs).",
            link="/maestro",
            texto_link="Volver"
        )

    if os.path.exists(ruta):
        os.remove(ruta)

    return render_template(
        "mensaje.html",
        titulo="Éxito",
        mensaje="Archivo enviado correctamente",
        link="/maestro",
        texto_link="Volver"
    )

# ---------- EJECUCIÓN (RENDER) ----------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )

