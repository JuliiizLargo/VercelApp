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
    "roma": ["Coliseo","Fontana de Trevi","Vaticano","Piazza Navona"],
    "nueva york": ["Central Park","Estatua de la Libertad","Times Square","Empire State"],
    "cancún": ["Playas del Caribe","Isla Mujeres","Ruinas de Tulum","Cenotes"]
}

# Recomendaciones de comida típica por destino
COMIDAS = {
    "parís": ["croissant y café", "crêpes saladas", "bistró francés", "macarons"],
    "madrid": ["tortilla española", "bocata de calamares", "tapas y cañas", "churros con chocolate"],
    "roma": ["espresso y cornetto", "pasta cacio e pepe", "pizza al taglio", "gelato"],
    "nueva york": ["bagel con cream cheese", "slice de pizza", "ramen o deli", "cheesecake"],
    "cancún": ["huevos motuleños", "tacos de cochinita", "mariscos frescos", "nieves y marquesitas"]
}

# Base de actividades para combinar
ACTIVIDADES_BASE = [
    "tour guiado",
    "sesión de fotos",
    "entrada prioritaria",
    "paseo a pie por el barrio",
    "visita a museo cercano",
    "crucero corto/traslado escénico",
    "tiempo libre para compras"
]

# Configuración por tema
THEME_CONFIG = {
    "clasico": {
        "extra_actividades": ["mirador panorámico", "recorrido en tranvía/turibús"],
        "tips": [
            "Compra entradas con antelación para evitar filas.",
            "Usa transporte público o camina: ahorra tiempo en horas pico.",
            "Lleva efectivo chico para entradas y mercados.",
            "Verifica horarios de cierre; muchos lugares cierran los lunes.",
            "Hidrátate y usa calzado cómodo."
        ],
        "comidas_bias": []
    },
    "arte": {
        "extra_actividades": [
            "visita a galería independiente",
            "museo de arte moderno",
            "tour de murales/arte urbano",
            "taller corto (acuarela/fotografía)"
        ],
        "tips": [
            "Revisa días de entrada gratuita a museos.",
            "Llega temprano a exposiciones populares para evitar filas.",
            "Descarga la app del museo para audioguía gratuita."
        ],
        "comidas_bias": ["café de autor", "panadería artesanal"]
    },
    "foodie": {
        "extra_actividades": [
            "tour gastronómico",
            "mercado local con degustación",
            "clase corta de cocina típica",
            "ruta de cafés/pastelerías"
        ],
        "tips": [
            "Reserva con antelación en restaurantes muy valorados.",
            "Pregunta por menús del día para probar platos locales.",
            "Evita zonas demasiado turísticas para mejores precios."
        ],
        "comidas_bias": ["bistró local", "street food recomendado", "degustación de postres"]
    },
    "low-cost": {
        "extra_actividades": [
            "free walking tour",
            "parques y miradores gratuitos",
            "museos con día sin costo",
            "picnic en plaza/parque"
        ],
        "tips": [
            "Aprovecha días gratuitos y horarios con descuento.",
            "Compra snacks en supermercados para ahorrar.",
            "Usa pases de transporte por día/semanal."
        ],
        "comidas_bias": ["menú del día económico", "comida callejera local", "panadería de barrio"]
    },
    "familiar": {
        "extra_actividades": [
            "parque con zona infantil",
            "acuario/zoológico (si aplica)",
            "museo interactivo",
            "paseo en bicicleta familiar"
        ],
        "tips": [
            "Planifica descansos y snacks para niños.",
            "Verifica alturas mínimas y accesibilidad.",
            "Elige horarios tempranos para evitar multitudes."
        ],
        "comidas_bias": ["opciones kid-friendly", "helados/gelato", "restaurante casual"]
    }
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
        return min(int(match.group(1)), 14)  # tope de 14 días
    return 3  # por defecto 3 días

# -----------------------------
# Detectar tema
# -----------------------------
def extraer_tema(question: str) -> str:
    q = question.lower()
    # permite variantes comunes
    if any(x in q for x in ["arte", "artístico", "artes"]):
        return "arte"
    if any(x in q for x in ["foodie", "gastron", "comida", "gourmet"]):
        return "foodie"
    if any(x in q for x in ["low cost", "low-cost", "barato", "económico", "economico"]):
        return "low-cost"
    if any(x in q for x in ["familiar", "niños", "ninos", "familia"]):
        return "familiar"
    # también acepta formato "tema: X"
    m = re.search(r"tema\s*:\s*([a-z\- ]+)", q)
    if m:
        cand = m.group(1).strip()
        # normaliza a una de las claves conocidas
        mapping = {
            "arte": "arte",
            "foodie": "foodie",
            "low cost": "low-cost",
            "low-cost": "low-cost",
            "familiar": "familiar"
        }
        return mapping.get(cand, "clasico")
    return "clasico"

# -----------------------------
# creación de itinerario realista con tema
# -----------------------------
def crear_itinerario_real(ciudad: str, dias: int, tema: str) -> str:
    cfg = THEME_CONFIG.get(tema, THEME_CONFIG["clasico"])

    sitios = LUGARES.get(ciudad, [])
    if not sitios:
        sitios = ["Centro histórico", "Museo principal", "Mirador de la ciudad", "Mercado local"]

    # Pool de actividades y tips según tema
    actividades_pool = list(set(ACTIVIDADES_BASE + cfg["extra_actividades"]))
    tips_pool = list(set(THEME_CONFIG["clasico"]["tips"] + cfg["tips"]))

    # Comidas mezclando típicas del destino + sesgo por tema
    comidas_base = COMIDAS.get(ciudad, ["plato típico", "street food", "cafetería local", "postre regional"])
    comidas_pool = list(set(comidas_base + cfg["comidas_bias"]))

    plan_dias = []
    idx = 0
    for d in range(1, dias + 1):
        mañana = sitios[idx % len(sitios)]
        tarde = sitios[(idx + 1) % len(sitios)]
        noche = sitios[(idx + 2) % len(sitios)]
        idx += 3

        act_m = random.choice(actividades_pool)
        act_t = random.choice(actividades_pool)
        act_n = random.choice(["paseo nocturno", "mirador al atardecer", "recorrido iluminado"])

        desayuno = random.choice(comidas_pool)
        comida = random.choice(comidas_pool)
        postre = random.choice(comidas_pool)

        tip = random.choice(tips_pool)

        # Ajustes ligeros por tema en los textos
        prefijo = ""
        if tema == "low-cost":
            prefijo = " (opción gratuita/económica)"
        if tema == "foodie":
            postre = f"ruta dulce: {postre}"
        if tema == "familiar":
            act_n = "actividad tranquila nocturna"

        dia_txt = (
            f"- Día {d}\n"
            f"  Mañana: {act_m.title()} en {mañana}{prefijo} + desayuno: {desayuno}.\n"
            f"  Tarde: {act_t.title()} en {tarde}{prefijo} + almuerzo: {comida}.\n"
            f"  Noche: {act_n.title()} por {noche}{prefijo} + postre/café: {postre}.\n"
            f"  Tip: {tip}"
        )
        plan_dias.append(dia_txt)

    return "\n".join(plan_dias)

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
    tema = extraer_tema(state["question"])
    cuerpo = crear_itinerario_real(d, dias, tema)
    tema_label = "Clásico" if tema == "clasico" else tema.replace("-", " ").title()
    header = f"Itinerario de {dias} días en {d.title()} — Tema: {tema_label}\n"
    extra = (
        "\nIncluye:\n"
        "• Actividades por franja (mañana/tarde/noche)\n"
        "• Lugares icónicos de la ciudad\n"
        "• Sugerencias de comida (con sesgo del tema)\n"
        "• Un tip logístico por día\n"
        "Sugerencia: Puedes indicar el tema así: 'tema: foodie' o 'itinerario low cost'.\n"
    )
    return {**state, "answer": header + cuerpo + "\n" + extra + f"{DISCLAIMER}"}

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
        return {**state, "blocked": True, "answer": "Lo siento, no tengo información sobre esa consulta."}
    return {**state, "categoria": cat}

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


