import os
import uvicorn
from .api import create_app
from .config import PORT
os.umask(0o077)
if __name__=='__main__':
    uvicorn.run(create_app(),host='127.0.0.1',port=PORT,access_log=False)
