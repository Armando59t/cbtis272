import os
from flask import Flask, request, render_template, redirect, session
from pymongo import MongoClient
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)

# ---------- VARIABLES DE ENTORNO (RENDER) ----------
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave_respaldo")

MONGO_URI = os.environ.get("MONGO_URI")
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

# ---------- FUNCIONES ----------
def solo_maestros(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if not session.get("maestro_logged"):
            return redirect("/maestro/login")
        return f(*args, **kwargs)
    return decorador

def archivo_permitido(nombre):
    return os.path.splitext(nombre)[1].lower() in ALLOWED_EXTENSIONS

# ---------- INICIO ----------
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

    if usuarios.find_one({"curp": datos["curp"]}):
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
    usuario = usuarios.find_one({
        "curp": request.form["curp"],
        "email": request.form["email"]
    })

    if usuario:
        session.clear()
        session["alumno"] = usuario["curp"]
        session["nombre"] = usuario["nombres"]
        return render_template("menu_alumno.html", nombre=usuario["nombres"])
    else:
        return render_template(
            "mensaje.html",
            titulo="Error",
            mensaje="Datos incorrectos",
            link="/login",
            texto_link="Intentar de nuevo"
        )

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
        admin = admins.find_one({
            "usuario": request.form["usuario"],
            "password": request.form["password"]
        })

        if admin:
            session.clear()
            session["admin"] = True
            return redirect("/admin")

        return render_template(
            "mensaje.html",
            titulo="Error",
            mensaje="Acceso denegado",
            link="/admin/login",
            texto_link="Intentar"
        )

    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin/login")

    return render_template("admin.html", usuarios=list(usuarios.find()))

# ---------- MAESTROS ----------
@app.route("/maestro/login", methods=["GET", "POST"])
def login_maestro():
    if request.method == "POST":
        maestro = maestros.find_one({
            "usuario": request.form["usuario"],
            "password": request.form["password"]
        })

        if maestro:
            session.clear()
            session["maestro_logged"] = True
            session["maestro_nombre"] = maestro["nombre"]
            return redirect("/maestro")

        return render_template(
            "mensaje.html",
            titulo="Error",
            mensaje="Acceso denegado",
            link="/maestro/login",
            texto_link="Intentar"
        )

    return render_template("maestro_login.html")

@app.route("/maestro")
@solo_maestros
def panel_maestro():
    return render_template("maestro_menu.html", nombre=session["maestro_nombre"])

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
        msg.body = f"Archivo enviado desde BWERBUNG por el maestro {session['maestro_nombre']}."

        with open(ruta, "rb") as f:
            msg.attach(
                nombre_seguro,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f.read()
            )

        mail.send(msg)
    except Exception as e:
        if os.path.exists(ruta):
            os.remove(ruta)

        return render_template(
            "mensaje.html",
            titulo="Error",
            mensaje=f"No se pudo enviar el correo: {e}",
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
