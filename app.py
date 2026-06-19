import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename

# Importar el analizador inteligente
from csv_analyzer import analyze_csv_advanced, validate_csv_file

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'un-secreto-muy-seguro-para-desarrollo')

# Configuración de subidas y límites de tamaño (5MB)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

# Asegurarse de que la carpeta uploads exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Manejador para archivos que exceden los 5MB o errores genéricos de tamaño
@app.errorhandler(413)
def request_entity_too_large(error):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
        return jsonify({
            'error': 'El archivo excede el límite de tamaño permitido de 5MB.'
        }), 413
    flash('El archivo excede el límite de tamaño permitido de 5MB.')
    return redirect(url_for('index'))

@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    csv_files = [f for f in files if f.endswith('.csv')]
    current_file = session.get('current_file')
    
    if current_file and current_file not in csv_files:
        session.pop('current_file', None)
        current_file = None
        
    return render_template('index.html', csv_files=csv_files, current_file=current_file)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No se proporcionó la parte del archivo en la solicitud.')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo.')
        return redirect(url_for('index'))
    
    if file:
        filename = secure_filename(file.filename)
        # Validar extensión antes de guardar temporalmente
        if not ('.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'):
            flash('Tipo de archivo no permitido. Solo se aceptan archivos con extensión .csv.')
            return redirect(url_for('index'))

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Validar contenido del archivo guardado
        is_valid, error_msg = validate_csv_file(file_path)
        if not is_valid:
            os.remove(file_path) # Eliminar archivo inválido
            flash(error_msg)
            return redirect(url_for('index'))
        
        session['current_file'] = filename
        flash(f'Archivo "{filename}" subido exitosamente.')
        return redirect(url_for('index'))
    
    flash('Error al subir el archivo.')
    return redirect(url_for('index'))

@app.route('/process', methods=['GET'])
def process_data():
    filename = request.args.get('file') or session.get('current_file')
    
    if not filename:
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
        if files:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], x)), reverse=True)
            filename = files[0]
            session['current_file'] = filename
        else:
            flash('Sube un archivo CSV antes de procesar.')
            return redirect(url_for('index'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        flash(f'El archivo "{filename}" no se encuentra disponible.')
        session.pop('current_file', None)
        return redirect(url_for('index'))

    try:
        # Analizar el CSV usando nuestra función inteligente
        analysis_results, df = analyze_csv_advanced(file_path)
        
        # Mapear columnas para mostrar en la tabla de estructura
        info = []
        for col, col_data in analysis_results['columnas'].items():
            info.append({
                'columna': col,
                'tipo_original': col_data['tipo_original'],
                'tipo_detectado': col_data['tipo_detectado'],
                'no_nulos': col_data['no_nulos'],
                'nulos': col_data['nulos']
            })
            
        # Preparar la previsualización (primeras 10 filas)
        preview_headers = list(df.columns)
        # Convertir nans a cadena vacía para renderizado web seguro
        preview_rows = df.head(10).fillna('').values.tolist()
        
        analysis = {
            'archivo': filename,
            'delimitador': analysis_results['delimitador_detectado'],
            'total_filas': analysis_results['total_filas'],
            'total_columnas': analysis_results['total_columnas'],
            'analisis_columnas': info,
            'preview_headers': preview_headers,
            'preview_rows': preview_rows
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('json') == 'true':
            return jsonify(analysis)
        
        csv_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
        return render_template('index.html', csv_files=csv_files, current_file=filename, analysis=analysis)

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('json') == 'true':
            return jsonify({'error': f'Error al procesar el archivo: {str(e)}'}), 500
        flash(f'Error al procesar el archivo CSV: {str(e)}')
        return redirect(url_for('index'))

@app.route('/stats', methods=['GET'])
def stats_data():
    filename = request.args.get('file') or session.get('current_file')
    
    if not filename:
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
        if files:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], x)), reverse=True)
            filename = files[0]
            session['current_file'] = filename
        else:
            flash('Sube un archivo CSV antes de consultar estadísticas.')
            return redirect(url_for('index'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        flash(f'El archivo "{filename}" no se encuentra disponible.')
        session.pop('current_file', None)
        return redirect(url_for('index'))

    try:
        # Analizar el CSV usando nuestra función inteligente
        analysis_results, df = analyze_csv_advanced(file_path)
        
        # Filtrar estadísticas para las columnas numéricas
        numeric_stats = {}
        for col, col_data in analysis_results['columnas'].items():
            if col_data.get('tipo_detectado') == 'numérico' and 'estadisticas' in col_data:
                numeric_stats[col] = col_data['estadisticas']
                
        if not numeric_stats:
            stats_response = {
                'archivo': filename,
                'no_numeric': True,
                'mensaje': 'El archivo no contiene columnas identificadas como numéricas para generar estadísticas descriptivas.',
                'total_filas': analysis_results['total_filas'],
                'total_columnas': analysis_results['total_columnas']
            }
        else:
            stats_response = {
                'archivo': filename,
                'no_numeric': False,
                'total_filas': analysis_results['total_filas'],
                'columnas_numericas': list(numeric_stats.keys()),
                'estadisticas': numeric_stats
            }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('json') == 'true':
            return jsonify(stats_response)
            
        csv_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
        return render_template('index.html', csv_files=csv_files, current_file=filename, stats=stats_response)

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('json') == 'true':
            return jsonify({'error': f'Error al calcular estadísticas: {str(e)}'}), 500
        flash(f'Error al calcular estadísticas: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
