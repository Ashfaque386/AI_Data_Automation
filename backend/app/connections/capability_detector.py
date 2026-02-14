"""
Capability Detector - Detects database capabilities and features
"""
from typing import Dict, Any
import logging
from sqlalchemy.orm import Session

from app.models.connection import ConnectionProfile
from app.connections.connection_manager import connection_manager
from app.connections.connectors.base_connector import DatabaseCapabilities
from app.core.crypto import decrypt_password

logger = logging.getLogger(__name__)


class CapabilityDetector:
    """
    Detects and caches database capabilities.
    
    Automatically detects database version, features, extensions,
    and other capabilities for optimal query generation and UI features.
    """
    
    def detect_and_save(self, db: Session, connection: ConnectionProfile) -> DatabaseCapabilities:
        """
        Detect capabilities and save to connection profile.
        
        Args:
            db: Database session
            connection: ConnectionProfile to detect
            
        Returns:
            DatabaseCapabilities object
        """
        try:
            # Decrypt password
            decrypted_password = decrypt_password(connection.encrypted_password)
            
            # Get connector
            connector = connection_manager.get_connector(connection, decrypted_password)
            
            # Detect capabilities
            capabilities = connector.detect_capabilities()
            
            # Save to connection profile
            connection.capabilities = self._capabilities_to_dict(capabilities)
            db.commit()
            
            logger.info(f"Detected capabilities for {connection.name}: {capabilities.version}")
            
            return capabilities
            
        except Exception as e:
            logger.error(f"Failed to detect capabilities for {connection.name}: {str(e)}")
            raise
    
    def _capabilities_to_dict(self, capabilities: DatabaseCapabilities) -> Dict[str, Any]:
        """Convert DatabaseCapabilities to dict for JSON storage."""
        return {
            "version": capabilities.version,
            "supports_transactions": capabilities.supports_transactions,
            "supports_stored_procedures": capabilities.supports_stored_procedures,
            "supports_views": capabilities.supports_views,
            "supports_materialized_views": capabilities.supports_materialized_views,
            "supports_json": capabilities.supports_json,
            "supports_full_text_search": capabilities.supports_full_text_search,
            "max_connections": capabilities.max_connections,
            "features": capabilities.features,
            "extensions": capabilities.extensions
        }
    
    def get_cached_capabilities(self, connection: ConnectionProfile) -> Dict[str, Any]:
        """
        Get cached capabilities from connection profile.
        
        Args:
            connection: ConnectionProfile
            
        Returns:
            Capabilities dict or empty dict if not detected
        """
        return connection.capabilities or {}
    
    def supports_feature(self, connection: ConnectionProfile, feature: str) -> bool:
        """
        Check if connection supports a specific feature.
        
        Args:
            connection: ConnectionProfile
            feature: Feature name (e.g., 'transactions', 'stored_procedures')
            
        Returns:
            True if feature is supported
        """
        capabilities = self.get_cached_capabilities(connection)
        feature_map = {
            'transactions': 'supports_transactions',
            'stored_procedures': 'supports_stored_procedures',
            'views': 'supports_views',
            'materialized_views': 'supports_materialized_views',
            'json': 'supports_json',
            'full_text_search': 'supports_full_text_search'
        }
        
        capability_key = feature_map.get(feature)
        if capability_key:
            return capabilities.get(capability_key, False)
        
        return False


# Global capability detector instance
capability_detector = CapabilityDetector()
