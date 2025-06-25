from flask import Flask, request, render_template, redirect
from pymongo import MongoClient

app = Flask(__name__)

# Conexión a MongoDB Atlas
client = MongoClient("mongodb+srv://armando59:trejo.arty@cluster0.osxgqoy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["cbtis272"]
usuarios = db["usuarios"]

@app.route("/")
def inicio():
    return redirect("/login")

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
        return "Ese CURP ya está registrado. <a href='/login'>Inicia sesión</a>"

    usuarios.insert_one(datos)
    return "¡Registro exitoso! <a href='/login'>Inicia sesión</a>"

@app.route("/login")
def mostrar_login():
    return render_template("login.html")

@app.route("/iniciar_sesion", methods=["POST"])
def iniciar_sesion():
    curp = request.form["curp"]
    email = request.form["email"]

    usuario = usuarios.find_one({"curp": curp, "email": email})

    if usuario:
        return f"¡Bienvenido {usuario['nombres']}!"
    else:
        return "CURP o correo incorrecto. <a href='/login'>Intenta de nuevo</a>"

if __name__ == "__main__":
    app.run(debug=True)
