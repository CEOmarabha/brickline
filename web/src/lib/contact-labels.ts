import type { ContactSource } from "@/lib/contacts";

export const CONTACT_SOURCE_LABEL: Record<ContactSource, string> = {
  overture: "Overture Maps",
  chicago_business_licenses: "Chicago business licenses",
  company_website: "Company website",
};

export const CONFIDENCE_LABEL = { high: "High match", medium: "Medium match" } as const;
