import "server-only";

import { dealsStatus } from "@/lib/assistant-deals";
import { callBrief, draftEmail, outreachStatus } from "@/lib/assistant-outreach";
import { liftLabel, pct } from "@/lib/format";
import { buildInsights } from "@/lib/insights";
import { DEFAULT_FILTERS, queryLeads } from "@/lib/lead-query";
import { MIN_VALUED_WON, type RevenueTotals, type SegmentOutcome } from "@/lib/outcomes";
import {
  areaNames,
  areaSignal,
  type CloseRates,
  expectedValue,
  type Lead,
  leadsForWorkspace,
  ownerTypeFor,
  type Snapshot,
  tradeProbability,
} from "@/lib/snapshot";
import {
  isOpenLead,
  LEAD_FOLLOW_UP_DAYS,
  type LeadStatusRow,
  STATUS_LABEL,
  type Workspace,
  workspaceLabel,
} from "@/lib/workspace";

export interface ToolContext {
  snap: Snapshot;
  ws: Workspace;
  /** The signed-in viewer (`viewerId()`), never the client workspace id. Null when nobody is verified. */
  owner: string | null;
  statuses: Map<string, LeadStatusRow>;
  rates: CloseRates;
  outcomes: { rows: SegmentOutcome[]; revenue: RevenueTotals; permitJobValue: number };
}

/** JSON-schema tool definitions for the Messages API. All tools are read-only. */
export const TOOL_DEFS = [
  {
    name: "search_leads",
    description:
      "Search this workspace's leads (violations, 311 complaints, porch inspection requests, vacant buildings, closed restaurant spaces and investor purchases) in its trade and neighborhoods. Returns up to `limit` leads with chance of work and expected value.",
    input_schema: {
      type: "object",
      properties: {
        kind: {
          type: "string",
          enum: ["all", "violation", "complaint", "porch_request", "vacant", "closed_restaurant", "investor_purchase"],
        },
        tier: { type: "string", enum: ["all", "act_now", "this_week", "monitor"] },
        neighborhood: { type: "string", description: "Community area name, e.g. 'Logan Square'" },
        status: { type: "string", enum: ["all", "open", "contacted", "meeting", "won", "lost", "not_relevant"] },
        sort: { type: "string", enum: ["priority", "value", "newest", "probability"] },
        query: { type: "string", description: "Text to match in address, owner or buyer" },
        limit: { type: "integer", minimum: 1, maximum: 15 },
      },
    },
  },
  {
    name: "get_lead",
    description: "Full detail for one lead by id: evidence, owner or buyer, permits since, why it scores as it does.",
    input_schema: { type: "object", properties: { lead_id: { type: "string" } }, required: ["lead_id"] },
  },
  {
    name: "neighborhood_stats",
    description:
      "Demand by Chicago community area for this workspace's trade: last-90-day signals vs a year earlier, permits, investor purchases, major projects, open leads.",
    input_schema: {
      type: "object",
      properties: {
        neighborhood: { type: "string", description: "Optional single area name" },
        only_my_areas: { type: "boolean" },
        sort_by: { type: "string", enum: ["open_leads", "signals", "growth", "investor_purchases", "major_projects"] },
        limit: { type: "integer", minimum: 1, maximum: 20 },
      },
    },
  },
  {
    name: "competitors",
    description: "Top contractors in this trade citywide (permits in 12 months, growth, share) and who wins violation-driven jobs.",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "pipeline",
    description: `Leads this workspace has worked, by status, including follow-ups that are overdue (contacted ${LEAD_FOLLOW_UP_DAYS}+ days ago).`,
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "my_results",
    description:
      "Measured outcomes by signal type, the close rates used in scoring (measured or default), and the measured revenue: won jobs with a job value the user entered (count, total, median, revenue per worked lead), overall and by signal, and whether expected value uses the user's median job value or the permit-based typical job for each signal. Only entered values are counted; nothing is estimated.",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "suggested_moves",
    description: "The dashboard's data-driven suggested next moves for this workspace.",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "commercial_projects",
    description:
      "Properties likely to apply for a $100k+ permit within 180 days (pre-application signal), in this workspace's areas.",
    input_schema: { type: "object", properties: { limit: { type: "integer", minimum: 1, maximum: 15 } } },
  },
  {
    name: "commercial_opportunities",
    description:
      "The two citywide commercial pilot lists on /commercial (read-only, not filtered by workspace). list='new_business': build-out permits at commercial, mixed-use and 7+ unit addresses with no business license yet (model: how often a new business license follows within a year vs comparable addresses, timing, who arrives; plus the newest spaces with class, permit date, cost, work, contractors and the historical new-license rate). list='open_trades': trades that follow a $1M+ permit (per-trade follow-on rate, share going to a contractor not on the big permit, timing, mostly-locked-in flag; plus recent big permits with the trades that have already appeared). These are targeting lists for sellers, not a chance of work for any trade. Owner names and mailing addresses are not included.",
    input_schema: {
      type: "object",
      properties: {
        list: { type: "string", enum: ["new_business", "open_trades"] },
        limit: { type: "integer", minimum: 1, maximum: 15 },
      },
      required: ["list"],
    },
  },
  {
    name: "outreach_status",
    description:
      "The founder's own sales outreach: his pipeline of contractor prospects he pitches (counts by status, who is due today or overdue with the next step, the latest pipeline events) plus this workspace's lead-outreach summary (lead counts by status and overdue lead follow-ups). Phone numbers, email addresses and notes are never included; each prospect has a /prospects/<id> link where he sees them.",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "draft_email",
    description:
      "Draft an outreach email or letter for the founder to review and send himself; nothing is sent. For a contractor prospect pass prospect_id (from outreach_status or a /prospects/<id> link; an exact company name also works) and optionally step 1, 2 or 3 (day 0, 4 and 10 of the cold-email sequence; default is the next step in his pipeline). For a lead in this workspace pass lead_id to get the letter (or business email) the app drafts for that property owner. Returns subject, body, channel, compliance notes and requires_human_send.",
    input_schema: {
      type: "object",
      properties: {
        prospect_id: { type: "string", description: "Prospect id such as 'porch-mr-porch', or an exact company name" },
        step: { type: "integer", minimum: 1, maximum: 3, description: "Email 1, 2 or 3 of the sequence; omit for the next step" },
        lead_id: { type: "string" },
      },
    },
  },
  {
    name: "call_brief",
    description:
      "Preparation for a call the founder dials himself to a published business line: opening statement, reason for calling grounded in the data, discovery questions, likely objections with honest answers, suggested next step and compliance reminders. Pass prospect_id (a contractor he pitches) or lead_id. For individual homeowners the brief requires a skip-traced number that passed a Do Not Call scrub, hand-dialed. Refuses for prospects marked Not interested. The assistant never places calls.",
    input_schema: {
      type: "object",
      properties: {
        prospect_id: { type: "string", description: "Prospect id such as 'porch-mr-porch', or an exact company name" },
        lead_id: { type: "string" },
      },
    },
  },
  {
    name: "deals_status",
    description:
      "The founder's own deals: buyers he found and contacts personally and hands to partner vendors for a planning or referral fee. Counts by status, follow-ups due today or overdue (with the next step and a /deals/<id> link), totals quoted, fees and fees collected, and funnel numbers by source (contacted, replied, booked, median days from found to booked), all from his own records. For privacy it never includes buyer names, deal titles, handles, links to posts, contact details, locations, budgets or notes: refer to a deal by its type, event date and link.",
    input_schema: { type: "object", properties: {} },
  },
] as const;

type Input = Record<string, unknown>;
const str = (v: unknown) => (typeof v === "string" ? v : undefined);
const int = (v: unknown, d: number, max: number) =>
  Math.min(max, Math.max(1, Number.isInteger(v) ? (v as number) : d));

function areaIdByName(snap: Snapshot, name: string | undefined): number | undefined {
  if (!name) return undefined;
  const n = name.trim().toLowerCase();
  return snap.areas.find((a) => a.name.toLowerCase() === n)?.id ?? snap.areas.find((a) => a.name.toLowerCase().includes(n))?.id;
}

/** The headline chance for kinds whose signal is not itself a job (cited, sold). */
function headlineChance(l: Lead): Record<string, string> {
  if (l.kind === "complaint") return { chance_it_gets_cited_120d: pct(l.probability) };
  if (l.kind === "vacant") return { chance_it_sells_within_a_year: pct(l.probability) };
  if (l.kind === "closed_restaurant") {
    return {
      chance_new_food_business_licensed_within_a_year: pct(l.probability),
      chance_build_out_permit_within_a_year: pct(l.tradeProbabilities.general ?? 0),
    };
  }
  return {};
}

function compactLead(l: Lead, ctx: ToolContext) {
  const names = areaNames(ctx.snap);
  return {
    id: l.id,
    kind: l.kind,
    link: `/leads/${encodeURIComponent(l.id)}`,
    address: l.address,
    neighborhood: l.communityArea ? names.get(l.communityArea) : null,
    signal: l.title,
    signal_date: l.signalDate,
    days_ago: l.ageDays,
    priority: l.tier,
    status: STATUS_LABEL[ctx.statuses.get(l.id)?.status ?? "new"],
    chance_of_work: pct(tradeProbability(l, ctx.ws.trade, ctx.snap)),
    ...headlineChance(l),
    expected_value_usd: Math.round(expectedValue(l, ctx.ws.trade, ctx.snap, ctx.rates)),
    contact:
      l.kind === "investor_purchase"
        ? { buyer: l.buyer.name, purchases_last_2y: l.buyer.purchases24m }
        : {
            owner: l.owner.name,
            owner_type: l.owner.type,
            has_mailing_address: Boolean(l.owner.mailing),
            approach: ownerTypeFor(l) === "company" ? "business contact, mail as backup" : "mail",
          },
  };
}

function leadStatusCounts(statuses: Map<string, LeadStatusRow>): Record<string, number> {
  return Object.fromEntries(
    Object.entries(STATUS_LABEL).map(([k, v]) => [v, [...statuses.values()].filter((s) => s.status === k).length]),
  );
}

const daysSince = (d: Date) => Math.floor((Date.now() - d.getTime()) / 86_400_000);

/** This workspace's lead outreach, as the `pipeline` tool counts it, without free-text notes or owner details. */
function leadOutreachSummary(ctx: ToolContext) {
  const byId = new Map(ctx.snap.leads.map((l) => [l.id, l]));
  const overdue = [...ctx.statuses.values()]
    .filter((s) => s.status === "contacted" && daysSince(s.updatedAt) >= LEAD_FOLLOW_UP_DAYS)
    .sort((a, b) => a.updatedAt.getTime() - b.updatedAt.getTime());
  return {
    workspace: workspaceLabel(ctx.ws),
    counts_by_status: leadStatusCounts(ctx.statuses),
    overdue_follow_ups_total: overdue.length,
    overdue_follow_ups: overdue.slice(0, 15).map((s) => {
      const l = byId.get(s.leadId);
      return {
        lead_id: s.leadId,
        address: l?.address ?? null,
        signal: l?.title ?? null,
        link: l ? `/leads/${encodeURIComponent(l.id)}` : null,
        days_since_contacted: daysSince(s.updatedAt),
        has_notes: s.note.trim() !== "",
      };
    }),
  };
}
export type LeadOutreachSummary = ReturnType<typeof leadOutreachSummary>;

export async function runTool(name: string, input: Input, ctx: ToolContext): Promise<unknown> {
  const { snap, ws, statuses } = ctx;
  const names = areaNames(snap);
  switch (name) {
    case "search_leads": {
      const area = areaIdByName(snap, str(input.neighborhood));
      if (str(input.neighborhood) && area === undefined) return { error: `Unknown neighborhood "${input.neighborhood}"` };
      const leads = queryLeads(
        snap,
        ws,
        statuses,
        {
          ...DEFAULT_FILTERS,
          kind: str(input.kind) ?? "all",
          tier: str(input.tier) ?? "all",
          status: str(input.status) ?? "all",
          sort: str(input.sort) ?? "priority",
          q: (str(input.query) ?? "").slice(0, 100),
          area: area ? String(area) : "all",
        },
        ctx.rates,
      );
      return { total_matches: leads.length, leads: leads.slice(0, int(input.limit, 8, 15)).map((l) => compactLead(l, ctx)) };
    }
    case "get_lead": {
      const id = str(input.lead_id) ?? "";
      const l = snap.leads.find((x) => x.id === id);
      if (!l) return { error: "No lead with that id in this week's data" };
      return {
        ...compactLead(l, ctx),
        why: l.probabilityBasis,
        evidence: l.evidence,
        owner_mailing: l.owner.mailing,
        next_step: l.action,
        ...(l.tradeProbabilities
          ? {
              chance_of_work_by_trade: Object.fromEntries(
                Object.entries(l.tradeProbabilities).map(([k, v]) => [k, pct(v)]),
              ),
            }
          : {}),
        note: statuses.get(l.id)?.note ?? "",
        ...(l.kind === "investor_purchase"
          ? {
              buyer_other_properties: l.buyer.otherProperties,
              contractors_buyer_used: l.buyer.contractorsUsed,
              permits_since_purchase: l.permitsSince,
            }
          : {}),
        source: l.sourceUrl,
      };
    }
    case "neighborhood_stats": {
      const only = input.only_my_areas !== false && ws.areas.length > 0;
      const single = areaIdByName(snap, str(input.neighborhood));
      const open = leadsForWorkspace(snap, ws.trade, []).filter((l) => isOpenLead(statuses, l.id));
      const rows = snap.areas
        .filter((a) => (single ? a.id === single : !only || ws.areas.includes(a.id)))
        .map((a) => {
          const sig = areaSignal(a, ws.trade);
          return {
            neighborhood: a.name,
            signals_last_90_days: sig.now,
            signals_same_period_last_year: sig.before,
            trade_permits_last_90_days: a.permits[ws.trade].last90,
            investor_purchases_last_180_days: a.investorPurchases.last180,
            major_projects_last_90_days: a.majorProjects.last90,
            open_leads: open.filter((l) => l.communityArea === a.id).length,
          };
        });
      const key = {
        open_leads: (r: (typeof rows)[number]) => r.open_leads,
        signals: (r: (typeof rows)[number]) => r.signals_last_90_days,
        growth: (r: (typeof rows)[number]) => r.signals_last_90_days - r.signals_same_period_last_year,
        investor_purchases: (r: (typeof rows)[number]) => r.investor_purchases_last_180_days,
        major_projects: (r: (typeof rows)[number]) => r.major_projects_last_90_days,
      }[str(input.sort_by) ?? "open_leads"] ?? ((r: (typeof rows)[number]) => r.open_leads);
      return {
        signal_type: ws.trade === "general" ? "major projects" : `${snap.trades[ws.trade].label.toLowerCase()} violations`,
        rows: rows.sort((a, b) => key(b) - key(a)).slice(0, int(input.limit, 8, 20)),
      };
    }
    case "competitors": {
      const c = snap.competitors[ws.trade];
      return {
        trade: snap.trades[ws.trade].label,
        top_contractors: c.contractors.slice(0, 10).map((x) => ({
          name: x.name,
          jobs_last_12m: x.jobs12m,
          jobs_prior_12m: x.jobsPrev12m,
          share: pct(x.share),
          typical_job_usd: x.medianCost,
          active_in: x.areas.map((a) => names.get(a)),
        })),
        winning_violation_jobs: c.violationJobsWon,
      };
    }
    case "pipeline": {
      const byId = new Map(snap.leads.map((l) => [l.id, l]));
      const now = Date.now();
      const rows = [...statuses.values()].map((s) => {
        const l = byId.get(s.leadId);
        return {
          lead: l ? compactLead(l, ctx) : { id: s.leadId, note: "no longer in this week's data" },
          status: STATUS_LABEL[s.status],
          note: s.note,
          days_since_update: Math.floor((now - s.updatedAt.getTime()) / 86_400_000),
        };
      });
      return {
        counts: leadStatusCounts(statuses),
        overdue_follow_ups: rows.filter((r) => r.status === "Contacted" && r.days_since_update >= LEAD_FOLLOW_UP_DAYS),
        recent: rows.sort((a, b) => a.days_since_update - b.days_since_update).slice(0, 15),
      };
    }
    case "my_results": {
      const { revenue, rows, permitJobValue } = ctx.outcomes;
      return {
        by_signal: rows,
        close_rates_used: {
          homeowners_by_mail: ctx.rates.individual ?? `${pct(snap.meta.assumptions.winRate.individual)} (default)`,
          companies_and_investors: ctx.rates.company ?? `${pct(snap.meta.assumptions.winRate.company)} (default)`,
        },
        measured_revenue: {
          source: "Job values the user typed on Won leads. Nothing is estimated; won jobs without a value are not counted.",
          won_jobs: revenue.won,
          won_jobs_with_value: revenue.wonWithValue,
          total_won_value_usd: revenue.wonWithValue > 0 ? revenue.totalWonValue : null,
          median_job_value_usd: revenue.medianJobValue,
          leads_worked: revenue.worked,
          revenue_per_worked_lead_usd: revenue.revenuePerWorkedLead,
          by_signal: rows
            .filter((r) => r.won > 0)
            .map((r) => ({
              signal: r.label,
              won: r.won,
              won_with_value: r.wonWithValue,
              total_won_value_usd: r.wonWithValue > 0 ? r.totalWonValue : null,
              median_job_value_usd: r.medianJobValue,
              revenue_per_worked_lead_usd: r.revenuePerWorkedLead,
              expected_value_job_value: r.jobValueMeasured
                ? `measured median ${r.medianJobValue}`
                : `permit-based ${permitJobValue} (needs ${MIN_VALUED_WON} won jobs with a value, has ${r.wonWithValue})`,
            })),
        },
      };
    }
    case "suggested_moves":
      return buildInsights(snap, ws, leadsForWorkspace(snap, ws.trade, ws.areas), statuses, ctx.rates).map((i) => ({
        title: i.title,
        detail: i.detail,
        link: i.href,
      }));
    case "commercial_projects": {
      const projects = snap.commercial.preApplication.projects
        .filter((p) => ws.areas.length === 0 || (p.communityArea !== null && ws.areas.includes(p.communityArea)))
        .slice(0, int(input.limit, 8, 15));
      return {
        base_rate: pct(snap.commercial.preApplication.baseRate, 2),
        projects: projects.map((p) => ({
          address: p.address,
          neighborhood: p.communityArea ? names.get(p.communityArea) : null,
          owner: p.owner,
          chance_of_major_permit_in_180_days: pct(p.probability),
          signals: p.signals,
          recent_gcs: p.recentGcs,
        })),
      };
    }
    case "commercial_opportunities": {
      const { newBusiness, openTrades } = snap.commercial;
      const limit = int(input.limit, 8, 15);
      const days = (lo: number | null, hi: number | null) => (lo === null || hi === null ? null : `${lo.toFixed(0)}-${hi.toFixed(0)}`);
      if (str(input.list) === "new_business") {
        const m = newBusiness.model;
        return {
          what: "Build-out permits at commercial, mixed-use or 7+ unit addresses with no business license in force on the permit date (and none since). A targeting list for sellers to new businesses, not a chance of work for any trade.",
          period: m.period,
          historical_permits: m.signals,
          permits_per_week: m.perWeek,
          new_license_within_a_year: pct(m.rate),
          comparable_addresses_rate: pct(m.matchedRate),
          lift_vs_comparable: `${m.lift.toFixed(1)}x (${liftLabel(m.lift)})`,
          addresses_with_other_recent_permit_rate: pct(m.busyRate),
          lift_vs_those: `${m.liftVsBusy.toFixed(1)}x (${liftLabel(m.liftVsBusy)})`,
          median_days_permit_to_license: m.medianDays,
          middle_half_days: days(m.daysP25, m.daysP75),
          by_address_class: m.byClass.map((c) => ({
            class: c.class,
            permits: c.signals,
            new_license_within_a_year: pct(c.rate),
            comparable_rate: pct(c.matchedRate),
            lift: `${c.lift.toFixed(1)}x (${liftLabel(c.lift)})`,
          })),
          who_arrives_share: m.byGroup.map((g) => ({ business_type: g.group, share: pct(g.share, 0) })),
          current_spaces_total: newBusiness.spacesTotal,
          spaces: newBusiness.spaces.slice(0, limit).map((s) => ({
            address: s.address,
            neighborhood: s.communityArea ? names.get(s.communityArea) : null,
            address_class: s.class,
            permit_date: s.permitDate,
            days_since_permit: s.ageDays,
            permit_cost_usd: s.reportedCost,
            work: s.workDescription,
            contractors: s.contractors.map((c) => `${c.name} (${c.role})`),
            historical_new_license_rate_within_a_year: pct(s.historicalRate),
            also_closed_restaurant: s.alsoClosedRestaurant,
            owner_type: s.owner.company ? "company" : "individual",
            permit_record: s.sourceUrl,
          })),
          csv: "/export/new-business",
          page: "/commercial",
        };
      }
      if (str(input.list) === "open_trades") {
        const m = openTrades.model;
        const labels = new Map(m.byTrade.map((t) => [t.trade, t.label]));
        return {
          what: "Trades that follow a $1M+ new-construction or renovation permit within 540 days, and whether the follow-on contractor was already on the big permit. A targeting list for sellers in the open trades, not a chance of work for any trade.",
          period: m.period,
          historical_big_permits: m.bigPermits,
          big_permits_per_week_all_address_types: m.perWeek,
          any_of_sign_elevator_electrical_follow_on: pct(m.followOnRate, 0),
          lift_vs_addresses_with_100k_to_1m_permit: `${m.liftVsBusy.toFixed(1)}x (${liftLabel(m.liftVsBusy)})`,
          median_days_to_first_follow_on: m.medianDays,
          middle_half_days: days(m.daysP25, m.daysP75),
          by_trade: m.byTrade.map((t) => ({
            trade: t.label,
            big_permits_followed_by_it: pct(t.followOnRate, 0),
            big_permits_with_a_new_contractor: pct(t.newContractorRate, 0),
            follow_on_permits_to_a_new_contractor: t.newShare === null ? null : pct(t.newShare, 0),
            median_days: t.medianDays,
            middle_half_days: days(t.daysP25, t.daysP75),
            lift_vs_busy_addresses: t.liftVsBusy === null ? null : `${t.liftVsBusy.toFixed(1)}x (${liftLabel(t.liftVsBusy)})`,
            mostly_locked_in: t.mostlyLockedIn,
            cohort_permits: t.signals,
          })),
          recent_big_permits_total: openTrades.recentTotal,
          recent_big_permits: openTrades.recent.slice(0, limit).map((b) => ({
            address: b.address,
            neighborhood: b.communityArea ? names.get(b.communityArea) : null,
            address_class: b.class,
            permit_type: b.permitType,
            permit_date: b.permitDate,
            days_since_permit: b.ageDays,
            cost_usd: b.reportedCost,
            work: b.description,
            contractors_on_permit: b.contractors.map((c) => `${c.name} (${c.role})`),
            trades_already_appeared: b.appeared.map((t) => labels.get(t) ?? t),
            permit_record: b.sourceUrl,
          })),
          page: "/commercial",
        };
      }
      return { error: "list must be 'new_business' or 'open_trades'" };
    }
    case "outreach_status":
      return outreachStatus(ctx, leadOutreachSummary(ctx));
    case "draft_email":
      return draftEmail(input, ctx);
    case "call_brief":
      return callBrief(input, ctx);
    case "deals_status":
      return dealsStatus(ctx);
    default:
      return { error: `Unknown tool ${name}` };
  }
}
