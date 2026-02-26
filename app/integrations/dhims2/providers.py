"""
Data Extraction Providers for DHIMS2

Provides data from LHIMS system for submission to DHIMS2.
The ReportingDataProvider interface allows swappable implementations.
"""
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ReportingDataProvider(ABC):
    """
    Abstract base class for data providers.
    
    Implement this interface to provide data for DHIMS2 submissions.
    """
    
    source_table: str = "unknown"
    
    @abstractmethod
    def get_values(
        self,
        org_unit_uid: str,
        period: str,
        report_type: str
    ) -> Dict[str, Any]:
        """
        Get metric values for the given org unit, period, and report type.
        
        Args:
            org_unit_uid: DHIS2 org unit UID
            period: Period string (e.g., "2026-01")
            report_type: Report type identifier
            
        Returns:
            Dictionary mapping internal_metric_key -> value
        """
        pass


class AggregatedIndicatorsProvider(ReportingDataProvider):
    """
    Provider that aggregates data from existing LHIMS tables.
    
    Computes totals from:
    - OPD visits
    - IPD admissions
    - Lab tests
    - etc.
    """
    
    source_table = "aggregated_indicators"
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_values(
        self,
        org_unit_uid: str,
        period: str,
        report_type: str
    ) -> Dict[str, Any]:
        """
        Get aggregated indicator values.
        
        Args:
            org_unit_uid: DHIS2 org unit UID (for filtering)
            period: Period string (YYYY-MM)
            report_type: Type of report (e.g., "monthly_service", "quarterly_anc")
            
        Returns:
            Dictionary of metric key -> value
        """
        # Parse period
        try:
            year, month = map(int, period.split("-"))
            period_start = datetime(year, month, 1)
            # End of month
            if month == 12:
                period_end = datetime(year + 1, 1, 1)
            else:
                period_end = datetime(year, month + 1, 1)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid period format: {period}, using current date")
            period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
            period_end = datetime.utcnow()
        
        values: Dict[str, Any] = {}
        
        # Map report type to queries
        if report_type == "monthly_service":
            values = self._get_monthly_service(period_start, period_end)
        elif report_type == "monthly_anc":
            values = self._get_anc_indicators(period_start, period_end)
        elif report_type == "monthly_delivery":
            values = self._get_delivery_indicators(period_start, period_end)
        elif report_type == "monthly_ipd":
            values = self._get_ipd_indicators(period_start, period_end)
        else:
            logger.warning(f"Unknown report type: {report_type}")
        
        return values
    
    def _get_monthly_service(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Get monthly service statistics."""
        from app.models.opd_models import OPDVisit
        from app.models.encounter_models import Encounter
        
        values: Dict[str, Any] = {}
        
        # Total OPD visits
        opd_query = self.db.query(OPDVisit).filter(
            OPDVisit.created_at >= period_start,
            OPDVisit.created_at < period_end
        )
        opd_total = opd_query.count()
        values["OPD_TOTAL"] = opd_total
        
        # OPD by gender (if gender info available)
        opd_male = opd_query.join(Encounter).filter(
            Encounter.patient_id.in_(
                self.db.query(Encounter.patient_id).filter(
                    Encounter.gender == "male"
                ).distinct()
            )
        ).count() if hasattr(Encounter, 'gender') else 0
        values["OPD_MALE"] = opd_male
        values["OPD_FEMALE"] = opd_total - opd_male
        
        # New cases vs revisits (if visit_type available)
        new_cases = opd_query.filter(
            OPDVisit.visit_type == "new"
        ).count() if hasattr(OPDVisit, 'visit_type') else opd_total
        values["OPD_NEW"] = new_cases
        values["OPD_REVISIT"] = opd_total - new_cases
        
        return values
    
    def _get_anc_indicators(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Get ANC (Antenatal Care) indicators."""
        from app.models.antenatal_models import AntenatalVisit
        
        values: Dict[str, Any] = {}
        
        anc_visits = self.db.query(AntenatalVisit).filter(
            AntenatalVisit.visit_date >= period_start,
            AntenatalVisit.visit_date < period_end
        )
        
        # Total ANC visits
        values["ANC_TOTAL"] = anc_visits.count()
        
        # ANC1 (first visits)
        anc1 = anc_visits.filter(AntenatalVisit.visit_number == 1).count()
        values["ANC1"] = anc1
        
        # ANC4 (fourth visits)
        anc4 = anc_visits.filter(AntenatalVisit.visit_number == 4).count()
        values["ANC4"] = anc4
        
        # ANC coverage (if population data available, would need facility catchment)
        # For now, just return counts
        
        return values
    
    def _get_delivery_indicators(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Get delivery statistics."""
        from app.models.birth_models import BirthRecord
        
        values: Dict[str, Any] = {}
        
        births = self.db.query(BirthRecord).filter(
            BirthRecord.delivery_date >= period_start,
            BirthRecord.delivery_date < period_end
        )
        
        values["DELIVERY_TOTAL"] = births.count()
        
        # Delivery types
        normal_delivery = births.filter(
            BirthRecord.delivery_type == "normal"
        ).count()
        values["DELIVERY_NORMAL"] = normal_delivery
        
        cesarean = births.filter(
            BirthRecord.delivery_type == "cesarean"
        ).count()
        values["DELIVERY_CESAREAN"] = cesarean
        
        # Live births vs stillbirths
        live_births = births.filter(
            BirthRecord.birth_outcome == "live_birth"
        ).count()
        values["LIVE_BIRTH"] = live_births
        
        stillbirths = births.filter(
            BirthRecord.birth_outcome == "still_birth"
        ).count()
        values["STILL_BIRTH"] = stillbirths
        
        return values
    
    def _get_ipd_indicators(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Get IPD (Inpatient) indicators."""
        from app.models.ipd_models import Admission
        
        values: Dict[str, Any] = {}
        
        admissions = self.db.query(Admission).filter(
            Admission.admission_date >= period_start,
            Admission.admission_date < period_end
        )
        
        values["IPD_ADMISSIONS"] = admissions.count()
        
        # Discharges
        discharges = admissions.filter(
            Admission.status == "discharged"
        ).count()
        values["IPD_DISCHARGES"] = discharges
        
        # Deaths
        deaths = admissions.filter(
            Admission.discharge_status == "death"
        ).count()
        values["IPD_DEATHS"] = deaths
        
        # Transfers
        transfers = admissions.filter(
            Admission.discharge_status == "referral"
        ).count()
        values["IPD_TRANSFERS"] = transfers
        
        # Average length of stay (if we have discharge dates)
        # This is a simplified calculation
        
        return values


class DiseaseReportingProvider(ReportingDataProvider):
    """
    Provider for disease/condition reporting.
    
    Aggregates disease cases for DHIMS2 disease surveillance reports.
    """
    
    source_table = "diseases"
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_values(
        self,
        org_unit_uid: str,
        period: str,
        report_type: str
    ) -> Dict[str, Any]:
        """Get disease case counts."""
        from app.models.disease_models import EncounterDisease
        from app.models.encounter_models import Encounter
        
        values: Dict[str, Any] = {}
        
        # Parse period
        try:
            year, month = map(int, period.split("-"))
            period_start = datetime(year, month, 1)
            if month == 12:
                period_end = datetime(year + 1, 1, 1)
            else:
                period_end = datetime(year, month + 1, 1)
        except (ValueError, AttributeError):
            period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
            period_end = datetime.utcnow()
        
        # Get diseases with case counts
        disease_counts = self.db.query(
            EncounterDisease.disease_id,
            EncounterDisease.disease_name,
        ).join(
            Encounter, Encounter.id == EncounterDisease.encounter_id
        ).filter(
            Encounter.created_at >= period_start,
            Encounter.created_at < period_end
        ).all()
        
        # Aggregate by disease
        for disease_id, disease_name in disease_counts:
            key = f" disease_{disease_id}"
            values[key] = values.get(key, 0) + 1
        
        return values


# Registry of available providers
PROVIDER_REGISTRY: Dict[str, type] = {
    "aggregated_indicators": AggregatedIndicatorsProvider,
    "disease_reporting": DiseaseReportingProvider,
}


def get_provider(provider_name: str, db: Session) -> ReportingDataProvider:
    """
    Get a data provider by name.
    
    Args:
        provider_name: Name of the provider
        db: Database session
        
    Returns:
        Provider instance
        
    Raises:
        ValueError: If provider not found
    """
    provider_class = PROVIDER_REGISTRY.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    return provider_class(db)
