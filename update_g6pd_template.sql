-- Update G6PD Screening template from dropdown to text field
-- This script updates the existing G6PD template in the database

-- 1. Update the schema_json in lab_template_versions for G6PD template
-- First, find the G6PD template ID
DO $$
DECLARE
    g6pd_template_id UUID;
    version_id UUID;
BEGIN
    -- Get the G6PD template ID
    SELECT id INTO g6pd_template_id 
    FROM lab_templates 
    WHERE name = 'G6PD' AND is_deleted = false
    LIMIT 1;
    
    IF g6pd_template_id IS NOT NULL THEN
        RAISE NOTICE 'Found G6PD template with ID: %', g6pd_template_id;
        
        -- Update all published versions of the template
        FOR version_id IN 
            SELECT id FROM lab_template_versions 
            WHERE template_id = g6pd_template_id AND status = 'PUBLISHED'
        LOOP
            -- Update the schema_json to change g6pd_result from choice to text
            UPDATE lab_template_versions
            SET schema_json = 
                jsonb_set(
                    jsonb_set(
                        schema_json::jsonb - 'g6pd_result',
                        '{g6pd_result}',
                        '{"label": "G6PD Status", "type": "text"}'::jsonb
                    ),
                    '{g6pd_result}',
                    '{"label": "G6PD Status", "type": "text"}'::jsonb
                )
            WHERE id = version_id;
            
            RAISE NOTICE 'Updated template version: %', version_id;
        END LOOP;
        
        -- Also update draft versions
        FOR version_id IN 
            SELECT id FROM lab_template_versions 
            WHERE template_id = g6pd_template_id AND status = 'DRAFT'
        LOOP
            UPDATE lab_template_versions
            SET schema_json = 
                jsonb_set(
                    jsonb_set(
                        schema_json::jsonb - 'g6pd_result',
                        '{g6pd_result}',
                        '{"label": "G6PD Status", "type": "text"}'::jsonb
                    ),
                    '{g6pd_result}',
                    '{"label": "G6PD Status", "type": "text"}'::jsonb
                )
            WHERE id = version_id;
            
            RAISE NOTICE 'Updated draft version: %', version_id;
        END LOOP;
    ELSE
        RAISE NOTICE 'G6PD template not found';
    END IF;
END $$;

-- 2. Update the reference range for g6pd_result to "-"
UPDATE lab_reference_ranges
SET text_range = '-'
WHERE field_code = 'g6pd_result';

-- Verify the changes
SELECT 
    lt.name as template_name,
    ltv.version,
    ltv.status,
    ltv.schema_json->'g6pd_result' as g6pd_field_config
FROM lab_templates lt
JOIN lab_template_versions ltv ON lt.id = ltv.template_id
WHERE lt.name = 'G6PD' AND lt.is_deleted = false;

SELECT field_code, text_range FROM lab_reference_ranges WHERE field_code = 'g6pd_result';
