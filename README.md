# 📊 Dashboard de Visualización de Datos CSV

Aplicación web que permite cargar archivos CSV, detectar automáticamente sus columnas y tipos de datos, y generar gráficas interactivas configurables por el usuario.

---

## 🚀 Funcionalidades

- ✅ Carga de archivos CSV (hasta 5 MB)
- ✅ Detección automática de tipos de columna (numérico, texto, fecha)
- ✅ 4 tipos de gráfica: barras, líneas, pastel, dispersión
- ✅ Selector de ejes X e Y configurables
- ✅ Estadísticas básicas: media, mediana, mínimo, máximo
- ✅ Exportación del gráfico como imagen PNG
- ✅ Drag & Drop para subir archivos
- ✅ Manejo de errores y validaciones

---

## 🛠️ Tecnologías utilizadas

| Tecnología | Uso |
|------------|-----|
| Python + Flask | Backend y servidor web |
| Pandas | Procesamiento y análisis de datos CSV |
| Chart.js | Renderizado de gráficas interactivas |
| HTML/CSS/JavaScript | Interfaz de usuario |
| Werkzeug | Manejo seguro de archivos |

---

## 📂 Estructura del proyecto

```text
PROYECTO-Lenguajes-P/
├── app.py
├── requirements.txt
├── csv_analyzer.py
├── test_csv_analyzer.py
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
└── uploads/
```

---

## 📥 Instalación

```bash
git clone https://github.com/Leiston09/Dashboard-de-Visualizaci-n-de-Datos-CSV.git
cd Dashboard-de-Visualizaci-n-de-Datos-CSV

python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt

python app.py
```

Abrir en el navegador:

```text
http://127.0.0.1:5000
```

---

## 📖 Cómo usar

1. Subir un archivo CSV (máximo 5 MB).
2. Seleccionar el tipo de gráfica.
3. Elegir las columnas para los ejes X e Y.
4. Actualizar la gráfica.
5. Exportar el resultado en formato PNG.

---

## 🧪 Datasets de prueba

### Ventas mensuales

```csv
mes,ventas,ganancias
Enero,1000,200
Febrero,1500,300
Marzo,1200,250
Abril,1800,400
Mayo,2000,500
```

### Estudiantes

```csv
nombre,edad,calificacion,ciudad
Ana,20,85,Quito
Luis,22,90,Guayaquil
Maria,19,78,Cuenca
Carlos,21,92,Quito
Laura,20,88,Guayaquil
```

### Finanzas

```csv
fecha,categoria,monto,tipo
2024-01-01,Alimentos,150,gasto
2024-01-02,Transporte,30,gasto
2024-01-03,Salario,1200,ingreso
2024-01-04,Alimentos,80,gasto
2024-01-05,Entretenimiento,50,gasto
```

---

## 👥 Integrantes del equipo

- Alvarado Limones Diana Elizabeth
- López Reyes Danna Julexy
- Leiston Alexander Holguin Aguirre
- Aniston Ismail Piguave Tello

---

## 📄 Licencia

Proyecto académico desarrollado para la asignatura **Lenguajes de Programación**.