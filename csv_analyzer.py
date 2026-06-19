import csv
import pandas as pd
import numpy as np

def detect_delimiter(file_path):
    """
    Detecta automáticamente el delimitador de un archivo CSV usando csv.Sniffer.
    Soporta comas, puntos y comas, tabulaciones y barras verticales.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Leer los primeros 4096 caracteres para el análisis del delimitador
            sample = f.read(4096)
            if not sample:
                return ','
            
            # Buscar delimitadores comunes si el Sniffer falla o requiere más contexto
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=[',', ';', '\t', '|'])
            return dialect.delimiter
    except Exception:
        # En caso de fallo, buscar manualmente la frecuencia de caracteres separadores típicos en la primera línea
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                candidates = [';', ',', '\t', '|']
                counts = {c: first_line.count(c) for c in candidates}
                best_candidate = max(counts, key=counts.get)
                if counts[best_candidate] > 0:
                    return best_candidate
        except Exception:
            pass
        return ','  # Delimitador por defecto

def analyze_csv_advanced(file_path):
    """
    Lee un archivo CSV detectando su delimitador, identifica el tipo de datos
    de cada columna (numérico, fecha o texto) y calcula estadísticas básicas.
    
    Retorna:
        dict: Un diccionario con los metadatos, tipo detectado y estadísticas detalladas por columna.
        DataFrame: El objeto pandas DataFrame leído.
    """
    # 1. Detectar delimitador
    delimiter = detect_delimiter(file_path)
    
    # 2. Leer archivo con el delimitador detectado
    try:
        # Cargamos el dataframe inicialmente sin conversión estricta para realizar nuestro análisis
        df = pd.read_csv(file_path, sep=delimiter, low_memory=False)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo CSV: {str(e)}")
        
    analysis_results = {
        'delimitador_detectado': delimiter,
        'total_filas': len(df),
        'total_columnas': len(df.columns),
        'columnas': {}
    }
    
    # 3. Analizar cada columna
    for col in df.columns:
        series = df[col]
        non_null_series = series.dropna()
        
        col_info = {
            'tipo_original': str(series.dtype),
            'nulos': int(series.isnull().sum()),
            'no_nulos': int(series.notnull().sum()),
        }
        
        if len(non_null_series) == 0:
            col_info['tipo_detectado'] = 'vacio'
            analysis_results['columnas'][col] = col_info
            continue
            
        # Intentar clasificar el tipo
        # A. ¿Es Numérico?
        is_numeric = False
        numeric_series = None
        if pd.api.types.is_bool_dtype(series):
            # Columnas booleanas se tratan como texto o categóricas, no numéricas
            pass
        elif pd.api.types.is_numeric_dtype(series):
            is_numeric = True
            numeric_series = series
        else:
            try:
                # Intentar conversión para ver si la mayoría de campos de texto representan números
                conv = pd.to_numeric(series, errors='coerce')
                # Si el 80% o más se convierte con éxito, lo consideramos numérico
                if conv.notnull().sum() / len(non_null_series) >= 0.8:
                    is_numeric = True
                    numeric_series = conv
            except Exception:
                pass
                
        # B. ¿Es Fecha?
        is_date = False
        date_series = None
        if not is_numeric:
            # Solo buscar fechas en columnas tipo object/string que tengan caracteres de fecha comunes
            is_str_col = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
            if is_str_col:
                sample_values = non_null_series.astype(str).head(15)
                has_date_separators = any(any(char in val for char in ['-', '/', ':', ' ']) for val in sample_values)
                if has_date_separators:
                    try:
                        conv_date = pd.to_datetime(series, errors='coerce')
                        if conv_date.notnull().sum() / len(non_null_series) >= 0.8:
                            is_date = True
                            date_series = conv_date
                    except Exception:
                        pass
                        
        # Registrar tipo detectado y estadísticas correspondientes
        if is_numeric:
            col_info['tipo_detectado'] = 'numérico'
            # Calcular estadísticas especificadas por el usuario (media, mediana, mínimo, máximo)
            stats = {
                'media': float(numeric_series.mean()) if pd.notnull(numeric_series.mean()) else None,
                'mediana': float(numeric_series.median()) if pd.notnull(numeric_series.median()) else None,
                'mínimo': float(numeric_series.min()) if pd.notnull(numeric_series.min()) else None,
                'máximo': float(numeric_series.max()) if pd.notnull(numeric_series.max()) else None,
                'desv_estandar': float(numeric_series.std()) if pd.notnull(numeric_series.std()) else None
            }
            # Redondear para legibilidad
            for k, v in stats.items():
                if v is not None:
                    stats[k] = round(v, 4)
            col_info['estadisticas'] = stats
            
        elif is_date:
            col_info['tipo_detectado'] = 'fecha'
            # Para fechas, las estadísticas de rango son ideales
            min_date = date_series.min()
            max_date = date_series.max()
            col_info['estadisticas'] = {
                'mínimo': min_date.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(min_date) else None,
                'máximo': max_date.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(max_date) else None
            }
            
        else:
            col_info['tipo_detectado'] = 'texto'
            # Para texto, el conteo de valores únicos y la moda son las métricas indicadas
            value_counts = non_null_series.value_counts()
            col_info['estadisticas'] = {
                'valores_únicos': int(non_null_series.nunique()),
                'más_frecuente': str(value_counts.index[0]) if len(value_counts) > 0 else None,
                'frecuencia_más_frecuente': int(value_counts.iloc[0]) if len(value_counts) > 0 else 0
            }
            
        analysis_results['columnas'][col] = col_info
        
    return analysis_results, df


def validate_csv_file(file_path):
    """
    Valida un archivo CSV para:
    1. Archivos que no sean CSV (archivos binarios, etc.)
    2. Archivos mayores a 5MB
    3. Delimitadores no soportados
    4. Datos vacíos (tamaño 0, o sin filas, o solo headers vacíos)
    
    Retorna (bool, msg) indicando si es válido y un mensaje de error si no lo es.
    """
    import os
    
    # 1. Validar existencia
    if not os.path.exists(file_path):
        return False, "El archivo no existe."
        
    # 2. Validar tamaño mayor a 5MB
    size_bytes = os.path.getsize(file_path)
    if size_bytes > 5 * 1024 * 1024:
        return False, "El archivo excede el límite de tamaño permitido de 5MB."
        
    # 3. Validar datos vacíos (archivo de tamaño 0)
    if size_bytes == 0:
        return False, "El archivo está vacío (0 bytes)."
        
    # 4. Validar si es binario (archivos que no son CSV)
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return False, "El archivo no es un CSV válido (parece ser un archivo binario)."
    except Exception as e:
        return False, f"No se pudo leer el archivo: {str(e)}"
        
    # 5. Validar que se pueda decodificar como texto
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content_sample = f.read(10240)
    except Exception as e:
        return False, f"El archivo no contiene texto legible: {str(e)}"
        
    # 6. Validar delimitador
    try:
        delimiter = detect_delimiter(file_path)
        supported_delimiters = [',', ';', '\t', '|']
        if delimiter not in supported_delimiters:
            return False, "Delimitador no soportado. Los delimitadores permitidos son: coma (,), punto y coma (;), tabulación (\\t) y barra vertical (|)."
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
            
        if not first_line:
            return False, "El archivo está vacío o tiene una estructura inválida."
            
        # Comprobar si el primer renglón contiene delimitadores no soportados y ninguno soportado
        # Ej: si tiene ':' pero no tiene ',' ';' '\t' '|'
        has_supported_delimiter = any(delim in first_line for delim in supported_delimiters)
        
    except Exception as e:
        return False, f"Error al analizar el formato del archivo: {str(e)}"
        
    # 7. Validar contenido vacío (sin filas de datos) y delimitador
    try:
        df = pd.read_csv(file_path, sep=delimiter, nrows=5, low_memory=False)
        if len(df) == 0:
            return False, "El archivo no contiene filas de datos (solo la cabecera)."
            
        if len(df.columns) == 0:
            return False, "El archivo no tiene columnas válidas."
            
        # Si se leyó como 1 sola columna y el nombre de la columna contiene un delimitador no soportado común como ':'
        if len(df.columns) == 1:
            col_name = str(df.columns[0])
            for unsupported_delim in [':']:
                if unsupported_delim in col_name and not any(sd in col_name for sd in supported_delimiters):
                    return False, f"Delimitador no soportado '{unsupported_delim}'. Los delimitadores permitidos son: coma (,), punto y coma (;), tabulación (\\t) y barra vertical (|)."
                    
    except Exception as e:
        return False, f"No se pudo leer el archivo CSV: {str(e)}"
        
    return True, ""
