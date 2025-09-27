from flask import Flask, request, jsonify, send_from_directory
import random, re, os

# Mantiene el frontend en la raíz
app = Flask(__name__, static_folder="static", static_url_path="")

# -----------------------------
# Datos ficticios
# -----------------------------
DESTINOS = [
    "parís",
    "madrid",
    "roma",
    "nueva york",
    "cancún"
    ]
CLIMAS = [
    "soleado con 25°C",
    "lluvioso con 18°C",
    "nublado con 20°C",
    "ventoso con 22°C",
    "caluroso con 30°C",
    "templado con 23°C"
    ]
COSTOS = [
    "700 USD",
    "850 USD",
    "1000 USD",
    "1200 USD",
    "1500 USD",
    "2000 USD"
    ]
LUGARES = {
    "parís": ["Torre Eiffel","Museo del Louvre","Catedral de Notre Dame","Montmartre"],
    "madrid": ["Palacio Real","Museo del Prado","Parque del Retiro","Plaza Mayor"],
    "roma": ["Coliseo","Fontana di Trevi","Vaticano","Piazza Navona"],
    "nueva york": ["Central Park","Estatua de la Libertad","Times Square","Empire State"],
    "cancún": ["Playas del Caribe","Isla Mujeres","Ruinas de Tulum","Cenotes"]
}
DISCLAIMER = "ℹ Nota: Esta información es ficticia y solo con fines académicos."

# -----------------------------
# Guardrails (filtros de seguridad)
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
# Extraer destino
# -----------------------------
def extraer_destino(question: str) -> str:
    q = question.lower()
    for ciudad in DESTINOS:
        if ciudad in q:
            return ciudad
    return random.choice(DESTINOS)

# -----------------------------
# Detectar cantidad de días
# -----------------------------
def extraer_dias(question: str) -> int:
    match = re.search(r"(\d+)\s*d[ií]as?", question.lower())
    if match:
        return min(int(match.group(1)), 14)  # tope de 14 días para no hacer respuestas gigantes
    return 3  # por defecto 3 días

# -----------------------------
# Clasificador simple
# -----------------------------
def clasificador(state):
    if state["blocked"]:
        return state
    q = state["question"].lower()
    if "clima" in q:
        cat = "clima"
    elif "precio" in q or "costo" in q:
        cat = "costos"
    elif "itinerario" in q or "plan" in q:
        cat = "itinerario"
    else:
        cat = "lugares"
    return {**state, "categoria": cat}

# -----------------------------
# Agentes de respuesta
# -----------------------------
def agente_clima(state):
    d = extraer_destino(state["question"])
    return {**state, "answer": f"El clima en {d.title()} es {random.choice(CLIMAS)}. {DISCLAIMER}"}

def agente_costos(state):
    d = extraer_destino(state["question"])
    return {**state, "answer": f"Viajar a {d.title()} cuesta en promedio {random.choice(COSTOS)} por persona. {DISCLAIMER}"}

def agente_lugares(state):
    d = extraer_destino(state["question"])
    sitios = ", ".join(random.sample(LUGARES.get(d, ["lugares turísticos destacados"]), k=3))
    return {**state, "answer": f"En {d.title()} te recomiendo visitar: {sitios}. {DISCLAIMER}"}

def agente_itinerario(state):
    d = extraer_destino(state["question"])
    dias = extraer_dias(state["question"])
    # Crea un itinerario dinámico
    plan = [f"- Día {i+1}: Actividades sugeridas en {d.title()}."
            for i in range(dias)]
    return {**state, "answer": f"Itinerario de {dias} días en {d.title()}:\n" + "\n".join(plan) + f"\n{DISCLAIMER}"}

# -----------------------------
# Orquestador
# -----------------------------
def run_graph(question: str):
    st = {"question": question}
    st = guardrails(st)
    if st["blocked"]:
        return st
    st = clasificador(st)
    if st["categoria"] == "clima":
        return agente_clima(st)
    if st["categoria"] == "costos":
        return agente_costos(st)
    if st["categoria"] == "itinerario":
        return agente_itinerario(st)
    return agente_lugares(st)

# -----------------------------
# Endpoints Flask
# -----------------------------
@app.route("/api/ask", methods=["POST"])
def ask():
    if not request.is_json:
        return jsonify({"answer": "La solicitud debe ser JSON."}), 400
    data = request.get_json(silent=True)
    if not data or "question" not in data:
        return jsonify({"answer": "Falta el campo 'question'."}), 400
    return jsonify(run_graph(data["question"]))

@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

# Para pruebas locales
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

