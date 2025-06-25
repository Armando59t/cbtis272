from flask import Flask, request, render_template, redirect, session
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_super_secreta'

# Conexión a MongoDB Atlas
client = MongoClient("mongodb+srv://armando59:trejo.arty@cluster0.osxgqoy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["cbtis272"]
usuarios = db["usuarios"]

# Página de inicio
@app.route("/")
def inicio():
    return render_template("index.html")

# ------------------ REGISTRO ------------------

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
        return render_template("mensaje.html", titulo="CURP ya registrado", mensaje="Este CURP ya fue usado. Si ya te registraste, inicia sesión.", link="/login", texto_link="Ir al Login")

    usuarios.insert_one(datos)
    return render_template("mensaje.html", titulo="¡Registro Exitoso!", mensaje="Tu registro ha sido guardado correctamente.", link="/login", texto_link="Iniciar sesión")

# ------------------ LOGIN ------------------

@app.route("/login")
def mostrar_login():
    return render_template("login.html")

@app.route("/iniciar_sesion", methods=["POST"])
def iniciar_sesion():
    curp = request.form["curp"]
    email = request.form["email"]

    usuario = usuarios.find_one({"curp": curp, "email": email})

    if usuario:
        mensaje = f"¡Bienvenido {usuario['nombres']}!"
        return render_template("mensaje.html", titulo="Inicio de Sesión Correcto", mensaje=mensaje, link="/", texto_link="Volver al inicio")
    else:
        return render_template("mensaje.html", titulo="Error", mensaje="CURP o correo incorrecto.", link="/login", texto_link="Intentar de nuevo")

# ------------------ REINSCRIPCIÓN ------------------

@app.route("/reinscripcion", methods=["GET", "POST"])
def reinscripcion():
    if request.method == "POST":
        curp = request.form["curp"]
        alumno = usuarios.find_one({"curp": curp})
        if alumno:
            return render_template("reinscripcion_form.html", alumno=alumno)
        else:
            return render_template("mensaje.html", titulo="No encontrado", mensaje="El CURP no se encontró.", link="/reinscripcion", texto_link="Intentar de nuevo")
    return render_template("buscar_reinscripcion.html")

@app.route("/actualizar_reinscripcion", methods=["POST"])
def actualizar_reinscripcion():
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
    return render_template("mensaje.html", titulo="¡Reinscripción Exitosa!", mensaje="Tus datos fueron actualizados correctamente.", link="/", texto_link="Volver al inicio")

# ------------------ ADMIN ------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]
        if usuario == "admin" and password == "1234":
            session["admin_logged_in"] = True
            return redirect("/admin")
        else:
            return render_template("mensaje.html", titulo="Error", mensaje="Usuario o contraseña incorrectos.", link="/admin/login", texto_link="Intentar de nuevo")
    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")
    lista_usuarios = list(usuarios.find())
    return render_template("admin.html", usuarios=lista_usuarios)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/")

# ------------------

if __name__ == "__main__":
    app.run(debug=True)
