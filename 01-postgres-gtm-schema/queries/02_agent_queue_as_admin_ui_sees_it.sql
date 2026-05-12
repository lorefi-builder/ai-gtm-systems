-- What the /gtm-admin/queue UI from folder 03 renders.
-- Two sections: email_ops queue and content_ops queue.

select agent_name,
       output_type,
       target_ref,
       status,
       created_at,
       payload -> 'variant_name' as proposed_variant,
       payload -> 'subject'      as proposed_subject,
       payload -> 'rationale'    as rationale
from gtm.agent_outputs
where status = 'pending_review'
order by agent_name, created_at desc;
