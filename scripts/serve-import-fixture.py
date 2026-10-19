"""Serve only original test files; never expose the repository or private model data."""
import functools
import http.server
import shutil
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    shutil.copy(root/'research/fixtures/browser-import/article.html',Path(directory)/'article.html')
    shutil.copy(root/'extensions/chrome/extract.js',Path(directory)/'extract.js')
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=directory)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',8766),handler)
    print('Original fixture: http://127.0.0.1:8766/article.html',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
