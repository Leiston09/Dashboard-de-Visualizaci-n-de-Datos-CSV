import os
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename

from csv_analyzer import analyze_csv_advanced, validate_csv_file, detect_delimiter

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024


# =========================
# ERROR 413
# =========================
@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'Archivo demasiado grande (max 5MB)'}), 413


# =========================
# LIST FILES
# =========================
@app.route('/api/list_files')
def list_files():
    files = []
    upload_dir = app.config['UPLOAD_FOLDER']
    for f in os.listdir(upload_dir):
        if f.endswith('.csv'):
            path = os.path.join(upload_dir, f)
            files.append({
                "name": f,
                "size": round(os.path.getsize(path) / 1024, 2)
            })
    return jsonify(files)


# =========================
# INDEX
# =========================
@app.route('/')
def index():
    current = session.get('current_file')
    upload_dir = app.config['UPLOAD_FOLDER']

    if current:
        path = os.path.join(upload_dir, current)
        if not os.path.exists(path):
            session.pop('current_file', None)
            current = None

    csv_files = [f for f in os.listdir(upload_dir) if f.endswith('.csv')]

    return render_template('index.html',
                           csv_files=csv_files,
                           current_file=current)



# =========================
# UPLOAD (CON RESPUESTA JSON PARA AJAX)
# =========================
@app.route('/upload', methods=['POST'])
def upload():
    print("=" * 60)
    print("📤 RECIBIENDO ARCHIVO")
    print("=" * 60)
    
    # Verificar si la petición es AJAX (tiene el header X-Requested-With)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if 'file' not in request.files:
        print("❌ No hay archivo en la petición")
        if is_ajax:
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        flash('No se seleccionó ningún archivo')
        return redirect(url_for('index'))

    file = request.files['file']
    print(f"📄 Nombre del archivo: {file.filename}")

    if file.filename == '':
        print("❌ Nombre de archivo vacío")
        if is_ajax:
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        flash('No se seleccionó ningún archivo')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    print(f"🔒 Nombre seguro: {filename}")

    if not filename.endswith('.csv'):
        print("❌ No es un CSV")
        if is_ajax:
            return jsonify({'success': False, 'message': 'Solo se permiten archivos CSV'}), 400
        flash('Solo se permiten archivos CSV')
        return redirect(url_for('index'))

    upload_dir = app.config['UPLOAD_FOLDER']
    print(f"📁 Directorio de uploads: {upload_dir}")
    
    if not os.path.exists(upload_dir):
        print(f"⚠️ Directorio no existe, creando...")
        os.makedirs(upload_dir, exist_ok=True)
    
    path = os.path.join(upload_dir, filename)
    print(f"💾 Guardando en: {path}")
    
    try:
        file.save(path)
        print(f"✅ Archivo guardado correctamente")
    except Exception as e:
        print(f"❌ Error al guardar: {e}")
        if is_ajax:
            return jsonify({'success': False, 'message': f'Error al guardar: {str(e)}'}), 500
        flash(f'Error al guardar el archivo: {e}')
        return redirect(url_for('index'))

    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"📊 Tamaño del archivo: {size} bytes")
    else:
        print("❌ El archivo no se guardó correctamente")
        if is_ajax:
            return jsonify({'success': False, 'message': 'Error al guardar el archivo'}), 500
        flash('Error al guardar el archivo')
        return redirect(url_for('index'))

    # Validar el archivo CSV
    ok, msg = validate_csv_file(path)
    if not ok:
        print(f"❌ Validación fallida: {msg}")
        os.remove(path)
        if is_ajax:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg)
        return redirect(url_for('index'))

    session['current_file'] = filename
    print(f"✅ Archivo guardado en sesión: {filename}")
    print("=" * 60)
    
    # ============================================================
    # RESPUESTA SEGÚN EL TIPO DE PETICIÓN
    # ============================================================
    if is_ajax:
        return jsonify({
            'success': True,
            'filename': filename,
            'message': f'Archivo "{filename}" cargado correctamente'
        })
    else:
        flash(f'Archivo "{filename}" cargado correctamente')
        return redirect(url_for('index'))


# =========================
# PROCESS
# =========================
@app.route('/process')
def process():
    filename = request.args.get('file') or session.get('current_file')

    if not filename:
        return jsonify({'error': 'No se ha seleccionado ningún archivo.'}), 400

    upload_dir = app.config['UPLOAD_FOLDER']
    path = os.path.join(upload_dir, filename)

    if not os.path.exists(path):
        session.pop('current_file', None)
        return jsonify({'error': f'El archivo "{filename}" no existe.'}), 404

    try:
        session['current_file'] = filename
        
        analysis, df = analyze_csv_advanced(path)

        cols = []
        for c, d in analysis['columnas'].items():
            cols.append({
                "columna": str(c),
                "tipo_detectado": d["tipo_detectado"],
                "nulos": d["nulos"],
                "no_nulos": d["no_nulos"]
            })

        size_kb = round(os.path.getsize(path) / 1024, 2)

        # ============================================================
        # PREPARAR DATOS DE TABLA
        # ============================================================
        all_rows = df.fillna("").values.tolist()
        
        # Calcular promedios de columnas numéricas
        averages = []
        for col in df.columns:
            numeric_series = pd.to_numeric(df[col], errors='coerce')
            if numeric_series.notna().sum() > 0:
                avg = numeric_series.mean()
                averages.append(round(avg, 2) if not pd.isna(avg) else '')
            else:
                averages.append('')

        return jsonify({
            "archivo": filename,
            "delimitador": analysis["delimitador_detectado"],
            "total_filas": analysis["total_filas"],
            "total_columnas": analysis["total_columnas"],
            "tamano_kb": size_kb,
            "analisis_columnas": cols,
            "preview_headers": [str(c) for c in df.columns],
            "preview_rows": all_rows,
            "averages": averages,
            "df_info": {
                "columnas": df.columns.tolist(),
                "tipos": [str(dtype) for dtype in df.dtypes],
                "num_filas": len(df)
            }
        })
    except Exception as e:
        return jsonify({'error': f'Error al procesar: {str(e)}'}), 500


# =========================
# STATS
# =========================
@app.route('/stats')
def stats():
    filename = request.args.get('file') or session.get('current_file')

    if not filename:
        return jsonify({'error': 'No se ha seleccionado ningún archivo.'}), 400

    upload_dir = app.config['UPLOAD_FOLDER']
    path = os.path.join(upload_dir, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'Archivo no encontrado.'}), 404

    try:
        delim = detect_delimiter(path)
        df = pd.read_csv(path, sep=delim)
        
        result = {}

        for col in df.columns:
            series = pd.to_numeric(df[col], errors='coerce')
            numeric_series = series.dropna()
            
            if len(numeric_series) == 0:
                text_series = df[col].dropna().astype(str)
                if len(text_series) > 0:
                    value_counts = text_series.value_counts()
                    result[str(col)] = {
                        "tipo": "texto",
                        "total": int(len(df[col])),
                        "no_nulos": int(len(text_series)),
                        "nulos": int(df[col].isnull().sum()),
                        "valores_unicos": int(len(value_counts)),
                        "moda": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                        "frecuencia_moda": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                        "porcentaje_nulos": round((df[col].isnull().sum() / len(df[col])) * 100, 2)
                    }
                continue

            n = len(numeric_series)
            total = len(df[col])
            nulos = df[col].isnull().sum()
            porcentaje_nulos = round((nulos / total) * 100, 2) if total > 0 else 0
            
            media = float(numeric_series.mean())
            mediana = float(numeric_series.median())
            
            moda_values = numeric_series.mode()
            moda = float(moda_values.iloc[0]) if len(moda_values) > 0 else None
            
            minimo = float(numeric_series.min())
            maximo = float(numeric_series.max())
            rango = maximo - minimo
            desviacion = float(numeric_series.std())
            varianza = float(numeric_series.var())
            
            q1 = float(numeric_series.quantile(0.25))
            q2 = float(numeric_series.quantile(0.50))
            q3 = float(numeric_series.quantile(0.75))
            iqr = q3 - q1
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = numeric_series[(numeric_series < lower_bound) | (numeric_series > upper_bound)]
            outliers_count = len(outliers)
            outliers_percent = round((outliers_count / n) * 100, 2) if n > 0 else 0
            
            if desviacion > 0:
                skewness = float(((numeric_series - media) ** 3).mean() / (desviacion ** 3))
            else:
                skewness = 0.0
            
            if desviacion > 0:
                kurtosis = float(((numeric_series - media) ** 4).mean() / (desviacion ** 4)) - 3
            else:
                kurtosis = 0.0
            
            if skewness > 0.5:
                skewness_label = "Sesgo positivo (cola a la derecha)"
            elif skewness < -0.5:
                skewness_label = "Sesgo negativo (cola a la izquierda)"
            else:
                skewness_label = "Aproximadamente simétrica"
            
            if kurtosis > 1:
                kurtosis_label = "Leptocúrtica (picos altos)"
            elif kurtosis < -1:
                kurtosis_label = "Platicúrtica (picos bajos)"
            else:
                kurtosis_label = "Mesocúrtica (normal)"
            
            suma = float(numeric_series.sum())
            
            result[str(col)] = {
                "tipo": "numérico",
                "total": int(total),
                "no_nulos": int(n),
                "nulos": int(nulos),
                "porcentaje_nulos": porcentaje_nulos,
                "media": round(media, 4),
                "mediana": round(mediana, 4),
                "moda": round(moda, 4) if moda is not None else None,
                "minimo": round(minimo, 4),
                "maximo": round(maximo, 4),
                "rango": round(rango, 4),
                "desviacion_estandar": round(desviacion, 4),
                "varianza": round(varianza, 4),
                "q1": round(q1, 4),
                "q2": round(q2, 4),
                "q3": round(q3, 4),
                "iqr": round(iqr, 4),
                "outliers": int(outliers_count),
                "porcentaje_outliers": outliers_percent,
                "skewness": round(skewness, 4),
                "skewness_label": skewness_label,
                "kurtosis": round(kurtosis, 4),
                "kurtosis_label": kurtosis_label,
                "suma": round(suma, 4)
            }

        return jsonify({
            "archivo": filename,
            "total_columnas": len(df.columns),
            "total_filas": len(df),
            "estadisticas": result
        })
    except Exception as e:
        import traceback
        print(f"[ERROR] en stats: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# =========================
# CHART_DATA (CON VALIDACIONES Y LOGS COMPLETOS)
# =========================
@app.route('/chart_data')
def chart_data():
    filename = request.args.get('file')
    column_x = request.args.get('column_x')
    column_y = request.args.get('column_y') or request.args.get('column')
    chart_type = request.args.get('type', 'bar')
    group_size = request.args.get('group_size', default=1, type=int)

    print("=" * 80)
    print("📊 CHART_DATA - PETICIÓN RECIBIDA")
    print("=" * 80)
    print(f"📂 Archivo: {filename}")
    print(f"📌 Eje X: {column_x}")
    print(f"📌 Eje Y: {column_y}")
    print(f"📌 Tipo: {chart_type}")
    print(f"📌 Group Size: {group_size}")
    print("-" * 80)

    if not filename:
        return jsonify({'error': 'Falta el parámetro file'}), 400
    
    if not column_y:
        return jsonify({'error': 'Falta el parámetro column_y'}), 400

    upload_dir = app.config['UPLOAD_FOLDER']
    path = os.path.join(upload_dir, filename)
    
    if not os.path.exists(path):
        return jsonify({'error': f'Archivo "{filename}" no encontrado'}), 404

    try:
        delim = detect_delimiter(path)
        df = pd.read_csv(path, sep=delim)
        
        print(f"📋 Columnas del CSV: {df.columns.tolist()}")
        print(f"📋 Total filas: {len(df)}")
        print("-" * 80)
        
        if column_y not in df.columns:
            return jsonify({'error': f'Columna "{column_y}" no existe'}), 400

        # ============================================================
        # VALIDACIÓN: Verificar que la columna Y sea numérica
        # ============================================================
        test_series = pd.to_numeric(df[column_y], errors='coerce')
        if test_series.isna().all():
            print(f"❌ ERROR: La columna '{column_y}' no contiene datos numéricos")
            return jsonify({'error': f'La columna "{column_y}" no contiene datos numéricos válidos'}), 400

        # ============================================================
        # CASO ESPECIAL: X e Y son la MISMA columna
        # ============================================================
        if column_x and column_x in df.columns and column_x == column_y:
            print("🔹 CASO ESPECIAL: X e Y son la MISMA columna")
            print(f"🔹 Columna: {column_y}")
            
            series = pd.to_numeric(df[column_y], errors='coerce')
            numeric_series = series.dropna()
            
            if numeric_series.empty:
                return jsonify({'error': f'No hay datos numéricos en "{column_y}"'}), 400
            
            numeric_series = numeric_series.astype(float)
            
            # ORDENAR DE MENOR A MAYOR
            numeric_series = numeric_series.sort_values()
            
            labels = [str(i+1) for i in range(len(numeric_series))]
            values = numeric_series.tolist()
            
            print(f"🔹 Valores REALES ORDENADOS de {column_y}: {values[:10]}...")
            print(f"🔹 Total: {len(values)} valores")
            print(f"🔹 Min: {values[0] if values else 'N/A'}, Max: {values[-1] if values else 'N/A'}")
            print("-" * 80)
            
            print("📤 DATOS A ENVIAR AL FRONTEND:")
            print(f"   labels: {labels[:10]}...")
            print(f"   values: {values[:10]}...")
            print("=" * 80)
            
            return jsonify({
                "labels": labels,
                "values": values,
                "column": column_y,
                "chart_type": chart_type,
                "info": {
                    "min": values[0] if values else None,
                    "max": values[-1] if values else None,
                    "count": len(values)
                }
            })

        # ============================================================
        # CASO 1: SOLO EJE Y (sin X)
        # ============================================================
        if not column_x or column_x not in df.columns:
            print("🔹 CASO 1: SOLO EJE Y")
            print(f"🔹 Columna Y: {column_y}")
            
            series = pd.to_numeric(df[column_y], errors='coerce')
            numeric_series = series.dropna()
            
            if numeric_series.empty:
                return jsonify({'error': f'No hay datos numéricos en "{column_y}"'}), 400
            
            numeric_series = numeric_series.astype(float)
            
            # Si tiene pocos valores únicos (<= 20), mostrar frecuencia
            if numeric_series.nunique() <= 20:
                value_counts = numeric_series.value_counts().sort_index()
                labels = [str(k) for k in value_counts.index]
                values = [int(v) for v in value_counts.values]
                print(f"🔹 Pocos valores únicos ({numeric_series.nunique()}) → FRECUENCIA")
                print(f"🔹 Labels: {labels}")
                print(f"🔹 Values: {values}")
            else:
                # Si tiene muchos valores únicos, mostrar valores reales ORDENADOS
                numeric_series = numeric_series.sort_values()
                labels = [str(i+1) for i in range(len(numeric_series))]
                values = numeric_series.tolist()
                print(f"🔹 Muchos valores únicos ({numeric_series.nunique()}) → VALORES REALES ORDENADOS")
            
            print("📤 DATOS A ENVIAR AL FRONTEND:")
            print(f"   labels: {labels[:10]}...")
            print(f"   values: {values[:10]}...")
            print("=" * 80)
            
            return jsonify({
                "labels": labels,
                "values": values,
                "column": column_y,
                "chart_type": chart_type
            })
        
        # ============================================================
        # CASO 2: EJE X + EJE Y (columnas DIFERENTES)
        # ============================================================
        print("🔹 CASO 2: EJE X + EJE Y (columnas diferentes)")
        print(f"🔹 Columna X: {column_x}")
        print(f"🔹 Columna Y: {column_y}")

        # ============================================================
        # VALIDACIÓN: Verificar que la columna X exista
        # ============================================================
        if column_x not in df.columns:
            print(f"❌ ERROR: La columna '{column_x}' no existe en el CSV")
            return jsonify({'error': f'La columna "{column_x}" no existe en el CSV'}), 400

        df_clean = df[[column_x, column_y]].copy()

        # Convertir Y a numérico
        df_clean[column_y] = pd.to_numeric(df_clean[column_y], errors='coerce')

        # Eliminar filas sin valor en Y
        df_clean = df_clean.dropna(subset=[column_y])

        if df_clean.empty:
            return jsonify({'error': f'No hay datos válidos con las columnas seleccionadas'}), 400

        # Convertir X a string y rellenar nulos
        df_clean[column_x] = df_clean[column_x].fillna("Vacío").astype(str)

        print(f"🔹 Filas después de limpiar: {len(df_clean)}")
        print(f"🔹 Valores únicos en X: {df_clean[column_x].nunique()}")

        # ============================================================
        # DETECTAR QUÉ TIPO DE COLUMNA ES Y
        # ============================================================

        # 1. ¿Es una CALIFICACION (1-5)?
        is_calificacion = 'calificacion' in column_y.lower() or \
                        'calificación' in column_y.lower()

        # 2. ¿Es un ID o identificador?
        is_id = column_y.lower() == 'id' or \
                'código' in column_y.lower() or \
                'codigo' in column_y.lower()

        # 3. Verificar valores únicos
        unique_values = df_clean[column_y].unique()
        is_likely_calificacion = len(unique_values) <= 5 and all(1 <= v <= 5 for v in unique_values if not pd.isna(v))
        is_likely_id = len(unique_values) > 20

        print(f"🔹 is_calificacion: {is_calificacion}")
        print(f"🔹 is_id: {is_id}")
        print(f"🔹 is_likely_calificacion: {is_likely_calificacion}")
        print(f"🔹 is_likely_id: {is_likely_id}")
        print(f"🔹 Valores únicos de {column_y}: {len(unique_values)}")
        print(f"🔹 Rango de {column_y}: min={df_clean[column_y].min()}, max={df_clean[column_y].max()}")

        # ============================================================
        # DECIDIR QUÉ OPERACIÓN USAR
        # ============================================================

        if is_calificacion or is_likely_calificacion:
            # Calificación → PROMEDIO
            grouped = df_clean.groupby(column_x)[column_y].mean()
            print(f"🔹 Usando PROMEDIO de {column_y} (es una calificación)")
            print(f"🔹 Resultado: {grouped.to_dict()}")
            
        elif is_id or is_likely_id:
            # ID o identificador → CONTEO
            grouped = df_clean.groupby(column_x)[column_y].count()
            print(f"🔹 Usando CONTEO de {column_y} (es un identificador)")
            print(f"🔹 Resultado: {grouped.to_dict()}")
            
        else:
            # Otras columnas numéricas
            if chart_type in ['line', 'area']:
                grouped = df_clean.groupby(column_x)[column_y].mean()
                print(f"🔹 Usando PROMEDIO de {column_y}")
            else:
                grouped = df_clean.groupby(column_x)[column_y].sum()
                print(f"🔹 Usando SUMA de {column_y}")
            print(f"🔹 Resultado: {grouped.to_dict()}")

        # ============================================================
        # MANTENER ORDEN DE APARICIÓN Y APLICAR AGRUPACIÓN
        # ============================================================
        categories_order = []
        for item in df_clean[column_x]:
            if item not in categories_order:
                categories_order.append(item)

        grouped = grouped.reindex(categories_order)

        # ============================================================
        # SI HAY MUCHAS CATEGORÍAS Y group_size > 1, AGRUPAR POR RANGOS
        # ============================================================
        labels = []
        values = []

        if len(grouped) > 20 and group_size > 1:
            print(f"🔹 Aplicando agrupación manual: {group_size} en {group_size}")
            # Agrupar los valores en bloques de group_size
            grouped_list = list(grouped.items())
            temp_labels = []
            temp_values = []
            
            for i in range(0, len(grouped_list), group_size):
                chunk = grouped_list[i:i+group_size]
                chunk_labels = [item[0] for item in chunk]
                chunk_values = [item[1] for item in chunk]
                
                if len(chunk) == 1:
                    temp_labels.append(str(chunk_labels[0]))
                    temp_values.append(float(chunk_values[0]))
                else:
                    # Crear rango
                    first = str(chunk_labels[0])
                    last = str(chunk_labels[-1])
                    temp_labels.append(f"{first}-{last}")
                    temp_values.append(float(np.mean(chunk_values) if chart_type in ['line', 'area'] else np.sum(chunk_values)))
            
            labels = temp_labels
            values = temp_values
            print(f"🔹 Agrupado en {len(labels)} grupos")
        else:
            labels = [str(k) for k in grouped.index]
            values = [float(v) if pd.notna(v) else 0.0 for v in grouped.values]

        # ============================================================
        # VALIDACIÓN FINAL: Verificar que los datos sean consistentes
        # ============================================================
        print(f"🔹 Total labels: {len(labels)}")
        print(f"🔹 Total values: {len(values)}")
        print(f"🔹 Labels: {labels[:10]}...")
        print(f"🔹 Values: {values[:10]}...")
        
        if len(labels) == 0 or len(values) == 0:
            return jsonify({'error': 'No se pudieron generar datos para la gráfica'}), 400

        print("=" * 80)
        print("📤 DATOS ENVIADOS AL FRONTEND:")
        print(f"   Total datos: {len(labels)}")
        print(f"   Rango Y: min={min(values) if values else 'N/A'}, max={max(values) if values else 'N/A'}")
        print("=" * 80)

        return jsonify({
            "labels": labels,
            "values": values,
            "column": column_y,
            "chart_type": chart_type,
            "info": {
                "count": len(labels),
                "min_y": min(values) if values else None,
                "max_y": max(values) if values else None,
                "sum_y": sum(values) if values else 0
            }
        })
    
    except Exception as e:
        import traceback
        print("❌ ERROR:")
        print(traceback.format_exc())
        return jsonify({'error': f'Error al generar gráfica: {str(e)}'}), 500


# =========================
# DELETE FILE
# =========================
@app.route('/delete_file', methods=['POST'])
def delete_file():
    filename = request.json.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'message': 'No se especificó ningún archivo'}), 400
    
    upload_dir = app.config['UPLOAD_FOLDER']
    path = os.path.join(upload_dir, filename)
    
    if not os.path.exists(path):
        return jsonify({'success': False, 'message': f'El archivo "{filename}" no existe'}), 404
    
    try:
        os.remove(path)
        print(f"🗑️ Archivo eliminado: {filename}")
        
        # Si el archivo eliminado era el actual, limpiar sesión
        if session.get('current_file') == filename:
            session.pop('current_file', None)
        
        return jsonify({'success': True, 'message': f'Archivo "{filename}" eliminado correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al eliminar: {str(e)}'}), 500


# =========================
# DELETE ALL FILES
# =========================
@app.route('/delete_all_files', methods=['POST'])
def delete_all_files():
    upload_dir = app.config['UPLOAD_FOLDER']
    
    try:
        files = [f for f in os.listdir(upload_dir) if f.endswith('.csv')]
        deleted = []
        for f in files:
            path = os.path.join(upload_dir, f)
            os.remove(path)
            deleted.append(f)
        
        print(f"🗑️ Eliminados todos los archivos: {deleted}")
        session.pop('current_file', None)
        
        return jsonify({
            'success': True, 
            'message': f'Eliminados {len(deleted)} archivos',
            'deleted': deleted
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al eliminar: {str(e)}'}), 500




# =========================
# MAIN
# =========================
if __name__ == '__main__':
    app.run(debug=True)