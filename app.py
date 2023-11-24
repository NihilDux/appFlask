from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
from datetime import datetime
from flask_socketio import SocketIO, emit
import json

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app)

SECRET_KEY = 'your-secret-key'  # Cambiar esto por una clave segura.

def obtener_ultima_version():
    with open('data.json', 'r') as file:
        return json.load(file)

def obtener_profesor(profesor_id):
    data = request.get_json()
    return next((profesor for profesor in data.get('profesores', []) if profesor["id"] == profesor_id), None)

def obtener_curso(profesor_id, curso_id): ## Revisar esto
    profesor = obtener_profesor(profesor_id)
    return next((curso for curso in profesor["cursos"] if curso["id"] == curso_id), None)

@app.route('/crear_clase', methods=['POST'])
def crear_clase():
    datas = request.get_json()
    data = obtener_ultima_version()

    # Obtener los datos necesarios del cuerpo de la solicitud
    profesor_id = datas.get('profesor_id')
    curso_id = datas.get('curso_id')

    # Obtener la fecha actual como string en formato ISO
    fecha_actual = datetime.utcnow().strftime("%d,%m,%Y")

    # Obtener la información del curso
    curso = obtener_curso(profesor_id, curso_id)
    
    if curso:
        # Crear la nueva clase
        nueva_clase = {
            "id": len(data.get('clases', [])) + 1,
            "profesor_id": profesor_id,
            "curso_id": curso_id,
            "fecha": fecha_actual,
            "alumnos_registrados": [{"id": alumno["id"], "user": alumno["user"], "nombre": alumno["nombre"], "presente": "no"} for alumno in curso.get('alumnos', [])],
            # Agrega otros campos según sea necesario
        }

        # Realizar copia de seguridad antes de modificar los datos
        copia_seguridad = data.copy()

        # Agregar la nueva clase a la lista
        data.get('clases', []).append(nueva_clase)
        socketio.emit('update_data')

        try:
            # Guardar los datos en data.json después de la creación exitosa
            with open('data.json', 'w') as file:
                json.dump({"profesores": data.get('profesores', []), "usuarios": data.get('usuarios', []), "clases": data.get('clases', [])}, file, indent=2)

            return jsonify({"message": "Clase creada exitosamente", "clase": nueva_clase}), 201

        except Exception as e:
            # Revertir a la copia de seguridad en caso de error
            data = copia_seguridad
            with open('data.json', 'w') as file:
                json.dump(data, file, indent=2)
            
            return jsonify({"message": f"Error al crear la clase: {str(e)}"}), 500

    else:
        return jsonify({"message": "Curso no encontrado"}), 404



@app.route('/login', methods=['POST'])
def login():
    datas = request.get_json()
    username = datas.get('user')
    password = datas.get('password')

    data = obtener_ultima_version()

    user = next((u for u in data.get('usuarios', []) if u["user"] == username and u["password"] == password), None)

    if user:
        user_info = {'user_id': user['id'], 'username': user['user'], 'perfil': user['perfil']}
        
        # Genera un token JWT con la información del usuario
        token = jwt.encode(user_info, SECRET_KEY, algorithm='HS256')


        socketio.emit('data_updated')

        return jsonify({'access_token': token, 'user_id': user['id'], 'username': user['user']}), 200

    return jsonify({"message": "Credenciales incorrectas"}), 401

@socketio.on('update_data')
def handle_update():
    emit('data_updated', {'message': 'Datos actualizados'})



@app.route('/profesores', methods=['GET'])
def obtener_profesores():
    data = obtener_ultima_version()
    
    profesores_actualizados = data.get('profesores', [])

    socketio.emit('data_updated')

    return jsonify(profesores_actualizados), 200, {'Content-Type': 'application/json; charset=utf-8'}

@app.route('/profesores/<int:profesor_id>/cursos', methods=['GET'])
def obtener_cursos_profesor(profesor_id):
    data = obtener_ultima_version()

    profesor_actualizado = next((p for p in data.get('profesores', []) if p["id"] == profesor_id), None)

    if not profesor_actualizado:
        return jsonify({"message": "Profesor no encontrado"}, 404)

    socketio.emit('data_updated')

    return jsonify(profesor_actualizado["cursos"]), 200, {'Content-Type': 'application/json; charset=utf-8'}


@app.route('/profesores/<int:profesor_id>/cursos/<int:curso_id>/alumnos', methods=['GET'])
def obtener_alumnos_curso(profesor_id, curso_id):
    data = obtener_ultima_version()

    profesor_actualizado = next((p for p in data.get('profesores', []) if p["id"] == profesor_id), None)
    
    if not profesor_actualizado:
        return jsonify({"message": "Profesor no encontrado"}, 404)

    curso_actualizado = next((c for c in profesor_actualizado["cursos"] if c["id"] == curso_id), None)
    
    if not curso_actualizado:
        return jsonify({"message": "Curso no encontrado"}, 404)

    socketio.emit('data_updated')

    return jsonify(curso_actualizado["alumnos"]), 200


@app.route('/buscar_profesor', methods=['POST'])
def buscar_profesor_por_usuario():
    data = obtener_ultima_version()
    datas = request.get_json()
    username = datas.get('username')
    
    user_encontrado = next((u for u in data.get('usuarios',[]) if u["user"] == username), None)
    
    if user_encontrado:

        nombre_profesor = user_encontrado['nombre']
        profesor = next((p for p in data.get('profesores',[]) if p["nombre"] == nombre_profesor), None)
        
        if profesor:
            socketio.emit('data_updated')
            return jsonify({'id': profesor['id']}), 200
    
    return jsonify({"message": "Profesor no encontrado"}, 404)


@app.route('/usuario', methods=['POST'])
def obtener_usuario_por_username():
    data = obtener_ultima_version()
    datas = request.get_json()
    username = datas.get('user')
    usuario = next((u for u in data.get('usuarios',[]) if u["user"] == username), None)
    if usuario:
        socketio.emit('data_updated')
        return jsonify(usuario), 200
    return jsonify({"message": "Usuario no encontrado"}, 404)

@socketio.on('update_data')
def handle_update():
    # Emitir datos actualizados a todos los clientes conectados
    emit('data_updated', {'message': 'Datos actualizados'})

if __name__ == '__main__':
    app.run(debug=True)
