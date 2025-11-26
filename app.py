# app.py - BWERBUNG (Flask) - Versión con módulo Maestro integrado
import os
from datetime import datetime
from functools import wraps
from flask import Flask, request, render_template, redirect, session, url_for
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from flask_mail import Mail, Message

# ===== CONFIG =====
app = Flask(__name__)

# Usa variables de entorno (recomendado). Si no existen, usa valores por defecto para desarrollo.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave_secreta_segura")

MONGO_URI = os.environ.get("MONGO_URI",
    "mongodb+srv://armando59:trejo.arty@cluster0.osxgqoy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI)
db = client["cbtis272"]
usuarios = db["usuarios"]
admins = db["admins"]
maestros = db["maestros"]  # nueva colección para maestros

# Carpeta para subir archivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {".xls", ".xlsx"}  # extensiones permitidas

# ===== CONFIG MAIL =====
# Rellenar estas variables en el entorno de despliegue (Render)
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "tu_correo@gmail.com")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "tu_contraseña_app")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"])

mail = Mail(app)

# ===== Helpers =====
def allowed_file(filename):
    if not filename:
        return False
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS

def solo_maestros(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("maestro_logged_in"):
            return redirect("/maestro/login")
        return f(*args, **kwargs)
    return wrapper

# ===== RUTAS PÚBLICAS =====
@app.route("/")
def inicio():
    return render_template("index.html")

# ----------- REGISTRO ALUMNO -----------
@app.route("/registro")
def mostrar_registro():
    return render_template("registro.html")

@app.route("/registrar", methods=["POST"])
def registrar():
    datos = {
        "apellido_paterno": request.form["apellido_paterno"],
        "apellido_materno": request.form["apellido_materno"],
        "nombres": request.form["nombres"],
        "periodo": request.form["periodo"],
        "semestre": request.form["semestre"],
        "turno": request.form["turno"],
        "carrera": request.form["carrera"],
        "curp": request.form["curp"],
        "fecha_nacimiento": request.form["fecha_nacimiento"],
        "lugar_nacimiento": request.form["lugar_nacimiento"],
        "estado_civil": request.form["estado_civil"],
        "colonia": request.form["colonia"],
        "domicilio": request.form["domicilio"],
        "cp": request.form["cp"],
        "telefono": request.form["telefono"],
        "email": request.form["email"],
        "tipo_sangre": request.form["tipo_sangre"],
        "alergias": request.form["alergias"],
        "nombre_tutor": request.form["nombre_tutor"],
        "telefono_tutor": request.form["telefono_tutor"],
        "email_tutor": request.form["email_tutor"],
        "escuela_anterior": request.form["escuela_anterior"],
        "discapacidad": request.form["discapacidad"],
        "observaciones_medicas": request.form["observaciones_medicas"],
        "contacto_extra_nombre": request.form["contacto_extra_nombre"],
        "contacto_extra_telefono": request.form["contacto_extra_telefono"]
    }

    if usuarios.find_one({"curp": datos["curp"]}):
        return render_template("mensaje.html", titulo="CURP ya registrada", mensaje="Ese CURP ya está registrado", link="/login", texto_link="Inicia sesión")

    usuarios.insert_one(datos)
    return render_template("mensaje.html", titulo="Registro exitoso", mensaje="¡Tu registro fue guardado!", link="/login", texto_link="Inicia sesión")

# ===== LOGIN ALUMNO =====
@app.route("/login")
def mostrar_login():
    return render_template("login.html")

@app.route("/iniciar_sesion", methods=["POST"])
def iniciar_sesion():
    curp = request.form["curp"]
    email = request.form["email"]

    usuario = usuarios.find_one({"curp": curp, "email": email})
    if usuario:
        session.clear()
        session["alumno_nombre"] = usuario["nombres"]
        session["alumno_curp"] = usuario["curp"]
        return render_template("menu_alumno.html", nombre=usuario["nombres"])
    else:
        return render_template("mensaje.html", titulo="Error", mensaje="CURP o correo incorrecto", link="/login", texto_link="Intentar de nuevo")

# ===== LOGOUT (aplica a cualquier rol) =====
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ===== REINSCRIPCION ALUMNO =====
@app.route("/reinscripcion", methods=["GET", "POST"])
def reinscripcion():
    if not session.get("alumno_curp"):
        return redirect("/login")

    curp = session["alumno_curp"]
    alumno = usuarios.find_one({"curp": curp})

    if request.method == "POST":
        nuevos_datos = {
            "semestre": request.form["semestre"],
            "turno": request.form["turno"],
            "telefono": request.form["telefono"],
            "email": request.form["email"],
            "domicilio": request.form["domicilio"],
            "colonia": request.form["colonia"],
            "cp": request.form["cp"],
            "alergias": request.form["alergias"],
            "nombre_tutor": request.form["nombre_tutor"],
            "telefono_tutor": request.form["telefono_tutor"],
            "email_tutor": request.form["email_tutor"],
            "contacto_extra_nombre": request.form["contacto_extra_nombre"],
            "contacto_extra_telefono": request.form["contacto_extra_telefono"],
            "fecha_reinscripcion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        usuarios.update_one({"curp": curp}, {"$set": nuevos_datos})
        return render_template("mensaje.html", titulo="Reinscripción exitosa", mensaje="Tus datos fueron actualizados correctamente", link="/", texto_link="Volver al inicio")

    return render_template("reinscripcion_form.html", alumno=alumno)

# ===== ADMIN =====
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]
        admin = admins.find_one({"usuario": usuario, "password": password})
        if admin:
            session.clear()
            session["admin_logged_in"] = True
            return redirect("/admin")
        else:
            return render_template("mensaje.html", titulo="Acceso denegado", mensaje="Usuario o contraseña incorrectos", link="/admin/login", texto_link="Intentar de nuevo")
    return render_template("admin_login.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    usuarios_encontrados = []
    if request.method == "POST":
        busqueda = request.form["busqueda"]
        usuarios_encontrados = list(usuarios.find({
            "$or": [
                {"nombres": {"$regex": busqueda, "$options": "i"}},
                {"curp": {"$regex": busqueda, "$options": "i"}}
            ]
        }))
    else:
        usuarios_encontrados = list(usuarios.find())

    return render_template("admin.html", usuarios=usuarios_encontrados)

@app.route("/admin/alumno/<curp>")
def ver_alumno(curp):
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    alumno = usuarios.find_one({"curp": curp})
    if not alumno:
        return render_template("mensaje.html", titulo="No encontrado", mensaje="Alumno no encontrado", link="/admin", texto_link="Volver")
    return render_template("alumno_detalle.html", alumno=alumno)

@app.route("/admin/alumno/<curp>/editar", methods=["GET", "POST"])
def editar_alumno(curp):
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    alumno = usuarios.find_one({"curp": curp})
    if not alumno:
        return render_template("mensaje.html", titulo="No encontrado", mensaje="Alumno no encontrado", link="/admin", texto_link="Volver")

    if request.method == "POST":
        datos_actualizados = {
            "apellido_paterno": request.form["apellido_paterno"],
            "apellido_materno": request.form["apellido_materno"],
            "nombres": request.form["nombres"],
            "periodo": request.form["periodo"],
            "semestre": request.form["semestre"],
            "turno": request.form["turno"],
            "carrera": request.form["carrera"],
            "curp": request.form["curp"],
            "fecha_nacimiento": request.form["fecha_nacimiento"],
            "lugar_nacimiento": request.form["lugar_nacimiento"],
            "estado_civil": request.form["estado_civil"],
            "colonia": request.form["colonia"],
            "domicilio": request.form["domicilio"],
            "cp": request.form["cp"],
            "telefono": request.form["telefono"],
            "email": request.form["email"],
            "tipo_sangre": request.form["tipo_sangre"],
            "alergias": request.form["alergias"],
            "nombre_tutor": request.form["nombre_tutor"],
            "telefono_tutor": request.form["telefono_tutor"],
            "email_tutor": request.form["email_tutor"],
            "escuela_anterior": request.form["escuela_anterior"],
            "discapacidad": request.form["discapacidad"],
            "observaciones_medicas": request.form["observaciones_medicas"],
            "contacto_extra_nombre": request.form["contacto_extra_nombre"],
            "contacto_extra_telefono": request.form["contacto_extra_telefono"]
        }

        usuarios.update_one({"curp": curp}, {"$set": datos_actualizados})
        return render_template("mensaje.html", titulo="Actualización exitosa", mensaje="Datos actualizados correctamente", link="/admin", texto_link="Volver al panel")

    return render_template("editar_alumno.html", alumno=alumno)

# ===== MAESTRO: LOGIN, PANEL Y SUBIDA DE EXCEL =====
@app.route("/maestro/login", methods=["GET", "POST"])
def maestro_login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        maestro = maestros.find_one({"usuario": usuario, "password": password})
        if maestro:
            session.clear()
            session["maestro_logged_in"] = True
            session["maestro_nombre"] = maestro.get("nombre", usuario)
            return redirect("/maestro")
        else:
            return render_template("mensaje.html",
                titulo="Acceso denegado",
                mensaje="Usuario o contraseña incorrectos",
                link="/maestro/login",
                texto_link="Intentar de nuevo"
            )
    return render_template("maestro_login.html")

@app.route("/maestro")
@solo_maestros
def maestro_panel():
    return render_template("maestro_menu.html", nombre=session.get("maestro_nombre"))

@app.route("/maestro/subir_excel")
@solo_maestros
def subir_excel_maestro():
    return render_template("subir_excel_maestro.html")

@app.route("/maestro/enviar_excel", methods=["POST"])
@solo_maestros
def enviar_excel_maestro():
    if "excel" not in request.files:
        return render_template("mensaje.html", titulo="Error", mensaje="No se seleccionó ningún archivo", link="/maestro", texto_link="Volver")

    archivo = request.files["excel"]
    correo_destino = request.form.get("correo", "").strip()

    if archivo.filename == "":
        return render_template("mensaje.html", titulo="Error", mensaje="Nombre de archivo inválido", link="/maestro", texto_link="Volver")

    if not allowed_file(archivo.filename):
        return render_template("mensaje.html", titulo="Error", mensaje="Solo se permiten archivos Excel (.xlsx, .xls)", link="/maestro", texto_link="Volver")

    if not correo_destino:
        return render_template("mensaje.html", titulo="Error", mensaje="Debe indicar un correo destinatario", link="/maestro", texto_link="Volver")

    # Guardar archivo temporalmente con nombre seguro
    filename = secure_filename(archivo.filename)
    ruta_guardada = os.path.join(UPLOAD_FOLDER, f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
    archivo.save(ruta_guardada)

    # Preparar y enviar correo
    try:
        msg = Message("Archivo Excel enviado desde Bwerbung",
                      sender=app.config["MAIL_DEFAULT_SENDER"],
                      recipients=[correo_destino])
        msg.body = f"El maestro {session.get('maestro_nombre')} ha enviado un archivo Excel desde Bwerbung.\n\nArchivo: {filename}"
        with app.open_resource(ruta_guardada) as fp:
            # MIME tipo genérico para Excel
            msg.attach(filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fp.read())

        mail.send(msg)
    except Exception as e:
        # Si falla el envío, borrar archivo temporal y mostrar error
        if os.path.exists(ruta_guardada):
            os.remove(ruta_guardada)
        return render_template("mensaje.html", titulo="Error al enviar", mensaje=f"No se pudo enviar el correo: {e}", link="/maestro", texto_link="Volver")

    # Borrar archivo temporal
    if os.path.exists(ruta_guardada):
        os.remove(ruta_guardada)

    return render_template("mensaje.html", titulo="Éxito", mensaje="Excel enviado correctamente", link="/maestro", texto_link="Volver")

# ===== EJECUCIÓN =====
if __name__ == "__main__":
    # En producción Render u otro hosting se suele arrancar con gunicorn.
    # Aquí lo dejamos en False por seguridad.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
