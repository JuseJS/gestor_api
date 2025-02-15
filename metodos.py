# Jose Antonio Navarro Perez

import psycopg2
import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)


### Helper Functions ###
def handle_response(data, status_code=200):
    """
    Helper function to handle HTTP responses.
    Handles both successful responses and errors.
    """
    if isinstance(data, tuple) and len(data) == 2:
        return jsonify(data[0]), data[1]

    if status_code >= 400:  # It's an error
        return jsonify({"error": str(data)}), status_code

    return jsonify(data), status_code


def handle_request(required_fields=None):
    """
    Helper function to validate required fields in the request.
    Returns a dictionary with the validated fields or raises an exception.
    """
    try:
        body = request.json
        if required_fields:
            missing_fields = [field for field in required_fields if field not in body]
            if missing_fields:
                raise KeyError(f"Missing required fields: {', '.join(missing_fields)}")
        return body
    except Exception as e:
        raise KeyError(str(e))


### Database Connection Function ###
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

        if cursor.description is None:
            connection.commit()
            cursor.close()
            connection.close()
            return None

        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in results]

        cursor.close()
        connection.close()

        return data

    except psycopg2.Error as e:
        print("Error:", e)
        return {"error": str(e)}, 500


### Test Route ###
@app.route('/api/test', methods=['GET'])
def hello_world():
    return handle_response({"msg": "Hello, world!"})


### Authentication Routes ###
@app.route('/api/auth/login', methods=['POST'])
def manager_login():
    try:
        body = handle_request(required_fields=["user", "passwd"])

        query = """
            SELECT g.id, g.usuario, e.nombre
            FROM public."Gestor" g
            JOIN public."Empleado" e ON g.empleado = e.id
            WHERE g.usuario = %s 
            AND g.passwd = %s
        """
        result = ejecutar_sql(query, (body["user"], body["passwd"]))

        if not result:
            return handle_response("Invalid credentials", 401)

        return handle_response({
            "id": result[0]['id'],
            "user": result[0]['usuario'],
            "name": result[0]['nombre'],
            "role": "Gestor"
        })
    except KeyError as e:
        return handle_response(str(e), 400)


### Employee Routes ###
@app.route('/api/empleados', methods=['GET'])
def get_employees():
    query = """
        SELECT e.nombre,
        CASE 
            WHEN g.id IS NOT NULL THEN 'Gestor'
            WHEN p.id IS NOT NULL THEN 'Programador'
        END as employee_type
        FROM public."Empleado" e
        LEFT JOIN public."Gestor" g ON e.id = g.empleado
        LEFT JOIN public."Programador" p ON e.id = p.empleado
    """
    result = ejecutar_sql(query)
    return handle_response(result)


@app.route('/api/programadores', methods=['GET'])
def get_programmers():
    query = """
        SELECT p.id, e.nombre
        FROM public."Programador" p
        JOIN public."Empleado" e ON p.empleado = e.id
    """
    result = ejecutar_sql(query)
    return handle_response(result)


### Project Routes ###
# Project Retrieval Routes
@app.route('/api/proyectos/finalizados', methods=['GET'])
def get_projects():
    query = """
        SELECT p.*
        FROM public."Proyecto" p
        WHERE p.fecha_finalizacion < CURRENT_TIMESTAMP
        AND p.fecha_finalizacion IS NOT NULL
    """
    result = ejecutar_sql(query)
    return handle_response(result)


@app.route('/api/proyectos/activos', methods=['GET'])
def get_active_projects():
    query = """
        SELECT p.id, p.nombre, p.descripcion, p.fecha_creacion, p.fecha_inicio, p.cliente
        FROM public."Proyecto" p
        WHERE p.fecha_finalizacion > CURRENT_TIMESTAMP
        or p.fecha_finalizacion IS NULL
    """
    result = ejecutar_sql(query)
    print(result)
    return handle_response(result)


@app.route('/api/proyectos/gestor/activos', methods=['POST'])
def get_active_projects_by_manager():
    try:
        body = handle_request(required_fields=["id"])

        query = """
                SELECT p.id, p.nombre, p.descripcion, p.fecha_creacion, p.fecha_inicio, p.cliente
                FROM public."Proyecto" p
                JOIN public."GestoresProyecto" gp ON p.id = gp.proyecto
                WHERE p.fecha_finalizacion > CURRENT_TIMESTAMP
                OR p.fecha_finalizacion IS NULL
                AND gp.gestor = %s
            """
        result = ejecutar_sql(query, (body["id"],))
        print(result)
        return handle_response(result)

    except KeyError as e:
        return handle_response(str(e), 400)
    except Exception as e:
        return handle_response(f"Error fetching projects: {str(e)}", 500)


@app.route('/api/proyectos/gestor/finalizados', methods=['POST'])
def get_ended_projects_by_manager():
    try:
        body = handle_request(required_fields=["id"])

        query = """
                SELECT p.*
                FROM public."Proyecto" p
                JOIN public."GestoresProyecto" gp ON p.id = gp.proyecto
                WHERE p.fecha_finalizacion < CURRENT_TIMESTAMP
                AND p.fecha_finalizacion IS NOT NULL
                AND gp.gestor = %s
            """
        result = ejecutar_sql(query, (body["id"],))
        print(result)
        return handle_response(result)

    except KeyError as e:
        return handle_response(str(e), 400)
    except Exception as e:
        return handle_response(f"Error fetching projects: {str(e)}", 500)


@app.route('/api/proyectos/<int:proyecto_id>/obtener-programadores', methods=['GET'])
def get_project_assigned_programmers(proyecto_id):
    try:
        query = """
            SELECT p.id, e.nombre
            FROM public."ProgramadoresProyecto" pp
            JOIN public."Programador" p ON pp.programador = p.id
            JOIN public."Empleado" e ON p.empleado = e.id
            WHERE pp.proyecto = %s
        """
        result = ejecutar_sql(query, (proyecto_id,))
        return handle_response(result)

    except Exception as e:
        return handle_response(f"Error: {str(e)}", 500)


# Project Management Routes
@app.route('/api/proyectos/crear', methods=['POST'])
def create_project():
    try:
        body = handle_request(required_fields=["name", "description", "startDate", "client"])
        creation_date = datetime.datetime.now()

        query = """
            INSERT INTO public."Proyecto"
            (nombre, descripcion, fecha_creacion, fecha_inicio, cliente)
            VALUES (%s, %s, %s, %s, %s);
        """

        result = ejecutar_sql(query, (
            body["name"],
            body["description"],
            creation_date,
            body["startDate"],
            body["client"]
        ))

        return handle_response({
            "name": body["name"],
            "description": body["description"],
            "creation_date": creation_date.isoformat(),
            "start_date": body["startDate"],
            "client": body["client"]
        }, 201)

    except KeyError as e:
        return handle_response(str(e), 400)
    except Exception as e:
        return handle_response(f"Error creating project: {str(e)}", 500)


# Project Assignment Routes
@app.route('/api/proyectos/asignar-gestor', methods=['POST'])
def assign_manager_to_project():
    try:
        body = handle_request(required_fields=["gestor", "proyecto"])
        assignment_date = datetime.datetime.now()

        query = """
            INSERT INTO public."GestoresProyecto"
            (gestor, proyecto, fecha_asignacion)
            VALUES (%s, %s, %s);
        """

        result = ejecutar_sql(query, (
            body["gestor"],
            body["proyecto"],
            assignment_date
        ))

        return handle_response({
            "manager": body["gestor"],
            "project": body["proyecto"],
            "assignment_date": assignment_date.isoformat()
        }, 201)

    except KeyError as e:
        return handle_response(str(e), 400)
    except Exception as e:
        return handle_response(f"Error assigning manager to project: {str(e)}", 500)


@app.route('/api/proyectos/asignar-programador', methods=['POST'])
def assign_programmer_to_project():
    try:
        body = handle_request(required_fields=["programador", "proyecto"])
        assignment_date = datetime.datetime.now()

        query = """
            INSERT INTO public."ProgramadoresProyecto"
            (programador, proyecto, fecha_asignacion)
            VALUES (%s, %s, %s);
        """

        result = ejecutar_sql(query, (
            body["programador"],
            body["proyecto"],
            assignment_date
        ))

        return handle_response({
            "programmer": body["programador"],
            "project": body["proyecto"],
            "assignment_date": assignment_date.isoformat()
        }, 201)

    except KeyError as e:
        return handle_response(str(e), 400)
    except Exception as e:
        return handle_response(f"Error assigning programmer to project: {str(e)}", 500)


@app.route('/api/proyectos/modificar-cliente', methods=['POST'])
def update_project_client():
    try:
        body = handle_request(required_fields=["cliente", "proyecto"])

        query = """
                UPDATE public."Proyecto"
                SET cliente = %s
                WHERE id = %s;
        """

        result = ejecutar_sql(query, (
            body["cliente"],
            body["proyecto"]
        ))

        return handle_response({
            "client": body["cliente"],
            "project": body["proyecto"]
        }, 200)

    except KeyError as e:
        return handle_response(str(e), 400)
    except Exception as e:
        return handle_response(f"Error updating project client: {str(e)}", 500)


### Task Routes ###
# Task Creation and Assignment
@app.route('/api/tareas/crear', methods=['POST'])
def create_task():
    try:
        body = handle_request(required_fields=["gestor", "nombre", "descripcion", "estimacion", "proyecto"])
        creation_date = datetime.datetime.now()

        query_check_manager = """
            SELECT *
            FROM public."GestoresProyecto"
            WHERE proyecto = %s 
            AND gestor = %s;
        """
        result_check_manager = ejecutar_sql(query_check_manager, (
            body["proyecto"],
            body["gestor"]
        ))

        if not result_check_manager:
            return handle_response("You are not assigned as a manager to this project.", 400)

        query = """
            INSERT INTO public."Tarea"
            (nombre, descripcion, estimacion, fecha_creacion, proyecto, programador)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        params = (
            body["nombre"],
            body["descripcion"],
            body["estimacion"],
            creation_date,
            body["proyecto"],
            body.get("programador")
        )

        result = ejecutar_sql(query, params)

        response_data = {
            "id": result[0]["id"] if result else None,
            "nombre": body["nombre"],
            "descripcion": body["descripcion"],
            "estimacion": body["estimacion"],
            "fecha_creacion": creation_date.isoformat(),
            "proyecto": body["proyecto"],
            "programador": body.get("programador")
        }

        return handle_response(response_data, 201)

    except KeyError as e:
        return handle_response(str(e), 400)
    except Exception as e:
        return handle_response(f"Error adding task to project: {str(e)}", 500)


@app.route('/api/tareas/asignar-programador', methods=['POST'])
def assign_programmer_to_task():
    try:
        body = handle_request(required_fields=["programador", "tarea"])

        query = """
            UPDATE public."Tarea"
            SET programador = %s
            WHERE id = %s;
        """

        result = ejecutar_sql(query, (
            body["programador"],
            body["tarea"]
        ))

        return handle_response({
            "programmer": body["programador"],
            "task": body["tarea"]
        }, 201)

    except KeyError as e:
        return handle_response(str(e), 400)
    except Exception as e:
        return handle_response(f"Error assigning programmer to task: {str(e)}", 500)


# Task Retrieval Routes
@app.route('/api/proyectos/<int:proyecto_id>/tareas', methods=['GET'])
def get_project_tasks(proyecto_id):
    try:
        query = """
                SELECT t.* 
                FROM public."Tarea" t
                WHERE t.proyecto = %s
            """
        result = ejecutar_sql(query, (proyecto_id,))
        return handle_response(result)

    except Exception as e:
        return handle_response(f"Error fetching tasks: {str(e)}", 500)


@app.route('/api/proyectos/<int:proyecto_id>/tareas/asignadas', methods=['GET'])
def get_assigned_tasks(proyecto_id):
    try:
        query = """
                SELECT t.* 
                FROM public."Tarea" t
                WHERE t.proyecto = %s 
                AND t.programador IS NOT NULL
            """
        result = ejecutar_sql(query, (proyecto_id,))
        return handle_response(result)

    except Exception as e:
        return handle_response(f"Error fetching tasks: {str(e)}", 500)


if __name__ == '__main__':
    app.run(debug=True)

"""
LIST OF ORGANIZED ROUTES:

# Test route
GET /api/test

# Authentication routes
POST /api/auth/login

# Employee routes
GET /api/empleados
GET /api/programadores

# Project routes
GET /api/proyectos
GET /api/proyectos/activos
GET /api/proyectos/gestor
GET /api/proyectos/{proyecto_id}/obtener-programadores
POST /api/proyectos/crear
POST /api/proyectos/asignar-gestor
POST /api/proyectos/asignar-programador
POST /api/proyectos/modificar-cliente

# Task routes
POST /api/tareas/crear
POST /api/tareas/asignar-programador
GET /api/proyectos/{proyecto_id}/tareas
GET /api/proyectos/{proyecto_id}/tareas/asignadas
"""