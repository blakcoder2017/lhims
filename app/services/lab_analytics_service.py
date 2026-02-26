"""
Lab Analytics Service

This module provides analytics and KPI calculations for the lab module.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.encounter_models import LabOrder, OrderStatus
from app.models.lab_models import LabSample, SampleStatus, QCRecord, QCStatus


class LabAnalyticsService:
    """Service for calculating lab KPIs and analytics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_order_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_walk_in: bool = True
    ) -> Dict[str, Any]:
        """
        Get lab order statistics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            include_walk_in: Include walk-in orders
            
        Returns:
            Dictionary with order statistics
        """
        query = self.db.query(LabOrder)
        
        if start_date:
            query = query.filter(LabOrder.ordered_at >= start_date)
        if end_date:
            query = query.filter(LabOrder.ordered_at <= end_date)
        
        if not include_walk_in:
            query = query.filter(LabOrder.is_walk_in == False)
        
        total_orders = query.count()
        
        # Status breakdown
        pending = query.filter(LabOrder.status == OrderStatus.PENDING.value).count()
        in_progress = query.filter(LabOrder.status == OrderStatus.IN_PROGRESS.value).count()
        completed = query.filter(LabOrder.status == OrderStatus.COMPLETED.value).count()
        cancelled = query.filter(LabOrder.status == OrderStatus.CANCELLED.value).count()
        
        # Priority breakdown
        routine = query.filter(LabOrder.priority == 'routine').count()
        urgent = query.filter(LabOrder.priority == 'urgent').count()
        stat = query.filter(LabOrder.priority == 'stat').count()
        
        return {
            'total_orders': total_orders,
            'by_status': {
                'pending': pending,
                'in_progress': in_progress,
                'completed': completed,
                'cancelled': cancelled
            },
            'by_priority': {
                'routine': routine,
                'urgent': urgent,
                'stat': stat
            },
            'completion_rate': round((completed / total_orders * 100) if total_orders > 0 else 0, 1)
        }
    
    def get_sample_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get sample tracking statistics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dictionary with sample statistics
        """
        query = self.db.query(LabSample)
        
        if start_date:
            query = query.filter(LabSample.created_at >= start_date)
        if end_date:
            query = query.filter(LabSample.created_at <= end_date)
        
        total_samples = query.count()
        
        # Status breakdown
        collected = query.filter(LabSample.status == SampleStatus.COLLECTED.value).count()
        received = query.filter(LabSample.status == SampleStatus.RECEIVED.value).count()
        processing = query.filter(LabSample.status == SampleStatus.PROCESSING.value).count()
        completed = query.filter(LabSample.status == SampleStatus.COMPLETED.value).count()
        rejected = query.filter(LabSample.status == SampleStatus.REJECTED.value).count()
        expired = query.filter(LabSample.status == SampleStatus.EXPIRED.value).count()
        
        # Rejection rate
        rejection_rate = round((rejected / total_samples * 100) if total_samples > 0 else 0, 1)
        
        return {
            'total_samples': total_samples,
            'by_status': {
                'collected': collected,
                'received': received,
                'processing': processing,
                'completed': completed,
                'rejected': rejected,
                'expired': expired
            },
            'rejection_rate': rejection_rate
        }
    
    def get_turnaround_time_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate turnaround time statistics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dictionary with TAT statistics
        """
        # Get completed orders with completion times
        query = self.db.query(LabOrder).filter(
            LabOrder.status == OrderStatus.COMPLETED.value,
            LabOrder.completed_at.isnot(None),
            LabOrder.ordered_at.isnot(None)
        )
        
        if start_date:
            query = query.filter(LabOrder.ordered_at >= start_date)
        if end_date:
            query = query.filter(LabOrder.ordered_at <= end_date)
        
        orders = query.all()
        
        if not orders:
            return {
                'average_tat_hours': 0,
                'min_tat_hours': 0,
                'max_tat_hours': 0,
                'by_priority': {}
            }
        
        # Calculate TAT for each order
        tat_by_priority = {'routine': [], 'urgent': [], 'stat': []}
        all_tat = []
        
        for order in orders:
            if order.completed_at and order.ordered_at:
                tat_hours = (order.completed_at - order.ordered_at).total_seconds() / 3600
                all_tat.append(tat_hours)
                
                priority = order.priority or 'routine'
                if priority in tat_by_priority:
                    tat_by_priority[priority].append(tat_hours)
        
        # Calculate statistics
        avg_tat = sum(all_tat) / len(all_tat) if all_tat else 0
        min_tat = min(all_tat) if all_tat else 0
        max_tat = max(all_tat) if all_tat else 0
        
        # Calculate averages by priority
        tat_by_priority_avg = {}
        for priority, tat_list in tat_by_priority.items():
            if tat_list:
                tat_by_priority_avg[priority] = round(sum(tat_list) / len(tat_list), 1)
            else:
                tat_by_priority_avg[priority] = 0
        
        return {
            'average_tat_hours': round(avg_tat, 1),
            'min_tat_hours': round(min_tat, 1),
            'max_tat_hours': round(max_tat, 1),
            'by_priority': tat_by_priority_avg
        }
    
    def get_qc_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get quality control statistics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dictionary with QC statistics
        """
        query = self.db.query(QCRecord)
        
        if start_date:
            query = query.filter(QCRecord.performed_at >= start_date)
        if end_date:
            query = query.filter(QCRecord.performed_at <= end_date)
        
        total_qc = query.count()
        
        # Status breakdown
        passed = query.filter(QCRecord.status == QCStatus.PASSED.value).count()
        failed = query.filter(QCRecord.status == QCStatus.FAILED.value).count()
        out_of_range = query.filter(QCRecord.status == QCStatus.OUT_OF_RANGE.value).count()
        pending = query.filter(QCRecord.status == QCStatus.PENDING.value).count()
        
        # Failure rate
        failure_rate = round((failed / total_qc * 100) if total_qc > 0 else 0, 1)
        out_of_range_rate = round((out_of_range / total_qc * 100) if total_qc > 0 else 0, 1)
        
        return {
            'total_qc_tests': total_qc,
            'by_status': {
                'passed': passed,
                'failed': failed,
                'out_of_range': out_of_range,
                'pending': pending
            },
            'failure_rate': failure_rate,
            'out_of_range_rate': out_of_range_rate
        }
    
    def get_critical_results_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get critical results statistics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dictionary with critical results statistics
        """
        query = self.db.query(LabOrder).filter(
            LabOrder.critical_called == True
        )
        
        if start_date:
            query = query.filter(LabOrder.critical_called_at >= start_date)
        if end_date:
            query = query.filter(LabOrder.critical_called_at <= end_date)
        
        total_critical = query.count()
        
        # Get orders with critical flags
        critical_flagged = self.db.query(LabOrder).filter(
            LabOrder.flags_json.isnot(None)
        )
        
        if start_date:
            critical_flagged = critical_flagged.filter(LabOrder.ordered_at >= start_date)
        if end_date:
            critical_flagged = critical_flagged.filter(LabOrder.ordered_at <= end_date)
        
        critical_flagged_count = 0
        for order in critical_flagged:
            if order.flags_json:
                for field, flag_info in order.flags_json.items():
                    if flag_info.get('flag') == 'CRITICAL':
                        critical_flagged_count += 1
                        break
        
        return {
            'critical_results_count': total_critical,
            'critical_flagged_count': critical_flagged_count,
            'communication_documented': total_critical
        }
    
    def get_test_volume_by_category(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get test volume by category/test name.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            limit: Number of top tests to return
            
        Returns:
            List of test volumes
        """
        query = self.db.query(
            LabOrder.test_name,
            func.count(LabOrder.id).label('count')
        )
        
        if start_date:
            query = query.filter(LabOrder.ordered_at >= start_date)
        if end_date:
            query = query.filter(LabOrder.ordered_at <= end_date)
        
        results = query.group_by(LabOrder.test_name).order_by(func.count(LabOrder.id).desc()).limit(limit).all()
        
        return [
            {'test_name': test_name, 'count': count}
            for test_name, count in results
        ]
    
    def get_daily_volume_trend(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily order volume trend.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of daily volumes
        """
        start_date = datetime.now() - timedelta(days=days)
        
        results = self.db.query(
            func.date(LabOrder.ordered_at).label('date'),
            func.count(LabOrder.id).label('count')
        ).filter(
            LabOrder.ordered_at >= start_date
        ).group_by(
            func.date(LabOrder.ordered_at)
        ).order_by(
            func.date(LabOrder.ordered_at)
        ).all()
        
        return [
            {'date': str(result.date), 'count': result.count}
            for result in results
        ]
    
    def get_full_dashboard_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get all analytics data for the dashboard.
        
        Args:
            start_date: Start date for filtering (default: 30 days ago)
            end_date: End date for filtering (default: now)
            
        Returns:
            Complete dashboard data
        """
        # Default to last 30 days
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'order_statistics': self.get_order_statistics(start_date, end_date),
            'sample_statistics': self.get_sample_statistics(start_date, end_date),
            'turnaround_time': self.get_turnaround_time_stats(start_date, end_date),
            'qc_statistics': self.get_qc_statistics(start_date, end_date),
            'critical_results': self.get_critical_results_stats(start_date, end_date),
            'top_tests': self.get_test_volume_by_category(start_date, end_date),
            'daily_trend': self.get_daily_volume_trend(30)
        }


def get_lab_analytics(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get lab analytics data.
    
    Args:
        db: Database session
        start_date: Start date for filtering
        end_date: End date for filtering
        
    Returns:
        Complete analytics data
    """
    service = LabAnalyticsService(db)
    return service.get_full_dashboard_data(start_date, end_date)
