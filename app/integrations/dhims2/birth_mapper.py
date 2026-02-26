"""
DHIMS2 Birth Data Mapper

Maps LHIMS birth records to DHIMS2 format for reporting.
This is used for Ghana Health Service monthly reporting requirements.

Reference: DHIMS2 Maternal and Neonatal Health Indicators
"""

from typing import Dict, Any, Optional
from datetime import date
from app.models.birth_models import BirthRecord
from app.models.baby_discharge_models import BabyDischarge


class BirthRecordMapper:
    """Maps birth records to DHIMS2 data format."""
    
    # DHIMS2 Data Element UIDs (These would be configured in DHIMS2 settings)
    # Placeholder UIDs - would be replaced with actual DHIMS2 UIDs
    DHIMS2_UIDS = {
        # Delivery outcomes
        "live_births": ".LiveBirths",
        "stillbirths": "Stillbirths",
        "early_neonatal_deaths": "EarlyNeonatalDeaths",
        
        # Delivery types
        "normal_delivery": "NormalDelivery",
        "vacuum_delivery": "VacuumDelivery",
        "caesarean_section": "CaesareanSection",
        
        # Birth weight
        "low_birth_weight": "LowBirthWeight",
        "very_low_birth_weight": "VeryLowBirthWeight",
        "normal_birth_weight": "NormalBirthWeight",
        
        # Place of delivery
        "facility_delivery": "FacilityDelivery",
        "community_delivery": "CommunityDelivery",
        
        # Birth attendant
        "births_by_doctor": "BirthsByDoctor",
        "births_by_midwife": "BirthsByMidwife",
        "births_by_nurse": "BirthsByNurse",
        
        # Complications
        "maternal_complications": "MaternalComplications",
        "neonatal_complications": "NeonatalComplications",
        
        # Interventions
        "blood_transfusion": "BloodTransfusion",
        "manual_removal_placenta": "ManualRemovalPlacenta",
        
        # Immunisations
        "bcg_given": "BCGGiven",
        "vitamin_k_given": "VitaminKGiven",
        "polio_given": "PolioGiven",
        
        # Newborn care
        "skin_to_skin": "SkinToSkin",
        "early_breastfeeding": "EarlyBreastfeeding",
        
        # Gestational age
        "preterm_births": "PretermBirths",
        "term_births": "TermBirths",
        
        # Special categories
        "teenage_delivery": "TeenageDelivery",
        "multiple_births": "MultipleBirths",
        "male_babies": "MaleBabies",
        "female_babies": "FemaleBabies",
        
        # PNC
        "pnc_visit_48hrs": "PNC48hrs",
        "pnc_visit_6days": "PNC6days",
        "pnc_visit_6weeks": "PNC6weeks",
    }
    
    @staticmethod
    def map_birth_record_to_dhims2(
        birth_record: BirthRecord,
        baby_discharge: Optional[BabyDischarge] = None
    ) -> Dict[str, Any]:
        """
        Convert a birth record to DHIMS2 format.
        
        Args:
            birth_record: The birth record to map
            baby_discharge: Optional baby discharge summary
            
        Returns:
            Dictionary with DHIMS2-formatted data
        """
        data = {
            # Organisation unit would be set from facility
            "org_unit": birth_record.facility_name or "Unknown",
            
            # Period (YYYYMM format)
            "period": birth_record.birth_date.strftime("%Y%m") if birth_record.birth_date else "",
            
            # Data elements
            "data_values": []
        }
        
        # Map delivery outcome
        if birth_record.birth_outcome:
            if birth_record.birth_outcome.lower() == "live":
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["live_births"],
                    "value": 1
                })
            elif birth_record.birth_outcome.lower() == "stillbirth":
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["stillbirths"],
                    "value": 1
                })
        
        # Map delivery type
        if birth_record.delivery_type:
            delivery_type = birth_record.delivery_type.lower()
            if delivery_type == "vaginal" or delivery_type == "normal":
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["normal_delivery"],
                    "value": 1
                })
            elif delivery_type == "vacuum":
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["vacuum_delivery"],
                    "value": 1
                })
            elif delivery_type == "caesarean":
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["caesarean_section"],
                    "value": 1
                })
        
        # Map birth weight
        if birth_record.weight_kg:
            weight = float(birth_record.weight_kg)
            if weight < 1.5:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["very_low_birth_weight"],
                    "value": 1
                })
            elif weight < 2.5:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["low_birth_weight"],
                    "value": 1
                })
            else:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["normal_birth_weight"],
                    "value": 1
                })
        
        # Map place of delivery
        if birth_record.place_of_delivery:
            place = birth_record.place_of_delivery.lower()
            if "facility" in place or "hospital" in place or "health" in place:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["facility_delivery"],
                    "value": 1
                })
            else:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["community_delivery"],
                    "value": 1
                })
        else:
            # Default to facility
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["facility_delivery"],
                "value": 1
            })
        
        # Map birth attendant
        if birth_record.attendant_category:
            att = birth_record.attendant_category.lower()
            if "doctor" in att:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["births_by_doctor"],
                    "value": 1
                })
            elif "midwife" in att:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["births_by_midwife"],
                    "value": 1
                })
            elif "nurse" in att:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["births_by_nurse"],
                    "value": 1
                })
        
        # Map blood transfusion
        if birth_record.blood_transfusion:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["blood_transfusion"],
                "value": 1 if birth_record.blood_transfusion else 0
            })
        
        # Map manual removal of placenta
        if birth_record.manual_removal_placenta is not None:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["manual_removal_placenta"],
                "value": 1 if birth_record.manual_removal_placenta else 0
            })
        
        # Map immunisations (from baby discharge if available, else from birth record)
        if baby_discharge:
            if baby_discharge.bcg_date:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["bcg_given"],
                    "value": 1
                })
            if baby_discharge.vitamin_k_date:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["vitamin_k_given"],
                    "value": 1
                })
            if baby_discharge.oral_polio_date:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["polio_given"],
                    "value": 1
                })
        else:
            # Fall back to birth record fields
            if birth_record.bcg_vaccine:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["bcg_given"],
                    "value": 1
                })
            if birth_record.vitamin_k_administered:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["vitamin_k_given"],
                    "value": 1
                })
            if birth_record.polio_vaccine:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["polio_given"],
                    "value": 1
                })
        
        # Map skin-to-skin
        if birth_record.skin_to_skin:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["skin_to_skin"],
                "value": 1
            })
        
        # Map early breastfeeding
        if birth_record.breastfeeding_initiated_1hr or birth_record.breastfeeding_30min:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["early_breastfeeding"],
                "value": 1
            })
        
        # Map gestational age
        if birth_record.gestational_age_weeks:
            if birth_record.gestational_age_weeks < 37:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["preterm_births"],
                    "value": 1
                })
            elif birth_record.gestational_age_weeks >= 37:
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["term_births"],
                    "value": 1
                })
        
        # Map child sex
        if birth_record.gender:
            gender = birth_record.gender.lower()
            if gender == "male" or gender == "m":
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["male_babies"],
                    "value": 1
                })
            elif gender == "female" or gender == "f":
                data["data_values"].append({
                    "data_element": BirthRecordMapper.DHIMS2_UIDS["female_babies"],
                    "value": 1
                })
        
        # Map PNC visits
        if birth_record.pnc1_date:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["pnc_visit_48hrs"],
                "value": 1
            })
        if birth_record.pnc2_date:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["pnc_visit_6days"],
                "value": 1
            })
        if birth_record.pnc3_date:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["pnc_visit_6weeks"],
                "value": 1
            })
        
        # Map complications (labour/delivery)
        if birth_record.labour_delivery_complications:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["maternal_complications"],
                "value": 1
            })
        
        # Map neonatal complications
        if birth_record.baby_complications:
            data["data_values"].append({
                "data_element": BirthRecordMapper.DHIMS2_UIDS["neonatal_complications"],
                "value": 1
            })
        
        return data
    
    @staticmethod
    def get_maternal_health_summary(birth_records: list) -> Dict[str, Any]:
        """
        Generate maternal health summary statistics from birth records.
        
        Args:
            birth_records: List of birth records for a period
            
        Returns:
            Dictionary with summary statistics including calculated rates
        """
        from datetime import date
        
        today = date.today()
        
        summary = {
            "total_deliveries": len(birth_records),
            "live_births": 0,
            "stillbirths": 0,
            "normal_delivery": 0,
            "vacuum_delivery": 0,
            "caesarean_section": 0,
            "low_birth_weight": 0,
            "very_low_birth_weight": 0,
            "blood_transfusion": 0,
            "manual_removal_placenta": 0,
            "bcg_given": 0,
            "vitamin_k_given": 0,
            "pnc_48hrs": 0,
            "pnc_6days": 0,
            "pnc_6weeks": 0,
            # New fields
            "facility_delivery": 0,
            "community_delivery": 0,
            "births_by_doctor": 0,
            "births_by_midwife": 0,
            "births_by_nurse": 0,
            "skin_to_skin": 0,
            "early_breastfeeding": 0,
            "preterm_births": 0,
            "term_births": 0,
            "teenage_delivery": 0,
            "multiple_births": 0,
            "male_babies": 0,
            "female_babies": 0,
        }
        
        for record in birth_records:
            # Count outcomes
            if record.birth_outcome:
                if record.birth_outcome.lower() == "live":
                    summary["live_births"] += 1
                elif record.birth_outcome.lower() == "stillbirth":
                    summary["stillbirths"] += 1
            
            # Count delivery types
            if record.delivery_type:
                dt = record.delivery_type.lower()
                if dt in ["vaginal", "normal"]:
                    summary["normal_delivery"] += 1
                elif dt == "vacuum":
                    summary["vacuum_delivery"] += 1
                elif dt == "caesarean":
                    summary["caesarean_section"] += 1
            
            # Count birth weight
            if record.weight_kg:
                weight = float(record.weight_kg)
                if weight < 1.5:
                    summary["very_low_birth_weight"] += 1
                    summary["low_birth_weight"] += 1
                elif weight < 2.5:
                    summary["low_birth_weight"] += 1
            
            # Count blood transfusion
            if record.blood_transfusion:
                summary["blood_transfusion"] += 1
            
            # Count manual removal
            if record.manual_removal_placenta:
                summary["manual_removal_placenta"] += 1
            
            # Count immunisations
            if record.bcg_vaccine:
                summary["bcg_given"] += 1
            if record.vitamin_k_administered:
                summary["vitamin_k_given"] += 1
            
            # Count PNC visits
            if record.pnc1_date:
                summary["pnc_48hrs"] += 1
            if record.pnc2_date:
                summary["pnc_6days"] += 1
            if record.pnc3_date:
                summary["pnc_6weeks"] += 1
            
            # Count place of delivery
            if record.place_of_delivery:
                place = record.place_of_delivery.lower()
                if "facility" in place or "hospital" in place or "health" in place:
                    summary["facility_delivery"] += 1
                else:
                    summary["community_delivery"] += 1
            else:
                summary["facility_delivery"] += 1
            
            # Count birth attendant
            if record.attendant_category:
                att = record.attendant_category.lower()
                if "doctor" in att:
                    summary["births_by_doctor"] += 1
                elif "midwife" in att:
                    summary["births_by_midwife"] += 1
                elif "nurse" in att:
                    summary["births_by_nurse"] += 1
            
            # Count skin-to-skin
            if record.skin_to_skin:
                summary["skin_to_skin"] += 1
            
            # Count early breastfeeding
            if record.breastfeeding_initiated_1hr or record.breastfeeding_30min:
                summary["early_breastfeeding"] += 1
            
            # Count gestational age
            if record.gestational_age_weeks:
                if record.gestational_age_weeks < 37:
                    summary["preterm_births"] += 1
                elif record.gestational_age_weeks >= 37:
                    summary["term_births"] += 1
            
            # Count multiple births
            if record.number_of_babies and record.number_of_babies > 1:
                summary["multiple_births"] += 1
            
            # Count child sex (male/female)
            if record.gender:
                gender = record.gender.lower()
                if gender == "male" or gender == "m":
                    summary["male_babies"] += 1
                elif gender == "female" or gender == "f":
                    summary["female_babies"] += 1
            
            # Count teenage delivery (mother under 18)
            if record.mother and record.mother.date_of_birth:
                mother_age = (today - record.mother.date_of_birth).days // 365
                if mother_age < 18:
                    summary["teenage_delivery"] += 1
        
        # Calculate rates
        live_births = max(summary["live_births"], 1)
        total_deliveries = max(summary["total_deliveries"], 1)
        
        summary["institutional_delivery_rate"] = round((summary["facility_delivery"] / total_deliveries) * 100, 1)
        summary["low_birth_weight_rate"] = round((summary["low_birth_weight"] / live_births) * 100, 1)
        summary["pnc_coverage_rate"] = round((summary["pnc_48hrs"] / live_births) * 100, 1)
        skilled_attendants = summary["births_by_doctor"] + summary["births_by_midwife"] + summary["births_by_nurse"]
        summary["skilled_birth_attendant_rate"] = round((skilled_attendants / total_deliveries) * 100, 1)
        
        return summary
