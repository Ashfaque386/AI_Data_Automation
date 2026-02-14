"""
Connection Manager - Manages multiple database connections
"""
from typing import Dict, Optional
from uuid import UUID
import logging

from app.models.connection import ConnectionProfile, ConnectionType
from app.core.crypto import decrypt_password, decrypt_value
from app.connections.connectors.base_connector import BaseConnector, HealthCheckResult
from app.connections.connectors.postgres_connector import PostgreSQLConnector
from app.connections.connectors.mysql_connector import MySQLConnector
from app.connections.connectors.sqlite_connector import SQLiteConnector
from app.connections.connectors.mongodb_connector import MongoDBConnector

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages database connections and connection pools.
    
    Provides centralized access to multiple database connections with
    automatic pooling, health monitoring, and lifecycle management.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self._connectors: Dict[int, BaseConnector] = {}
        self._connection_profiles: Dict[int, ConnectionProfile] = {}
    
    def get_connector(self, connection_profile: ConnectionProfile, decrypted_password: str = None) -> BaseConnector:
        """
        Get or create a connector for the given connection profile.
        
        Args:
            connection_profile: ConnectionProfile model instance
            decrypted_password: Decrypted password (if not provided, will decrypt from profile)
            
        Returns:
            BaseConnector instance for the database type
            
        Raises:
            ValueError: If database type is not supported
            ConnectionError: If connection fails
        """
        connection_id = connection_profile.id
        
        # Return existing connector if available
        if connection_id in self._connectors:
            connector = self._connectors[connection_id]
            if connector.is_connected():
                return connector
            else:
                # Reconnect if disconnected
                connector.connect()
                return connector
        
        # Create new connector
        if not decrypted_password:
            decrypted_password = decrypt_password(connection_profile.encrypted_password)
            
        decrypted_connection_string = None
        if hasattr(connection_profile, 'encrypted_connection_string') and connection_profile.encrypted_connection_string:
            decrypted_connection_string = decrypt_value(connection_profile.encrypted_connection_string)
        
        # Get connection string (prioritizing the full URI if present)
        connection_string = connection_profile.get_connection_string(decrypted_password, decrypted_connection_string)
        
        # Select connector based on database type
        connector_class = self._get_connector_class(connection_profile.db_type)
        
        connector = connector_class(
            connection_string=connection_string,
            pool_size=connection_profile.pool_size,
            timeout=connection_profile.timeout_seconds
        )
        
        # Connect
        try:
            connector.connect()
            self._connectors[connection_id] = connector
            self._connection_profiles[connection_id] = connection_profile
            logger.info(f"Connected to database: {connection_profile.name} (ID: {connection_id})")
            return connector
        except Exception as e:
            logger.error(f"Failed to connect to {connection_profile.name}: {str(e)}")
            raise

    def create_temp_connector(self, connection_profile: ConnectionProfile, decrypted_password: str = None, decrypted_connection_string: str = None) -> BaseConnector:
        """
        Create a temporary connector without caching.
        Use for testing connections or discovering databases.
        """
        if not decrypted_password and connection_profile.encrypted_password:
             decrypted_password = decrypt_password(connection_profile.encrypted_password)
             
        if not decrypted_connection_string and hasattr(connection_profile, 'encrypted_connection_string') and connection_profile.encrypted_connection_string:
             decrypted_connection_string = decrypt_value(connection_profile.encrypted_connection_string)
            
        connection_string = connection_profile.get_connection_string(decrypted_password, decrypted_connection_string)
        
        connector_class = self._get_connector_class(connection_profile.db_type)
        
        connector = connector_class(
            connection_string=connection_string,
            pool_size=1, # Minimal pool for temp operations
            timeout=10   # Shorter timeout
        )
        
        connector.connect()
        return connector
    
    def _get_connector_class(self, db_type: ConnectionType):
        """Get connector class for database type."""
        connector_map = {
            ConnectionType.POSTGRESQL: PostgreSQLConnector,
            ConnectionType.MYSQL: MySQLConnector,
            ConnectionType.MARIADB: MySQLConnector,  # Use MySQL connector for MariaDB
            ConnectionType.SQLITE: SQLiteConnector,
            ConnectionType.MONGODB: MongoDBConnector,
            # TODO: Add Oracle, SQL Server connectors
        }
        
        connector_class = connector_map.get(db_type)
        if not connector_class:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        return connector_class
    
    def close_connection(self, connection_id: int) -> None:
        """
        Close and remove a connection.
        
        Args:
            connection_id: Connection profile ID
        """
        if connection_id in self._connectors:
            connector = self._connectors[connection_id]
            connector.disconnect()
            del self._connectors[connection_id]
            del self._connection_profiles[connection_id]
            logger.info(f"Closed connection ID: {connection_id}")
    
    def close_all_connections(self) -> None:
        """Close all active connections."""
        for connection_id in list(self._connectors.keys()):
            self.close_connection(connection_id)
        logger.info("Closed all connections")
    
    def health_check(self, connection_id: int) -> Optional[HealthCheckResult]:
        """
        Perform health check on a connection.
        
        Args:
            connection_id: Connection profile ID
            
        Returns:
            HealthCheckResult or None if connection not found
        """
        if connection_id not in self._connectors:
            return None
        
        connector = self._connectors[connection_id]
        return connector.test_connection()
    
    def get_active_connections(self) -> Dict[int, str]:
        """
        Get list of active connections.
        
        Returns:
            Dict mapping connection_id to connection name
        """
        return {
            conn_id: profile.name
            for conn_id, profile in self._connection_profiles.items()
        }
    
    def cleanup_idle_connections(self) -> int:
        """
        Cleanup idle/disconnected connections.
        
        Returns:
            Number of connections cleaned up
        """
        cleaned = 0
        for connection_id in list(self._connectors.keys()):
            connector = self._connectors[connection_id]
            if not connector.is_connected():
                self.close_connection(connection_id)
                cleaned += 1
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} idle connections")
        
        return cleaned


# Global connection manager instance
connection_manager = ConnectionManager()
