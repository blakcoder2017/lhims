-- Update Stool Routine Examination template with new parameters
-- Parameters: Physical Examination, Colour, Consistency, Mucus, Blood, MICROSCOPY section
-- Pus Cells, Ova, Cyst, Yeast Cells, Red Blood Cells, Larvae, Bacteria, Fat droplets, Epithelial Cells
-- All fields are text type (accept both numbers and text)

DO $$
DECLARE
    stool_template_id UUID;
    version_id UUID;
    new_version_num INTEGER;
BEGIN
    -- Get the Stool Routine Examination template ID (using the actual name in DB)
    SELECT id INTO stool_template_id 
    FROM lab_templates 
    WHERE name = 'Lab Test - STOOL_RE' AND is_deleted = false
    LIMIT 1;
    
    IF stool_template_id IS NOT NULL THEN
        RAISE NOTICE 'Found Stool R/E template with ID: %', stool_template_id;
        
        -- Get current version number
        SELECT COALESCE(current_version, 0) + 1 INTO new_version_num 
        FROM lab_templates WHERE id = stool_template_id;
        
        -- Update the template version number
        UPDATE lab_templates 
        SET current_version = new_version_num, updated_at = NOW() 
        WHERE id = stool_template_id;
        
        RAISE NOTICE 'Updated template version to: %', new_version_num;
        
        -- Get existing version ID to update
        SELECT id INTO version_id 
        FROM lab_template_versions 
        WHERE template_id = stool_template_id AND status = 'PUBLISHED'
        ORDER BY version DESC
        LIMIT 1;
        
        IF version_id IS NOT NULL THEN
            -- Update the schema_json with new fields (all text type)
            UPDATE lab_template_versions
            SET schema_json = '{
                "meta": {
                    "name": "Stool R/E",
                    "discipline": "PARASITOLOGY",
                    "version": 5,
                    "description": "Stool Routine Examination - Parasitology",
                    "specimen_type": "Stool"
                },
                "layout": {
                    "sections": [
                        {
                            "id": "sec_physical",
                            "title": "Physical Examination",
                            "rows": [
                                {
                                    "columns": [
                                        {"width": 6, "items": ["colour"]},
                                        {"width": 6, "items": ["consistency"]}
                                    ]
                                },
                                {
                                    "columns": [
                                        {"width": 6, "items": ["mucus"]},
                                        {"width": 6, "items": ["blood"]}
                                    ]
                                }
                            ]
                        },
                        {
                            "id": "sec_microscopy",
                            "title": "MICROSCOPY",
                            "rows": [
                                {
                                    "columns": [
                                        {"width": 6, "items": ["pus_cells"]},
                                        {"width": 6, "items": ["red_blood_cells"]}
                                    ]
                                },
                                {
                                    "columns": [
                                        {"width": 6, "items": ["ova"]},
                                        {"width": 6, "items": ["cyst"]}
                                    ]
                                },
                                {
                                    "columns": [
                                        {"width": 6, "items": ["yeast_cells"]},
                                        {"width": 6, "items": ["larvae"]}
                                    ]
                                },
                                {
                                    "columns": [
                                        {"width": 6, "items": ["bacteria"]},
                                        {"width": 6, "items": ["fat_droplets"]}
                                    ]
                                },
                                {
                                    "columns": [
                                        {"width": 12, "items": ["epithelial_cells"]}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "fields": {
                    "colour": {
                        "type": "text",
                        "code": "colour",
                        "label": "Colour"
                    },
                    "consistency": {
                        "type": "text",
                        "code": "consistency",
                        "label": "Consistency"
                    },
                    "mucus": {
                        "type": "text",
                        "code": "mucus",
                        "label": "Mucus"
                    },
                    "blood": {
                        "type": "text",
                        "code": "blood",
                        "label": "Blood"
                    },
                    "pus_cells": {
                        "type": "text",
                        "code": "pus_cells",
                        "label": "Pus Cells"
                    },
                    "red_blood_cells": {
                        "type": "text",
                        "code": "red_blood_cells",
                        "label": "Red Blood Cells"
                    },
                    "ova": {
                        "type": "text",
                        "code": "ova",
                        "label": "Ova"
                    },
                    "cyst": {
                        "type": "text",
                        "code": "cyst",
                        "label": "Cyst"
                    },
                    "yeast_cells": {
                        "type": "text",
                        "code": "yeast_cells",
                        "label": "Yeast Cells"
                    },
                    "larvae": {
                        "type": "text",
                        "code": "larvae",
                        "label": "Larvae"
                    },
                    "bacteria": {
                        "type": "text",
                        "code": "bacteria",
                        "label": "Bacteria"
                    },
                    "fat_droplets": {
                        "type": "text",
                        "code": "fat_droplets",
                        "label": "Fat droplets"
                    },
                    "epithelial_cells": {
                        "type": "text",
                        "code": "epithelial_cells",
                        "label": "Epithelial Cells"
                    }
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            }'::jsonb,
            change_note = 'Updated Stool R/E template - all fields changed to text type'
            WHERE id = version_id;
            
            RAISE NOTICE 'Updated template schema for version: %', version_id;
        ELSE
            RAISE NOTICE 'No published version found for Stool R/E template';
        END IF;
    ELSE
        RAISE NOTICE 'Stool R/E template not found';
    END IF;
END $$;

-- Verify the changes
SELECT 
    lt.name as template_name,
    lt.discipline,
    lt.current_version as version,
    ltv.status
FROM lab_templates lt
JOIN lab_template_versions ltv ON lt.id = ltv.template_id
WHERE lt.name = 'Lab Test - STOOL_RE' AND lt.is_deleted = false
ORDER BY ltv.version DESC
LIMIT 5;

-- Show all fields in the updated template
SELECT 
    jsonb_object_keys(ltv.schema_json->'fields') as field_code
FROM lab_template_versions ltv
JOIN lab_templates lt ON lt.id = ltv.template_id
WHERE lt.name = 'Lab Test - STOOL_RE' AND lt.is_deleted = false
AND ltv.status = 'PUBLISHED'
ORDER BY field_code;
