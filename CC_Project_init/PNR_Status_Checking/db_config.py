# config.py for PNR Service

db_config = {
    'host': 'host.docker.internal',  # Change to your MySQL host
    'user': 'root',
    'password': 'mithun0611',
    'database': 'pnr_db',  # Dedicated database for PNR service
    'port': 3306,
    'auth_plugin': 'mysql_native_password'  # Add this if needed for your MySQL version
}