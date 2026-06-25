import os
import tempfile
import unittest
import io
from app import app


class TestFlaskApp(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

        self.test_upload_dir = tempfile.TemporaryDirectory()
        app.config['UPLOAD_FOLDER'] = self.test_upload_dir.name

        self.client = app.test_client()

    def tearDown(self):
        self.test_upload_dir.cleanup()

    # =========================
    # INDEX
    # =========================
    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    # =========================
    # UPLOAD
    # =========================
    def test_upload_csv(self):
        csv_data = "col1,col2,col3\n1,2,3\n4,5,6"

        file = (io.BytesIO(csv_data.encode('utf-8')), 'ventas.csv')

        with self.client as c:
            response = c.post(
                '/upload',
                data={'file': file},
                content_type='multipart/form-data',
                follow_redirects=True
            )

            self.assertEqual(response.status_code, 200)

            path = os.path.join(app.config['UPLOAD_FOLDER'], 'ventas.csv')
            self.assertTrue(os.path.exists(path))

            with c.session_transaction() as sess:
                self.assertEqual(sess.get('current_file'), 'ventas.csv')

    # =========================
    # PROCESS
    # =========================
    def test_process(self):
        csv_data = "id,nombre,valor\n1,A,100\n2,B,200"

        file = (io.BytesIO(csv_data.encode('utf-8')), 'ventas.csv')

        with self.client as c:
            c.post('/upload', data={'file': file}, content_type='multipart/form-data')

            response = c.get('/process?file=ventas.csv')
            self.assertEqual(response.status_code, 200)

            data = response.get_json()

            self.assertEqual(data['archivo'], 'ventas.csv')
            self.assertEqual(data['total_columnas'], 3)
            self.assertIn('preview_headers', data)

    # =========================
    # STATS
    # =========================
    # STATS
    # =========================
    def test_stats(self):
        csv_data = "id,valor\n1,100\n2,200\n3,300"

        file = (io.BytesIO(csv_data.encode('utf-8')), 'ventas.csv')

        with self.client as c:
            c.post('/upload', data={'file': file}, content_type='multipart/form-data')

            response = c.get('/stats?file=ventas.csv')
            self.assertEqual(response.status_code, 200)

            data = response.get_json()

            self.assertIn('estadisticas', data)

            if not data.get('no_numeric'):
                self.assertIn('valor', data['estadisticas'])

    # =========================
    # CHART DATA
    # =========================
    def test_chart_data_no_x_column(self):
        csv_data = "id,valor\n1,100\n2,200\n3,300"
        file = (io.BytesIO(csv_data.encode('utf-8')), 'ventas.csv')

        with self.client as c:
            c.post('/upload', data={'file': file}, content_type='multipart/form-data')

            # Sin column_x, debería usar números de índice
            response = c.get('/chart_data?file=ventas.csv&column=valor&type=bar')
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertEqual(data['labels'], ['0', '1', '2'])
            self.assertEqual(data['values'], [100.0, 200.0, 300.0])

    def test_chart_data_with_x_column(self):
        # 20 filas, pero solo 3 nombres/categorías únicos (repetidos)
        csv_rows = ["nombre,valor"]
        # A, B, C repetidos
        for i in range(20):
            name = "A" if i % 3 == 0 else ("B" if i % 3 == 1 else "C")
            csv_rows.append(f"{name},{10}")
        csv_data = "\n".join(csv_rows)

        file = (io.BytesIO(csv_data.encode('utf-8')), 'ventas.csv')

        with self.client as c:
            c.post('/upload', data={'file': file}, content_type='multipart/form-data')

            # Con column_x, debería agrupar por nombre y mantener el orden de aparición (A, B, C)
            response = c.get('/chart_data?file=ventas.csv&column_x=nombre&column_y=valor&type=bar')
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertEqual(data['labels'], ['A', 'B', 'C'])
            # 20 filas: A aparece 7 veces (0,3,6,9,12,15,18), B 7 veces (1,4,7,10,13,16,19), C 6 veces (2,5,8,11,14,17)
            # Cada valor es 10.0, por lo que las sumas son A=70.0, B=70.0, C=60.0
            self.assertEqual(data['values'], [70.0, 70.0, 60.0])


if __name__ == '__main__':
    unittest.main()