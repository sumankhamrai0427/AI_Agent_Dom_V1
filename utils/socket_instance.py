from flask_socketio import SocketIO

# Global SocketIO instance to avoid circular imports
socketio = SocketIO(cors_allowed_origins="*")
