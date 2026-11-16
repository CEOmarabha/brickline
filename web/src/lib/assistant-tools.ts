import "server-only";

import { callBrief, draftEmail, outreachStatus } from "@/lib/assistant-outreach";
import { pct } from "@/lib/format";
import { buildInsights } from "@/lib/insights";
import { DEFAULT_FILTERS, queryLeads } from "@/lib/lead-query";
import type { SegmentOutcome } from "@/lib/outcomes";
import {
  areaNames,
  type CloseRates,
  expectedValue,
  type Lead,
  leadsForWorkspace,
  ownerTypeFor,
  type Snapshot,
  tradeProbability,
} from "@/lib/snapshot";
import { type LeadStatusRow, STATUS_LABEL, type Workspace, workspaceLabel } from "@/lib/workspace";

export interface ToolContext {
  snap: Snapshot;
  ws: Workspace;
  /** The signed-in viewer (`viewerId()`), never the client workspace id. Null when nobody is verified. */
  owner: string | null;
  statuses: Map<string, LeadStatusRow>;
  rates: CloseRates;
  outcomes: { rows: SegmentOutcome[] };
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
    description: "Leads this workspace has worked, by status, including follow-ups that are overdue (contacted 21+ days ago).",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "my_results",
    description: "Measured outcomes by signal type and the close rates used in scoring (measured or default).",
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
      "Preparation for a call the founder dials himself to a published business line: opening statement, reason for calling grounded in the data, discovery questions, likely objections with honest answers, suggested next step and compliance reminders. Pass prospect_id (a contractor he pitches) or lead_id (company-owned properties only). Refuses for individual homeowners (mail only) and for prospects marked Not interested. The assistant never places calls.",
    input_schema: {
      type: "object",
      properties: {
        prospect_id: { type: "string", description: "Prospect id such as 'porch-mr-porch', or an exact company name" },
        lead_id: { type: "string" },
      },
    },
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

/** A lead left at Contacted this many days or longer counts as an overdue follow-up. */
const LEAD_FOLLOW_UP_DAYS = 21;

function leadStatusCounts(statuses: Map<string, LeadStatusRow>): Record<string, number> {
  return Object.fromEntries(
    Object.entries(STATUS_LABEL).map(([k, v]) => [v, [...statuses.values()].filter((s) => s.status === k).length]),
  );
}

const daysSince = (d: Date) => Math.floor((Date.now() - d.getTime()) / 86_400_000);

/** This workspace's lead outreach, as the `pipeline` tool counts it, without free-text notes or owner details. */
export function leadOutreachSummary(ctx: ToolContext) {
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
      const open = leadsForWorkspace(snap, ws.trade, []).filter((l) => !statuses.has(l.id));
      const rows = snap.areas
        .filter((a) => (single ? a.id === single : !only || ws.areas.includes(a.id)))
        .map((a) => {
          const sig =
            ws.trade === "general"
              ? { now: a.majorProjects.last90, before: a.majorProjects.lastYear }
              : { now: a.violations[ws.trade]?.last90 ?? 0, before: a.violations[ws.trade]?.lastYear ?? 0 };
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
    case "my_results":
      return {
        by_signal: ctx.outcomes.rows,
        close_rates_used: {
          homeowners_by_mail: ctx.rates.individual ?? `${pct(snap.meta.assumptions.winRate.individual)} (default)`,
          companies_and_investors: ctx.rates.company ?? `${pct(snap.meta.assumptions.winRate.company)} (default)`,
        },
      };
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
    case "outreach_status":
      return outreachStatus(ctx, leadOutreachSummary(ctx));
    case "draft_email":
      return draftEmail(input, ctx);
    case "call_brief":
      return callBrief(input, ctx);
    default:
      return { error: `Unknown tool ${name}` };
  }
}
