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
        "alergias": request.form["alergias"]
    }

    if usuarios.find_one({"curp": datos["curp"]}):
        return render_template("mensaje.html", titulo="CURP ya registrada", mensaje="Ese CURP ya está registrado", link="/login", texto_link="Inicia sesión")

    usuarios.insert_one(datos)
    return render_template("mensaje.html", titulo="Registro exitoso", mensaje="¡Tu registro fue guardado!", link="/login", texto_link="Inicia sesión")

@app.route("/login")
def mostrar_login():
    return render_template("login.html")

@app.route("/iniciar_sesion", methods=["POST"])
def iniciar_sesion():
    curp = request.form["curp"]
    email = request.form["email"]

    usuario = usuarios.find_one({"curp": curp, "email": email})

    if usuario:
        return render_template("mensaje.html", titulo="Bienvenido", mensaje=f"Bienvenido, {usuario['nombres']}", link="/", texto_link="Ir al inicio")
    else:
        return render_template("mensaje.html", titulo="Error", mensaje="CURP o correo incorrecto", link="/login", texto_link="Intentar de nuevo")

@app.route("/reinscripcion", methods=["GET", "POST"])
def reinscripcion():
    if request.method == "POST":
        curp = request.form["curp"]
        alumno = usuarios.find_one({"curp": curp})
        if alumno:
            return render_template("reinscripcion_form.html", alumno=alumno)
        else:
            return render_template("mensaje.html", titulo="No encontrado", mensaje="CURP no encontrado", link="/reinscripcion", texto_link="Volver")
    return render_template("buscar_reinscripcion.html")

@app.route("/guardar_reinscripcion", methods=["POST"])
def guardar_reinscripcion():
    curp = request.form["curp"]
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

# ----------- ADMIN -----------

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

@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    lista_usuarios = []
    if request.method == "POST":
        busqueda = request.form.get("busqueda", "")
        lista_usuarios = list(usuarios.find({
            "$or": [
                {"nombres": {"$regex": busqueda, "$options": "i"}},
                {"curp": {"$regex": busqueda, "$options": "i"}}
            ]
        }))
    else:
        lista_usuarios = list(usuarios.find())

    return render_template("admin.html", usuarios=lista_usuarios)

@app.route("/admin", methods=["POST"])
def admin_post():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    busqueda = request.form["busqueda"]
    lista_usuarios = list(usuarios.find({
        "$or": [
            {"nombres": {"$regex": busqueda, "$options": "i"}},
            {"curp": {"$regex": busqueda, "$options": "i"}}
        ]
    }))
    return render_template("admin.html", usuarios=lista_usuarios)

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
            "alergias": request.form["alergias"]
        }

        usuarios.update_one({"curp": curp}, {"$set": datos_actualizados})

        return render_template("mensaje.html", titulo="Actualización exitosa", mensaje="Datos actualizados correctamente", link="/admin", texto_link="Volver al panel")

    return render_template("editar_alumno.html", alumno=alumno)

# ----------- CERRAR SESIÓN ADMIN -----------
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/admin/login")

if __name__ == "__main__":
    app.run(debug=True)
