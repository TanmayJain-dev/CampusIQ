import os
import sys
import json
import urllib.request
import threading
import socket
import unittest
from http.server import HTTPServer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import CampusIQRequestHandler, load_vault_drive_map, get_cached_catalog

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

class TestDriveVaultStreaming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.server = HTTPServer(('127.0.0.1', cls.port), CampusIQRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f'http://127.0.0.1:{cls.port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_drive_map_integrity(self):
        drive_map = load_vault_drive_map()
        files = drive_map.get('files', {})
        self.assertGreaterEqual(len(files), 700, 'Drive map should contain over 700 verified resources')
        for rel_path, f_id in files.items():
            self.assertTrue(bool(f_id), f'Empty Drive ID for {rel_path}')

    def test_catalog_integrity(self):
        catalog = get_cached_catalog()
        self.assertGreaterEqual(len(catalog), 700, 'Catalog should have over 700 items')
        
        categories = {r.get('category') for r in catalog}
        self.assertIn('Akash Solved Question Banks', categories)
        self.assertIn('Lecture Notes & Theory', categories)
        self.assertIn('Previous Year Papers', categories)

    def test_api_resources_endpoint(self):
        req = urllib.request.Request(f'{self.base_url}/api/resources')
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertEqual(data.get('status'), 'success')
            self.assertGreaterEqual(data.get('total'), 700)
            self.assertGreater(len(data.get('resources')), 0)

    def test_api_resources_tree_endpoint(self):
        req = urllib.request.Request(f'{self.base_url}/api/resources/tree')
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertEqual(data.get('status'), 'success')
            self.assertIn('tree', data)
            semesters = data['tree']['semesters']
            self.assertIn('1', semesters)
            sem1_subjs = semesters['1'].get('subjects', {})
            self.assertIn('Applied Chemistry', sem1_subjs)
            akash_in_chem = sem1_subjs['Applied Chemistry'].get('categories', {}).get('Akash Solved Question Banks', [])
            self.assertGreater(len(akash_in_chem), 0, 'Semester 1 Chemistry must include Akash solved bank')

    def test_drive_stream_range_partial_content(self):
        akash_id = '1uf-L4ZM7osO3XYI3wVvUE9Gmpp2eZQ0V'
        req = urllib.request.Request(f'{self.base_url}/api/resources/view?id={akash_id}')
        req.add_header('Range', 'bytes=0-1023')
        
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 206, 'Should return HTTP 206 Partial Content')
            self.assertEqual(resp.headers.get('Content-Type'), 'application/pdf')
            self.assertEqual(resp.headers.get('Accept-Ranges'), 'bytes')
            self.assertIn('bytes 0-1023/', resp.headers.get('Content-Range'))
            content = resp.read()
            self.assertEqual(len(content), 1024)
            self.assertTrue(content.startswith(b'%PDF-'), 'Range request must yield valid PDF binary header')

if __name__ == '__main__':
    unittest.main()
