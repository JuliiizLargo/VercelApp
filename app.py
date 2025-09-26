from flask import Flask, request, jsonify, send_from_directory
import random, re, os

# Se agrega static_folder para servir el HTML y archivos estáticos de forma más clara
app = Flask(__name__, static_folder=".", static_url_path="")

# -----------------------------
# 1) Datos ficticios
# -----------------------------
DESTINOS = ["parís", "madrid", "roma", "nueva york", "cancún"]

CLIMAS = [
    "soleado con 25°C",
    "lluvioso con 18°C",
    "nublado con 20°C",
    "ventoso con 22°C",
    "caluroso con 30°C",
    "templado con 23°C"
]

COSTOS = ["700 USD", "850 USD", "1000 USD", "1200 USD", "1500 USD", "2000 USD"]

LUGARES = {
    "parís": ["Torre Eiffel", "Museo del Louvre", "Catedral de Notre Dame", "Montmartre"],
    "madrid": ["Palacio Real", "Museo del Prado", "Parque del Retiro", "Plaza Mayor"],
    "roma": ["Coliseo", "Fontana di Trevi", "Vaticano", "Piazza Navona"],
    "nueva york": ["Central Park", "Estatua de la Libertad", "Times Square", "Empire State"],
    "cancún": ["Playas del Caribe", "Isla Mujeres", "Ruinas de Tulum", "Cenotes"]
}

DISCLAIMER = "ℹNota: Esta información es ficticia y solo con fines académicos."


# -----------------------------
# 2) Guardrails (filtros de seguridad)
# -----------------------------
def guardrails(state):
    question = state["question"].lower().strip()

    # Verificar que haya texto
    if not question:
        return {**state, "blocked": True, "answer": "No hay ninguna pregunta de entrada."}

    # Filtro de contenido dañino
    palabras_prohibidas = [
        "odio","odiar","violencia","insulto","insultar","matar","robar","pegar","agredir","golpear",
        "lastimar","amenazar","dañar","abusar","secuestrar","secuestro","torturar","herir","discriminar",
        "humillar","intimidar","vengar","sabotear","maltratar","violar","corromper","estafar","traicionar",
        "despreciar","destruir","oprimir","castigar","maldecir","provocar","burlar","manipular","saquear",
        "extorsionar","asesinar"
    ]
    if any(p in question for p in palabras_prohibidas):
        return {**state, "blocked": True, "answer": "Contenido inapropiado detectado."}

    # Datos personales
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", question):
        return {**state, "blocked": True, "answer": "No puedo procesar correos electrónicos."}
    if re.search(r"\+?\d{8,}", question):
        return {**state, "blocked": True, "answer": "No puedo mostrar datos de contacto."}

    # Preguntas muy cortas
    if len(question.split()) < 2:
        return {**state, "blocked": True, "answer": "Pregunta demasiado corta para recomendar algo."}

    # Plagio / acceso no autorizado
    if any(p in question for p in ["plagio","descargar libro gratis","bypass","paywall"]):
        return {**state, "blocked": True, "answer": "No puedo ayudar con tareas de plagio o acceso no autorizado."}

    # Salud / legal
    if any(p in question for p in ["medicina","tratamiento","receta","abogado","demanda"]):
        return {**state, "blocked": True, "answer": "Este sistema no está diseñado para dar consejos médicos o legales."}

    return {**state, "blocked": False}


# -----------------------------
# 3) Extraer destino
# -----------------------------
def extraer_destino(question: str) -> str:
    q = question.lower()
    for ciudad in DESTINOS:
        if ciudad in q:
            return ciudad
    return random.choice(DESTINOS)


# -----------------------------
# 4) Clasificador
# -----------------------------
def clasificador(state):
    if state["blocked"]:
        return state

    q = state["question"].lower()
    if "clima" in q or "temperatura" in q:
        categoria = "clima"
    elif "precio" in q or "costo" in q or "presupuesto" in q or "vale" in q:
        categoria = "costos"
    else:
        categoria = "lugares"

    return {**state, "categoria": categoria}


# -----------------------------
# 5) Agentes
# -----------------------------
def agente_clima(state):
    destino = extraer_destino(state["question"])
    clima = random.choice(CLIMAS)
    return {**state, "context": "[Agente Clima]",
            "answer": f"El clima en {destino.title()} es {clima}. {DISCLAIMER}"}

def agente_costos(state):
    destino = extraer_destino(state["question"])
    costo = random.choice(COSTOS)
    return {**state, "context": "[Agente Costos]",
            "answer": f"Viajar a {destino.title()} cuesta en promedio {costo} por persona. {DISCLAIMER}"}

def agente_lugares(state):
    destino = extraer_destino(state["question"])
    lugares = LUGARES.get(destino, ["lugares turísticos destacados"])
    seleccion = random.sample(lugares, k=min(3, len(lugares)))
    lugares_txt = ", ".join(seleccion)
    return {**state, "context": "[Agente Lugares]",
            "answer": f"En {destino.title()} te recomiendo visitar: {lugares_txt}. {DISCLAIMER}"}


# -----------------------------
# 6) Orquestador
# -----------------------------
def run_graph(question: str):
    state = {"question": question}
    state = guardrails(state)
    if state["blocked"]:
        return state

    state = clasificador(state)

    if state["categoria"] == "clima":
        return agente_clima(state)
    elif state["categoria"] == "costos":
        return agente_costos(state)
    else:
        return agente_lugares(state)


# -----------------------------
# 7) Flask Endpoints
# -----------------------------

@app.route("/api/ask", methods=["POST"])
def ask():
    """
    Endpoint para recibir preguntas.
    - Se agrega validación de JSON.
    - Retorna código 400 si el JSON no es válido.
    """
    if not request.is_json:
        return jsonify({"answer": "La solicitud debe ser JSON."}), 400

    data = request.get_json(silent=True)
    if not data or "question" not in data:
        return jsonify({"answer": "Falta el campo 'question'."}), 400

    question = data.get("question", "")
    return jsonify(run_graph(question))


@app.route("/", methods=["GET"])
def serve_index():
    """
    Sirve el archivo index.html.
    - Compatible con Vercel porque usa static_folder configurado.
    """
    return send_from_directory(app.static_folder, "index.html")


# Punto de entrada para pruebas locales
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' permite que Vercel escuche correctamente
    app.run(host="0.0.0.0", port=port)
