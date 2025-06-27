from flask import Flask, request, render_template, redirect, session
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"

# Conexión a MongoDB Atlas
client = MongoClient("mongodb+srv://armando59:trejo.arty@cluster0.osxgqoy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["cbtis272"]
usuarios = db["usuarios"]
admins = db["admins"]

@app.route("/")
def inicio():
    return render_template("index.html")

# ---------- REGISTRO ----------
@app.route("/registro")
def mostrar_registro():
    return render_template("registro.html")

@app.route("/registrar", methods=["POST"])
def registrar():
    datos = {
        "apellido_paterno": request.form["apellido_paterno"],
        "apellido_materno": request.form["apellido_materno"],
        "nombres": request.form["nombres"],
        "curp": request.form["curp"],
        "fecha_nacimiento": request.form["fecha_nacimiento"],
        "lugar_nacimiento": request.form["lugar_nacimiento"],
        "estado_civil": request.form["estado_civil"],
        "periodo": request.form["periodo"],
        "semestre": request.form["semestre"],
        "turno": request.form["turno"],
        "carrera": request.form["carrera"],
        "colonia": request.form["colonia"],
        "domicilio": request.form["domicilio"],
        "cp": request.form["cp"],
        "telefono": request.form["telefono"],
        "email": request.form["email"],
        "tipo_sangre": request.form["tipo_sangre"],
        "alergias": request.form["alergias"],
        "nombre_tutor": request.form["nombre_tutor"],
        "telefono_tutor": request.form["telefono_tutor"],
        "correo_tutor": request.form["correo_tutor"],
        "secundaria": request.form["secundaria"],
        "discapacidad": request.form["discapacidad"],
        "observaciones_medicas": request.form["observaciones_medicas"],
        "contacto_emergencia": request.form["contacto_emergencia"],
        "telefono_emergencia": request.form["telefono_emergencia"]
    }

    if usuarios.find_one({"curp": datos["curp"]}):
        return render_template("mensaje.html", titulo="CURP ya registrada", mensaje="Ese CURP ya está registrado", link="/login", texto_link="Inicia sesión")

    usuarios.insert_one(datos)
    return render_template("mensaje.html", titulo="Registro exitoso", mensaje="¡Tu registro fue guardado correctamente!", link="/login", texto_link="Inicia sesión")

# ---------- LOGIN ALUMNO ----------
@app.route("/login")
def mostrar_login():
    return render_template("login.html")

@app.route("/iniciar_sesion", methods=["POST"])
def iniciar_sesion():
    curp = request.form["curp"]
    email = request.form["email"]

    usuario = usuarios.find_one({"curp": curp, "email": email})

    if usuario:
        session["alumno_nombre"] = usuario["nombres"]
        session["alumno_curp"] = usuario["curp"]
        return render_template("menu_alumno.html", nombre=usuario["nombres"])
    else:
        return render_template("mensaje.html", titulo="Error", mensaje="CURP o correo incorrecto", link="/login", texto_link="Intentar de nuevo")

# ---------- REINSCRIPCIÓN ----------
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
            "fecha_reinscripcion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        usuarios.update_one({"curp": curp}, {"$set": nuevos_datos})
        return render_template("mensaje.html", titulo="Reinscripción exitosa", mensaje="Tus datos fueron actualizados", link="/", texto_link="Ir al inicio")

    return render_template("reinscripcion_form.html", alumno=alumno)

# ---------- ADMIN ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        admin = admins.find_one({"usuario": usuario, "password": password})
        if admin:
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
