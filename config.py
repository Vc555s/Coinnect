import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///coinnect.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Filebase configuration
    FILEBASE_ACCESS_KEY = os.environ.get('FILEBASE_ACCESS_KEY', '')
    FILEBASE_SECRET_KEY = os.environ.get('FILEBASE_SECRET_KEY', '')
    
    # IPFS Gateway URL - for viewing files
    IPFS_GATEWAY_URL = 'https://ipfs.filebase.io/ipfs/'
