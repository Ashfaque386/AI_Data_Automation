"""
Health Monitor Service - Monitors connection health
"""
from typing import List, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from app.models.connection import ConnectionProfile, HealthStatus
from app.models.connection_health import ConnectionHealthLog
from app.connections.connection_manager import connection_manager
from app.core.crypto import decrypt_password

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Monitors database connection health.
    
    Performs periodic health checks, logs results, and updates
    connection status in the database.
    """
    
    async def monitor_all_connections(self, db: Session) -> None:
        """
        Monitor health of all active connections.
        
        Args:
            db: Database session
        """
        connections = db.query(ConnectionProfile).filter(
            ConnectionProfile.is_active == True
        ).all()
        
        for connection in connections:
            await self.check_connection(db, connection)
    
    async def check_connection(self, db: Session, connection: ConnectionProfile) -> HealthStatus:
        """
        Check health of a single connection.
        
        Args:
            db: Database session
            connection: ConnectionProfile to check
            
        Returns:
            HealthStatus enum value
        """
        try:
            # Decrypt password
            decrypted_password = decrypt_password(connection.encrypted_password)
            
            # Get or create connector
            connector = connection_manager.get_connector(connection, decrypted_password)
            
            # Perform health check
            health_result = connector.test_connection()
            
            # Determine status
            if health_result.is_healthy:
                new_status = HealthStatus.ONLINE
                connection.failed_attempts = 0
            else:
                connection.failed_attempts += 1
                if connection.failed_attempts >= 3:
                    new_status = HealthStatus.OFFLINE
                else:
                    new_status = HealthStatus.DEGRADED
            
            # Update connection profile
            connection.health_status = new_status
            connection.last_health_check = health_result.timestamp
            connection.response_time_ms = health_result.response_time_ms
            
            # Log health check
            self.log_health_status(
                db=db,
                connection_id=connection.id,
                status=new_status.value,
                response_time_ms=health_result.response_time_ms,
                error_message=health_result.error_message,
                checked_by="system"
            )
            
            db.commit()
            
            logger.info(f"Health check for {connection.name}: {new_status.value} ({health_result.response_time_ms}ms)")
            
            return new_status
            
        except Exception as e:
            logger.error(f"Health check failed for {connection.name}: {str(e)}")
            
            # Update as offline
            connection.health_status = HealthStatus.OFFLINE
            connection.failed_attempts += 1
            connection.last_health_check = datetime.utcnow()
            
            self.log_health_status(
                db=db,
                connection_id=connection.id,
                status=HealthStatus.OFFLINE.value,
                response_time_ms=0,
                error_message=str(e),
                checked_by="system"
            )
            
            db.commit()
            
            return HealthStatus.OFFLINE
    
    def log_health_status(
        self,
        db: Session,
        connection_id: int,
        status: str,
        response_time_ms: int,
        error_message: Optional[str] = None,
        checked_by: str = "system"
    ) -> ConnectionHealthLog:
        """
        Log health check result.
        
        Args:
            db: Database session
            connection_id: Connection profile ID
            status: Health status string
            response_time_ms: Response time in milliseconds
            error_message: Error message if check failed
            checked_by: Who triggered the check
            
        Returns:
            Created ConnectionHealthLog instance
        """
        log = ConnectionHealthLog(
            connection_id=connection_id,
            status=status,
            response_time_ms=response_time_ms,
            error_message=error_message,
            checked_by=checked_by
        )
        db.add(log)
        db.commit()
        return log
    
    def get_health_history(
        self,
        db: Session,
        connection_id: int,
        hours: int = 24
    ) -> List[ConnectionHealthLog]:
        """
        Get health check history for a connection.
        
        Args:
            db: Database session
            connection_id: Connection profile ID
            hours: Number of hours to look back
            
        Returns:
            List of ConnectionHealthLog entries
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return db.query(ConnectionHealthLog).filter(
            ConnectionHealthLog.connection_id == connection_id,
            ConnectionHealthLog.timestamp >= since
        ).order_by(ConnectionHealthLog.timestamp.desc()).all()
    
    def alert_on_failure(self, connection: ConnectionProfile) -> None:
        """
        Send alert when connection fails.
        
        Args:
            connection: Failed connection profile
        """
        # TODO: Implement alerting (email, webhook, etc.)
        logger.warning(f"ALERT: Connection {connection.name} is offline after {connection.failed_attempts} attempts")


# Global health monitor instance
health_monitor = HealthMonitor()
