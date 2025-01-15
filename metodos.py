import psycopg2
import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

### Jose Antonio Navarro Perez

def ejecutar_sql(sql_text, params=None):
    host = "localhost"
    port = "5432"
    dbname = "alexsoft"
    user = "postgres"
    password = "postgres"

    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )

        cursor = connection.cursor()

        if params:
            cursor.execute(sql_text, params)
        else:
            cursor.execute(sql_text)

        # Si la consulta no devuelve resultados (como un INSERT)
        if cursor.description is None:
            connection.commit()
            cursor.close()
            connection.close()
            return None

        # Para consultas SELECT
        columnas = [desc[0] for desc in cursor.description]
        resultados = cursor.fetchall()
        datos = [dict(zip(columnas, fila)) for fila in resultados]

        cursor.close()
        connection.close()

        return datos

    except psycopg2.Error as e:
        print("Error:", e)
        return {"error": str(e)}, 500

# Ruta de prueba
@app.route('/api/test', methods=['GET'])
def hola_mundo():
    return jsonify({"msg": "Hola, mundo!"})

# Rutas de autenticación
@app.route('/api/auth/login', methods=['POST'])
def gestor_login():
    try:
        body_request = request.json
        user = body_request["user"]
        passwd = body_request["passwd"]

        query = """
            SELECT g.id, g.usuario, e.nombre
            FROM public."Gestor" g
            JOIN public."Empleado" e ON g.empleado = e.id
            WHERE g.usuario = %s 
            AND g.passwd = %s
        """
        resultado = ejecutar_sql(query, (user, passwd))

        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]

        if not resultado:
            return jsonify({"error": "Credenciales inválidas"}), 401

        return jsonify({
            "id": resultado[0]['id'],
            "usuario": resultado[0]['usuario'],
            "nombre": resultado[0]['nombre']
        })

    except KeyError:
        return jsonify({"error": "JSON inválido"}), 400

# Rutas de empleados
@app.route('/api/empleados', methods=['GET'])
def obtener_empleados():
    query = """
        SELECT e.nombre,
        CASE 
            WHEN g.id IS NOT NULL THEN 'Gestor'
            WHEN p.id IS NOT NULL THEN 'Programador'
        END as empleado
        FROM public."Empleado" e
        LEFT JOIN public."Gestor" g ON e.id = g.empleado
        LEFT JOIN public."Programador" p ON e.id = p.empleado
    """
    resultado = ejecutar_sql(query)
    if isinstance(resultado, tuple):
        return jsonify(resultado[0]), resultado[1]
    return jsonify(resultado)

@app.route('/api/programadores', methods=['GET'])
def obtener_programadores():
    query = """
        SELECT p.*, e.email, e.nombre
        FROM public."Programador" p
        JOIN public."Empleado" e ON p.empleado = e.id
    """
    resultado = ejecutar_sql(query)
    if isinstance(resultado, tuple):
        return jsonify(resultado[0]), resultado[1]
    return jsonify(resultado)

# Rutas de proyectos
@app.route('/api/proyectos', methods=['GET'])
def obtener_proyectos():
    query = """
        SELECT p.*, c.nombre_empresa as cliente_nombre
        FROM public."Proyecto" p
        JOIN public."Cliente" c ON p.cliente = c.id
    """
    resultado = ejecutar_sql(query)
    if isinstance(resultado, tuple):
        return jsonify(resultado[0]), resultado[1]
    return jsonify(resultado)

@app.route('/api/proyectos/activos', methods=['GET'])
def obtener_proyectos_activos():
    query = """
        SELECT p.id, p.nombre, p.descripcion, p.fecha_creacion, p.fecha_inicio, c.nombre_empresa as cliente
        FROM public."Proyecto" p
        JOIN public."Cliente" c ON p.cliente = c.id
        WHERE p.fecha_finalizacion > CURRENT_TIMESTAMP
        or p.fecha_finalizacion IS NULL
    """
    resultado = ejecutar_sql(query)
    if isinstance(resultado, tuple):
        return jsonify(resultado[0]), resultado[1]
    return jsonify(resultado)

@app.route('/api/proyectos/gestor', methods=['GET'])
def obtener_proyectos_por_gestor():
    try:
        body_request = request.json
        gestor_id = body_request["id"]

        query = """
                SELECT p.* 
                FROM public."Proyecto" p
                JOIN public."GestoresProyecto" gp ON p.id = gp.proyecto
                WHERE gp.gestor = %s
            """
        resultado = ejecutar_sql(query, (gestor_id,))
        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]
        return jsonify(resultado)

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al obtener las tareas: {str(e)}"}), 500

@app.route('/api/proyectos/crear', methods=['POST'])
def crear_proyecto():
    try:
        body_request = request.json
        nombre = body_request["nombre"]
        descripcion = body_request["descripcion"]
        fecha_inicio = body_request["fecha_inicio"]
        cliente = body_request["cliente"]

        fecha_creacion = datetime.datetime.now()

        query = """
            INSERT INTO public."Proyecto"
            (nombre, descripcion, fecha_creacion, fecha_inicio, cliente)
            VALUES (%s, %s, %s, %s, %s);
        """

        resultado = ejecutar_sql(query, (
            nombre,
            descripcion,
            fecha_creacion,
            fecha_inicio,
            cliente
        ))

        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]

        return jsonify({
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_creacion": fecha_creacion.isoformat(),
            "fecha_inicio": fecha_inicio,
            "cliente": cliente
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al crear el proyecto: {str(e)}"}), 500

@app.route('/api/proyectos/asignar-gestor', methods=['POST'])
def asignar_gestor_proyecto():
    try:
        body_request = request.json
        gestor = body_request["gestor"]
        proyecto = body_request["proyecto"]

        fecha_asignacion = datetime.datetime.now()

        query = """
            INSERT INTO public."GestoresProyecto"
            (gestor, proyecto, fecha_asignacion)
            VALUES (%s, %s, %s);
        """

        resultado = ejecutar_sql(query, (
            gestor,
            proyecto,
            fecha_asignacion
        ))

        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]

        return jsonify({
            "gestor": gestor,
            "proyecto": proyecto,
            "fecha_asignacion": fecha_asignacion.isoformat()
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al asignar el gestor al proyecto: {str(e)}"}), 500

@app.route('/api/proyectos/asignar-programador', methods=['POST'])
def asignar_programador_proyecto():
    try:
        body_request = request.json
        programador = body_request["programador"]
        proyecto = body_request["proyecto"]

        fecha_asignacion = datetime.datetime.now()

        query = """
            INSERT INTO public."ProgramadoresProyecto"
            (programador, proyecto, fecha_asignacion)
            VALUES (%s, %s, %s);
        """

        resultado = ejecutar_sql(query, (
            programador,
            proyecto,
            fecha_asignacion
        ))

        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]

        return jsonify({
            "programador": programador,
            "proyecto": proyecto,
            "fecha_asignacion": fecha_asignacion.isoformat()
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al asignar el programador al proyecto: {str(e)}"}), 500

@app.route('/api/proyectos/modificar-cliente', methods=['POST'])
def modificar_cliente_proyecto():
    try:
        body_request = request.json
        cliente = body_request["cliente"]
        proyecto = body_request["proyecto"]

        query = """
                UPDATE public."Proyecto"
                SET cliente = %s
                WHERE id = %s;
        """

        resultado = ejecutar_sql(query, (
            cliente,
            proyecto
        ))

        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]

        return jsonify({
            "cliente": cliente,
            "proyecto": proyecto
        }), 200

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al modificar el cliente del proyecto: {str(e)}"}), 500

# Rutas de tareas
@app.route('/api/tareas/crear', methods=['POST'])
def crear_tarea():
    try:
        body_request = request.json
        gestor = body_request["gestor"]
        nombre = body_request["nombre"]
        descripcion = body_request["descripcion"]
        estimacion = body_request["estimacion"]
        proyecto = body_request["proyecto"]

        fecha_creacion = datetime.datetime.now()

        query_comprobar_gestor = """
                SELECT *
                FROM public."GestoresProyecto"
                WHERE proyecto = %s 
                AND gestor = %s;
        """

        resultado_comprobar_gestor = ejecutar_sql(query_comprobar_gestor, (
            proyecto,
            gestor
        ))

        if not resultado_comprobar_gestor:
            return jsonify({"error": f"No estas asignado como gestor a este proyecto."}), 400

        if isinstance(resultado_comprobar_gestor, tuple):
            return jsonify(resultado_comprobar_gestor[0]), resultado_comprobar_gestor[1]

        query = """
                    INSERT INTO public."Tarea"
                    (nombre, descripcion, estimacion, fecha_creacion, proyecto)
                    VALUES (%s, %s, %s, %s, %s);
                """

        resultado = ejecutar_sql(query, (
            nombre,
            descripcion,
            estimacion,
            fecha_creacion,
            proyecto
        ))

        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]

        return jsonify({
            "nombre": nombre,
            "descripcion": descripcion,
            "estimacion": estimacion,
            "fecha_creacion": fecha_creacion.isoformat(),
            "proyecto": proyecto
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al añadir tarea al proyecto: {str(e)}"}), 500

@app.route('/api/tareas/asignar-programador', methods=['POST'])
def asignar_programador_tarea():
    try:
        body_request = request.json
        programador = body_request["programador"]
        tarea = body_request["tarea"]

        query = """
            UPDATE public."Tarea"
            SET programador = %s
            WHERE id = %s;
        """

        resultado = ejecutar_sql(query, (
            programador,
            tarea
        ))

        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]

        return jsonify({
            "programador": programador,
            "tarea": tarea
        }), 201

    except KeyError as e:
        return jsonify({"error": f"Campo requerido faltante: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al asignar el programador a la tarea: {str(e)}"}), 500

@app.route('/api/proyectos/<int:proyecto_id>/tareas', methods=['GET'])
def obtener_tareas_proyecto(proyecto_id):
    try:
        query = """
                SELECT t.* 
                FROM public."Tarea" t
                WHERE t.proyecto = %s
            """
        resultado = ejecutar_sql(query, (proyecto_id,))
        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]
        return jsonify(resultado)

    except Exception as e:
        return jsonify({"error": f"Error al obtener las tareas: {str(e)}"}), 500

@app.route('/api/proyectos/<int:proyecto_id>/tareas/asignadas', methods=['GET'])
def obtener_tareas_asignadas_proyecto(proyecto_id):
    try:
        query = """
                SELECT t.* 
                FROM public."Tarea" t
                WHERE t.proyecto = %s 
                AND t.programador IS NOT NULL
            """
        resultado = ejecutar_sql(query, (proyecto_id,))
        if isinstance(resultado, tuple):
            return jsonify(resultado[0]), resultado[1]
        return jsonify(resultado)

    except Exception as e:
        return jsonify({"error": f"Error al obtener las tareas: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)

"""
LISTADO DE RUTAS ORGANIZADAS:

# Ruta de prueba
GET /api/test

# Rutas de autenticación
POST /api/auth/login

# Rutas de empleados
GET /api/empleados
GET /api/programadores

# Rutas de proyectos
GET /api/proyectos
GET /api/proyectos/activos
GET /api/proyectos/gestor
POST /api/proyectos/crear
POST /api/proyectos/asignar-gestor
POST /api/proyectos/asignar-programador
POST /api/proyectos/modificar-cliente

# Rutas de tareas
POST /api/tareas/crear
POST /api/tareas/asignar-programador
GET /api/proyectos/{proyecto_id}/tareas
GET /api/proyectos/{proyecto_id}/tareas/asignadas
"""