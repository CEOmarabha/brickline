"""Opportunity lifecycles: every trigger we can see in public records, the jobs it sets off, and who sells them.

    uv run python -m engine.leads.lifecycles

A lifecycle is a storyline that starts with a public record (a block-party permit, a new-construction permit, a
restaurant closing...) and runs through stages, each needing services that some local company sells. For every
lifecycle this module measures, from the warehouse, how often the trigger happened in the last 365 days; for every
service, how many Chicago businesses Overture lists in matching categories (the companies to connect or sell to)
and, where public data shows it, how often the job is already covered by a named company (the incumbent).

Writes web/data/lifecycles.json (the app's /opportunities page; counts and descriptions only, no names) and
research/findings/lifecycles-<as-of>.md. Read-only on the warehouse; deterministic. docs/20 tells the stories.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from engine import db
from engine.score.signals import INVESTOR_RE

OUT = Path("web/data/lifecycles.json")
SNAPSHOT = Path("web/data/snapshot.json")
FINDINGS = Path("research/findings")

# Overture categories (primary or alternate) of the companies that sell each service.
VENDORS: dict[str, tuple[str, str]] = {
    "event_planner": ("Event planners", r"party_and_event_planning|event_or_party_service|wedding_planning"),
    "party_rentals": (
        "Party and equipment rentals (tables, chairs, tents)",
        r"party_equipment_rental|^rental_service|machine_and_tool_rental|kids_recreation_and_party",
    ),
    "linen": ("Linen and laundry services", r"linen|laundry_service|uniform"),
    "florist": ("Florists", r"florist|flowers_and_gifts"),
    "caterer": ("Caterers and food trucks", r"caterer|food_truck|food_service|barbecue_restaurant"),
    "bakery": ("Bakeries and cakes", r"bakery|cupcake|cake"),
    "music": ("DJs and musicians", r"dj_service|musician|music_production"),
    "photo_video": (
        "Photographers, videographers, photo booths",
        r"event_photography|session_photography|photography_service|videographer|video_film_production|photo_booth",
    ),
    "decor_balloons": (
        "Decor, balloons and party supplies",
        r"party_supply|balloon|home_decor|interior_design",
    ),
    "av_stage": ("Sound, lighting and stage", r"audiovisual|audio_visual|event_technology|lighting"),
    "venue": ("Event venues", r"event_venue|music_venue|banquet|festival_venue"),
    "security": ("Security and guards", r"security_service"),
    "transport": ("Valet, limo, party bus", r"valet|limo|party_bus"),
    "sanitation": (
        "Portable toilets and event waste",
        r"portable|garbage_collection|b2b_cleaning_and_waste|recycling",
    ),
    "printing_signs": (
        "Printing, signs and banners",
        r"printing|commercial_printer|sign_making|b2b_promotional",
    ),
    "cleaning_home": ("Residential cleaning", r"home_cleaning|carpet_cleaning|cleaning_service"),
    "cleaning_commercial": (
        "Commercial and janitorial cleaning",
        r"janitorial|office_cleaning|window_washing|cleaning_service",
    ),
    "junk_dumpster": (
        "Junk removal, dumpsters and hauling",
        r"junk_removal|garbage_collection|junkyard|b2b_cleaning_and_waste",
    ),
    "restoration": ("Water, fire and mold restoration", r"damage_restoration|fire_and_water|mold"),
    "pest_control": ("Pest control", r"pest_control"),
    "gc": (
        "General contractors and remodelers",
        r"building_or_construction_service|general_contractor|kitchen_remodeling|home_service",
    ),
    "demolition": ("Demolition and excavation", r"demolition|excavation"),
    "masonry": ("Masonry and concrete", r"masonry|concrete"),
    "roofing": ("Roofing and gutters", r"roofing|gutter"),
    "plumbing": ("Plumbers", r"plumbing"),
    "electrical": ("Electricians", r"electrician"),
    "hvac": ("Heating, cooling and duct cleaning", r"hvac|air_duct"),
    "finishes": ("Painting and flooring", r"^painting|flooring|carpet_store"),
    "windows_doors": (
        "Windows, doors and glass",
        r"windows_installation|window_supplier|glass_and_mirror|door_sales|garage_door",
    ),
    "landscaping": ("Landscaping, trees and snow", r"landscaping|lawn_service|tree_service|snow_removal"),
    "fencing": ("Fencing", r"fence"),
    "design": (
        "Architects, engineers and surveyors",
        r"architect|engineering_service|structural_engineer|civil_engineer|land_surveying",
    ),
    "inspection": ("Home inspectors and appraisers", r"home_inspector|appraisal"),
    "locks_alarms": ("Locksmiths and alarm systems", r"locksmith|security_systems"),
    "movers": ("Movers, storage and truck rental", r"^mover|self_storage|storage_facility|truck_rental"),
    "property_mgmt": ("Property managers", r"property_management"),
    "real_estate": (
        "Real estate agents and brokers",
        r"real_estate_agent|real_estate_service|commercial_real_estate",
    ),
    "insurance": ("Insurance agents", r"insurance"),
    "it_telecom": ("IT, internet and phones", r"it_service|internet_service_provider|telecommunications"),
    "furniture": ("Furniture and office supply", r"furniture_store|furniture_assembly|office_supply"),
    "elevator_fire": ("Elevator and fire protection", r"elevator|fire_protection"),
    "kitchen_equipment": ("Kitchen equipment and appliances", r"kitchen_supply|appliance"),
}


@dataclass(frozen=True)
class Service:
    name: str
    vendor: str  # key in VENDORS
    incumbent: str = "Not visible in public data: ask, or offer to match the current provider."
    metric: str | None = None  # key in measured incumbent metrics


@dataclass(frozen=True)
class Stage:
    name: str
    when: str
    services: tuple[Service, ...]


@dataclass(frozen=True)
class Lifecycle:
    id: str
    family: str  # events | property | business | cleanup
    name: str
    story: str
    trigger: str
    source: str
    volume: str | None  # key in measured volumes
    notice: str
    buyer: str
    reach: str
    stages: tuple[Stage, ...]
    app_link: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


S = Service
NAMED_ON_PERMIT = "Named on the building permit when a permit covers the work."

LIFECYCLES: tuple[Lifecycle, ...] = (
    # ------------------------------------------------------------------ events
    Lifecycle(
        "block_party",
        "events",
        "Block party",
        "A neighbor files a block-party permit about a month ahead. In the weeks before, the host lines up tables, "
        "chairs and a tent, a bounce house, a DJ, food and drinks; on the day there may be a photographer and ice; "
        "the next morning the street needs cleaning and the trash hauled. Most blocks that held a party do it "
        "again the next summer, so last year's hosts are next year's leads months before they file.",
        "CDOT block-party permit (host name and mailing address on the application)",
        "CDOT pubx-yq2d",
        "block_party",
        "Filed a median 32 days ahead; repeat blocks known a year ahead (see hosts list)",
        "The host (a private person)",
        "Letter or door hanger to the host's mailing address; manual call or text only after a skip trace and a "
        "Do Not Call scrub (D-027)",
        (
            Stage(
                "Planning",
                "4-6 weeks before",
                (
                    S("Event planning or a party package", "event_planner"),
                    S("Printed flyers for the block", "printing_signs"),
                ),
            ),
            Stage(
                "Rentals and food",
                "1-2 weeks before",
                (
                    S("Tables, chairs, tents, bounce house", "party_rentals"),
                    S("Catering, grill, food truck", "caterer"),
                    S("Cake and desserts", "bakery"),
                    S("Balloons and decor", "decor_balloons"),
                ),
            ),
            Stage(
                "Day of",
                "event day",
                (
                    S("DJ or band", "music"),
                    S("Photographer or photo booth", "photo_video"),
                ),
            ),
            Stage("After", "next day", (S("Street and yard cleanup, trash hauling", "junk_dumpster"),)),
        ),
        app_link="/events",
        tags=("small", "private host", "seasonal"),
    ),
    Lifecycle(
        "street_festival",
        "events",
        "Street festival, parade or race",
        "An organization (chamber, church, nonprofit, promoter) files a festival, parade or athletic permit about "
        "two months ahead. The event needs stages, sound, tents, fencing, portable toilets, security, food vendors "
        "and printing before, staffing on the day, and cleanup and waste hauling after. The same organizers come "
        "back every year.",
        "CDOT festival, parade, athletic and assembly permits",
        "CDOT pubx-yq2d",
        "street_festival",
        "Festivals visible a median 59 days ahead; recurring series known the season before",
        "The organizing organization",
        "Business phone, email or website of the organizer (organizations only on the list)",
        (
            Stage(
                "Production",
                "1-3 months before",
                (
                    S("Event production and planning", "event_planner"),
                    S("Stage, sound and lighting", "av_stage"),
                    S("Tents, tables, fencing and generators", "party_rentals"),
                    S("Signs, banners and printing", "printing_signs"),
                ),
            ),
            Stage(
                "Site services",
                "event week",
                (
                    S("Portable toilets and waste stations", "sanitation"),
                    S("Security staff", "security"),
                    S("Food vendors and caterers", "caterer"),
                ),
            ),
            Stage("After", "next day", (S("Site cleanup and waste hauling", "junk_dumpster"),)),
        ),
        app_link="/events",
        tags=("organization", "recurring"),
    ),
    Lifecycle(
        "park_wedding",
        "events",
        "Wedding or party at a Park District venue",
        "A couple or family reserves a Park District field house or garden for a wedding or celebration. The "
        "reservation shows the venue and date; the hosts still need flowers, linens, decor, catering, a cake, music, "
        "a photographer, transport and cleanup. Park reservations appear late (median days after the start), so "
        "this works through venue partnerships rather than the open data.",
        "Park District venue rentals (wedding, social)",
        "Chicago Park District pk66-w54g",
        "park_wedding",
        "Listed late in the open data; venues know months ahead",
        "The couple or family (private persons, not named in the data)",
        "Partner with the venues; the open data has no host contact",
        (
            Stage(
                "Planning",
                "3-9 months before",
                (
                    S("Wedding and party planners", "event_planner"),
                    S("Florals", "florist"),
                    S("Linens and decor", "linen"),
                    S("Catering and bar", "caterer"),
                    S("Cake", "bakery"),
                ),
            ),
            Stage(
                "Day of",
                "event day",
                (
                    S("DJ or band", "music"),
                    S("Photo and video", "photo_video"),
                    S("Limo, party bus or valet", "transport"),
                ),
            ),
            Stage("After", "next day", (S("Venue cleanup", "cleaning_commercial"),)),
        ),
        app_link="/events",
        tags=("private host", "venue partner"),
    ),
    Lifecycle(
        "org_special_event",
        "events",
        "Fair or fundraiser with one-day food and drink licenses",
        "Fairs, church festivals and fundraisers bring in vendors who each take a one-day Special Event Food or "
        "Liquor license. The license shows up only days ahead, and most holders are the vendors themselves: of 393 "
        "that held one in 2+ of the last 3 years, 291 are restaurants, 44 food trucks and 35 bars or breweries; 23 "
        "are organizers. So this list is mostly partners to recruit (they want the event calendar), and the events "
        "themselves come from the festival permits.",
        "City Special Event Food and Special Event Liquor licenses",
        "Chicago business licenses r5kz-chrr",
        "special_event",
        "License a median 6 days ahead; repeat vendors known a year ahead",
        "The vendor (restaurant, truck, bar) and the event organizer",
        "Business phone, email or website",
        (
            Stage(
                "Planning",
                "1-2 months before (repeat holders)",
                (
                    S("Tents, tables and generators", "party_rentals"),
                    S("Food and drink supply, catering", "caterer"),
                    S("Printing and signs", "printing_signs"),
                ),
            ),
            Stage(
                "Day of",
                "event day",
                (
                    S("Portable toilets and waste", "sanitation"),
                    S("Security", "security"),
                ),
            ),
            Stage("After", "next day", (S("Cleanup", "junk_dumpster"),)),
        ),
        tags=("organization", "recurring"),
    ),
    Lifecycle(
        "grand_opening",
        "events",
        "Grand opening of a new business",
        "A build-out permit at an empty storefront predicts a new business license about five months later. "
        "Before opening the tenant buys signs, cleaning, insurance, internet and furniture; at opening it throws a "
        "ribbon cutting with balloons, flowers, food and a photographer.",
        "Build-out permit at a space with no license in force (signal lab H33)",
        "Chicago permits and licenses",
        "new_business",
        "Median 157 days from build-out permit to license (H33)",
        "The incoming business (often named on the permit)",
        "Business phone, email or website",
        (
            Stage(
                "Pre-opening",
                "1-5 months before",
                (
                    S("Signs and storefront graphics", "printing_signs"),
                    S("Post-construction cleaning", "cleaning_commercial"),
                    S("Internet, phones and IT", "it_telecom"),
                    S("Furniture and fixtures", "furniture"),
                    S("Insurance", "insurance"),
                    S("Alarm system and locks", "locks_alarms"),
                ),
            ),
            Stage(
                "Opening event",
                "opening week",
                (
                    S("Balloons and decor", "decor_balloons"),
                    S("Flowers", "florist"),
                    S("Catering", "caterer"),
                    S("Photographer", "photo_video"),
                ),
            ),
            Stage(
                "Running",
                "after opening",
                (
                    S("Recurring janitorial", "cleaning_commercial"),
                    S("Pest control contract", "pest_control"),
                ),
            ),
        ),
        app_link="/commercial",
        tags=("organization", "proven signal"),
    ),
    # ------------------------------------------------------------------ property and construction
    Lifecycle(
        "new_construction",
        "property",
        "New building, from zoning to move-in",
        "A zoning change is introduced (a median 313 days before the new-construction permit, H34), the old "
        "building comes down, and the new one goes up trade by trade: survey and design, demolition and "
        "excavation, foundation and masonry, framing and roofing, plumbing, electrical and HVAC, windows, drywall, "
        "paint and floors, landscaping and fencing. Dumpsters and portable toilets serve the whole job, then "
        "post-construction cleaning, and finally the new owners or tenants need movers, internet and property "
        "management. Permits name the general contractor and many trades, so the incumbent is often visible.",
        "Zoning reclassification, wrecking permit, new-construction permit",
        "City Clerk, Chicago permits",
        "new_construction",
        "Zoning ~10 months before the permit; permit issued before work starts",
        "Developer or owner, then the general contractor",
        "Business contacts of the GC and developer",
        (
            Stage(
                "Pre-construction",
                "before the permit",
                (
                    S(
                        "Architects, engineers, surveyors",
                        "design",
                        NAMED_ON_PERMIT,
                        "new_construction:architect",
                    ),
                    S(
                        "Demolition and excavation",
                        "demolition",
                        "The wrecking contractor is the contractor named on the wrecking permit.",
                        "wrecking:gc",
                    ),
                ),
            ),
            Stage(
                "Structure",
                "months 1-4",
                (
                    S("General contractor", "gc", NAMED_ON_PERMIT, "new_construction:gc"),
                    S("Masonry and concrete", "masonry", NAMED_ON_PERMIT, "new_construction:masonry"),
                    S("Roofing", "roofing"),
                    S(
                        "Dumpsters and hauling",
                        "junk_dumpster",
                        "Named on the CDOT dumpster permit (the hauler).",
                        "dumpster:hauler",
                    ),
                    S("Fencing and site security", "fencing"),
                ),
            ),
            Stage(
                "Systems and finishes",
                "months 3-9",
                (
                    S("Electrical", "electrical", NAMED_ON_PERMIT, "new_construction:electrical"),
                    S("Plumbing", "plumbing", NAMED_ON_PERMIT, "new_construction:plumbing"),
                    S("HVAC", "hvac", NAMED_ON_PERMIT, "new_construction:hvac"),
                    S("Windows and doors", "windows_doors"),
                    S("Paint and flooring", "finishes"),
                ),
            ),
            Stage(
                "Close-out",
                "last month",
                (
                    S("Post-construction cleaning", "cleaning_commercial"),
                    S("Landscaping", "landscaping"),
                    S("Alarm system and locks", "locks_alarms"),
                ),
            ),
            Stage(
                "Occupancy",
                "after completion",
                (
                    S("Property management", "property_mgmt"),
                    S("Movers", "movers"),
                    S("Internet and phones", "it_telecom"),
                ),
            ),
        ),
        app_link="/commercial",
        tags=("organization", "incumbent visible"),
    ),
    Lifecycle(
        "investor_rehab",
        "property",
        "Investor buys, rehabs and resells or rents",
        "A company buys a house or flat (state transfer forms show it within about two weeks). It changes the "
        "locks, clears out the previous owner's things, pulls a permit a median 83-94 days after the sale, guts and "
        "rebuilds with a GC and trades, cleans and stages, then lists it for sale or rent and hands it to a "
        "property manager. A third of these buyers reuse a GC they used before.",
        "Company purchase (PTAX-203 transfer form, Assessor sales)",
        "Illinois PTAX-203, Cook County Assessor",
        "investor",
        "Days after recording; first permit a median 83-94 days after the sale",
        "The buying company",
        "Mailing address from the tax roll; business contacts where listed",
        (
            Stage(
                "Takeover",
                "weeks 0-4",
                (
                    S("Locksmith (rekey)", "locks_alarms"),
                    S("Cleanout and junk removal", "junk_dumpster"),
                    S("Insurance (vacant or builder's risk)", "insurance"),
                    S("Inspection and appraisal", "inspection"),
                ),
            ),
            Stage(
                "Rehab",
                "months 1-6",
                (
                    S(
                        "General contractor",
                        "gc",
                        "Named on the permit; 31% of buyers name a GC they used before.",
                        "renovation:gc",
                    ),
                    S("Electrical, plumbing, HVAC", "electrical", NAMED_ON_PERMIT, "renovation:electrical"),
                    S("Paint and flooring", "finishes"),
                    S(
                        "Dumpster",
                        "junk_dumpster",
                        "Named on the CDOT dumpster permit (the hauler).",
                        "dumpster:hauler",
                    ),
                ),
            ),
            Stage(
                "Exit",
                "months 4-9",
                (
                    S("Final cleaning", "cleaning_home"),
                    S("Staging and photos", "photo_video"),
                    S("Listing broker", "real_estate"),
                    S("Property management (rentals)", "property_mgmt"),
                ),
            ),
        ),
        app_link="/leads",
        tags=("organization", "proven signal"),
    ),
    Lifecycle(
        "code_repair",
        "property",
        "Owner ordered to make repairs",
        "A city inspector cites a porch, masonry or roof; often a 311 complaint came a month earlier. The owner "
        "needs a contractor, sometimes an engineer and an expediter for the permit, and a dumpster; 15% of porch "
        "citations lead to a permitted repair within a year (most within six months).",
        "Building violation, 311 building complaint",
        "Chicago violations and 311",
        "violation",
        "Complaint ~33 days before the citation; repair permit ~172 days after",
        "Property owner (mostly private persons)",
        "Letter with the not-a-bill box; phone after skip trace + DNC scrub",
        (
            Stage(
                "Diagnosis",
                "weeks 0-4",
                (
                    S(
                        "Engineer or architect (porch drawings)",
                        "design",
                        NAMED_ON_PERMIT,
                        "renovation:architect",
                    ),
                    S("Inspection", "inspection"),
                ),
            ),
            Stage(
                "Repair",
                "months 1-6",
                (
                    S(
                        "Porch, masonry or roofing contractor",
                        "masonry",
                        NAMED_ON_PERMIT,
                        "renovation:masonry",
                    ),
                    S("General contractor", "gc", NAMED_ON_PERMIT, "renovation:gc"),
                    S("Dumpster", "junk_dumpster"),
                ),
            ),
            Stage("After", "after the repair", (S("Cleanup and painting", "finishes"),)),
        ),
        app_link="/leads",
        tags=("private host", "proven signal"),
    ),
    Lifecycle(
        "vacant_building",
        "property",
        "Vacant building to sale and rehab",
        "Neighbors report a vacant building to 311. The owner needs it boarded and secured, the yard cleared and "
        "the building insured; 19% sell within a year, which starts the investor rehab story.",
        "311 vacant/abandoned building complaint",
        "Chicago 311",
        "vacant",
        "Sale a median 167 days after the complaint (19.4% within a year)",
        "Property owner",
        "Letter; phone after skip trace + DNC scrub",
        (
            Stage(
                "Securing",
                "weeks 0-8",
                (
                    S("Board-up, fencing, locks", "fencing"),
                    S("Cleanout and junk removal", "junk_dumpster"),
                    S("Vacant-building insurance", "insurance"),
                    S("Lawn and snow upkeep", "landscaping"),
                ),
            ),
            Stage("Sale", "months 2-12", (S("Broker", "real_estate"),)),
        ),
        app_link="/leads",
        tags=("proven signal",),
    ),
    Lifecycle(
        "home_sale",
        "property",
        "Household moves (home sold to a person)",
        "A family buys a home. Before and after closing they need an inspector, movers, cleaning of the old and "
        "new place, locks changed, internet, often paint and floors, then furniture.",
        "Residential sale to an individual (transfer form or Assessor sale)",
        "Illinois PTAX-203, Cook County Assessor",
        "home_sale",
        "Days after recording (PTAX); closing has already happened",
        "The buyer (private person)",
        "Letter to the property; no public phone or email",
        (
            Stage(
                "Move",
                "weeks 0-4",
                (
                    S("Movers and storage", "movers"),
                    S("Move-out and move-in cleaning", "cleaning_home"),
                    S("Locksmith", "locks_alarms"),
                    S("Internet", "it_telecom"),
                ),
            ),
            Stage(
                "Settle in",
                "months 1-6",
                (
                    S("Painting and flooring", "finishes"),
                    S("Furniture", "furniture"),
                    S("Landscaping", "landscaping"),
                ),
            ),
        ),
        tags=("private host",),
    ),
    # ------------------------------------------------------------------ business
    Lifecycle(
        "restaurant_opening",
        "business",
        "Restaurant opening",
        "A restaurant build-out permit is issued, the kitchen hood and grease trap go in, the health department "
        "does a pre-opening inspection about two weeks before the food license, and the place opens. Every step "
        "needs a vendor, and after opening the restaurant signs recurring contracts: pest control, hood cleaning, "
        "grease-trap pumping, linens, waste hauling and cleaning.",
        "Build-out permit, pre-opening 'License' food inspection, new retail food license",
        "Chicago permits, inspections, licenses",
        "restaurant_opening",
        "Build-out permit months ahead; pre-opening inspection ~14 days before the license",
        "Restaurant owner or operator",
        "Business phone, email or website",
        (
            Stage(
                "Build-out",
                "1-5 months before",
                (
                    S("General contractor", "gc", NAMED_ON_PERMIT, "renovation:gc"),
                    S("Kitchen equipment", "kitchen_equipment"),
                    S("Plumbing and grease trap", "plumbing", NAMED_ON_PERMIT, "renovation:plumbing"),
                    S("Hood, ventilation and HVAC", "hvac", NAMED_ON_PERMIT, "renovation:hvac"),
                    S("Signs", "printing_signs"),
                ),
            ),
            Stage(
                "Pre-opening",
                "last month",
                (
                    S("Post-construction cleaning", "cleaning_commercial"),
                    S("Insurance", "insurance"),
                    S("POS, internet and phones", "it_telecom"),
                ),
            ),
            Stage(
                "Recurring",
                "after opening",
                (
                    S("Pest control", "pest_control"),
                    S("Linen service", "linen"),
                    S("Janitorial", "cleaning_commercial"),
                    S("Waste hauling", "junk_dumpster"),
                ),
            ),
        ),
        app_link="/commercial",
        tags=("organization",),
    ),
    Lifecycle(
        "restaurant_closure",
        "business",
        "Restaurant closes, space re-tenants",
        "An inspector records a restaurant 'out of business'. The landlord clears the space, sells or scraps the "
        "equipment, lists it, and a third of the time a new food business is licensed there within a year, which "
        "starts a new build-out and a new opening.",
        "'Out of Business' food inspection (signal lab H26)",
        "Chicago food inspections",
        "closed_restaurant",
        "New license at the address 32% within a year, median 19 days",
        "Property owner, then the next tenant",
        "Letter to the owner; business contacts of the next tenant",
        (
            Stage(
                "Turnover",
                "weeks 0-8",
                (
                    S("Cleanout and equipment removal", "junk_dumpster"),
                    S("Deep cleaning", "cleaning_commercial"),
                    S("Commercial broker", "real_estate"),
                ),
            ),
            Stage(
                "Next tenant",
                "months 1-12",
                (
                    S("Build-out GC", "gc", NAMED_ON_PERMIT, "renovation:gc"),
                    S("Kitchen equipment", "kitchen_equipment"),
                ),
            ),
        ),
        app_link="/commercial",
        tags=("proven signal",),
    ),
    Lifecycle(
        "business_move",
        "business",
        "Business moves to a new location",
        "A licensed business changes location (the license history records it). The move needs movers, IT and "
        "phone setup, signs, cleaning of both spaces, furniture and an alarm system, and often an opening event.",
        "Business license change of location (C_LOC)",
        "Chicago business licenses r5kz-chrr",
        "business_move",
        "Recorded when the license moves (around the move)",
        "The business",
        "Business phone, email or website",
        (
            Stage(
                "Move",
                "around the move date",
                (
                    S("Commercial movers", "movers"),
                    S("IT, internet and phones", "it_telecom"),
                    S("Signs", "printing_signs"),
                    S("Move-out and move-in cleaning", "cleaning_commercial"),
                    S("Furniture", "furniture"),
                    S("Alarm and locks", "locks_alarms"),
                ),
            ),
            Stage(
                "Opening", "first month", (S("Opening event: balloons, flowers, catering", "decor_balloons"),)
            ),
        ),
        tags=("organization",),
    ),
    Lifecycle(
        "big_commercial_project",
        "business",
        "Large commercial project ($1M+ permit)",
        "A $1M+ permit is issued. The trades on the permit start; 62% of these sites add a sign, elevator or "
        "electrical permit within 18 months, mostly with contractors not on the first permit. At the end the "
        "building needs post-construction and window cleaning, security, janitorial and fire protection contracts.",
        "Permit with a reported cost of $1M or more (signal lab H29)",
        "Chicago permits",
        "big_permit",
        "Follow-on trades within 540 days (62%)",
        "Owner and GC",
        "Business contacts of the GC and owner",
        (
            Stage(
                "Follow-on trades",
                "months 1-18",
                (
                    S(
                        "Elevator and fire alarm",
                        "elevator_fire",
                        "Named on its own later permit; on $1M+ sites the follow-on contractor is usually not one on the first permit (H29).",
                    ),
                    S(
                        "Signs",
                        "printing_signs",
                        "Named on its own later permit; on $1M+ sites the follow-on contractor is usually not one on the first permit (H29).",
                    ),
                    S("Electrical", "electrical", NAMED_ON_PERMIT, "big_permit:electrical"),
                ),
            ),
            Stage(
                "Turnover",
                "completion",
                (
                    S("Post-construction and window cleaning", "cleaning_commercial"),
                    S("Security", "security"),
                    S("Janitorial contract", "cleaning_commercial"),
                ),
            ),
        ),
        app_link="/commercial",
        tags=("organization", "incumbent visible"),
    ),
    # ------------------------------------------------------------------ cleanup
    Lifecycle(
        "basement_flood",
        "cleanup",
        "Basement flood to restoration",
        "After heavy rain residents file 'water in basement' complaints. The household needs water extraction, "
        "drying and mold work, hauling of ruined contents, a plumber for the backflow or sewer, and sometimes "
        "insurance help. Permits rarely follow (signal lab H06 found no permit signal), so this is a cleanup and "
        "restoration lead, not a construction one.",
        "311 'Water in Basement' complaint",
        "Chicago 311",
        "basement_flood",
        "Same day to days after the storm",
        "Household (private person)",
        "Letter or door hanger; phone after skip trace + DNC scrub",
        (
            Stage(
                "Emergency",
                "days 0-3",
                (
                    S("Water extraction and drying", "restoration"),
                    S("Hauling of ruined contents", "junk_dumpster"),
                ),
            ),
            Stage(
                "Repair",
                "weeks 1-6",
                (
                    S("Plumber (backflow, sewer)", "plumbing"),
                    S("Drywall, paint and floors", "finishes"),
                ),
            ),
        ),
        tags=("private host", "cleanup"),
    ),
    Lifecycle(
        "demolition_cleanup",
        "cleanup",
        "Demolition and construction cleanup",
        "A wrecking permit is issued. The site needs a wrecking contractor, dumpsters and hauling, fencing, then "
        "a cleared lot or the start of new construction. Construction sites need rough, final and touch-up "
        "cleaning, and neighbors' properties sometimes need cleanup too.",
        "Wrecking/demolition permit, CDOT dumpster permit",
        "Chicago permits, CDOT pubx-yq2d",
        "wrecking",
        "Permit issued before work starts",
        "Owner, developer or wrecking contractor",
        "Business contacts",
        (
            Stage(
                "Demolition",
                "weeks 0-4",
                (
                    S(
                        "Wrecking contractor",
                        "demolition",
                        "The wrecking contractor is the contractor named on the wrecking permit.",
                        "wrecking:gc",
                    ),
                    S(
                        "Dumpsters and hauling",
                        "junk_dumpster",
                        "Named on the CDOT dumpster permit (the hauler).",
                        "dumpster:hauler",
                    ),
                    S("Fencing", "fencing"),
                ),
            ),
            Stage(
                "Construction cleaning",
                "end of the build",
                (S("Rough, final and touch-up cleaning", "cleaning_commercial"),),
            ),
        ),
        tags=("organization", "cleanup", "incumbent visible"),
    ),
    Lifecycle(
        "pest_complaint",
        "cleanup",
        "Rats and pests",
        "Residents file rodent complaints; restaurants get pest findings on inspections. The household or "
        "landlord needs pest control and often sealing, cleanup and garbage containers; restaurants need a "
        "service contract.",
        "311 rodent complaint, food inspection pest finding",
        "Chicago 311, food inspections",
        "rodent",
        "Same week",
        "Household, landlord or restaurant",
        "Letter to the owner; business contacts for restaurants",
        (
            Stage(
                "Treatment",
                "weeks 0-2",
                (
                    S("Pest control", "pest_control"),
                    S("Cleanup and junk removal", "junk_dumpster"),
                ),
            ),
        ),
        app_link="/pilots/pest",
        tags=("cleanup",),
    ),
)

# Stage timing in days relative to the event or trigger date (negative = before), for dated timelines on the
# event board. Event lifecycles only; [H] industry rules of thumb, not measured.
STAGE_OFFSETS: dict[tuple[str, str], tuple[int, int]] = {
    ("block_party", "Planning"): (-42, -28),
    ("block_party", "Rentals and food"): (-14, -7),
    ("block_party", "Day of"): (0, 0),
    ("block_party", "After"): (1, 1),
    ("street_festival", "Production"): (-90, -30),
    ("street_festival", "Site services"): (-7, 0),
    ("street_festival", "After"): (1, 2),
    ("park_wedding", "Planning"): (-270, -90),
    ("park_wedding", "Day of"): (0, 0),
    ("park_wedding", "After"): (1, 1),
    ("org_special_event", "Planning"): (-60, -30),
    ("org_special_event", "Day of"): (0, 0),
    ("org_special_event", "After"): (1, 1),
    ("grand_opening", "Pre-opening"): (-150, -30),
    ("grand_opening", "Opening event"): (-7, 0),
    ("grand_opening", "Running"): (30, 90),
}

# Volumes: how often each trigger happened in the 365 days before its source's newest record.
VOLUME_SQL: dict[str, str] = {
    "block_party": """SELECT count(*) FROM street_events WHERE worktype = 'BlockParty'
        AND start_date > (SELECT max(processed_date) FROM street_events) - INTERVAL 365 DAY
        AND start_date <= (SELECT max(processed_date) FROM street_events)""",
    "street_festival": """SELECT count(*) FROM street_events WHERE worktype IN ('Festival', 'Parade', 'Athletic')
        AND start_date > (SELECT max(processed_date) FROM street_events) - INTERVAL 365 DAY
        AND start_date <= (SELECT max(processed_date) FROM street_events)""",
    "park_wedding": """SELECT count(*) FROM park_events WHERE event_type IN ('Venue Rental - Wedding', 'Venue Rental - Social')
        AND start_date > (SELECT max(listed_date) FROM park_events) - INTERVAL 365 DAY
        AND start_date <= (SELECT max(listed_date) FROM park_events)""",
    "special_event": """SELECT count(*) FROM biz_license_history
        WHERE license_description IN ('Special Event Food', 'Special Event Liquor')
        AND start_date > (SELECT max(issue_date) FROM biz_license_history) - INTERVAL 365 DAY""",
    "restaurant_opening": """SELECT count(*) FROM food_licenses
        WHERE issue_date > (SELECT max(issue_date) FROM food_licenses) - INTERVAL 365 DAY""",
    "business_move": """SELECT count(*) FROM biz_license_history WHERE application_type = 'C_LOC'
        AND issue_date > (SELECT max(issue_date) FROM biz_license_history) - INTERVAL 365 DAY""",
    "new_construction": """SELECT count(*) FROM permits WHERE permit_type = 'PERMIT - NEW CONSTRUCTION'
        AND issue_date > (SELECT max(issue_date) FROM permits) - INTERVAL 365 DAY""",
    "wrecking": """SELECT count(*) FROM permits WHERE permit_type = 'PERMIT - WRECKING/DEMOLITION'
        AND issue_date > (SELECT max(issue_date) FROM permits) - INTERVAL 365 DAY""",
    "big_permit": """SELECT count(*) FROM permits WHERE reported_cost >= 1000000
        AND issue_date > (SELECT max(issue_date) FROM permits) - INTERVAL 365 DAY""",
    "home_sale": f"""SELECT count(*) FROM ptax_transfers WHERE exemption IS NULL AND price >= 10000
        AND coalesce(instrument_type, '') NOT IN ('Quit Claim Deed', 'Executor Deed')
        AND coalesce(total_parcels, 1) = 1 AND NOT additional_pins AND right(pin, 4) = '0000'
        AND NOT regexp_matches(upper(coalesce(buyer_name, '')), '{INVESTOR_RE}')
        AND recorded_date > (SELECT max(recorded_date) FROM ptax_transfers) - INTERVAL 365 DAY""",
    "vacant": """SELECT count(*) FROM sr311 WHERE sr_type = 'Vacant/Abandoned Building Complaint' AND NOT duplicate
        AND created_date > (SELECT max(created_date) FROM sr311) - INTERVAL 365 DAY""",
    "basement_flood": """SELECT count(*) FROM sr311 WHERE sr_type = 'Water in Basement Complaint' AND NOT duplicate
        AND created_date > (SELECT max(created_date) FROM sr311) - INTERVAL 365 DAY""",
    "rodent": """SELECT count(*) FROM sr311 WHERE sr_type = 'Rodent Baiting/Rat Complaint' AND NOT duplicate
        AND created_date > (SELECT max(created_date) FROM sr311) - INTERVAL 365 DAY""",
}
VOLUME_NOTE = {
    "home_sale": "Non-condo sales to non-company buyers on state transfer forms recorded in the last 365 days.",
    "investor": "Open investor leads in the snapshot (240-day window; ~74 a week recently).",
    "violation": "Open violation leads in the snapshot (150-day window, all trades).",
    "closed_restaurant": "Open closed-restaurant leads in the snapshot (180-day window).",
    "new_business": "Current spaces on the 'New business coming' list.",
}
ROLE_PERMIT_TYPES = {
    "new_construction": "permit_type = 'PERMIT - NEW CONSTRUCTION'",
    "renovation": "permit_type = 'PERMIT - RENOVATION/ALTERATION'",
    "wrecking": "permit_type = 'PERMIT - WRECKING/DEMOLITION'",
    "big_permit": "reported_cost >= 1000000",
}
ROLES = ("gc", "electrical", "plumbing", "hvac", "masonry", "architect", "wrecking", "elevator", "sign")


def measure_incumbents(con) -> dict[str, float]:
    """Share of permits (last 730 days) that name a party in each role, by permit group; hauler on dumpster permits."""
    out: dict[str, float] = {}
    for group, where in ROLE_PERMIT_TYPES.items():

        def named(role: str) -> str:
            roles = "('gc', 'owner_gc')" if role == "gc" else f"('{role}')"
            return f"avg((EXISTS (SELECT 1 FROM permit_parties pp WHERE pp.permit_id = p.id AND pp.role IN {roles}))::INT)"

        cols = ", ".join(f"{named(r)} AS {r}" for r in ROLES)
        row = con.execute(f"""
            SELECT {cols} FROM permits p
            WHERE {where} AND issue_date > (SELECT max(issue_date) FROM permits) - INTERVAL 730 DAY
        """).fetchone()
        for r, v in zip(ROLES, row, strict=True):
            out[f"{group}:{r}"] = round(v or 0.0, 4)
    out["dumpster:hauler"] = round(
        con.execute("""
            SELECT avg((hauler IS NOT NULL)::INT) FROM dumpster_permits
            WHERE issue_date > (SELECT max(issue_date) FROM dumpster_permits) - INTERVAL 365 DAY
        """).fetchone()[0]
        or 0.0,
        4,
    )
    return out


def measure_vendors(con) -> dict[str, dict]:
    """Chicago businesses Overture lists in each vendor group, and how many show a phone, email or website."""
    out = {}
    for key, (label, rx) in VENDORS.items():
        n, phone, email, site = con.execute(
            """
            SELECT count(*), count(*) FILTER (WHERE len(phones) > 0), count(*) FILTER (WHERE len(emails) > 0),
                count(*) FILTER (WHERE len(websites) > 0)
            FROM places
            WHERE in_chicago AND status IS DISTINCT FROM 'permanently_closed'
              AND list_bool_or(list_transform(list_prepend(category, coalesce(categories, [])),
                                              lambda c: regexp_matches(coalesce(c, ''), ?)))
        """,
            [rx],
        ).fetchone()
        out[key] = {
            "label": label,
            "companies": n,
            "withPhone": phone,
            "withEmail": email,
            "withWebsite": site,
        }
    return out


def measure_volumes(con, snap: dict | None) -> dict[str, int | None]:
    out: dict[str, int | None] = {k: con.execute(q).fetchone()[0] for k, q in VOLUME_SQL.items()}
    leads = (snap or {}).get("leads", [])
    for kind, key in (
        ("investor_purchase", "investor"),
        ("violation", "violation"),
        ("closed_restaurant", "closed_restaurant"),
    ):
        out[key] = sum(1 for x in leads if x["kind"] == kind) if snap else None
    out["new_business"] = ((snap or {}).get("commercial", {}).get("newBusiness", {}) or {}).get("spacesTotal")
    return out


def build(con, snap: dict | None) -> dict:
    vendors = measure_vendors(con)
    incumbents = measure_incumbents(con)
    volumes = measure_volumes(con, snap)
    as_of = con.execute("SELECT max(issue_date) FROM permits").fetchone()[0].isoformat()
    lifecycles = []
    for lc in LIFECYCLES:
        lifecycles.append(
            {
                "id": lc.id,
                "family": lc.family,
                "name": lc.name,
                "story": lc.story,
                "trigger": lc.trigger,
                "source": lc.source,
                "volume12m": volumes.get(lc.volume) if lc.volume else None,
                "volumeNote": VOLUME_NOTE.get(lc.volume or ""),
                "notice": lc.notice,
                "buyer": lc.buyer,
                "reach": lc.reach,
                "appLink": lc.app_link,
                "tags": list(lc.tags),
                "stages": [
                    {
                        "name": st.name,
                        "when": st.when,
                        "offsetDays": list(STAGE_OFFSETS[(lc.id, st.name)])
                        if (lc.id, st.name) in STAGE_OFFSETS
                        else None,
                        "services": [
                            {
                                "name": sv.name,
                                "vendor": sv.vendor,
                                "incumbent": sv.incumbent,
                                "incumbentShare": incumbents.get(sv.metric) if sv.metric else None,
                            }
                            for sv in st.services
                        ],
                    }
                    for st in lc.stages
                ],
            }
        )
    return {"asOf": as_of, "vendors": vendors, "incumbents": incumbents, "lifecycles": lifecycles}


def render(data: dict) -> str:
    v = data["vendors"]
    lines = [
        f"# Opportunity lifecycles ({data['asOf']})",
        "",
        "Generated by `uv run python -m engine.leads.lifecycles`. Volumes are the last 365 days of each trigger's "
        "source; vendor counts are Chicago businesses in matching Overture categories (open, not permanently "
        "closed); incumbent shares are the share of permits in the last 730 days that name a company in that role.",
        "",
        "| Lifecycle | Family | Triggers (12 months) | Notice | Stages | Services |",
        "| --- | --- | ---: | --- | ---: | ---: |",
    ]
    for lc in data["lifecycles"]:
        vol = f"{lc['volume12m']:,}" if isinstance(lc["volume12m"], int) else "—"
        n_services = sum(len(s["services"]) for s in lc["stages"])
        lines.append(
            f"| {lc['name']} | {lc['family']} | {vol} | {lc['notice']} | {len(lc['stages'])} | {n_services} |"
        )
    lines += ["", "## Vendors by service group (Chicago, Overture)", "",
              "| Group | Companies | With phone | With email | With website |", "| --- | ---: | ---: | ---: | ---: |"]  # fmt: skip
    for key in sorted(v, key=lambda k: -v[k]["companies"]):
        x = v[key]
        lines.append(
            f"| {x['label']} | {x['companies']:,} | {x['withPhone']:,} | {x['withEmail']:,} | {x['withWebsite']:,} |"
        )
    lines += ["", "## Who already covers the job (share of permits naming a company, last 730 days)", "",
              "| Permit group | " + " | ".join(ROLES) + " |", "| --- |" + " ---: |" * len(ROLES)]  # fmt: skip
    for group in ROLE_PERMIT_TYPES:
        lines.append(
            f"| {group} | "
            + " | ".join(f"{data['incumbents'][f'{group}:{r}'] * 100:.0f}%" for r in ROLES)
            + " |"
        )
    lines += [
        f"\nDumpster permits naming the hauler (last 365 days): {data['incumbents']['dumpster:hauler'] * 100:.0f}%.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    con = db.connect()
    snap = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else None
    data = build(con, snap)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n")
    FINDINGS.mkdir(parents=True, exist_ok=True)
    path = FINDINGS / f"lifecycles-{data['asOf']}.md"
    path.write_text(render(data))
    total_services = sum(len(s["services"]) for lc in data["lifecycles"] for s in lc["stages"])
    print(f"wrote {args.out} and {path}: {len(data['lifecycles'])} lifecycles, {total_services} services")
    for lc in data["lifecycles"]:
        print(f"  {lc['id']:<24} {lc['volume12m']!s:>8}  {lc['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
