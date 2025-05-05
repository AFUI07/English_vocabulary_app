# Versión PRO 1.6.2 - COMPLETAMENTE FUNCIONAL
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import random
import pyttsx3
import threading
import os
from datetime import datetime

# Configuración de voz
engine = pyttsx3.init()
engine.setProperty('voice', 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\Speech\\Voices\\Tokens\\TTS_MS_EN-GB_HAZEL_11.0')
engine.setProperty('rate', 150)


# Variables globales
nivel = None
dataset = []
preguntas = []
pregunta_actual = 0
usadas_esta_sesion = set()
repeticiones_hover = {}
palabras_prohibidas = set()
palabras_reto = []
respuestas_incorrectas = set()

# Leer palabras prohibidas
if os.path.exists("last_session.txt"):
    with open("last_session.txt", "r") as f:
        palabras_prohibidas = set(f.read().splitlines())

# ---------- FUNCIONES UTILES ----------
def reproducir_texto(texto):
    """Reproduce texto en un hilo separado"""
    def speak():
        engine.say(texto)
        engine.runAndWait()
    threading.Thread(target=speak, daemon=True).start()

def mostrar_traduccion(event, palabra):
    """Muestra tooltip con traducción desde columna C"""
    traduccion = "not available"
    for p, d, t in dataset:
        if p == palabra:
            traduccion = t if pd.notna(t) and str(t).strip() != "" else "not available"
            break
    
    tooltip = tk.Toplevel()
    tooltip.wm_overrideredirect(True)
    tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
    
    label = tk.Label(tooltip, text=f"→ {traduccion}", 
                    background="#ffffe0", relief='solid', borderwidth=1,
                    font=('Arial', 10), justify='left')
    label.pack(ipadx=5, ipady=2)
    
    tooltip.after(3000, tooltip.destroy)

# ---------- HOME ----------
def seleccionar_archivo():
    archivo = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    entry_ruta.delete(0, tk.END)
    entry_ruta.insert(0, archivo)

def seleccionar_nivel(n):
    global nivel
    nivel = n
    if n == 3:
        messagebox.showinfo("Level", "You will play level 3 (Random mode)")
    else:
        messagebox.showinfo("Level", f"You will play level {n}")

def iniciar_juego():
    global dataset, preguntas, pregunta_actual, usadas_esta_sesion, respuestas_incorrectas
    
    respuestas_incorrectas.clear()

    if not nivel:
        messagebox.showerror("Error", "Choose a level first")
        return

    ruta = entry_ruta.get().strip()
    if not ruta:
        messagebox.showerror("Error", "Select an Excel file")
        return

    try:
        if nivel == 3:
            hoja = random.choice(['Hoja1', 'Hoja2'])
        else:
            hoja = 'Hoja1' if nivel == 1 else 'Hoja2'
            
        df = pd.read_excel(ruta, sheet_name=hoja, engine='openpyxl')
        # Asegurarse de que hay al menos 3 columnas, si no, rellenar con vacío
        if len(df.columns) < 3:
            df[2] = ""
        dataset = [(str(p).strip(), str(d).strip(), str(t).strip() if pd.notna(t) else "") 
                  for p, d, t in zip(df.iloc[:,0], df.iloc[:,1], df.iloc[:,2]) 
                  if str(p).strip() not in palabras_prohibidas]
        
        if not dataset:
            messagebox.showerror("Error", "No words available. Clean the last_session.txt file.")
            return
            
        if nivel == 3:
            num_preguntas = random.randint(5, min(20, len(dataset)))
        else:
            num_preguntas = int(entry_num_preguntas.get())
            if num_preguntas <= 0 or num_preguntas > len(dataset):
                raise ValueError
    except Exception as e:
        messagebox.showerror("Error", f"Error reading file: {str(e)}")
        return

    preguntas.clear()
    preguntas.extend(random.sample(dataset, num_preguntas))
    pregunta_actual = 0
    usadas_esta_sesion.clear()
    repeticiones_hover.clear()

    # Limpiar ventanas
    for widget in ventana_juego.winfo_children():
        widget.pack_forget()
    for widget in ventana_resumen.winfo_children():
        widget.pack_forget()
    
    # Reconstruir elementos de juego
    contador_preguntas.pack(anchor='ne')
    label_definicion.pack(pady=20)
    
    for btn_data in botones:
        btn_data['frame'].pack(pady=5)
    
    control_frame.pack(pady=10)
    btn_next.pack(side=tk.LEFT, padx=5)
    tk.Button(control_frame, text="🏠 HOME", command=volver_home).pack(side=tk.LEFT, padx=5)
    
    ventana_home.pack_forget()
    ventana_juego.pack()
    cargar_pregunta()

# ---------- JUEGO ----------
def reproducir_hover(event):
    texto = event.widget.cget("text")
    if repeticiones_hover.get(texto, 0) < 2:
        reproducir_texto(texto)
        repeticiones_hover[texto] = repeticiones_hover.get(texto, 0) + 1

def cargar_pregunta():
    global repeticiones_hover

    contador_preguntas.config(text=f"Question {pregunta_actual + 1} of {len(preguntas)}")
    
    palabra, definicion, traduccion = preguntas[pregunta_actual]
    usadas_esta_sesion.add(palabra)
    
    # Configurar según nivel
    if nivel == 3:
        label_definicion.config(text=palabra)
        otras_definiciones = [d for p, d, t in dataset if d != definicion]
        distractores = random.sample(otras_definiciones, min(4, len(otras_definiciones)))
        opciones = distractores + [definicion]
    else:
        label_definicion.config(text=definicion)
        otras_palabras = [p for p, d, t in dataset if p != palabra]
        distractores = random.sample(otras_palabras, min(4, len(otras_palabras)))
        opciones = distractores + [palabra]
    
    random.shuffle(opciones)
    repeticiones_hover = {op: 0 for op in opciones}

    for i in range(len(opciones)):
        btn_data = botones[i]
        btn = btn_data['boton']
        btn_trad = btn_data['traduccion']
        
        btn.config(text=opciones[i], state=tk.NORMAL)
        btn.unbind("<Enter>")
        btn.bind("<Enter>", reproducir_hover)
        
        btn_trad.unbind("<Enter>")
        btn_trad.bind("<Enter>", lambda e, p=opciones[i]: mostrar_traduccion(e, p))
        
        if nivel == 3:
            btn.config(command=lambda op=opciones[i]: verificar_respuesta(op, definicion))
        else:
            btn.config(command=lambda op=opciones[i]: verificar_respuesta(op, palabra))
        
        btn_data['frame'].pack(pady=5)

    btn_next.config(state=tk.DISABLED)
    reproducir_texto(palabra if nivel == 3 else definicion)

mensajes_correcto = [ "Nice job", "You nailed it", "Crushed it", "Killed it", "Smashed it", "Boom! That’s how it’s done", "You’re on fire", "Legendary move", "Chef’s kiss",
    "Mic drop moment", "That was smooth", "Too good", "stop showing off", "Certified boss move", "You deserve a slow clap", "Not bad for a human", "Call the fire department",
    "cause you’re lit", "Slayed it", "You just leveled up", "That was spicy","10/10, would watch again", "¡Muy bien hecho!", "¡Excelente!", "¡Siuuuu, lo lograste!",
    "¡Buen trabajo!","¡Esa era fácil!", "¡Vamos mejorando!", "¡Esa no se te escapó!", "¡Estás en racha!", "¡Nivel Dios!","¡Exactamente!", "¡Eres un crack!", "¡Correcto!",
    "¡Perfecto!", "¡Tienes talento para esto!", "¡Bien ahí!", "¡Otra más para la colección!", "¡Boom! 💥", "¡Sigue así!", "¡Eres imparable!", "¡Bien hecho, campeón!"    
]
mensajes_incorrecto = ["❌ Don't worry", "❌ Keep trying", "❌ Better next time", "❌ ooops", "❌ Incorrect", "❌ You can do it better"]

def verificar_respuesta(seleccionada, correcta):
    if nivel == 3:
        es_correcta = seleccionada == correcta
        palabra_mostrar = [p for p, d, t in preguntas if d == correcta][0]
    else:
        es_correcta = seleccionada == correcta
        palabra_mostrar = correcta
    
    if es_correcta:
        messagebox.showinfo("✅ Correct", random.choice(mensajes_correcto))
    else:
        messagebox.showerror(random.choice(mensajes_incorrecto), f"The right answer was: {palabra_mostrar}")
        respuestas_incorrectas.add(palabra_mostrar)
        reproducir_texto(palabra_mostrar)

    for btn_data in botones:
        btn_data['boton'].config(state=tk.DISABLED)
    btn_next.config(state=tk.NORMAL)

def siguiente_pregunta():
    global pregunta_actual
    pregunta_actual += 1

    if pregunta_actual >= len(preguntas):
        mostrar_resumen()
    else:
        cargar_pregunta()

def volver_home():
    ventana_juego.pack_forget()
    ventana_resumen.pack_forget()
    ventana_home.pack()

def mostrar_resumen():
    global palabras_reto
    
    ventana_juego.pack_forget()
    
    # Seleccionar palabras para el reto
    palabras_reto = random.sample(usadas_esta_sesion, min(len(usadas_esta_sesion)//2 + 1, len(usadas_esta_sesion)))

    # Guardar sesión
    with open("last_session.txt", "w") as f:
        f.write("\n".join(usadas_esta_sesion))
    
    # Exportar resumen
    timestamp = datetime.now().strftime("%Y%m%d")
    export_filename = f"vocabulary_session_{timestamp}.txt"
    with open(export_filename, "w") as f:
        f.write("=== VOCABULARY TRAINER SESSION ===\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total words: {len(usadas_esta_sesion)}\n")
        f.write(f"Your mistakes: {len(respuestas_incorrectas)}\n\n")
        f.write("All practiced words:\n")
        f.write("\n".join(sorted(usadas_esta_sesion)))
        f.write("\n\nWriting challenge:\n")
        f.write(", ".join(palabras_reto))
    
    # Construir ventana de resumen
    label_titulo_resumen.config(text="Session Summary")
    label_titulo_resumen.pack(pady=10)
    
    # Frame para el contenido
    content_frame = tk.Frame(ventana_resumen)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    # Panel de palabras
    words_frame = tk.Frame(content_frame)
    words_frame.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(words_frame, text="All practiced words:", font=('Arial', 10, 'bold')).pack(anchor='w')
    text_palabras = tk.Text(words_frame, height=6, wrap=tk.WORD)
    text_palabras.pack(fill=tk.BOTH, expand=True)
    text_palabras.insert(tk.END, ", ".join(sorted(usadas_esta_sesion)))
    text_palabras.config(state=tk.DISABLED)
    
    # Panel de errores
    if respuestas_incorrectas:
        tk.Label(words_frame, text="\nYour mistakes:", 
                font=('Arial', 10, 'bold'), fg='red').pack(anchor='w')
        text_errores = tk.Text(words_frame, height=3, wrap=tk.WORD, fg='red')
        text_errores.pack(fill=tk.BOTH, expand=True)
        text_errores.insert(tk.END, ", ".join(sorted(respuestas_incorrectas)))
        text_errores.config(state=tk.DISABLED)
    
    # Panel de reto
    tk.Label(words_frame, text="\nWriting challenge:", 
            font=('Arial', 10, 'bold')).pack(anchor='w')
    text_reto = tk.Text(words_frame, height=3, wrap=tk.WORD, fg='blue')
    text_reto.pack(fill=tk.BOTH, expand=True)
    text_reto.insert(tk.END, ", ".join(palabras_reto))
    text_reto.config(state=tk.DISABLED)
    
    # Botones
    btn_frame = tk.Frame(content_frame)
    btn_frame.pack(pady=20)
    
    tk.Button(btn_frame, text="CLOSE", command=root.destroy, width=10).pack(side=tk.LEFT, padx=10)
    
    ventana_resumen.pack(fill=tk.BOTH, expand=True)

# ---------- INTERFAZ ----------
root = tk.Tk()
root.title("Vocabulary Trainer PRO")
root.geometry("750x650")

style = ttk.Style()
style.configure('TButton', font=('Arial', 10), padding=5)
style.configure('TLabel', font=('Arial', 11))

# ---------- VENTANA HOME ----------
ventana_home = tk.Frame(root, padx=20, pady=20)
ventana_home.pack()

tk.Label(ventana_home, text="VOCABULARY TRAINER PRO", font=("Arial", 18, 'bold')).pack(pady=15)

file_frame = tk.Frame(ventana_home)
file_frame.pack(pady=10, fill=tk.X)

entry_ruta = tk.Entry(file_frame, width=50, font=('Arial', 10))
entry_ruta.pack(side=tk.LEFT, padx=5)
tk.Button(file_frame, text="Search Excel", command=seleccionar_archivo).pack(side=tk.LEFT)

level_frame = tk.Frame(ventana_home)
level_frame.pack(pady=10)

tk.Label(level_frame, text="Select level:").pack(side=tk.LEFT, padx=5)
tk.Button(level_frame, text="Level 1", command=lambda: seleccionar_nivel(1)).pack(side=tk.LEFT, padx=5)
tk.Button(level_frame, text="Level 2", command=lambda: seleccionar_nivel(2)).pack(side=tk.LEFT, padx=5)
tk.Button(level_frame, text="Level 3", command=lambda: seleccionar_nivel(3)).pack(side=tk.LEFT, padx=5)

num_frame = tk.Frame(ventana_home)
num_frame.pack(pady=10)

tk.Label(num_frame, text="Number of questions:").pack(side=tk.LEFT, padx=5)
entry_num_preguntas = tk.Entry(num_frame, width=5)
entry_num_preguntas.pack(side=tk.LEFT)
entry_num_preguntas.insert(0, "10")

tk.Button(ventana_home, text="START TRAINING", command=iniciar_juego, 
         bg='#4CAF50', fg='white', font=('Arial', 12, 'bold')).pack(pady=20)

# ---------- VENTANA JUEGO ----------
ventana_juego = tk.Frame(root, padx=20, pady=20)

contador_preguntas = tk.Label(ventana_juego, text="", font=('Arial', 10, 'bold'))
label_definicion = tk.Label(ventana_juego, text="", wraplength=550, 
                           font=("Arial", 14), justify=tk.LEFT)

# Configurar botones con ícono de traducción
botones = []
for _ in range(5):
    frame = tk.Frame(ventana_juego)
    btn_trad = tk.Label(frame, text="📖", font=('Arial', 10), cursor="hand2")
    btn_trad.pack(side=tk.LEFT, padx=(0, 5))
    btn = tk.Button(frame, text="", width=35, height=2,
                   font=('Arial', 10), bg='#f0f0f0')
    btn.pack(side=tk.LEFT)
    botones.append({
        'frame': frame,
        'boton': btn,
        'traduccion': btn_trad
    })

control_frame = tk.Frame(ventana_juego)
btn_next = tk.Button(control_frame, text="NEXT ▶", state=tk.DISABLED, 
                    command=siguiente_pregunta, width=12)

# ---------- VENTANA RESUMEN ----------
ventana_resumen = tk.Frame(root)

label_titulo_resumen = tk.Label(ventana_resumen, text="", 
                               font=("Arial", 16, 'bold'))

root.mainloop()
