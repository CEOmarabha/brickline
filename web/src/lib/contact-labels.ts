import type { ContactSource } from "@/lib/contacts";

export const CONTACT_SOURCE_LABEL: Record<ContactSource, string> = {
  overture: "Overture Maps",
  chicago_business_licenses: "Chicago business licenses",
  company_website: "Company website",
  cdb_vendors: "Illinois CDB vendor list",
  idph_lead_contractors: "IDPH lead contractor registry",
  idph_asbestos_contractors: "IDPH asbestos contractor registry",
  foreclosed_rental_registry: "Chicago foreclosed rental registry",
  overture_at_mailing_address: "Overture Maps, listed at the mailing address",
};

export const CONFIDENCE_LABEL = { high: "High match", medium: "Medium match" } as const;
