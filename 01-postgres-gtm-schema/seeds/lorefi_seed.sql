-- lorefi_seed.sql
--
-- Fictional seed data for Lorefi, a cross-media narrative-discovery platform
-- for B2B media teams. Three products (Discover, Studio, Insights), priced
-- per seat, self-serve trial + sales-assisted enterprise motion.
--
-- Contents:
--   * 30 leads spread across funnel states
--   * ~125 activities (the funnel trigger does most of the funnel_state work)
--   * 3 experiments / 6 variants / 21 exposures
--   * 15 agent_outputs covering pending_review, approved, rejected, shipped
--
-- Re-runnable: TRUNCATEs everything (CASCADE) before reseeding. Run against
-- a database where the 001..005 migrations have already been applied.

BEGIN;

TRUNCATE
  gtm.agent_output_audit,
  gtm.agent_outputs,
  gtm.experiment_exposures,
  gtm.experiment_variants,
  gtm.experiments,
  gtm.activities,
  gtm.leads
RESTART IDENTITY CASCADE;

-- ---------------------------------------------------------------------------
-- Leads (30)
-- funnel_state is mostly left at the default 'anonymous' — the trigger in 005
-- advances it as activities are inserted below. The three 'known' leads have
-- no funnel-advancing activities, so we set the state explicitly.
-- ---------------------------------------------------------------------------

INSERT INTO gtm.leads
  (email, company, product_interest, source, source_campaign, owner_email, funnel_state, created_at) VALUES
  ('alex.rosen@verge.media',            'Verge Media',           'discover', 'organic_search',    'seo:cross-media-search',    'morgan@lorefi.com', 'anonymous', '2026-01-04 09:12'),
  ('priya.menon@atlaspublicradio.org',  'Atlas Public Radio',    'studio',   'content_marketing', 'guide:editorial-ops',       'morgan@lorefi.com', 'anonymous', '2026-01-06 14:42'),
  ('toni.alvarez@northshorepress.com',  'Northshore Press',      'insights', 'webinar',           'wbnr:measure-pickup',       'jules@lorefi.com',  'anonymous', '2026-01-07 10:01'),
  ('mira.chen@latticenewsroom.com',     'Lattice Newsroom',      'bundle',   'partner_referral',  'partner:onestream',         'priya@lorefi.com',  'anonymous', '2026-01-08 11:30'),
  ('diego.park@foliostudios.tv',        'Folio Studios',         'studio',   'conference',        'conf:newsrewired-2026',     'sam@lorefi.com',    'anonymous', '2026-01-09 09:30'),
  ('sasha.vance@riverlightmedia.com',   'Riverlight Media',      'discover', 'paid_search',       'gads:demo-now',             'jules@lorefi.com',  'anonymous', '2026-01-10 11:00'),
  ('yusuf.patel@northwindbureau.com',   'Northwind Bureau',      'insights', 'content_marketing', 'guide:audience-discovery',  'morgan@lorefi.com', 'anonymous', '2026-01-11 12:00'),
  ('hana.iverson@cresthilldaily.com',   'Cresthill Daily',       'discover', 'outbound',          'ob:strategic-accounts',     'priya@lorefi.com',  'anonymous', '2026-01-11 09:00'),
  ('mateo.ruiz@baysidebroadcasting.com','Bayside Broadcasting',  'studio',   'webinar',           'wbnr:editorial-velocity',   'sam@lorefi.com',    'anonymous', '2026-01-12 12:00'),
  ('kira.nakamura@ironpine.tv',         'Ironpine Network',      'bundle',   'newsletter',        'nl:cross-channel-january',  'morgan@lorefi.com', 'known',     '2026-01-17 09:00'),
  ('olu.adeyemi@mapleandstone.media',   'Maple & Stone Media',   'insights', 'partner_referral',  'partner:newscan',           'jules@lorefi.com',  'anonymous', '2026-01-19 08:45'),
  ('beatriz.costa@highlineaudio.fm',    'Highline Audio',        'studio',   'podcast_ad',        'pod:newsroom-craft',        'priya@lorefi.com',  'anonymous', '2026-01-20 10:00'),
  ('henry.lin@quadrantpress.com',       'Quadrant Press',        'discover', 'organic_search',    'seo:newsroom-tools',        'sam@lorefi.com',    'anonymous', '2026-01-21 09:00'),
  ('sienna.brooks@beaconhillmedia.com', 'Beacon Hill Media',     'insights', 'conference',        'conf:onlinemediaforum',     'morgan@lorefi.com', 'anonymous', '2026-01-23 13:00'),
  ('rafael.ortega@tideline.studio',     'Tideline Studios',      'bundle',   'social_organic',    'linkedin:org',              'jules@lorefi.com',  'known',     '2026-01-24 11:00'),
  ('aoife.sullivan@frontlinenewsroom.com','Frontline Newsroom',  'discover', 'content_marketing', 'post:measurement-failure',  'priya@lorefi.com',  'anonymous', '2026-01-25 10:00'),
  ('eli.glass@northstarpub.com',        'Northstar Publishing',  'studio',   'outbound',          'ob:enterprise-q1',          'sam@lorefi.com',    'anonymous', '2026-01-25 15:00'),
  ('quincy.watanabe@vellummedia.com',   'Vellum Media Group',    'bundle',   'paid_search',       'gads:lorefi-discover',      'morgan@lorefi.com', 'anonymous', '2026-01-27 10:05'),
  ('noor.hassan@halftide.audio',        'Halftide Audio',        'insights', 'podcast_ad',        'pod:long-arc',              'jules@lorefi.com',  'anonymous', '2026-01-28 16:00'),
  ('lior.cohen@longbridgepress.com',    'Long Bridge Press',     'discover', 'newsletter',        'nl:cross-channel-january',  'priya@lorefi.com',  'anonymous', '2026-01-29 14:00'),
  ('reggie.ford@loomstatemedia.com',    'Loomstate Media',       'studio',   'webinar',           'wbnr:measure-pickup',       'sam@lorefi.com',    'anonymous', '2026-01-30 16:00'),
  ('marta.klein@southforkdaily.com',    'Southfork Daily',       'discover', 'organic_search',    'seo:editorial-analytics',   'morgan@lorefi.com', 'anonymous', '2026-01-31 17:00'),
  ('ines.aguilar@cypressquarterly.com', 'Cypress Quarterly',     'insights', 'content_marketing', 'guide:editorial-ops',       'jules@lorefi.com',  'anonymous', '2026-02-01 13:00'),
  ('theo.whitman@glasshouse.studio',    'Glasshouse Studio',     'studio',   'partner_referral',  'partner:onestream',         'priya@lorefi.com',  'anonymous', '2026-02-02 16:00'),
  ('vivian.park@anchorbaynews.com',     'Anchor Bay News',       'bundle',   'conference',        'conf:newsrewired-2026',     'sam@lorefi.com',    'anonymous', '2026-02-03 14:22'),
  ('sami.okafor@riverbendreports.com',  'Riverbend Reports',     'discover', 'paid_search',       'gads:demo-now',             'morgan@lorefi.com', 'anonymous', '2026-02-04 13:00'),
  ('camille.tremblay@bluefinmedia.com', 'Bluefin Media',         'insights', 'social_organic',    'x:org',                     'jules@lorefi.com',  'known',     '2026-02-04 14:00'),
  ('andrei.volkov@skylinenewsroom.com', 'Skyline Newsroom',      'studio',   'outbound',          'ob:strategic-accounts',     'priya@lorefi.com',  'anonymous', '2026-02-05 10:00'),
  ('imogen.bryce@steepwatermag.com',    'Steepwater Magazine',   'bundle',   'webinar',           'wbnr:editorial-velocity',   'sam@lorefi.com',    'anonymous', '2026-02-07 11:00'),
  ('jin.park@echoplainsmedia.com',      'Echo Plains Media',     'discover', 'direct',            NULL,                        'morgan@lorefi.com', 'anonymous', '2026-02-08 10:00');


-- ---------------------------------------------------------------------------
-- Activities (~125)
-- Inserted in chronological order per lead. Activity types that map to funnel
-- transitions (mql_qualified, demo_booked, opp_created, closed_won/lost) will
-- advance gtm.leads.funnel_state via the trigger from 005.
-- ---------------------------------------------------------------------------

INSERT INTO gtm.activities (lead_id, activity_type, occurred_at, payload)
SELECT l.id, a.activity_type, a.occurred_at, a.payload
FROM gtm.leads l
JOIN (VALUES
  -- 1. alex.rosen -> won
  ('alex.rosen@verge.media',            'page_view',     '2026-01-04 09:11'::timestamptz, '{"path":"/discover"}'::jsonb),
  ('alex.rosen@verge.media',            'signup',        '2026-01-04 09:12'::timestamptz, '{}'::jsonb),
  ('alex.rosen@verge.media',            'mql_qualified', '2026-01-09 14:02'::timestamptz, '{"score":78,"signal":"pricing_view"}'::jsonb),
  ('alex.rosen@verge.media',            'demo_booked',   '2026-01-15 16:00'::timestamptz, '{"slot":"2026-01-22T18:00Z"}'::jsonb),
  ('alex.rosen@verge.media',            'demo_attended', '2026-01-22 18:05'::timestamptz, '{"attendees":3}'::jsonb),
  ('alex.rosen@verge.media',            'opp_created',   '2026-02-02 11:30'::timestamptz, '{"amount_usd":48000,"seats":12,"stage":"discovery"}'::jsonb),
  ('alex.rosen@verge.media',            'closed_won',    '2026-02-19 15:42'::timestamptz, '{"amount_usd":48000,"seats":12,"close_reason":"replaced two point tools"}'::jsonb),

  -- 2. priya.menon -> sql
  ('priya.menon@atlaspublicradio.org',  'page_view',     '2026-01-06 14:42'::timestamptz, '{"path":"/studio"}'::jsonb),
  ('priya.menon@atlaspublicradio.org',  'signup',        '2026-01-06 14:45'::timestamptz, '{}'::jsonb),
  ('priya.menon@atlaspublicradio.org',  'doc_download',  '2026-01-06 14:50'::timestamptz, '{"asset":"guide:editorial-ops"}'::jsonb),
  ('priya.menon@atlaspublicradio.org',  'mql_qualified', '2026-01-13 10:00'::timestamptz, '{"score":73,"signal":"guide_download"}'::jsonb),
  ('priya.menon@atlaspublicradio.org',  'demo_booked',   '2026-01-20 11:00'::timestamptz, '{"slot":"2026-01-27T16:00Z"}'::jsonb),

  -- 3. toni.alvarez -> mql
  ('toni.alvarez@northshorepress.com',  'page_view',     '2026-01-07 10:01'::timestamptz, '{"path":"/insights"}'::jsonb),
  ('toni.alvarez@northshorepress.com',  'signup',        '2026-01-07 10:04'::timestamptz, '{}'::jsonb),
  ('toni.alvarez@northshorepress.com',  'mql_qualified', '2026-01-14 13:00'::timestamptz, '{"score":68,"signal":"webinar_attended"}'::jsonb),

  -- 4. mira.chen -> won
  ('mira.chen@latticenewsroom.com',     'page_view',     '2026-01-08 11:30'::timestamptz, '{"path":"/pricing"}'::jsonb),
  ('mira.chen@latticenewsroom.com',     'signup',        '2026-01-08 11:35'::timestamptz, '{}'::jsonb),
  ('mira.chen@latticenewsroom.com',     'mql_qualified', '2026-01-12 09:00'::timestamptz, '{"score":82,"signal":"pricing_view"}'::jsonb),
  ('mira.chen@latticenewsroom.com',     'demo_booked',   '2026-01-19 14:00'::timestamptz, '{"slot":"2026-01-26T15:00Z"}'::jsonb),
  ('mira.chen@latticenewsroom.com',     'demo_attended', '2026-01-26 15:08'::timestamptz, '{"attendees":5}'::jsonb),
  ('mira.chen@latticenewsroom.com',     'opp_created',   '2026-02-10 10:00'::timestamptz, '{"amount_usd":96000,"seats":24,"stage":"proposal"}'::jsonb),
  ('mira.chen@latticenewsroom.com',     'closed_won',    '2026-02-28 16:15'::timestamptz, '{"amount_usd":96000,"seats":24,"close_reason":"replaced spreadsheet workflow"}'::jsonb),

  -- 5. diego.park -> opp
  ('diego.park@foliostudios.tv',        'page_view',     '2026-01-09 09:30'::timestamptz, '{"path":"/studio"}'::jsonb),
  ('diego.park@foliostudios.tv',        'signup',        '2026-01-09 09:32'::timestamptz, '{}'::jsonb),
  ('diego.park@foliostudios.tv',        'doc_download',  '2026-01-15 18:00'::timestamptz, '{"asset":"deck:studio-overview"}'::jsonb),
  ('diego.park@foliostudios.tv',        'mql_qualified', '2026-01-14 10:00'::timestamptz, '{"score":74}'::jsonb),
  ('diego.park@foliostudios.tv',        'demo_booked',   '2026-01-21 11:00'::timestamptz, '{"slot":"2026-01-28T15:00Z"}'::jsonb),
  ('diego.park@foliostudios.tv',        'opp_created',   '2026-02-09 14:00'::timestamptz, '{"amount_usd":72000,"seats":18,"stage":"discovery"}'::jsonb),

  -- 6. sasha.vance -> lost
  ('sasha.vance@riverlightmedia.com',   'page_view',     '2026-01-10 11:00'::timestamptz, '{"path":"/discover"}'::jsonb),
  ('sasha.vance@riverlightmedia.com',   'signup',        '2026-01-10 11:05'::timestamptz, '{}'::jsonb),
  ('sasha.vance@riverlightmedia.com',   'mql_qualified', '2026-01-15 09:00'::timestamptz, '{"score":71}'::jsonb),
  ('sasha.vance@riverlightmedia.com',   'demo_booked',   '2026-01-22 14:00'::timestamptz, '{"slot":"2026-01-29T17:00Z"}'::jsonb),
  ('sasha.vance@riverlightmedia.com',   'opp_created',   '2026-02-05 11:00'::timestamptz, '{"amount_usd":40000,"seats":10,"stage":"discovery"}'::jsonb),
  ('sasha.vance@riverlightmedia.com',   'closed_lost',   '2026-03-01 09:30'::timestamptz, '{"amount_usd":40000,"close_reason":"budget freeze"}'::jsonb),

  -- 7. yusuf.patel -> mql
  ('yusuf.patel@northwindbureau.com',   'page_view',     '2026-01-11 12:00'::timestamptz, '{"path":"/insights"}'::jsonb),
  ('yusuf.patel@northwindbureau.com',   'signup',        '2026-01-11 12:03'::timestamptz, '{}'::jsonb),
  ('yusuf.patel@northwindbureau.com',   'mql_qualified', '2026-01-19 09:00'::timestamptz, '{"score":65}'::jsonb),

  -- 8. hana.iverson -> sql
  ('hana.iverson@cresthilldaily.com',   'page_view',     '2026-01-11 09:00'::timestamptz, '{"path":"/discover"}'::jsonb),
  ('hana.iverson@cresthilldaily.com',   'signup',        '2026-01-11 09:02'::timestamptz, '{}'::jsonb),
  ('hana.iverson@cresthilldaily.com',   'nurture_open',  '2026-01-15 15:00'::timestamptz, '{"campaign":"onb:day-3"}'::jsonb),
  ('hana.iverson@cresthilldaily.com',   'mql_qualified', '2026-01-16 14:00'::timestamptz, '{"score":79}'::jsonb),
  ('hana.iverson@cresthilldaily.com',   'demo_booked',   '2026-01-23 13:00'::timestamptz, '{"slot":"2026-01-30T15:00Z"}'::jsonb),

  -- 9. mateo.ruiz -> opp
  ('mateo.ruiz@baysidebroadcasting.com','page_view',     '2026-01-12 12:00'::timestamptz, '{"path":"/studio"}'::jsonb),
  ('mateo.ruiz@baysidebroadcasting.com','signup',        '2026-01-12 12:03'::timestamptz, '{}'::jsonb),
  ('mateo.ruiz@baysidebroadcasting.com','mql_qualified', '2026-01-18 09:00'::timestamptz, '{"score":80}'::jsonb),
  ('mateo.ruiz@baysidebroadcasting.com','demo_booked',   '2026-01-25 10:00'::timestamptz, '{"slot":"2026-02-01T16:00Z"}'::jsonb),
  ('mateo.ruiz@baysidebroadcasting.com','opp_created',   '2026-02-15 12:30'::timestamptz, '{"amount_usd":54000,"seats":13,"stage":"proposal"}'::jsonb),

  -- 10. kira.nakamura -> known
  ('kira.nakamura@ironpine.tv',         'page_view',     '2026-01-17 09:00'::timestamptz, '{"path":"/insights"}'::jsonb),
  ('kira.nakamura@ironpine.tv',         'signup',        '2026-01-17 09:03'::timestamptz, '{}'::jsonb),

  -- 11. olu.adeyemi -> won
  ('olu.adeyemi@mapleandstone.media',   'page_view',     '2026-01-19 08:45'::timestamptz, '{"path":"/insights"}'::jsonb),
  ('olu.adeyemi@mapleandstone.media',   'signup',        '2026-01-19 08:48'::timestamptz, '{}'::jsonb),
  ('olu.adeyemi@mapleandstone.media',   'mql_qualified', '2026-01-24 13:10'::timestamptz, '{"score":75}'::jsonb),
  ('olu.adeyemi@mapleandstone.media',   'demo_booked',   '2026-01-30 11:00'::timestamptz, '{"slot":"2026-02-04T17:00Z"}'::jsonb),
  ('olu.adeyemi@mapleandstone.media',   'demo_attended', '2026-02-04 17:02'::timestamptz, '{"attendees":2}'::jsonb),
  ('olu.adeyemi@mapleandstone.media',   'opp_created',   '2026-02-17 14:00'::timestamptz, '{"amount_usd":36000,"seats":9,"stage":"negotiation"}'::jsonb),
  ('olu.adeyemi@mapleandstone.media',   'closed_won',    '2026-03-05 09:20'::timestamptz, '{"amount_usd":36000,"seats":9,"close_reason":"insights replaces manual reports"}'::jsonb),

  -- 12. beatriz.costa -> sql
  ('beatriz.costa@highlineaudio.fm',    'page_view',     '2026-01-20 10:00'::timestamptz, '{"path":"/studio"}'::jsonb),
  ('beatriz.costa@highlineaudio.fm',    'signup',        '2026-01-20 10:03'::timestamptz, '{}'::jsonb),
  ('beatriz.costa@highlineaudio.fm',    'doc_download',  '2026-01-22 16:00'::timestamptz, '{"asset":"guide:podcast-attribution"}'::jsonb),
  ('beatriz.costa@highlineaudio.fm',    'mql_qualified', '2026-01-25 11:00'::timestamptz, '{"score":71,"signal":"podcast_ad_click"}'::jsonb),
  ('beatriz.costa@highlineaudio.fm',    'demo_booked',   '2026-02-01 09:00'::timestamptz, '{"slot":"2026-02-08T14:00Z"}'::jsonb),

  -- 13. henry.lin -> mql
  ('henry.lin@quadrantpress.com',       'page_view',     '2026-01-21 09:00'::timestamptz, '{"path":"/discover"}'::jsonb),
  ('henry.lin@quadrantpress.com',       'signup',        '2026-01-21 09:02'::timestamptz, '{}'::jsonb),
  ('henry.lin@quadrantpress.com',       'mql_qualified', '2026-01-28 11:00'::timestamptz, '{"score":70}'::jsonb),

  -- 14. sienna.brooks -> lost
  ('sienna.brooks@beaconhillmedia.com', 'page_view',     '2026-01-23 13:00'::timestamptz, '{"path":"/insights"}'::jsonb),
  ('sienna.brooks@beaconhillmedia.com', 'signup',        '2026-01-23 13:05'::timestamptz, '{}'::jsonb),
  ('sienna.brooks@beaconhillmedia.com', 'mql_qualified', '2026-01-29 11:30'::timestamptz, '{"score":68}'::jsonb),
  ('sienna.brooks@beaconhillmedia.com', 'demo_booked',   '2026-02-04 10:00'::timestamptz, '{"slot":"2026-02-11T15:00Z"}'::jsonb),
  ('sienna.brooks@beaconhillmedia.com', 'opp_created',   '2026-02-18 14:00'::timestamptz, '{"amount_usd":52000,"seats":13,"stage":"discovery"}'::jsonb),
  ('sienna.brooks@beaconhillmedia.com', 'closed_lost',   '2026-03-15 16:00'::timestamptz, '{"amount_usd":52000,"close_reason":"chose competitor","competitor":"NarrativeOps"}'::jsonb),

  -- 15. rafael.ortega -> known
  ('rafael.ortega@tideline.studio',     'page_view',     '2026-01-24 11:00'::timestamptz, '{"path":"/bundle"}'::jsonb),
  ('rafael.ortega@tideline.studio',     'signup',        '2026-01-24 11:04'::timestamptz, '{}'::jsonb),

  -- 16. aoife.sullivan -> mql
  ('aoife.sullivan@frontlinenewsroom.com','page_view',   '2026-01-25 10:00'::timestamptz, '{"path":"/blog/measurement-failure"}'::jsonb),
  ('aoife.sullivan@frontlinenewsroom.com','signup',      '2026-01-25 10:03'::timestamptz, '{}'::jsonb),
  ('aoife.sullivan@frontlinenewsroom.com','mql_qualified','2026-02-01 13:00'::timestamptz, '{"score":66}'::jsonb),

  -- 17. eli.glass -> opp
  ('eli.glass@northstarpub.com',        'page_view',     '2026-01-25 15:00'::timestamptz, '{"path":"/pricing"}'::jsonb),
  ('eli.glass@northstarpub.com',        'signup',        '2026-01-25 15:02'::timestamptz, '{}'::jsonb),
  ('eli.glass@northstarpub.com',        'nurture_open',  '2026-01-28 09:00'::timestamptz, '{"campaign":"ob:strategic-accounts-1"}'::jsonb),
  ('eli.glass@northstarpub.com',        'mql_qualified', '2026-01-31 11:00'::timestamptz, '{"score":85,"signal":"outbound_reply"}'::jsonb),
  ('eli.glass@northstarpub.com',        'demo_booked',   '2026-02-06 14:00'::timestamptz, '{"slot":"2026-02-13T17:00Z"}'::jsonb),
  ('eli.glass@northstarpub.com',        'opp_created',   '2026-02-28 10:00'::timestamptz, '{"amount_usd":120000,"seats":30,"stage":"negotiation"}'::jsonb),

  -- 18. quincy.watanabe -> won
  ('quincy.watanabe@vellummedia.com',   'page_view',     '2026-01-27 10:05'::timestamptz, '{"path":"/bundle"}'::jsonb),
  ('quincy.watanabe@vellummedia.com',   'signup',        '2026-01-27 10:08'::timestamptz, '{}'::jsonb),
  ('quincy.watanabe@vellummedia.com',   'mql_qualified', '2026-02-01 12:00'::timestamptz, '{"score":90,"signal":"high_seat_count"}'::jsonb),
  ('quincy.watanabe@vellummedia.com',   'demo_booked',   '2026-02-06 09:30'::timestamptz, '{"slot":"2026-02-13T16:00Z"}'::jsonb),
  ('quincy.watanabe@vellummedia.com',   'demo_attended', '2026-02-13 16:04'::timestamptz, '{"attendees":7}'::jsonb),
  ('quincy.watanabe@vellummedia.com',   'opp_created',   '2026-03-01 11:45'::timestamptz, '{"amount_usd":180000,"seats":45,"stage":"proposal"}'::jsonb),
  ('quincy.watanabe@vellummedia.com',   'closed_won',    '2026-03-22 17:30'::timestamptz, '{"amount_usd":180000,"seats":45,"close_reason":"bundle pricing beat unbundled competitor"}'::jsonb),

  -- 19. noor.hassan -> sql
  ('noor.hassan@halftide.audio',        'page_view',     '2026-01-28 16:00'::timestamptz, '{"path":"/insights"}'::jsonb),
  ('noor.hassan@halftide.audio',        'signup',        '2026-01-28 16:03'::timestamptz, '{}'::jsonb),
  ('noor.hassan@halftide.audio',        'nurture_click', '2026-01-31 13:00'::timestamptz, '{"campaign":"podcast_followup","cta":"book_demo"}'::jsonb),
  ('noor.hassan@halftide.audio',        'mql_qualified', '2026-02-02 10:00'::timestamptz, '{"score":76}'::jsonb),
  ('noor.hassan@halftide.audio',        'demo_booked',   '2026-02-09 14:00'::timestamptz, '{"slot":"2026-02-16T15:00Z"}'::jsonb),

  -- 20. lior.cohen -> mql
  ('lior.cohen@longbridgepress.com',    'page_view',     '2026-01-29 14:00'::timestamptz, '{"path":"/discover"}'::jsonb),
  ('lior.cohen@longbridgepress.com',    'signup',        '2026-01-29 14:02'::timestamptz, '{}'::jsonb),
  ('lior.cohen@longbridgepress.com',    'mql_qualified', '2026-02-05 10:00'::timestamptz, '{"score":67}'::jsonb),

  -- 21. reggie.ford -> lost
  ('reggie.ford@loomstatemedia.com',    'page_view',     '2026-01-30 16:00'::timestamptz, '{"path":"/studio"}'::jsonb),
  ('reggie.ford@loomstatemedia.com',    'signup',        '2026-01-30 16:03'::timestamptz, '{}'::jsonb),
  ('reggie.ford@loomstatemedia.com',    'mql_qualified', '2026-02-05 12:00'::timestamptz, '{"score":72}'::jsonb),
  ('reggie.ford@loomstatemedia.com',    'demo_booked',   '2026-02-12 09:00'::timestamptz, '{"slot":"2026-02-19T14:00Z"}'::jsonb),
  ('reggie.ford@loomstatemedia.com',    'opp_created',   '2026-02-26 15:30'::timestamptz, '{"amount_usd":30000,"seats":8,"stage":"discovery"}'::jsonb),
  ('reggie.ford@loomstatemedia.com',    'closed_lost',   '2026-03-20 13:00'::timestamptz, '{"amount_usd":30000,"close_reason":"timing — re-evaluate Q3"}'::jsonb),

  -- 22. marta.klein -> anonymous (page view only)
  ('marta.klein@southforkdaily.com',    'page_view',     '2026-01-31 17:00'::timestamptz, '{"path":"/blog/measurement-failure"}'::jsonb),

  -- 23. ines.aguilar -> sql
  ('ines.aguilar@cypressquarterly.com', 'page_view',     '2026-02-01 13:00'::timestamptz, '{"path":"/insights"}'::jsonb),
  ('ines.aguilar@cypressquarterly.com', 'signup',        '2026-02-01 13:04'::timestamptz, '{}'::jsonb),
  ('ines.aguilar@cypressquarterly.com', 'mql_qualified', '2026-02-07 09:00'::timestamptz, '{"score":80}'::jsonb),
  ('ines.aguilar@cypressquarterly.com', 'demo_booked',   '2026-02-14 11:00'::timestamptz, '{"slot":"2026-02-21T16:00Z"}'::jsonb),

  -- 24. theo.whitman -> mql
  ('theo.whitman@glasshouse.studio',    'page_view',     '2026-02-02 16:00'::timestamptz, '{"path":"/studio"}'::jsonb),
  ('theo.whitman@glasshouse.studio',    'signup',        '2026-02-02 16:03'::timestamptz, '{}'::jsonb),
  ('theo.whitman@glasshouse.studio',    'mql_qualified', '2026-02-09 11:00'::timestamptz, '{"score":72}'::jsonb),

  -- 25. vivian.park -> won
  ('vivian.park@anchorbaynews.com',     'page_view',     '2026-02-03 14:22'::timestamptz, '{"path":"/discover"}'::jsonb),
  ('vivian.park@anchorbaynews.com',     'signup',        '2026-02-03 14:25'::timestamptz, '{}'::jsonb),
  ('vivian.park@anchorbaynews.com',     'mql_qualified', '2026-02-08 10:10'::timestamptz, '{"score":76}'::jsonb),
  ('vivian.park@anchorbaynews.com',     'demo_booked',   '2026-02-13 13:00'::timestamptz, '{"slot":"2026-02-20T19:00Z"}'::jsonb),
  ('vivian.park@anchorbaynews.com',     'demo_attended', '2026-02-20 19:01'::timestamptz, '{"attendees":4}'::jsonb),
  ('vivian.park@anchorbaynews.com',     'opp_created',   '2026-03-04 15:00'::timestamptz, '{"amount_usd":60000,"seats":15,"stage":"proposal"}'::jsonb),
  ('vivian.park@anchorbaynews.com',     'closed_won',    '2026-03-25 11:00'::timestamptz, '{"amount_usd":60000,"seats":15,"close_reason":"insights bundle"}'::jsonb),

  -- 26. sami.okafor -> mql
  ('sami.okafor@riverbendreports.com',  'page_view',     '2026-02-04 13:00'::timestamptz, '{"path":"/discover"}'::jsonb),
  ('sami.okafor@riverbendreports.com',  'signup',        '2026-02-04 13:04'::timestamptz, '{}'::jsonb),
  ('sami.okafor@riverbendreports.com',  'mql_qualified', '2026-02-11 09:00'::timestamptz, '{"score":69}'::jsonb),

  -- 27. camille.tremblay -> known
  ('camille.tremblay@bluefinmedia.com', 'page_view',     '2026-02-04 14:00'::timestamptz, '{"path":"/insights"}'::jsonb),
  ('camille.tremblay@bluefinmedia.com', 'signup',        '2026-02-04 14:03'::timestamptz, '{}'::jsonb),

  -- 28. andrei.volkov -> opp
  ('andrei.volkov@skylinenewsroom.com', 'page_view',     '2026-02-05 10:00'::timestamptz, '{"path":"/studio"}'::jsonb),
  ('andrei.volkov@skylinenewsroom.com', 'signup',        '2026-02-05 10:04'::timestamptz, '{}'::jsonb),
  ('andrei.volkov@skylinenewsroom.com', 'mql_qualified', '2026-02-11 13:00'::timestamptz, '{"score":77}'::jsonb),
  ('andrei.volkov@skylinenewsroom.com', 'demo_booked',   '2026-02-18 09:00'::timestamptz, '{"slot":"2026-02-25T15:00Z"}'::jsonb),
  ('andrei.volkov@skylinenewsroom.com', 'opp_created',   '2026-03-10 11:00'::timestamptz, '{"amount_usd":48000,"seats":12,"stage":"discovery"}'::jsonb),

  -- 29. imogen.bryce -> sql
  ('imogen.bryce@steepwatermag.com',    'page_view',     '2026-02-07 11:00'::timestamptz, '{"path":"/bundle"}'::jsonb),
  ('imogen.bryce@steepwatermag.com',    'signup',        '2026-02-07 11:03'::timestamptz, '{}'::jsonb),
  ('imogen.bryce@steepwatermag.com',    'mql_qualified', '2026-02-13 14:00'::timestamptz, '{"score":72,"signal":"webinar_attendance"}'::jsonb),
  ('imogen.bryce@steepwatermag.com',    'demo_booked',   '2026-02-20 10:00'::timestamptz, '{"slot":"2026-02-27T17:00Z"}'::jsonb),

  -- 30. jin.park -> anonymous (page view only)
  ('jin.park@echoplainsmedia.com',      'page_view',     '2026-02-08 10:00'::timestamptz, '{"path":"/discover"}'::jsonb)
) AS a(email, activity_type, occurred_at, payload)
  ON l.email = a.email;


-- ---------------------------------------------------------------------------
-- Experiments (3) + variants (6)
-- ---------------------------------------------------------------------------

INSERT INTO gtm.experiments (name, hypothesis, primary_metric, started_at, status) VALUES
  ('subject_line_lift_q1',
   'A subject line naming a concrete cross-media outcome lifts reply rate over a vague curiosity hook.',
   'reply_rate',
   '2026-01-10', 'active'),
  ('paid_landing_hero_q1',
   'A product-screenshot hero outperforms an abstract editorial-aesthetic hero on paid-search landing pages.',
   'demo_request_rate',
   '2026-01-15', 'active'),
  ('nurture_sequence_v2',
   'A compact three-touch nurture beats a five-touch nurture for trial-to-SQL conversion.',
   'trial_to_sql_rate',
   '2026-01-20', 'paused');

INSERT INTO gtm.experiment_variants
  (experiment_id, variant_name, traffic_pct, is_control, subject_line, body_template)
SELECT e.id, v.variant_name, v.traffic_pct, v.is_control, v.subject_line, v.body_template
FROM gtm.experiments e
JOIN (VALUES
  ('subject_line_lift_q1', 'control',              50.0, true,  'Quick question about your newsroom',
                                                                'Hi {{first_name}}, mind if I send a short note about how {{company}} is finding story threads today?'),
  ('subject_line_lift_q1', 'outcome_named',        50.0, false, 'Find every story thread across your media',
                                                                'Hi {{first_name}}, most newsrooms miss roughly a third of cross-channel pickup. Two-minute walkthrough?'),
  ('paid_landing_hero_q1', 'abstract_hero',        50.0, true,  NULL, NULL),
  ('paid_landing_hero_q1', 'screenshot_hero',      50.0, false, NULL, NULL),
  ('nurture_sequence_v2',  'control_five_touch',   50.0, true,  NULL, NULL),
  ('nurture_sequence_v2',  'compact_three_touch',  50.0, false, NULL, NULL)
) AS v(experiment_name, variant_name, traffic_pct, is_control, subject_line, body_template)
  ON e.name = v.experiment_name;


-- ---------------------------------------------------------------------------
-- Experiment exposures (21)
-- ---------------------------------------------------------------------------

INSERT INTO gtm.experiment_exposures (variant_id, lead_id, exposed_at)
SELECT v.id, l.id, x.exposed_at
FROM (VALUES
  -- subject_line_lift_q1
  ('subject_line_lift_q1', 'control',             'alex.rosen@verge.media',             '2026-01-11 09:00'::timestamptz),
  ('subject_line_lift_q1', 'outcome_named',       'priya.menon@atlaspublicradio.org',   '2026-01-11 09:00'::timestamptz),
  ('subject_line_lift_q1', 'control',             'toni.alvarez@northshorepress.com',   '2026-01-11 09:05'::timestamptz),
  ('subject_line_lift_q1', 'outcome_named',       'mira.chen@latticenewsroom.com',      '2026-01-11 09:05'::timestamptz),
  ('subject_line_lift_q1', 'control',             'diego.park@foliostudios.tv',         '2026-01-12 09:00'::timestamptz),
  ('subject_line_lift_q1', 'outcome_named',       'yusuf.patel@northwindbureau.com',    '2026-01-12 09:00'::timestamptz),
  ('subject_line_lift_q1', 'outcome_named',       'hana.iverson@cresthilldaily.com',    '2026-01-13 10:00'::timestamptz),
  ('subject_line_lift_q1', 'control',             'mateo.ruiz@baysidebroadcasting.com', '2026-01-13 10:00'::timestamptz),

  -- paid_landing_hero_q1
  ('paid_landing_hero_q1', 'abstract_hero',       'sasha.vance@riverlightmedia.com',    '2026-01-15 11:00'::timestamptz),
  ('paid_landing_hero_q1', 'screenshot_hero',     'sami.okafor@riverbendreports.com',   '2026-02-04 13:00'::timestamptz),
  ('paid_landing_hero_q1', 'screenshot_hero',     'quincy.watanabe@vellummedia.com',    '2026-01-27 10:00'::timestamptz),
  ('paid_landing_hero_q1', 'abstract_hero',       'sienna.brooks@beaconhillmedia.com',  '2026-01-23 13:00'::timestamptz),
  ('paid_landing_hero_q1', 'screenshot_hero',     'noor.hassan@halftide.audio',         '2026-01-28 16:00'::timestamptz),
  ('paid_landing_hero_q1', 'abstract_hero',       'eli.glass@northstarpub.com',         '2026-01-25 15:00'::timestamptz),
  ('paid_landing_hero_q1', 'screenshot_hero',     'imogen.bryce@steepwatermag.com',     '2026-02-07 11:00'::timestamptz),

  -- nurture_sequence_v2
  ('nurture_sequence_v2',  'compact_three_touch', 'olu.adeyemi@mapleandstone.media',    '2026-01-20 09:00'::timestamptz),
  ('nurture_sequence_v2',  'compact_three_touch', 'vivian.park@anchorbaynews.com',      '2026-02-03 14:30'::timestamptz),
  ('nurture_sequence_v2',  'control_five_touch',  'ines.aguilar@cypressquarterly.com',  '2026-02-01 13:00'::timestamptz),
  ('nurture_sequence_v2',  'control_five_touch',  'lior.cohen@longbridgepress.com',     '2026-01-29 14:30'::timestamptz),
  ('nurture_sequence_v2',  'compact_three_touch', 'andrei.volkov@skylinenewsroom.com',  '2026-02-05 10:30'::timestamptz),
  ('nurture_sequence_v2',  'control_five_touch',  'theo.whitman@glasshouse.studio',     '2026-02-02 16:00'::timestamptz)
) AS x(experiment_name, variant_name, email, exposed_at)
JOIN gtm.experiments         e ON e.name = x.experiment_name
JOIN gtm.experiment_variants v ON v.experiment_id = e.id
                              AND v.variant_name  = x.variant_name
JOIN gtm.leads               l ON l.email         = x.email;


-- ---------------------------------------------------------------------------
-- Agent outputs (15)
-- Inserted as pending_review, then UPDATEd into other states so the audit
-- log captures real transitions. Slugs in payload identify rows for updates.
-- ---------------------------------------------------------------------------

INSERT INTO gtm.agent_outputs (agent_name, output_type, target_ref, payload) VALUES
  -- 5 will stay pending_review
  ('email_ops',   'subject_line_variant',
    (SELECT id::text FROM gtm.experiments WHERE name = 'subject_line_lift_q1'),
    '{"slug":"p1","subject_line":"Where did that story break first?","reasoning":"Curiosity hook tied to discovery use case"}'),
  ('email_ops',   'subject_line_variant',
    (SELECT id::text FROM gtm.experiments WHERE name = 'subject_line_lift_q1'),
    '{"slug":"p2","subject_line":"3 minutes to find every thread","reasoning":"Specific time-to-value framing"}'),
  ('content_ops', 'blog_draft', 'topic:editorial-velocity',
    '{"slug":"p3","title":"How fast newsrooms compound lead time","outline":["the velocity flywheel","what gets measured","Lorefi Studio fit"],"word_count":1100}'),
  ('content_ops', 'ad_copy',    'gads:lorefi-discover',
    '{"slug":"p4","headline":"Find every thread of your story","description":"Lorefi Discover surfaces cross-media pickup in under 30 seconds.","cta":"See it live"}'),
  ('content_ops', 'social_caption', 'linkedin:weekly-pulse',
    '{"slug":"p5","caption":"Three signals your newsroom is leaving pickup on the table — and one diagnostic you can run today.","hashtags":["editorialops","newsroomtools"]}'),

  -- 3 will be approved
  ('email_ops',   'subject_line_variant',
    (SELECT id::text FROM gtm.experiments WHERE name = 'subject_line_lift_q1'),
    '{"slug":"a1","subject_line":"What every newsroom misses about pickup","reasoning":"Loss-frame outperformed in Q4 holdout"}'),
  ('content_ops', 'blog_draft', 'topic:newsroom-tools-2026',
    '{"slug":"a2","title":"The newsroom tooling stack in 2026","outline":["where the seams are","who owns measurement","Insights vs spreadsheet sprawl"],"word_count":1400}'),
  ('content_ops', 'ad_copy',    'gads:demo-now',
    '{"slug":"a3","headline":"See your cross-media pickup in one view","description":"Lorefi Insights, free trial, no card needed.","cta":"Start trial"}'),

  -- 3 will be rejected
  ('email_ops',   'subject_line_variant',
    (SELECT id::text FROM gtm.experiments WHERE name = 'subject_line_lift_q1'),
    '{"slug":"r1","subject_line":"Checking in","reasoning":"Generic baseline"}'),
  ('content_ops', 'blog_draft', 'topic:ai-newsrooms-overhype',
    '{"slug":"r2","title":"AI will replace newsrooms — and other lies","outline":["why the hype cycle is wrong","what stays human"],"word_count":900}'),
  ('content_ops', 'social_caption', 'x:trending',
    '{"slug":"r3","caption":"Hot take: most newsrooms are doing it wrong. Here is why.","hashtags":["hottake"]}'),

  -- 4 will be approved AND shipped
  ('email_ops',   'subject_line_variant',
    (SELECT id::text FROM gtm.experiments WHERE name = 'subject_line_lift_q1'),
    '{"slug":"s1","subject_line":"Two minutes on the threads you are missing","reasoning":"Curiosity + concrete time investment"}'),
  ('content_ops', 'blog_draft', 'topic:cross-media-measurement',
    '{"slug":"s2","title":"Why cross-media measurement breaks under pressure","outline":["the breaking points","what we built","Insights walkthrough"],"word_count":1600}'),
  ('content_ops', 'ad_copy',    'gads:lorefi-discover',
    '{"slug":"s3","headline":"Track a story across every channel","description":"Lorefi Discover, built for B2B media teams.","cta":"Book a demo"}'),
  ('content_ops', 'social_caption', 'linkedin:newsroom-craft',
    '{"slug":"s4","caption":"The strongest newsrooms we work with all do this one thing differently.","hashtags":["editorialops","newsroomcraft"]}');


-- Move 7 rows to approved (3 stay approved, 4 will be shipped next).
UPDATE gtm.agent_outputs
SET status        = 'approved',
    reviewed_at   = '2026-04-01 10:00',
    reviewed_by   = 'morgan@lorefi.com',
    review_notes  = 'Tight framing, ship as is.'
WHERE payload->>'slug' IN ('a1','a2','a3','s1','s2','s3','s4');

-- Reject 3 rows.
UPDATE gtm.agent_outputs
SET status        = 'rejected',
    reviewed_at   = '2026-04-02 14:30',
    reviewed_by   = 'jules@lorefi.com',
    review_notes  = 'Off-brand or too generic — re-brief and retry.'
WHERE payload->>'slug' IN ('r1','r2','r3');

-- Ship 4 of the approved rows.
UPDATE gtm.agent_outputs
SET status      = 'shipped',
    shipped_at  = '2026-04-03 09:15',
    shipped_ref = CASE payload->>'slug'
                    WHEN 's1' THEN 'experiment_variant:shipped_two_minutes'
                    WHEN 's2' THEN 'cms:post:1024'
                    WHEN 's3' THEN 'gads:creative:88421'
                    WHEN 's4' THEN 'linkedin:post:9912'
                  END
WHERE payload->>'slug' IN ('s1','s2','s3','s4');

COMMIT;

-- Quick sanity counts (uncomment after seeding):
-- SELECT funnel_state, count(*) FROM gtm.leads GROUP BY 1 ORDER BY 1;
-- SELECT status, count(*) FROM gtm.agent_outputs GROUP BY 1 ORDER BY 1;
-- SELECT count(*) AS audit_rows FROM gtm.agent_output_audit;


-- ---------------------------------------------------------------------------
-- Q2 open_rate experiment: subject_line_lift_q2
--
-- Demonstrates the original `open_rate` path of the email-ops agent
-- (separate from the generalized signal_rate / multi-metric flow). Twelve
-- existing leads are exposed 6/6 across a control and an outcome_named
-- variant; email_opened activities are inserted so that:
--   - control       has 3 of 6 opens => 0.500 open rate (winner)
--   - outcome_named has 1 of 6 opens => 0.167 open rate (loser; the agent
--                                                        proposes replacements
--                                                        for this variant)
--
-- The agent's CTE in queue.ts filters `is_control = false`, so it targets
-- the non-control variant. Run the agent with OPEN_RATE_THRESHOLD=0.18 (or
-- 0.20) and MIN_SAMPLE_SIZE<=6 to see it fire on outcome_named.
-- ---------------------------------------------------------------------------

BEGIN;

-- Experiment
INSERT INTO gtm.experiments (name, hypothesis, primary_metric, status, started_at, ended_at) VALUES
  ('subject_line_lift_q2',
   'Specific outcome-named subject lines outperform generic "quick question" patterns for cold open rates.',
   'open_rate',
   'active',
   '2026-03-15 00:00:00+00',
   NULL);

-- Variants
INSERT INTO gtm.experiment_variants
  (experiment_id, variant_name, traffic_pct, is_control, subject_line, body_template)
SELECT e.id, v.variant_name, v.traffic_pct, v.is_control, v.subject_line, v.body_template
FROM gtm.experiments e
JOIN (VALUES
  ('control',       50.0, true,  'Quick note from Lorefi',                          NULL),
  ('outcome_named', 50.0, false, 'Surface every story your newsroom is missing',    NULL)
) AS v(variant_name, traffic_pct, is_control, subject_line, body_template)
  ON e.name = 'subject_line_lift_q2';

-- Exposures: 12 oldest leads, 6 to each variant. exposed_at spread across
-- 2026-03-15 .. 2026-03-25 (one exposure every two days within each variant).
WITH selected_leads AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn
  FROM gtm.leads
  ORDER BY created_at
  LIMIT 12
)
INSERT INTO gtm.experiment_exposures (variant_id, lead_id, exposed_at)
SELECT
  v.id,
  sl.id,
  ('2026-03-15 00:00:00+00'::timestamptz + (((sl.rn - 1) % 6) * INTERVAL '2 days'))
FROM selected_leads sl
JOIN gtm.experiment_variants v
  ON v.experiment_id = (SELECT id FROM gtm.experiments WHERE name = 'subject_line_lift_q2')
WHERE
     (sl.rn <= 6 AND v.variant_name = 'control')
  OR (sl.rn >  6 AND v.variant_name = 'outcome_named');

-- email_opened activities. occurred_at is >= the matching exposed_at so the
-- temporal join in fetchUnderperformingExperiments counts them.
--   control:       3 openers (rn=1, rn=2, rn=3)  -> 3/6 = 0.500 (winner)
--   outcome_named: 1 opener  (rn=7)              -> 1/6 = 0.167 (loser)
WITH selected_leads AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn
  FROM gtm.leads
  ORDER BY created_at
  LIMIT 12
)
INSERT INTO gtm.activities (lead_id, activity_type, occurred_at, payload)
SELECT sl.id, 'email_opened', op.occurred_at, op.payload
FROM selected_leads sl
JOIN (VALUES
  (1, '2026-03-16 10:00:00+00'::timestamptz, '{"variant": "control"}'::jsonb),
  (2, '2026-03-18 10:30:00+00'::timestamptz, '{"variant": "control"}'::jsonb),
  (3, '2026-03-20 11:00:00+00'::timestamptz, '{"variant": "control"}'::jsonb),
  (7, '2026-03-16 11:00:00+00'::timestamptz, '{"variant": "outcome_named"}'::jsonb)
) AS op(rn, occurred_at, payload) ON op.rn = sl.rn;

COMMIT;
