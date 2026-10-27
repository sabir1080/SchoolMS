"use client";

import { useEffect, useState } from "react";

import { api } from "./api";
import type { Brand } from "./brand";

export interface InstituteDetails {
  name: string;
  address: string;
  phone: string;
  email: string;
  logo?: string;
  brand?: Brand;
}

/** The institute's address, phone and logo for printed documents (admins only). */
export function useInstitute() {
  const [details, setDetails] = useState<InstituteDetails | null>(null);
  useEffect(() => {
    api<InstituteDetails>("/api/institute/settings/")
      .then((data) => setDetails({ ...data, logo: data.brand?.logo }))
      .catch(() => setDetails(null));
  }, []);
  return details;
}
