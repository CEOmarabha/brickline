-- Measured revenue tracking. Every value is typed in by the user; nothing is estimated.
--
-- Leads: lead_status.job_value_usd is the CURRENT job value of a Won lead (cleared when the lead leaves Won);
-- lead_event.job_value_usd is the value at the time of that event, so history keeps it.
-- Prospects (the founder's own sales pipeline): monthly_value_usd and fee_model are the deal terms of a Pilot or
-- Paying prospect, current on prospect_status and as-of-the-event on prospect_event.
--
-- Additive only. The column constraints sit inside ADD COLUMN IF NOT EXISTS, so re-running is harmless.

alter table lead_status
  add column if not exists job_value_usd numeric(12,2)
    constraint lead_status_job_value_nonneg check (job_value_usd is null or job_value_usd >= 0);

alter table lead_event
  add column if not exists job_value_usd numeric(12,2)
    constraint lead_event_job_value_nonneg check (job_value_usd is null or job_value_usd >= 0);

alter table prospect_status
  add column if not exists monthly_value_usd numeric(12,2)
    constraint prospect_status_monthly_value_nonneg check (monthly_value_usd is null or monthly_value_usd >= 0);

alter table prospect_status
  add column if not exists fee_model text not null default ''
    constraint prospect_status_fee_model_known
      check (fee_model in ('', 'subscription', 'per_lead', 'per_won_job', 'flat_pilot'));

alter table prospect_event
  add column if not exists monthly_value_usd numeric(12,2)
    constraint prospect_event_monthly_value_nonneg check (monthly_value_usd is null or monthly_value_usd >= 0);

alter table prospect_event
  add column if not exists fee_model text not null default ''
    constraint prospect_event_fee_model_known
      check (fee_model in ('', 'subscription', 'per_lead', 'per_won_job', 'flat_pilot'));
