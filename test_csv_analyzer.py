import os
import tempfile
import unittest
import pandas as pd
from csv_analyzer import detect_delimiter, analyze_csv_advanced

class TestCSVAnalyzer(unittest.TestCase):
    def setUp(self):
        # Crear un directorio temporal para las pruebas
        self.test_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        # Limpiar el directorio temporal
        self.test_dir.cleanup()

    def create_temp_file(self, content, suffix='.csv'):
        file_path = os.path.join(self.test_dir.name, next(tempfile._get_candidate_names()) + suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def test_detect_delimiter_comma(self):
        content = "name,age,city\nAlice,30,New York\nBob,25,Paris"
        file_path = self.create_temp_file(content)
        self.assertEqual(detect_delimiter(file_path), ',')

    def test_detect_delimiter_semicolon(self):
        content = "name;age;city\nAlice;30;New York\nBob;25;Paris"
        file_path = self.create_temp_file(content)
        self.assertEqual(detect_delimiter(file_path), ';')

    def test_detect_delimiter_tab(self):
        content = "name\tage\tcity\nAlice\t30\tNew York\nBob\t25\tParis"
        file_path = self.create_temp_file(content)
        self.assertEqual(detect_delimiter(file_path), '\t')

    def test_analyze_csv_advanced_types_and_stats(self):
        # Crear un CSV complejo con varios tipos y delimitado por punto y coma (;)
        content = (
            "id;nombre;fecha_nacimiento;puntaje;activo\n"
            "1;Alice;1990-05-15;85.5;True\n"
            "2;Bob;1995-10-20;90.0;False\n"
            "3;Charlie;1988-12-01;72.2;True\n"
            "4;Diana;2000-01-01;;True\n"  # Puntaje nulo
        )
        file_path = self.create_temp_file(content)
        
        results, df = analyze_csv_advanced(file_path)
        
        # Verificar metadatos
        self.assertEqual(results['delimitador_detectado'], ';')
        self.assertEqual(results['total_filas'], 4)
        self.assertEqual(results['total_columnas'], 5)
        
        # Verificar tipos detectados
        columnas = results['columnas']
        self.assertEqual(columnas['id']['tipo_detectado'], 'numérico')
        self.assertEqual(columnas['nombre']['tipo_detectado'], 'texto')
        self.assertEqual(columnas['fecha_nacimiento']['tipo_detectado'], 'fecha')
        self.assertEqual(columnas['puntaje']['tipo_detectado'], 'numérico')
        self.assertEqual(columnas['activo']['tipo_detectado'], 'texto') # Booleano tratado como texto o categórico

        # Verificar nulos y no nulos
        self.assertEqual(columnas['puntaje']['nulos'], 1)
        self.assertEqual(columnas['puntaje']['no_nulos'], 3)

        # Verificar estadísticas numéricas de 'puntaje'
        puntaje_stats = columnas['puntaje']['estadisticas']
        # Media de [85.5, 90.0, 72.2] = 82.5667
        self.assertAlmostEqual(puntaje_stats['media'], 82.5667, places=4)
        self.assertEqual(puntaje_stats['mínimo'], 72.2)
        self.assertEqual(puntaje_stats['máximo'], 90.0)
        self.assertEqual(puntaje_stats['mediana'], 85.5)

        # Verificar estadísticas de fechas para 'fecha_nacimiento'
        fecha_stats = columnas['fecha_nacimiento']['estadisticas']
        self.assertEqual(fecha_stats['mínimo'], '1988-12-01 00:00:00')
        self.assertEqual(fecha_stats['máximo'], '2000-01-01 00:00:00')

        # Verificar estadísticas de texto para 'nombre'
        nombre_stats = columnas['nombre']['estadisticas']
        self.assertEqual(nombre_stats['valores_únicos'], 4)

if __name__ == '__main__':
    unittest.main()
