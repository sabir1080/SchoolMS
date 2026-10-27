"use client";

import { useEffect, useState } from "react";

import { api } from "./api";

export interface InstituteDetails {
  name: string;
  address: string;
  phone: string;
  email: string;
  logo?: string;
}

/** The institute's address, phone and logo for printed documents (admins only). */
export function useInstitute() {
  const [details, setDetails] = useState<InstituteDetails | null>(null);
  useEffect(() => {
    api<InstituteDetails>("/api/institute/settings/").then(setDetails).catch(() => setDetails(null));
  }, []);
  return details;
}
